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


# ── Stdlib YAML-subset frontmatter parser ─────────────────────────────
# Supports exactly what governance cells and genome rules use:
#   scalars (quoted/plain strings, ints, floats, bools, null)
#   nested block mappings   (fitness:/lineage: + indented keys)
#   block sequences         (target_paths:\n  - "enzymes/*.sh")
#   flow collections        (tags: [a, b] / {k: v})
# Anything outside that subset raises FrontmatterError so the caller can report
# a *skipped* cell instead of silently acting on a half-parsed one.

class FrontmatterError(ValueError):
    """Frontmatter could not be parsed by the stdlib subset parser."""


_BOOL_TRUE = frozenset(('true', 'yes', 'on'))
_BOOL_FALSE = frozenset(('false', 'no', 'off'))
_NULL_VALUES = frozenset(('', '~', 'null'))
_INT_RE = re.compile(r'^[-+]?[0-9]+$')
# Mirrors pyyaml's YAML 1.1 float resolver: the mantissa needs a '.' and an
# exponent needs an explicit sign, so '1e3' and '1.5e3' stay strings.
_FLOAT_RE = re.compile(
    r'^[-+]?(?:[0-9]+\.[0-9]*(?:[eE][-+][0-9]+)?|\.[0-9]+(?:[eE][-+][0-9]+)?)$'
)
_SEQ_MAPPING_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.\-]*:(?:\s|$)')
# Indicators pyyaml rejects outright ('%', '@', '`', '!', '*') plus constructs we
# cannot honour without a real YAML engine ('|', '>' block scalars, '&' anchors).
# Refusing beats returning the raw text as a string and acting on wrong data.
_UNSUPPORTED_PREFIXES = ('|', '>', '&', '*', '!', '%', '@', '`')
_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0',
            '"': '"', '\\': '\\', '/': '/', "'": "'"}


def _skip_ws(text, i):
    while i < len(text) and text[i] in ' \t':
        i += 1
    return i


