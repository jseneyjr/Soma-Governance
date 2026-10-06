"""Frontmatter parsing utilities for Soma cells and genome rules.

Shared core module providing stdlib-fallback YAML frontmatter parsing with
zero required external dependencies.
"""
from __future__ import annotations

import os
import re

# ── Stdlib YAML-subset frontmatter parser ─────────────────────────────
# Supports exactly what governance cells and genome rules use:
#   scalars (quoted/plain strings, ints, floats, bools, null)
#   nested block mappings   (fitness:/lineage: + indented keys)
#   block sequences         (target_paths:\n  - "enzymes/*.sh")
#   flow collections        (tags: [a, b] / {k: v})
#   block scalars           (|, > with chomping indicators)
#   wrapped plain scalars   (multiline continuation lines)
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
# cannot honour without a real YAML engine ('&' anchors).
_UNSUPPORTED_PREFIXES = ('&', '*', '!', '%', '@', '`')
_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0',
            '"': '"', '\\': '\\', '/': '/', "'": "'", ' ': ' '}


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
            if nxt == 'u' and i + 5 < len(body):
                try:
                    code = int(body[i + 2:i + 6], 16)
                    out.append(chr(code))
                    i += 6
                    continue
                except ValueError:
                    pass
            if nxt == '\n':
                i += 2
                while i < len(body) and body[i] in ' \t':
                    i += 1
                continue
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


def _parse_block_scalar(lines, start, parent_indent, style):
    """Parse block scalar (| or >) lines with chomping indicators."""
    scalar_lines = []
    i = start
    while i < len(lines):
        line_indent, content, lineno = lines[i]
        if line_indent <= parent_indent:
            break
        scalar_lines.append(content)
        i += 1
    if style.startswith('|'):
        res = '\n'.join(scalar_lines)
    else:
        res = ' '.join(scalar_lines)
    if style.endswith('-'):
        res = res.rstrip('\n')
    elif not res.endswith('\n'):
        res = res + '\n'
    return res, i


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

        # Block scalar (| or >)
        if rest in ('|', '|-', '|+', '>', '>-', '>+'):
            mapping[key], i = _parse_block_scalar(lines, i + 1, indent, rest)
            continue

        if rest:
            # Check if rest is a quoted string that wraps across lines
            if rest[:1] in ('"', "'"):
                quote_char = rest[0]
                j = i
                accum = rest
                while not (len(accum) >= 2 and accum.endswith(quote_char) and not (accum.endswith('\\' + quote_char) and not accum.endswith('\\\\' + quote_char))):
                    j += 1
                    if j >= len(lines):
                        break
                    accum = accum + '\n' + lines[j][1]
                i = j + 1
                mapping[key] = _parse_scalar(accum)
                continue
            elif not rest[:1] in ('[', '{'):
                # Plain scalar: check for continuation lines indented > indent
                j = i + 1
                while j < len(lines):
                    next_indent, next_content, next_lineno = lines[j]
                    if next_indent <= indent:
                        break
                    if _SEQ_MAPPING_RE.match(next_content) or next_content.startswith('- ') or next_content == '-':
                        break
                    rest = rest + ' ' + next_content
                    j += 1
                i = j
                mapping[key] = _parse_scalar(rest)
                continue
            else:
                mapping[key] = _parse_scalar(rest)
                i += 1
                continue

        # Empty inline value:
        # Check if next line is a sequence at same indent (e.g. target_paths:\n- item)
        if i + 1 < len(lines) and lines[i + 1][0] == indent and (lines[i + 1][1] == '-' or lines[i + 1][1].startswith('- ')):
            mapping[key], i = _parse_block_seq(lines, i + 1, indent)
        elif i + 1 < len(lines) and lines[i + 1][0] > indent:
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
            item_map = {}
            k, idx = _read_token(body, 0, ':')
            v = body[idx + 1:].strip()
            item_map[str(_parse_scalar(k))] = _parse_scalar(v) if v else None
            j = i + 1
            while j < len(lines):
                ni, nc, nl = lines[j]
                if ni <= indent or nc.startswith('- ') or nc == '-':
                    break
                if ':' in nc:
                    nk, nidx = _read_token(nc, 0, ':')
                    nv = nc[nidx + 1:].strip()
                    item_map[str(_parse_scalar(nk))] = _parse_scalar(nv) if nv else None
                j += 1
            items.append(item_map)
            i = j
            continue
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
    """Parse YAML frontmatter from a cell/genome markdown file without external dependencies.

    Returns a dict on success, {} when there is no frontmatter (or it is
    empty), and None when frontmatter is present but cannot be parsed. The
    None-vs-{} distinction matters: callers must be able to tell "this file has
    no metadata" from "this file's metadata is broken and the cell was skipped".
    """
    if content.startswith('\ufeff'):
        content = content[1:]
    if not content.startswith('---'):
        return {}
    end = content.find('---', 3)
    if end == -1:
        return None  # opened frontmatter that is never closed
    fm_text = content[3:end].strip()
    if not fm_text:
        return {}

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


