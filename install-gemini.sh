#!/usr/bin/env bash
echo "DEPRECATED: Use 'bash install.sh gemini' or 'make install' instead."
echo "Forwarding to unified installer..."
exec "$(dirname "$0")/install.sh" gemini "$@"
