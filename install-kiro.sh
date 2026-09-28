#!/usr/bin/env bash
echo "DEPRECATED: Use 'bash install.sh kiro' instead."
echo "Forwarding to unified installer..."
exec "$(dirname "$0")/install.sh" kiro "$@"
