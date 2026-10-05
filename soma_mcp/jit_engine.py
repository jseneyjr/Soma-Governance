#!/usr/bin/env python3
"""JIT Cell Expression Engine — Soma v0.30

Implements just-in-time governance delivery based on context engineering research:
- Gloaguen et al. (2026): Static context files don't improve task success
- ACE (2025): Evolving, curated context improves agent performance by 10%+

Instead of dumping all rules into the system prompt, this engine:
1. Reads the current git diff to identify changed files
2. Matches cells by target_paths (fnmatch)
3. Ranks by Bayesian fitness score (highest first)
4. Returns only the top N cells (default: 3) with full guidance text
5. Includes relevant non-standard genome rules

Dependency policy: pyyaml is OPTIONAL here. soma_mcp/ must import and run on a
bare interpreter (see .soma/cells/walls/wall-mcp-zero-deps.md), so frontmatter
falls back to a stdlib parser covering the YAML subset the cells actually use.
"""
from __future__ import annotations

import os
import sys
import glob
import re
import subprocess
import fnmatch

from soma_mcp.cell_cache import CellCache

# Module-level singleton — persists across MCP tool invocations
_cell_cache = CellCache()

# pyyaml is an OPTIONAL dependency. When it is missing we parse the frontmatter
# subset used by cells with the stdlib parser below instead of failing to import.
try:
    import yaml
except ImportError:
    yaml = None


# Ensure parent dir is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def warn(message: str) -> None:
    """Emit a diagnostic on STDERR.

    stdout is the JSON-RPC transport — never write diagnostics there.
    """
    try:
        print(f"[soma-mcp] {message}", file=sys.stderr, flush=True)
    except Exception:
        pass


from soma_core.frontmatter import (
    FrontmatterError,
    parse_yaml_subset,
    parse_frontmatter,
    _parse_frontmatter,
    _get_body,
)



def get_git_diff_files(workspace: str) -> list[str]:
    """Get files changed in the current working tree + staged."""
    files = set()
    for cmd in [['git', 'diff', '--name-only'],
                ['git', 'diff', '--name-only', '--cached']]:
        try:
            output = subprocess.check_output(
                cmd, cwd=workspace, text=True, stderr=subprocess.DEVNULL,
                timeout=10,
            ).strip()
            if output:
                files.update(f for f in output.splitlines() if f)
        except Exception:
            pass
    return list(files)


def load_all_cells(workspace: str) -> list[dict[str, object]]:
    """Load all cells from .soma/cells/ using stdlib parser."""
    cells = []
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return cells

    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md':
            continue
        rel = os.path.relpath(cell_file, workspace)
        try:
            with open(cell_file, encoding="utf-8") as f:
                content = f.read()
            fm = parse_frontmatter(content)
            if fm is None:
                warn(f'skipped cell {rel}: malformed YAML frontmatter')
                continue
            if not fm:
                warn(f'skipped cell {rel}: no frontmatter metadata')
                continue
            # Skip expired cells (pruned by cell_expiry --prune)
            if fm.get('expired_at'):
                continue
            fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
            fm['_path'] = rel
            fm['_body'] = _get_body(content)
            fm['_full'] = content
            cells.append(fm)
        except Exception as e:
            warn(f'skipped cell {rel}: {e.__class__.__name__}: {e}')
    return cells


def match_cells_to_files(cells: list[dict[str, object]], changed_files: list[str]) -> list[dict[str, object]]:
    """Match cells to changed files by target_paths (fnmatch)."""
    matched = []
    for cell in cells:
        target_paths = cell.get('target_paths', [])
        if not target_paths:
            continue
        if isinstance(target_paths, str):
            target_paths = [target_paths]

        is_match = False
        matched_files = []
        for changed in changed_files:
            for pattern in target_paths:
                if fnmatch.fnmatch(changed, pattern) or fnmatch.fnmatch(os.path.basename(changed), pattern):
                    is_match = True
                    matched_files.append(changed)
                    break

        if is_match:
            cell_copy = cell.copy()
            cell_copy['_matched_files'] = list(set(matched_files))
            matched.append(cell_copy)

    return matched


