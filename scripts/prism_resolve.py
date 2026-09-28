"""Shared workspace resolution for Prism AI Steering scripts.

Resolution order:
1. PRISM_ROOT environment variable (most explicit)
2. CWD — check if current working directory has .prism/cells/
3. Walk up from CWD looking for .prism/cells/
4. Walk up from script location, SKIPPING vendor/ directories
5. Fallback to CWD
"""
import os


def resolve_workspace(caller_file=None):
    """Find the project root containing .prism/cells/.
    
    Args:
        caller_file: Pass __file__ from the calling script for walk-up from script location.
    """
    # 1. Explicit override via environment variable
    prism_root = os.environ.get("PRISM_ROOT")
    if prism_root and os.path.isdir(os.path.join(prism_root, ".prism", "cells")):
        return os.path.abspath(prism_root)

    # 2. Check CWD directly
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".prism", "cells")):
        return cwd

    # 3. Walk up from CWD
    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".prism", "cells")):
            return d
        d = os.path.dirname(d)

    # 4. Walk up from script location, skipping vendor/ directories
    if caller_file:
        d = os.path.dirname(os.path.abspath(caller_file))
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, ".prism", "cells")):
                # Skip if we're inside a vendor/ path
                if "/vendor/" not in d and not os.path.basename(os.path.dirname(d)) == "vendor":
                    return d
            d = os.path.dirname(d)

    # 5. Fallback to CWD
    return cwd
