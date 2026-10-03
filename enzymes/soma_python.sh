#!/usr/bin/env bash
# Soma — Python interpreter resolution
# Sourced by common.sh and by scripts that don't source it (common.sh can't
# be sourced twice: it declares readonly variables).
#
# Under Git Bash with a python.org install, `python3` can be the Windows App
# Installer stub: `command -v python3` succeeds, but running it prints a
# Microsoft Store message and exits 49 (BUG-037). So a candidate counts only
# if it actually runs Python 3.9+.

# Prints sys.executable if "$@" runs Python 3.9+. -I -S keeps the probe
# independent of the current directory, PYTHON* variables and site.
_soma_probe_python() {
  local out
  out="$("$@" -I -S -c 'import sys
if sys.version_info < (3, 9):
    sys.exit(1)
print(sys.executable)' </dev/null 2>/dev/null)" || return 1
  # Windows Python ends lines with CRLF; $(...) strips only the LF.
  out="${out%$'\r'}"
  [ -n "$out" ] || return 1
  printf '%s' "$out"
}

# Sets and exports SOMA_PYTHON, plus SOMA_PYTHON_RESOLVED (internal; don't set
# it yourself): 1 lets child scripts trust the result without probing again
# (hooks run under tight timeouts); 0 tells them resolution already failed,
# so a rejected preset isn't silently replaced further down the tree.
# - A preset SOMA_PYTHON is an explicit choice: it is probed, kept as given if
#   it works, and reported (no fallback) if it doesn't.
# - Otherwise the first of python3, python, `py -3` that runs Python 3.9+ wins,
#   stored as its absolute path (one word, so it quotes cleanly).
# Returns 1, with SOMA_PYTHON empty, when nothing works.
soma_resolve_python() {
  if [ -n "${SOMA_PYTHON:-}" ] && [ "${SOMA_PYTHON_RESOLVED:-}" = "1" ]; then
    export SOMA_PYTHON SOMA_PYTHON_RESOLVED
    return 0
  fi
  if [ "${SOMA_PYTHON_RESOLVED:-}" = "0" ]; then
    SOMA_PYTHON=""
    export SOMA_PYTHON SOMA_PYTHON_RESOLVED
    return 1
  fi
  SOMA_PYTHON_RESOLVED=""
  if [ -n "${SOMA_PYTHON:-}" ]; then
    if _soma_probe_python "$SOMA_PYTHON" >/dev/null; then
      SOMA_PYTHON_RESOLVED=1
      export SOMA_PYTHON SOMA_PYTHON_RESOLVED
      return 0
    fi
    echo "soma: SOMA_PYTHON=$SOMA_PYTHON is not a working Python 3.9+; fix or unset it" >&2
    SOMA_PYTHON=""
    SOMA_PYTHON_RESOLVED=0
    export SOMA_PYTHON SOMA_PYTHON_RESOLVED
    return 1
  fi
  local exe="" cmd
  for cmd in python3 python py; do
    command -v "$cmd" >/dev/null 2>&1 || continue
    if [ "$cmd" = "py" ]; then
      exe="$(_soma_probe_python py -3)" || exe=""
    else
      exe="$(_soma_probe_python "$cmd")" || exe=""
    fi
    if [ -n "$exe" ]; then break; fi
  done
  SOMA_PYTHON="$exe"
  if [ -n "$SOMA_PYTHON" ]; then SOMA_PYTHON_RESOLVED=1; else SOMA_PYTHON_RESOLVED=0; fi
  export SOMA_PYTHON SOMA_PYTHON_RESOLVED
  [ -n "$SOMA_PYTHON" ]
}

# Runs the resolved interpreter. Scripts call soma_resolve_python first, so
# this never probes; it only explains a missing interpreter.
soma_py() {
  if [ -z "${SOMA_PYTHON:-}" ]; then
    echo "soma: no working Python 3.9+ found (tried python3, python, py -3); set SOMA_PYTHON" >&2
    return 127
  fi
  "$SOMA_PYTHON" "$@"
}