def get_fitness_score(cell: dict[str, object]) -> float:
    """Extract fitness score from cell.

    INTENTIONAL DUPLICATION: wall-mcp-zero-deps prohibits importing from enzymes/
    Canonical source: enzymes/bayesian_score.py — keep in sync manually
    """
    fitness = cell.get('fitness', '')
    impact_weight = cell.get('impact_weight', 1.0)
    try:
        impact_weight = float(impact_weight)
    except (ValueError, TypeError):
        impact_weight = 1.0

    if isinstance(fitness, dict):
        score = fitness.get('score')
        # Compute from tp/triggers if available
        tp = fitness.get('true_positives', 0)
        triggers = fitness.get('triggers', 0)
        try:
            tp, triggers = int(tp), int(triggers)
            if triggers > 0:
                return ((tp + 1) / (triggers + 2)) * impact_weight
        except (ValueError, TypeError):
            pass
        if score is not None:
            try:
                return float(score) * impact_weight
            except (ValueError, TypeError):
                pass

    triggers = cell.get('triggers', '0')
    tp = cell.get('true_positives', '0')
    try:
        tp_int = int(tp)
        triggers_int = int(triggers)
        if triggers_int > 0:
            return ((tp_int + 1) / (triggers_int + 2)) * impact_weight
    except (ValueError, TypeError):
        pass
    return 0.5 * impact_weight


def rank_cells(matched_cells: list[dict[str, object]]) -> list[dict[str, object]]:
    """Rank matched cells by fitness score (highest first), with diversity bonus."""
    for cell in matched_cells:
        cell['_fitness_score'] = get_fitness_score(cell)

    # Sort by fitness (descending), then by match count (descending)
    return sorted(
        matched_cells,
        key=lambda c: (c['_fitness_score'], len(c.get('_matched_files', []))),
        reverse=True
    )


def ensure_type_diversity(ranked_cells: list[dict[str, object]], budget: int) -> list[dict[str, object]]:
    """Ensure we don't load N cells of the same type. Prefer diversity."""
    selected = []
    seen_types = set()

    # First pass: one of each type
    for cell in ranked_cells:
        ctype = cell.get('type', 'unknown')
        if ctype not in seen_types and len(selected) < budget:
            selected.append(cell)
            seen_types.add(ctype)

    # Second pass: fill remaining budget
    for cell in ranked_cells:
        if cell not in selected and len(selected) < budget:
            selected.append(cell)

    return selected


def format_cell_guidance(cell: dict[str, object]) -> dict[str, object]:
    """Format a cell into actionable, concise guidance text."""
    ctype = cell.get('type', 'unknown')
    hypothesis = cell.get('hypothesis', '')
    prediction = cell.get('prediction', '')
    body = cell.get('_body', '')
    name = cell.get('_name', '')
    matched = cell.get('_matched_files', [])
    fitness = cell.get('_fitness_score', 0)

    type_emoji = {
        'wall': '🧱',
        'vacuole': '🧫',
        'membrane': '🔬',
        'chloroplast': '🌿',
        'plasmodesmata': '🔗'
    }.get(ctype, '📋')

    type_label = {
        'wall': 'INVARIANT (must not violate)',
        'vacuole': 'ANTI-PATTERN TRAP (watch out)',
        'membrane': 'ESCALATION GATE (needs review)',
        'chloroplast': 'BEST PRACTICE (follow this pattern)',
        'plasmodesmata': 'CONTRACT (cross-service agreement)'
    }.get(ctype, ctype.upper())

    guidance = f"{type_emoji} [{type_label}] {name}\n"
    guidance += f"   Hypothesis: {hypothesis}\n"
    if prediction:
        guidance += f"   If violated: {prediction}\n"
    if matched:
        guidance += f"   Triggered by: {', '.join(matched[:5])}\n"
    if body:
        # Truncate body to keep context tight
        body_lines = body.strip().split('\n')[:8]
        guidance += f"   Detail: {' '.join(line.strip() for line in body_lines)[:300]}\n"
    guidance += f"   Fitness: {fitness:.2f}\n"

    return {
        'name': name,
        '_path': cell.get('_path', ''),
        'type': ctype,
        'enforcement': type_label,
        'hypothesis': hypothesis,
        'prediction': prediction,
        'matched_files': matched,
        'fitness': fitness,
        'guidance': guidance,
        'body': body[:500] if body else ''
    }