def dump_frontmatter(data: dict, body: str | None = None) -> str:
    """Serialize metadata dictionary to YAML frontmatter string without requiring PyYAML.

    If body is provided, returns the complete markdown document with delimiters:
        ---\\n{yaml}---\\n{body}
    If body is None, returns the YAML text only:
        {yaml}\\n
    """
    from datetime import date, datetime

    def _format_scalar(val: object) -> str:
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, (datetime, date)):
            return val.isoformat()
        s = str(val)
        if (
            not s
            or any(c in s for c in ":#{}[]|>&*!%@`,\n\"'")
            or s.strip() != s
            or s.lower() in _BOOL_TRUE
            or s.lower() in _BOOL_FALSE
            or s.lower() in _NULL_VALUES
            or _INT_RE.match(s)
            or _FLOAT_RE.match(s)
        ):
            escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        return s

    def _dump_lines(d: dict, indent: int = 0) -> list[str]:
        lines: list[str] = []
        prefix = " " * indent
        for k, v in d.items():
            key_str = str(k)
            if isinstance(v, dict):
                if not v:
                    lines.append(f"{prefix}{key_str}: {{}}")
                else:
                    lines.append(f"{prefix}{key_str}:")
                    lines.extend(_dump_lines(v, indent + 2))
            elif isinstance(v, list):
                if not v:
                    lines.append(f"{prefix}{key_str}: []")
                else:
                    lines.append(f"{prefix}{key_str}:")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"{prefix}  -")
                            lines.extend(_dump_lines(item, indent + 4))
                        else:
                            lines.append(f"{prefix}  - {_format_scalar(item)}")
            else:
                lines.append(f"{prefix}{key_str}: {_format_scalar(v)}")
        return lines

    yaml_text = "\n".join(_dump_lines(data)) + "\n"
    if body is not None:
        return f"---\n{yaml_text}---\n{body}"
    return yaml_text


def _get_body(content: str) -> str:
    """Extract the body text after YAML frontmatter."""
    if content.startswith('\ufeff'):
        content = content[1:]
    if not content.startswith('---'):
        return content
    end = content.find('---', 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


def parse_cell_frontmatter(content_or_path: str) -> tuple[dict[str, object], str]:
    """Parse a cell file or markdown content string into (frontmatter_dict, body).

    Args:
        content_or_path: Either a file path or raw markdown content string.

    Returns:
        (frontmatter_dict, body_text)

    Raises:
        FileNotFoundError: If a file path is provided but does not exist.
        ValueError: If frontmatter is missing, unclosed, or fails to parse.
    """
    if os.path.exists(content_or_path) and os.path.isfile(content_or_path):
        with open(content_or_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    else:
        content = content_or_path

    if content.startswith('\ufeff'):
        content = content[1:]
    if not content.startswith('---'):
        raise ValueError("No frontmatter delimiter")
    end = content.find('---', 3)
    if end == -1:
        raise ValueError("Unclosed frontmatter")

    fm_text = content[3:end].strip()
    if not fm_text:
        data = {}
    else:
        try:
            data = parse_yaml_subset(fm_text)
        except Exception as e:
            raise ValueError(f"Invalid YAML subset: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Frontmatter is not a mapping")

    body = content[end + 3:].lstrip('\n')
    return data, body


__all__ = [
    "FrontmatterError",
    "dump_frontmatter",
    "parse_cell_frontmatter",
    "parse_frontmatter",
    "parse_yaml_subset",
]

