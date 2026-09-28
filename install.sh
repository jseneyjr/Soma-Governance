#!/usr/bin/env bash
# Thin wrapper — delegates to install/install.sh
exec "$(dirname "$0")/install/install.sh" "$@"
