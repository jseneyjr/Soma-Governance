"""Soma CLI — user-facing governance commands."""
from __future__ import annotations

import re
from pathlib import Path


def resolve_root(args, default=None):
    """Resolve project/repo root from args, checking _root then _project_root."""
    root = getattr(args, '_root', getattr(args, '_project_root', None))
    if root is not None:
        return Path(root)
    return default if default is not None else Path.cwd()


def sanitize_display(text: str, max_len: int = 80) -> str:
    """Strip ANSI escapes and control chars, clamp length for safe terminal display."""
    # Remove ANSI escape sequences (CSI, OSC, and simple two-byte escapes)
    text = re.sub(r'\x1b(?:\[[0-9;?]*[a-zA-Z]|\].*?(?:\x07|\x1b\\)|[=><NOM78c])', '', text)
    # Remove other control characters (keep newline for now)
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)
    # Replace newlines with spaces
    text = text.replace('\n', ' ').replace('\r', '')
    text = text.replace('\t', ' ')
    # Clamp length
    if len(text) > max_len:
        text = text[:max_len - 3] + '...'
    return text