def _unescape_double(body):
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == '\\' and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_ESCAPES.get(nxt, '\\' + nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _read_token(text, i, stops):
    """Read a raw token until an unquoted char in `stops`. Returns (token, i).

    As in YAML, a quote is only special at the start of a token, so plain values
    containing an apostrophe (``shouldn't``) are read as-is.
    """
    start = i
    quote = None
    while i < len(text):
        ch = text[i]
        if quote:
            if quote == '"' and ch == '\\' and i + 1 < len(text):
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ('"', "'") and i == start:
            quote = ch
            i += 1
            continue
        if ch in stops:
            break
        i += 1
    if quote:
        raise FrontmatterError('unterminated quoted string')
    return text[start:i], i


def _strip_comment(line):
    """Drop a trailing ` #` comment that is not inside quotes."""
    out = []
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if quote == '"' and ch == '\\' and i + 1 < len(line):
                out.append(line[i:i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
            out.append(ch)
        elif ch in ('"', "'"):
            quote = ch
            out.append(ch)
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            break
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


def _parse_scalar(raw):
    """Convert a raw scalar token to a Python value."""
    text = raw.strip()
    if text[:1] in ('"', "'"):
        if len(text) < 2 or text[-1] != text[0]:
            # pyyaml raises here too; refusing beats returning a mangled string.
            raise FrontmatterError(f'unterminated quoted scalar: {text[:24]!r}')
        body = text[1:-1]
        return _unescape_double(body) if text[0] == '"' else body.replace("''", "'")
    if text[:1] in ('[', '{'):
        value, idx = _parse_flow(text, 0)
        if text[idx:].strip():
            raise FrontmatterError(f'trailing content after flow collection: {text[idx:][:20]!r}')
        return value
    lowered = text.lower()
    if lowered in _NULL_VALUES:
        return None
    if lowered in _BOOL_TRUE:
        return True
    if lowered in _BOOL_FALSE:
        return False
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    if text[:1] in _UNSUPPORTED_PREFIXES:
        raise FrontmatterError(f'unsupported YAML construct: {text[:24]!r}')
    return text


def _parse_flow(text, i):
    """Parse a flow node ([...], {...} or scalar). Returns (value, i)."""
    i = _skip_ws(text, i)
    if i >= len(text):
        raise FrontmatterError('unexpected end of flow collection')
    if text[i] == '[':
        return _parse_flow_seq(text, i)
    if text[i] == '{':
        return _parse_flow_map(text, i)
    raw, i = _read_token(text, i, ',]}')
    if not raw.strip():
        raise FrontmatterError('empty entry in flow collection')
    return _parse_scalar(raw), i


def _parse_flow_seq(text, i):
    items = []
    i = _skip_ws(text, i + 1)
    if i < len(text) and text[i] == ']':
        return items, i + 1
    while True:
        value, i = _parse_flow(text, i)
        items.append(value)
        i = _skip_ws(text, i)
        if i >= len(text):
            raise FrontmatterError('unterminated flow sequence')
        if text[i] == ']':
            return items, i + 1
        if text[i] != ',':
            raise FrontmatterError(f'malformed flow sequence near {text[i:i + 12]!r}')
        i = _skip_ws(text, i + 1)
        if i < len(text) and text[i] == ']':  # tolerate a trailing comma
            return items, i + 1


def _parse_flow_map(text, i):
    mapping = {}
    i = _skip_ws(text, i + 1)
    if i < len(text) and text[i] == '}':
        return mapping, i + 1
    while True:
        raw_key, i = _read_token(text, i, ':,}')
        if i >= len(text) or text[i] != ':':
            raise FrontmatterError('flow mapping entry is missing ":"')
        if not raw_key.strip():
            raise FrontmatterError('flow mapping entry is missing a key')
        value, i = _parse_flow(text, i + 1)
        mapping[str(_parse_scalar(raw_key))] = value
        i = _skip_ws(text, i)
        if i >= len(text):
            raise FrontmatterError('unterminated flow mapping')
        if text[i] == '}':
            return mapping, i + 1
        if text[i] != ',':
            raise FrontmatterError(f'malformed flow mapping near {text[i:i + 12]!r}')
        i = _skip_ws(text, i + 1)
        if i < len(text) and text[i] == '}':  # tolerate a trailing comma
            return mapping, i + 1


def _prepare_lines(text):
    """Strip comments/blanks. Returns [(indent, content, lineno), ...]."""
    prepared = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        leading = raw[:len(raw) - len(raw.lstrip(' \t'))]
        if '\t' in leading:
            raise FrontmatterError(f'line {lineno}: tab indentation is not supported')
        line = _strip_comment(raw)
        if not line.strip():
            continue
        prepared.append((len(line) - len(line.lstrip(' ')), line.strip(), lineno))
    return prepared


def _parse_collection(lines, start, indent):
    content = lines[start][1]
    if content == '-' or content.startswith('- '):
        return _parse_block_seq(lines, start, indent)
    return _parse_block_map(lines, start, indent)


def _parse_block_map(lines, start, indent):
    mapping = {}
    i = start
    while i < len(lines):
        line_indent, content, lineno = lines[i]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise FrontmatterError(f'line {lineno}: unexpected indentation')
        if content == '-' or content.startswith('- '):
            raise FrontmatterError(f'line {lineno}: unexpected sequence item inside a mapping')
        raw_key, idx = _read_token(content, 0, ':')
        if idx >= len(content) or content[idx] != ':':
            raise FrontmatterError(f'line {lineno}: expected "key: value"')
        if not raw_key.strip():
            raise FrontmatterError(f'line {lineno}: missing key')
        key = str(_parse_scalar(raw_key))
        rest = content[idx + 1:].strip()
        if rest:
            mapping[key] = _parse_scalar(rest)
            i += 1
            continue
        # Empty inline value: either a nested block below, or a null scalar.
        if i + 1 < len(lines) and lines[i + 1][0] > indent:
            mapping[key], i = _parse_collection(lines, i + 1, lines[i + 1][0])
        else:
            mapping[key] = None
            i += 1
    return mapping, i


def _parse_block_seq(lines, start, indent):
    items = []
    i = start
    while i < len(lines):
        line_indent, content, lineno = lines[i]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise FrontmatterError(f'line {lineno}: unexpected indentation in sequence')
        if not (content == '-' or content.startswith('- ')):
            break
        body = content[1:].strip()
        if not body:
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                value, i = _parse_collection(lines, i + 1, lines[i + 1][0])
                items.append(value)
            else:
                items.append(None)
                i += 1
            continue
        if _SEQ_MAPPING_RE.match(body):
            raise FrontmatterError(
                f'line {lineno}: sequences of mappings are outside the stdlib parser subset'
            )
        items.append(_parse_scalar(body))
        i += 1
    return items, i


def parse_yaml_subset(text: str) -> dict[str, object]:
    """Parse the YAML subset used by cells. Raises FrontmatterError otherwise."""
    lines = _prepare_lines(text)
    if not lines:
        return {}
    value, idx = _parse_collection(lines, 0, lines[0][0])
    if idx != len(lines):
        raise FrontmatterError(f'line {lines[idx][2]}: unparsed content')
    return value


def parse_frontmatter(content: str) -> dict[str, object] | None:
    """Parse YAML frontmatter from a cell/genome markdown file.

    Returns a dict on success, {} when there is no frontmatter (or it is
    empty), and None when frontmatter is present but cannot be parsed. The
    None-vs-{} distinction matters: callers must be able to tell "this file has
    no metadata" from "this file's metadata is broken and the cell was skipped".
    """
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return None  # opened frontmatter that is never closed
    fm_text = content[3:end].strip()
    if not fm_text:
        return {}

    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text)
        except Exception:
            return None
    else:
        try:
            data = parse_yaml_subset(fm_text)
        except FrontmatterError:
            return None
        except Exception:
            return None

    if data is None:
        return {}
    if not isinstance(data, dict):
        return None  # frontmatter must be a mapping
    return data


# Backwards-compatible private alias for in-module/legacy call sites.
_parse_frontmatter = parse_frontmatter


def _get_body(content):
    """Extract the body text after YAML frontmatter."""
    if not content.startswith('---'):
        return content
    end = content.find('---', 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


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
            cell['_matched_files'] = list(set(matched_files))
            matched.append(cell)

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
