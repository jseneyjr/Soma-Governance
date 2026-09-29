#!/usr/bin/env python3
"""JIT Cell Expression Engine — Soma v0.23

Implements just-in-time governance delivery based on context engineering research:
- Gloaguen et al. (2026): Static context files don't improve task success
- ACE (2025): Evolving, curated context improves agent performance by 10%+

Instead of dumping all rules into the system prompt, this engine:
1. Reads the current git diff to identify changed files
2. Matches cells by target_paths (fnmatch)
3. Ranks by Bayesian fitness score (highest first)
4. Returns only the top N cells (default: 3) with full guidance text
5. Includes relevant non-standard genome rules
"""

import os
import sys
import glob
import json
import re
import subprocess
import fnmatch

# Ensure parent dir is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse_frontmatter_stdlib(content):
    """Parse YAML frontmatter using only stdlib (no pyyaml required).

    Handles simple key: value pairs, inline lists, and block lists.
    """
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    result = {}
    current_key = None
    current_list = None
    for line in fm_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # List item under a key
        if stripped.startswith('- ') and current_key and current_list is not None:
            val = stripped[2:].strip().strip('"').strip("'")
            current_list.append(val)
            result[current_key] = current_list
            continue
        # Inline list: key: [val1, val2]
        m = re.match(r'^(\w[\w_-]*)\s*:\s*\[(.+)\]$', stripped)
        if m:
            current_key = m.group(1)
            vals = [v.strip().strip('"').strip("'") for v in m.group(2).split(',')]
            result[current_key] = vals
            current_list = None
            continue
        # Key: value
        m = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)$', stripped)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            if val == '':
                current_list = []
            else:
                result[current_key] = val
                current_list = None
            continue
    return result


def _get_body(content):
    """Extract the body text after YAML frontmatter."""
    if not content.startswith('---'):
        return content
    end = content.find('---', 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


def get_git_diff_files(workspace):
    """Get files changed in the current working tree + staged."""
    files = set()
    for cmd in ['git diff --name-only HEAD', 'git diff --name-only --cached',
                'git diff --name-only HEAD~1..HEAD']:
        try:
            output = subprocess.check_output(
                cmd, shell=True, cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if output:
                files.update(f for f in output.split('\n') if f)
        except Exception:
            pass
    return list(files)


def load_all_cells(workspace):
    """Load all cells from .soma/cells/ using stdlib parser."""
    cells = []
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return cells

    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md':
            continue
        try:
            with open(cell_file) as f:
                content = f.read()
            fm = _parse_frontmatter_stdlib(content)
            if fm:
                fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
                fm['_path'] = os.path.relpath(cell_file, workspace)
                fm['_body'] = _get_body(content)
                fm['_full'] = content
                cells.append(fm)
        except Exception:
            pass
    return cells


def match_cells_to_files(cells, changed_files):
    """Match cells to changed files by target_paths (fnmatch)."""
    matched = []
    for cell in cells:
        target_paths = cell.get('target_paths', [])
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
            cell['_matched_files'] = list(set(matched_files))
            matched.append(cell)

    return matched


def get_fitness_score(cell):
    """Extract fitness score from cell, with Bayesian fallback."""
    fitness = cell.get('fitness', '')
    if isinstance(fitness, dict):
        score = fitness.get('score')
        if score is not None:
            try:
                return float(score)
            except (ValueError, TypeError):
                pass
        # Compute from tp/fp if available
        tp = fitness.get('true_positives', 0)
        fp = fitness.get('false_positives', 0)
        try:
            tp, fp = int(tp), int(fp)
            if tp + fp > 0:
                return tp / (tp + fp)
        except (ValueError, TypeError):
            pass
    # Parse from string (stdlib parser gives us strings)
    triggers = cell.get('triggers', '0')
    tp = cell.get('true_positives', '0')
    fp = cell.get('false_positives', '0')
    try:
        tp_int = int(tp)
        fp_int = int(fp)
        if tp_int + fp_int > 0:
            return tp_int / (tp_int + fp_int)
    except (ValueError, TypeError):
        pass
    return 0.5  # Uninformative prior for new cells


def rank_cells(matched_cells):
    """Rank matched cells by fitness score (highest first), with diversity bonus."""
    for cell in matched_cells:
        cell['_fitness_score'] = get_fitness_score(cell)

    # Sort by fitness (descending), then by match count (descending)
    return sorted(
        matched_cells,
        key=lambda c: (c['_fitness_score'], len(c.get('_matched_files', []))),
        reverse=True
    )


def ensure_type_diversity(ranked_cells, budget):
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


def format_cell_guidance(cell):
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


def load_genome_rules(workspace, changed_files):
    """Load genome rules marked as non_standard that match changed files."""
    genome_dir = os.path.join(workspace, 'genome')
    if not os.path.isdir(genome_dir):
        return []

    relevant = []
    for rule_file in sorted(glob.glob(os.path.join(genome_dir, '*.md'))):
        try:
            with open(rule_file) as f:
                content = f.read()
            fm = _parse_frontmatter_stdlib(content)
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
        except Exception:
            pass
    return relevant


def express(workspace, changed_files=None, budget=None):
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
    all_cells = load_all_cells(workspace)
    matched = match_cells_to_files(all_cells, changed_files)
    ranked = rank_cells(matched)
    selected = ensure_type_diversity(ranked, budget)

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
