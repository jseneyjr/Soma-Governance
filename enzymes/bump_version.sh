#!/usr/bin/env bash
# Soma — Version Bump Enzyme
# Automatically synchronizes the version across all static surfaces.

if [ -z "$1" ]; then
    echo "Usage: make bump VERSION=<new_version>"
    echo "Example: make bump VERSION=0.92.0"
    exit 1
fi

NEW_VERSION="$1"
if [ ! -f "VERSION" ]; then
    echo "Error: VERSION file not found. Run from the repo root."
    exit 1
fi

OLD_VERSION=$(cat VERSION)
if [ "$OLD_VERSION" = "$NEW_VERSION" ]; then
    echo "Version is already $NEW_VERSION"
    exit 0
fi

echo "Bumping version from $OLD_VERSION to $NEW_VERSION..."

# We use Python for cross-platform file replacement (avoids sed -i differences between GNU/BSD).
python3 -c "
import os, sys

old = sys.argv[1]
new = sys.argv[2]

files = [
    'VERSION',
    'pyproject.toml',
    'soma_sdk/__init__.py',
    'soma_sdk_js/package.json',
    'README.md'
]

success = True
for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if old not in content:
            print(f'Warning: {old} not found in {f}.')
            
        content = content.replace(old, new)
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'  ✅ Updated {f}')
    else:
        print(f'  ❌ Error: {f} not found')
        success = False

if not success:
    sys.exit(1)
" "$OLD_VERSION" "$NEW_VERSION"

if [ $? -eq 0 ]; then
    echo "Successfully bumped all surfaces to $NEW_VERSION."
else
    echo "Failed to bump version."
    exit 1
fi
