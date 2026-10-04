#!/usr/bin/env bash
# Soma — Version Bump Enzyme
# Automatically synchronizes the version across all static surfaces.

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: make bump VERSION=<new_version>"
    echo "Example: make bump VERSION=0.92.0"
    exit 1
fi

NEW_VERSION="$1"
if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    echo "Error: Invalid semantic version format: '$NEW_VERSION'" >&2
    echo "Expected format: X.Y.Z or X.Y.Z-tag (e.g. 0.92.0 or 0.92.0-rc1)" >&2
    exit 1
fi
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"

if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: VERSION file not found at $VERSION_FILE. Run from repo root." >&2
    exit 1
fi

OLD_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
if [ "$OLD_VERSION" = "$NEW_VERSION" ]; then
    echo "Version is already $NEW_VERSION"
    exit 0
fi

echo "Bumping version from $OLD_VERSION to $NEW_VERSION..."

source "$(dirname "${BASH_SOURCE[0]}")/soma_python.sh"
soma_resolve_python || exit 1

soma_py -c '
import os, sys, re

repo_root = sys.argv[1]
old = sys.argv[2]
new = sys.argv[3]

handlers = {
    "VERSION": lambda c, o, n: (f"{n}\n", 1 if c.strip() == o else 0),
    "pyproject.toml": lambda c, o, n: re.subn(r"(?m)^version\s*=\s*\"" + re.escape(o) + r"\"", f"version = \"{n}\"", c),
    "soma_sdk/__init__.py": lambda c, o, n: re.subn(r"(?m)^__version__\s*=\s*([\"\x27])" + re.escape(o) + r"\1", rf"__version__ = \g<1>{n}\g<1>", c),
    "soma_sdk_js/package.json": lambda c, o, n: re.subn(r"(?m)^(\s*\"version\"\s*:\s*\")" + re.escape(o) + r"(\")", rf"\g<1>{n}\g<2>", c),
    "README.md": lambda c, o, n: re.subn(r"(\[!\[Version\]\(https://img\.shields\.io/badge/Version-)" + re.escape(o) + r"(-informational)", rf"\g<1>{n}\g<2>", c),
    "docs/KNOWN_ISSUES_WINDOWS.md": lambda c, o, n: re.subn(rf"(# Known Issues — Windows \(v){re.escape(o)}(\)\s+Open Windows issues as of v){re.escape(o)}", rf"\g<1>{n}\g<2>{n}", c),
}

updates = {}
for rel, fn in handlers.items():
    path = os.path.join(repo_root, rel)
    if not os.path.isfile(path):
        print(f"  ❌ Error: {rel} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content, count = fn(content, old, new)
    if count == 0:
        print(f"  ❌ Error: Version pattern for \"{old}\" not found in {rel}", file=sys.stderr)
        sys.exit(1)
    elif count > 1:
        print(f"  ❌ Error: Ambiguous match ({count} occurrences) in {rel}", file=sys.stderr)
        sys.exit(1)
    updates[path] = (rel, new_content)

for path, (rel, new_content) in updates.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  ✅ Updated {rel}")
' "$REPO_ROOT" "$OLD_VERSION" "$NEW_VERSION"

echo "Successfully bumped all surfaces to $NEW_VERSION."
