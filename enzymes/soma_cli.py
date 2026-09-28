#!/usr/bin/env python3
"""Soma CLI — lightweight project governance commands."""
import sys
import os
import subprocess
import glob
import json

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

def print_help():
    print("Soma CLI — Adaptive Governance")
    print("\nUsage: soma <command> [args]")
    print("\nCommands:")
    print("  init [--genesis]  Initialize Soma in the current project")
    print("  doctor            Check installation health")
    print("  status            Show current governance status")

def cmd_init(args):
    """Initialize Soma in current project: creates .soma/cells/ structure and optionally runs genesis."""
    print("Initializing Soma...")
    cells_dir = os.path.join(".soma", "cells")
    cell_types = ["walls", "vacuoles", "membranes", "chloroplasts", "plasmodesmata"]
    
    for ctype in cell_types:
        d = os.path.join(cells_dir, ctype)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, ".gitkeep"), "w") as f:
            f.write("")
            
    readme_path = os.path.join(cells_dir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as f:
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
        with open(mcp_path, "w") as f:
            json.dump(mcp_config, f, indent=2)
            f.write("\n")
            
    print(f"✅ Created .soma/cells/ with {len(cell_types)} cell types")
    print("✅ Created .mcp.json")
    
    if "--genesis" in args:
        print("💡 Run the genesis organ in your AI agent to populate cells.")

def cmd_doctor(args):
    """Check installation health."""
    print("Soma Health Check\n")
    
    cells_dir = os.path.join(".soma", "cells")
    if os.path.exists(cells_dir):
        print(f"✅ Cells directory found: {cells_dir}")
    else:
        print("❌ Cells directory missing")
        
    cell_types = ["walls", "vacuoles", "membranes", "chloroplasts", "plasmodesmata"]
    for ctype in cell_types:
        count = len(glob.glob(os.path.join(cells_dir, ctype, "*.md")))
        print(f"  - {ctype}: {count} cells")
        
    if subprocess.call(["python3", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        print("✅ python3 available")
    else:
        print("❌ python3 missing")
        
    try:
        import soma_mcp
        print("✅ soma_mcp imports successfully")
    except ImportError:
        print("❌ soma_mcp import failed")

def cmd_status(args):
    """Show current governance status."""
    print("Governance Status\n")
    
    cells_dir = os.path.join(".soma", "cells")
    cell_types = ["walls", "vacuoles", "membranes", "chloroplasts", "plasmodesmata"]
    for ctype in cell_types:
        count = len(glob.glob(os.path.join(cells_dir, ctype, "*.md")))
        print(f"  - {ctype}: {count} cells")
        
    try:
        from soma_sdk import Governance
        gov = Governance('.')
        grade = gov.grade()
        print(f"\nFitness Summary: {grade}")
    except ImportError:
        print("\nFitness Summary: N/A (pyyaml or soma_sdk missing)")
        
    if os.path.exists(".mcp.json"):
        print("\nMCP Status: Active (.mcp.json exists)")
    else:
        print("\nMCP Status: Inactive (.mcp.json missing)")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print_help()
        return
    cmd = sys.argv[1]
    cmds = {'init': cmd_init, 'doctor': cmd_doctor, 'status': cmd_status}
    if cmd in cmds:
        cmds[cmd](sys.argv[2:])
    else:
        print(f"Unknown command: {cmd}")
        print_help()

if __name__ == '__main__':
    main()
