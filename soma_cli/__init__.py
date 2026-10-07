"""Soma CLI — user-facing governance commands."""
from __future__ import annotations

__version__ = "0.108.0"

import re
from pathlib import Path


def resolve_root(args, default=None):
    """Resolve project/repo root from args, checking workspace then project/repo root attributes."""
    for attr in ('workspace', 'repo_root', 'project_root', '_root', '_project_root'):
        val = getattr(args, attr, None)
        if val:
            return Path(val)
    return default if default is not None else Path.cwd()


EMOJI_REPLACEMENTS = {
    "🧱": "[WALL]",
    "🧫": "[TRAP]",
    "🔬": "[GATE]",
    "🌿": "[PRACTICE]",
    "🔗": "[CONTRACT]",
    "📋": "[RULE]",
    "✅": "[PASS]",
    "❌": "[FAIL]",
    "⚠️": "[WARN]",
    "🔍": "[*]",
    "🛡️": "[GUARD]",
    "🛡": "[GUARD]",
    "⚡": "[FAST]",
    "⏳": "[WAIT]",
}


def sanitize_display(text: str, max_len: int = 80) -> str:
    """Strip ANSI escapes and control chars, clamp length for safe terminal display."""
    text = re.sub(r'\x1b(?:\[[0-9;?]*[a-zA-Z]|\].*?(?:\x07|\x1b\\)|[=><NOM78c])', '', text)
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)
    text = text.replace('\n', ' ').replace('\r', '')
    text = text.replace('\t', ' ')
    if len(text) > max_len:
        text = text[:max_len - 3] + '...'
    return text


def format_plain(text: str) -> str:
    """Convert emojis to plain bracketed text and strip remaining Unicode emoji glyphs."""
    for emoji, token in EMOJI_REPLACEMENTS.items():
        if emoji in text:
            text = text.replace(emoji, token)
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[\u2600-\u27bf]', '', text)
    return text


__all__ = [
    "resolve_root",
    "sanitize_display",
    "format_plain",
]
