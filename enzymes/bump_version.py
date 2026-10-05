#!/usr/bin/env python3
"""bump_version.py: Version Bump Enzyme for Soma.

Automatically synchronizes semantic version strings across all static surfaces:
- VERSION
- pyproject.toml
- soma_sdk/__init__.py
- soma_sdk_js/package.json
- README.md
- docs/KNOWN_ISSUES_WINDOWS.md
- SECURITY.md

Usage:
    python enzymes/bump_version.py <new_version>
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$")


def update_security(content: str, old: str, new: str) -> tuple[str, int]:
    old_mm = ".".join(old.split(".")[:2])
    new_mm = ".".join(new.split(".")[:2])
    if old_mm == new_mm:
        return content, 1
    c1, cnt1 = re.subn(rf"(\|\s*){re.escape(old_mm)}\.x(\s*\|\s*✅\s*\|)", rf"\g<1>{new_mm}.x\g<2>", content)
    c2, cnt2 = re.subn(rf"(\|\s*<\s*){re.escape(old_mm)}(\s*\|\s*❌\s*\|)", rf"\g<1>{new_mm}\g<2>", c1)
    return c2, 1 if (cnt1 == 1 and cnt2 == 1) else 0


HANDLERS = {
    "VERSION": lambda c, o, n: (f"{n}\n", 1 if c.strip() == o else 0),
    "pyproject.toml": lambda c, o, n: re.subn(r'(?m)^version\s*=\s*"' + re.escape(o) + r'"', f'version = "{n}"', c),
    "soma_sdk/__init__.py": lambda c, o, n: re.subn(
        r'(?m)^__version__\s*=\s*(["\x27])' + re.escape(o) + r"\1",
        rf"__version__ = \g<1>{n}\g<1>",
        c,
    ),
    "soma_sdk_js/package.json": lambda c, o, n: re.subn(
        r'(?m)^(\s*"version"\s*:\s*")' + re.escape(o) + r'(")',
        rf"\g<1>{n}\g<2>",
        c,
    ),
    "README.md": lambda c, o, n: re.subn(
        r"(\[!\[Version\]\(https://img\.shields\.io/badge/Version-)" + re.escape(o) + r"(-informational)",
        rf"\g<1>{n}\g<2>",
        c,
    ),
    "docs/KNOWN_ISSUES_WINDOWS.md": lambda c, o, n: re.subn(
        rf"(# Known Issues — Windows \(v){re.escape(o)}(\)\s+Open Windows issues as of v){re.escape(o)}",
        rf"\g<1>{n}\g<2>{n}",
        c,
    ),
    "SECURITY.md": update_security,
}


def bump_version(new_version: str, repo_root: Path | None = None, dry_run: bool = False) -> int:
    if not SEMVER_PATTERN.match(new_version):
        print(f"Error: Invalid semantic version format: '{new_version}'", file=sys.stderr)
        print("Expected format: X.Y.Z or X.Y.Z-tag (e.g. 0.94.0 or 0.94.0-rc1)", file=sys.stderr)
        return 1

    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    version_file = root / "VERSION"
    if not version_file.is_file():
        print(f"Error: VERSION file not found at {version_file}. Run from repo root.", file=sys.stderr)
        return 1

    old_version = version_file.read_text(encoding="utf-8").strip()
    if old_version == new_version:
        print(f"Version is already {new_version}")
        return 0

    mode_str = " (dry run)" if dry_run else ""
    print(f"Bumping version from {old_version} to {new_version}{mode_str}...")

    updates = {}
    for rel, fn in HANDLERS.items():
        path = root / rel
        if not path.is_file():
            print(f"  ❌ Error: {rel} not found", file=sys.stderr)
            return 1
        content = path.read_text(encoding="utf-8")
        new_content, count = fn(content, old_version, new_version)
        if count == 0:
            print(f'  ❌ Error: Version pattern for "{old_version}" not found in {rel}', file=sys.stderr)
            return 1
        elif count > 1:
            print(f"  ❌ Error: Ambiguous match ({count} occurrences) in {rel}", file=sys.stderr)
            return 1
        updates[path] = (rel, new_content)

    if dry_run:
        for path, (rel, _) in updates.items():
            print(f"  [dry-run] Would update {rel}")
        print(f"[dry-run] Dry run complete. All surfaces valid for {new_version}.")
        return 0

    for path, (rel, new_content) in updates.items():
        path.write_text(new_content, encoding="utf-8")
        print(f"  ✅ Updated {rel}")

    print(f"Successfully bumped all surfaces to {new_version}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Synchronize version across all surfaces")
    parser.add_argument("version", nargs="?", default="", help="New semantic version")
    parser.add_argument("--dry-run", action="store_true", help="Preview version bump without modifying files")
    args = parser.parse_args(argv)

    if not args.version:
        print("Usage: bump_version.py <new_version> [--dry-run]")
        print("Example: bump_version.py 0.94.0")
        return 1

    return bump_version(args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
