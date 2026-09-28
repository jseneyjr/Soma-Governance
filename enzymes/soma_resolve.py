"""Shared workspace resolution for Soma scripts.

Resolution order:
1. SOMA_ROOT environment variable (most explicit)
2. CWD — check if current working directory has .soma/cells/
3. Walk up from CWD looking for .soma/cells/
4. Walk up from script location, SKIPPING vendor/ directories
5. Fallback to CWD
"""
import os


def resolve_workspace(caller_file=None):
    """Find the project root containing .soma/cells/.
    
    Args:
        caller_file: Pass __file__ from the calling script for walk-up from script location.
    """
    # 1. Explicit override via environment variable
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
        return os.path.abspath(soma_root)

    # 2. Check CWD directly
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
        return cwd

    # 3. Walk up from CWD
    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma", "cells")):
            return d
        d = os.path.dirname(d)

    # 4. Walk up from script location, skipping vendor/ directories
    if caller_file:
        d = os.path.dirname(os.path.abspath(caller_file))
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, ".soma", "cells")):
                # Skip if we're inside a vendor/ path
                if "/vendor/" not in d and not os.path.basename(os.path.dirname(d)) == "vendor":
                    return d
            d = os.path.dirname(d)

    # 5. Fallback to CWD
    return cwd