def load_genome_rules(workspace: str, changed_files: list[str]) -> list[dict[str, str]]:
    """Load genome rules marked as non_standard that match changed files."""
    genome_dir = os.path.join(workspace, 'genome')
    if not os.path.isdir(genome_dir):
        return []

    relevant = []
    for rule_file in sorted(glob.glob(os.path.join(genome_dir, '*.md'))):
        rel = os.path.relpath(rule_file, workspace)
        try:
            with open(rule_file, encoding="utf-8") as f:
                content = f.read()
            fm = parse_frontmatter(content)
            if fm is None:
                warn(f'skipped genome rule {rel}: malformed YAML frontmatter')
                continue
            # Only include non-standard rules
            non_standard = fm.get('non_standard', 'false')
            if str(non_standard).lower() not in ('true', 'yes', '1'):
                continue
            # Include if it has target_paths matching, or if it has no target_paths (global)
            target_paths = fm.get('target_paths', [])
            if isinstance(target_paths, str):
                target_paths = [target_paths]
            if not target_paths:
                # Global non-standard rule — always include
                body = _get_body(content)
                relevant.append({
                    'name': os.path.splitext(os.path.basename(rule_file))[0],
                    'body': body[:500] if body else '',
                    'category': fm.get('category', 'general')
                })
            else:
                # Check if any changed files match
                for changed in changed_files:
                    for pattern in target_paths:
                        if fnmatch.fnmatch(changed, pattern):
                            body = _get_body(content)
                            relevant.append({
                                'name': os.path.splitext(os.path.basename(rule_file))[0],
                                'body': body[:500] if body else '',
                                'category': fm.get('category', 'general')
                            })
                            break
                    else:
                        continue
                    break
        except Exception as e:
            warn(f'skipped genome rule {rel}: {e.__class__.__name__}: {e}')
    return relevant


def express(workspace: str, changed_files: list[str] | None = None, budget: int | None = None) -> dict[str, object]:
    """Main JIT expression function.

    Returns the minimum effective governance context for the current change.
    """
    if budget is None:
        budget = int(os.environ.get('SOMA_CONTEXT_BUDGET', '3'))

    if not changed_files:
        changed_files = get_git_diff_files(workspace)

    if not changed_files:
        return {
            'relevant_cells': [],
            'genome_guidance': [],
            'context': 'No changed files detected. Governance guidance will be provided when files are modified.',
            'stats': {'total_cells': 0, 'matched': 0, 'expressed': 0}
        }

    # Load and match cells
    all_cells = _cell_cache.get_cells(workspace)
    matched = match_cells_to_files(all_cells, changed_files)

    # Score ALL matched cells first (fixes C3: mandatory cells displaying Fitness: 0.00)
    for cell in matched:
        cell['_fitness_score'] = get_fitness_score(cell)

    # Apply hot zone boost from bug registry (v0.85 antifragile loop)
    try:
        from soma_sdk.hot_zones import compute_cell_boost, load_report_from_workspace
        hz_report = load_report_from_workspace(workspace)
        if hz_report and (hz_report.active_file_zones or hz_report.active_pattern_zones):
            for cell in matched:
                fitness = cell.get('fitness', {})
                tp = int(fitness.get('true_positives', 0)) if isinstance(fitness, dict) else 0
                fp = int(fitness.get('false_positives', 0)) if isinstance(fitness, dict) else 0
                outcome_count = tp + fp
                boost = compute_cell_boost(cell, hz_report, outcome_count)
                if boost > 0:
                    cell['_fitness_score'] *= (1 + boost)
                    cell['_hot_zone_boost'] = boost
    except ImportError:
        pass  # Graceful degradation

    # Stage 0: Mandatory invariants — walls and gate-tier cells always load
    mandatory = []
    candidates = []
    for cell in matched:
        cell_type = cell.get('type', 'vacuole')
        enforcement = cell.get('enforcement', 'advisory')
        if cell_type == 'wall' or enforcement == 'gate':
            mandatory.append(cell)
        else:
            candidates.append(cell)

    # Stage 1-2: Rank and diversify remaining candidates within leftover budget
    remaining_budget = max(0, budget - len(mandatory))
    ranked = rank_cells(candidates)
    selected_candidates = ensure_type_diversity(ranked, remaining_budget)

    # Combine: mandatory first, then ranked candidates
    selected = mandatory + selected_candidates

    # Format guidance
    cell_guidance = [format_cell_guidance(c) for c in selected]

    # Load matching non-standard genome rules
    genome_rules = load_genome_rules(workspace, changed_files)

    # Build the combined guidance text
    guidance_parts = []
    if cell_guidance:
        guidance_parts.append("## Active Governance Cells\n")
        for cg in cell_guidance:
            guidance_parts.append(cg['guidance'])

    if genome_rules:
        guidance_parts.append("\n## Project-Specific Rules\n")
        for rule in genome_rules:
            guidance_parts.append(f"### {rule['name']}\n{rule['body']}\n")

    combined = '\n'.join(guidance_parts) if guidance_parts else 'No governance cells match your current changes.'

    return {
        'relevant_cells': cell_guidance,
        'genome_guidance': genome_rules,
        'context': combined,
        'stats': {
            'total_cells': len(all_cells),
            'matched': len(matched),
            'expressed': len(selected),
            'budget': budget,
            'changed_files': len(changed_files)
        }
    }
