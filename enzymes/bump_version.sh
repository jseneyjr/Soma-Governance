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

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/soma_python.sh"
soma_resolve_python || exit 1

soma_py "$SCRIPT_DIR/bump_version.py" "$@"
exit $?
