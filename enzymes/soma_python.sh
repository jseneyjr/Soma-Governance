#!/usr/bin/env bash
# Soma — Python interpreter resolution
# Sourced by common.sh and by scripts that don't source it (common.sh can't
# be sourced twice: it declares readonly variables).
#
# Under Git Bash with a python.org install, `python3` can be the Windows App
# Installer stub: `command -v python3` succeeds, but running it prints a
# Microsoft Store message and exits 49 (BUG-037). So a candidate counts only
# if it actually runs Python 3.9+.

# Sets and exports SOMA_PYTHON to an interpreter's absolute path (one word,
# so `py -3` and paths with spaces quote cleanly as "$SOMA_PYTHON").
# A preset SOMA_PYTHON that exists is trusted without probing: child scripts
# inherit the parent's result, and hooks run under tight timeouts. One that
# no longer exists (a deleted venv) is dropped and probed for. Returns 1, with
# SOMA_PYTHON empty, when nothing works. SOMA_PYTHON_FOUND_AS names the
# command that worked (python3, python or py), or "preset".
soma_resolve_python() {
  SOMA_PYTHON_FOUND_AS="preset"
  if [ -n "${SOMA_PYTHON:-}" ] && command -v "$SOMA_PYTHON" >/dev/null 2>&1; then
    export SOMA_PYTHON
    return 0
  fi
  local probe='import sys
if sys.version_info < (3, 9):
    sys.exit(1)
print(sys.executable)'
  local exe="" cmd
  for cmd in python3 python py; do
    command -v "$cmd" >/dev/null 2>&1 || continue
    if [ "$cmd" = "py" ]; then
      exe="$(py -3 -c "$probe" </dev/null 2>/dev/null)" || exe=""
    else
      exe="$("$cmd" -c "$probe" </dev/null 2>/dev/null)" || exe=""
    fi
    if [ -n "$exe" ]; then
      SOMA_PYTHON_FOUND_AS="$cmd"
      break
    fi
  done
  [ -n "$exe" ] || SOMA_PYTHON_FOUND_AS=""
  # Windows Python ends lines with CRLF; $(...) strips only the LF.
  exe="${exe%$'\r'}"
  SOMA_PYTHON="$exe"
  export SOMA_PYTHON
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
