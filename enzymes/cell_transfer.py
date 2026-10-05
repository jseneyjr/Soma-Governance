#!/usr/bin/env python3
"""cell_transfer.py: Copies a cell to another project with fitness reset.

Usage:
    python enzymes/cell_transfer.py <cell_id> --to /path/to/target/project
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    import json as yaml


def resolve_workspace() -> Optional[Path]:
    """Walk up from CWD to find project root with .soma/cells/."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(soma_root):
        return Path(soma_root).resolve()
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if "vendor" in candidate.parts:
            continue
        if (candidate / ".soma" / "cells").is_dir():
            return candidate
    return None


def transfer_cell(cell_id: str, target_dir_str: str, source_workspace: Path | None = None) -> int:
    repo_dir = source_workspace or resolve_workspace()
    if repo_dir is None or not (repo_dir / ".soma" / "cells").is_dir():
        print(
            f"Error: No Soma project found: no .soma/cells/ in {repo_dir or os.getcwd()} or any parent directory.",
            file=sys.stderr,
        )
        print("Run from inside the source project, or set SOMA_ROOT to its root.", file=sys.stderr)
        return 1

    target_dir = Path(target_dir_str).resolve()
    if not (target_dir / ".soma").is_dir():
        print("Error: Target directory does not have a .soma/ directory.", file=sys.stderr)
        print("Suggest running 'install --local' in the target directory first.", file=sys.stderr)
        return 1

    cells_dir = repo_dir / ".soma" / "cells"
    matches = list(cells_dir.rglob(f"*{cell_id}*.md"))
    if not matches:
        print(f"Error: Cell matching '{cell_id}' not found in {cells_dir}/", file=sys.stderr)
        return 1

    source_cell = matches[0]
    filename = source_cell.name
    target_basename = target_dir.name
    source_basename = repo_dir.name

    try:
        content = source_cell.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {source_cell}: {e}", file=sys.stderr)
        return 1

    if not content.startswith("---"):
        print("Error: Cell does not have YAML frontmatter.", file=sys.stderr)
        return 1

    end_idx = content.find("---", 3)
    if end_idx == -1:
        print("Error: Cell has malformed YAML frontmatter.", file=sys.stderr)
        return 1

    frontmatter_str = content[3:end_idx].strip()
    body_str = content[end_idx + 3:]

    try:
        metadata = yaml.safe_load(frontmatter_str) or {}
    except Exception as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return 1

    cell_type = metadata.get("type")
    if not cell_type:
        parent_name = source_cell.parent.name
        if "vacuoles" in parent_name:
            cell_type = "vacuole"
        elif "chloroplasts" in parent_name:
            cell_type = "chloroplast"
        elif "walls" in parent_name:
            cell_type = "wall"
        elif "membranes" in parent_name:
            cell_type = "membrane"
        elif "plasmodesmata" in parent_name:
            cell_type = "plasmodesmata"
        else:
            cell_type = "vacuole"

    plural_type = f"{cell_type}s" if not cell_type.endswith("s") else cell_type
    target_cell_dir = target_dir / ".soma" / "cells" / plural_type
    target_cell_dir.mkdir(parents=True, exist_ok=True)
    dest_file = target_cell_dir / filename

    if "fitness" not in metadata or not isinstance(metadata["fitness"], dict):
        metadata["fitness"] = {}
    metadata["fitness"]["triggers"] = 0
    metadata["fitness"]["true_positives"] = 0
    metadata["fitness"]["false_positives"] = 0
    metadata["fitness"]["score"] = None
    metadata["expiry_sessions"] = 5

    metadata["transferred_from"] = source_basename
    metadata["transfer_date"] = datetime.now(timezone.utc).isoformat() + "Z"

    gen = (
        metadata.get("lineage", {}).get("generation", 0)
        if isinstance(metadata.get("lineage"), dict)
        else 0
    )
    metadata["lineage"] = {
        "parent_id": source_cell.stem,
        "created_by": "transfer",
        "generation": gen + 1,
        "siblings": [],
    }

    try:
        new_frontmatter = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        clean_body = body_str[1:] if body_str.startswith("\n") else body_str
        dest_file.write_text(f"---\n{new_frontmatter}---\n{clean_body}", encoding="utf-8")
    except Exception as e:
        print(f"Error writing destination file {dest_file}: {e}", file=sys.stderr)
        return 1

    metrics_dir = repo_dir / ".soma" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    transfers_log = metrics_dir / "transfers.jsonl"
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "cell": filename,
        "target_project": target_basename,
    }
    try:
        with open(transfers_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Warning: Failed to write transfers log: {e}", file=sys.stderr)

    print(f"Transferred: {cell_id} -> {target_basename} (fitness reset, 5-session probation)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copies a cell to another project with fitness reset")
    parser.add_argument("cell_id", nargs="?", default="", help="ID of cell to transfer")
    parser.add_argument("--to", dest="target_dir", default="", help="Path to target project")
    args = parser.parse_args(argv)

    if not args.cell_id or not args.target_dir:
        print("Error: Missing cell_id or --to directory", file=sys.stderr)
        print("Usage: cell_transfer.py <cell_id> --to /path/to/target/project", file=sys.stderr)
        return 1

    return transfer_cell(cell_id=args.cell_id, target_dir_str=args.target_dir)


if __name__ == "__main__":
    sys.exit(main())
