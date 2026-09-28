#!/usr/bin/env bash
echo "DEPRECATED: Use 'bash install.sh copilot' instead."
echo "Forwarding to unified installer..."
exec "$(dirname "$0")/install.sh" copilot "$@"
