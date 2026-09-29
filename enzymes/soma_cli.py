#!/usr/bin/env python3
"""Soma CLI — lightweight project governance commands."""
import sys
import os
import subprocess
import glob
import json

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

CELL_TYPES = ["walls", "vacuoles", "membranes", "chloroplasts", "plasmodesmata"]


def print_help():
    print("Soma CLI — Adaptive Governance")
    print("\nUsage: soma <command> [args]")
    print("\nCommands:")
    print("  init [--genesis]  Initialize Soma in the current project")
    print("  doctor            Check installation health")
    print("  status            Show current governance status")
    print("\nExit codes: 0 = success, 1 = failure (doctor fails if any check fails).")

def cmd_init(args):
    """Initialize Soma in current project: creates .soma/cells/ structure and optionally runs genesis.

    Returns 0 on success, 1 if the project could not be initialized.
    """
    print("Initializing Soma...")
    cells_dir = os.path.join(".soma", "cells")

    try:
        for ctype in CELL_TYPES:
            d = os.path.join(cells_dir, ctype)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, ".gitkeep"), "w", encoding="utf-8") as f:
                f.write("")

        readme_path = os.path.join(cells_dir, "README.md")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write("# Soma Cells\n\nThis directory contains the adaptive immune system for your repository.\n")

        mcp_path = ".mcp.json"
        if not os.path.exists(mcp_path):
            mcp_config = {
                "mcpServers": {
                    "soma": {
                        "command": "python3",
                        "args": ["-m", "soma_mcp"],
                        "cwd": os.path.abspath(".")
                    }
                }
            }
            with open(mcp_path, "w", encoding="utf-8") as f:
                json.dump(mcp_config, f, indent=2)
                f.write("\n")
    except OSError as e:
        print(f"❌ Initialization failed: {e}", file=sys.stderr)
        return 1

    print(f"✅ Created .soma/cells/ with {len(CELL_TYPES)} cell types")
    print("✅ Created .mcp.json")
    
    if "--genesis" in args:
        print("💡 Run the genesis organ in your AI agent to populate cells.")

    return 0

def cmd_doctor(args):
    """Check installation health.

    Returns 0 only when every check passes, so `soma doctor` can gate CI.
    """
    print("Soma Health Check\n")

    failed = False

    cells_dir = os.path.join(".soma", "cells")
    if os.path.exists(cells_dir):
        print(f"✅ Cells directory found: {cells_dir}")
    else:
        print("❌ Cells directory missing")
        failed = True

    for ctype in CELL_TYPES:
        count = len(glob.glob(os.path.join(cells_dir, ctype, "*.md")))
        print(f"  - {ctype}: {count} cells")

    # Check `python3` on PATH specifically: that is the interpreter the
    # generated .mcp.json launches the server with.
    try:
        python_ok = subprocess.call(
            ["python3", "--version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) == 0
    except OSError:
        python_ok = False
    if python_ok:
        print("✅ python3 available")
    else:
        print("❌ python3 missing")
        failed = True

    try:
        import soma_mcp  # noqa: F401
        print("✅ soma_mcp imports successfully")
    except Exception as e:  # noqa: BLE001 - any import failure is a health failure
        print(f"❌ soma_mcp import failed: {type(e).__name__}: {e}")
        failed = True

    if failed:
        print("\n❌ Health check FAILED")
        return 1
    print("\n✅ Health check passed")
    return 0

def cmd_status(args):
    """Show current governance status.

    Returns 0 when there is governance to report on, 1 when Soma is not
    initialized here.
    """
    print("Governance Status\n")

    cells_dir = os.path.join(".soma", "cells")
    for ctype in CELL_TYPES:
        count = len(glob.glob(os.path.join(cells_dir, ctype, "*.md")))
        print(f"  - {ctype}: {count} cells")

    try:
        from soma_sdk import Governance
        gov = Governance('.')
        grade = gov.grade()
        print(f"\nFitness Summary: {grade}")
    except ImportError:
        print("\nFitness Summary: N/A (pyyaml or soma_sdk missing)")
    except Exception as e:  # noqa: BLE001 - status must never traceback
        # soma_sdk.governance raises RuntimeError (enzymes dir not found,
        # non-JSON command failure) and FileNotFoundError (script missing).
        # A status command must not hand the user a traceback.
        print(f"\nFitness Summary: N/A ({type(e).__name__}: {e})")

    if os.path.exists(".mcp.json"):
        print("\nMCP Status: Active (.mcp.json exists)")
    else:
        print("\nMCP Status: Inactive (.mcp.json missing)")

    if not os.path.isdir(cells_dir):
        print(f"\n❌ Soma is not initialized here ({cells_dir} missing). "
              "Run `soma init`.", file=sys.stderr)
        return 1
    return 0

def main():
    """Entry point. Always returns an int: the console script does sys.exit(main())."""
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print_help()
        return 0
    cmd = sys.argv[1]
    cmds = {'init': cmd_init, 'doctor': cmd_doctor, 'status': cmd_status}
    if cmd in cmds:
        code = cmds[cmd](sys.argv[2:])
        # Every command above returns an explicit int; None is coerced here so
        # the console-script wrapper (sys.exit(main())) always gets an int.
        return 0 if code is None else int(code)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    print_help()
    return 1

if __name__ == '__main__':
    sys.exit(main())
