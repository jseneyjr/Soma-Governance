#!/usr/bin/env python3
"""cell_create.py: Programmatic Cell Creation for Soma (pure Python engine).

Usage:
    python enzymes/cell_create.py --type <type> --hypothesis <hypothesis> [options]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


VALID_TYPES = {
    "vacuole": "vacuoles",
    "chloroplast": "chloroplasts",
    "wall": "walls",
    "membrane": "membranes",
    "plasmodesmata": "plasmodesmata",
}


def resolve_workspace() -> Path:
    """Resolve governed workspace root looking for .soma/cells."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(soma_root):
        return Path(soma_root).resolve()

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if "vendor" in candidate.parts:
            continue
        if (candidate / ".soma" / "cells").is_dir():
            return candidate
    return cwd


def validate_cell_id(cell_id: str | None) -> None:
    """Validate cell ID to prevent path traversal attacks."""
    if not cell_id:
        return
    if "/" in cell_id or "\\" in cell_id or ".." in cell_id:
        print("Error: Invalid ID_OVERRIDE contains path traversal characters.", file=sys.stderr)
        sys.exit(1)


def generate_slug(hypothesis: str, id_override: str | None = None) -> str:
    """Generate safe cell slug identifier."""
    if id_override:
        validate_cell_id(id_override)
        return id_override

    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", hypothesis.lower())
    slug = re.sub(r"\s+", "-", cleaned).strip("-")[:50].rstrip("-")
    return slug or "unnamed-cell"


def create_cell(
    cell_type: str,
    hypothesis: str,
    prediction: str = "",
    falsification: str = "",
    weight: float = 1.0,
    tags: list[str] | None = None,
    expiry_sessions: int | None = 15,
    expiry_days: int | None = 60,
    minimum_mode: str = "",
    id_override: str | None = None,
    effector: bool = False,
    memory: bool = False,
    target_paths: list[str] | None = None,
    domain: str = "correctness",
    workspace: Path | None = None,
) -> Path:
    """Create a new Soma cell file with validated frontmatter and body."""
    validate_cell_id(id_override)

    type_lower = cell_type.lower()
    if type_lower not in VALID_TYPES:
        print(
            "Error: Invalid type. Must be one of: vacuole, chloroplast, wall, membrane, plasmodesmata.",
            file=sys.stderr,
        )
        sys.exit(2)

    if effector and memory:
        print("Error: --effector and --memory are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    response_type = ""
    activation = ""
    decay_to_yaml = ""

    if effector:
        expiry_sessions = 3
        weight = 3.0
        response_type = "effector"
        minimum_mode = "tempest"
        decay_to_yaml = (
            "decay_to:\n"
            "  type: membrane\n"
            "  impact_weight: 1.0\n"
            "  minimum_mode: trident\n"
            "  response_type: memory\n"
            "  activation: dormant\n"
        )

    if memory:
        expiry_sessions = None
        weight = 1.5
        response_type = "memory"
        minimum_mode = "maelstrom"
        activation = "dormant"

    if not prediction:
        prediction = f"Behavior conforms to hypothesis: {hypothesis}"
    if not falsification:
        falsification = f"Behavior violates hypothesis: {hypothesis}"

    ws = workspace or resolve_workspace()
    type_plural = VALID_TYPES[type_lower]
    target_dir = ws / ".soma" / "cells" / type_plural
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = generate_slug(hypothesis, id_override)
    file_path = target_dir / f"{slug}.md"

    # Security: Unlink pre-existing symlinks to avoid symlink hijacking
    if file_path.is_symlink():
        file_path.unlink()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    type_title = type_lower.capitalize()
    truncated_hypo = hypothesis[:60] + ("..." if len(hypothesis) > 60 else "")

    def escape_yaml_string(val: str) -> str:
        s = val.replace("\\", "\\\\").replace('"', '\\"')
        return " ".join(s.splitlines())

    tags_list = tags or []
    paths_list = target_paths or []

    optional_lines = []
    if response_type:
        optional_lines.append(f"response_type: {response_type}")
    if minimum_mode:
        optional_lines.append(f"minimum_mode: {minimum_mode}")
    if activation:
        optional_lines.append(f"activation: {activation}")
    if decay_to_yaml:
        optional_lines.append(decay_to_yaml.rstrip())

    optional_block = ("\n" + "\n".join(optional_lines)) if optional_lines else ""

    expiry_sess_str = "null" if expiry_sessions is None else str(expiry_sessions)
    expiry_days_str = "null" if expiry_days is None else str(expiry_days)

    content = f"""---
id: {slug}
domain: {domain}
type: {type_lower}
hypothesis: "{escape_yaml_string(hypothesis)}"
prediction: "{escape_yaml_string(prediction)}"
falsification: "{escape_yaml_string(falsification)}"
expiry_sessions: {expiry_sess_str}
expiry_days: {expiry_days_str}
created: "{date_str}"
impact_weight: {weight}
tags: {json.dumps(tags_list)}
target_paths: {json.dumps(paths_list)}
lineage:
  parent_id: null
  created_by: "manual"
  generation: 0
  siblings: []{optional_block}
---
## {type_title}: {truncated_hypo}

{hypothesis}

### Prediction
{prediction}

### Falsification Criteria
{falsification}
"""

    file_path.write_text(content, encoding="utf-8")

    # Fail closed verification
    if not file_path.is_file() or file_path.stat().st_size == 0:
        print(f"ERROR: cell was not written correctly (empty file): {file_path}", file=sys.stderr)
        if file_path.exists():
            file_path.unlink()
        sys.exit(1)

    read_back = file_path.read_text(encoding="utf-8")
    if read_back.count("---") < 2:
        print(f"ERROR: cell frontmatter is malformed (missing closing '---'): {file_path}", file=sys.stderr)
        sys.exit(1)

    return file_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Programmatic Cell Creation for Soma", add_help=False)
    parser.add_argument("--help", action="store_true", default=False)
    parser.add_argument("-t", "--type", dest="cell_type", default="")
    parser.add_argument("-h", "--hypothesis", dest="hypothesis", default="")
    parser.add_argument("-p", "--prediction", dest="prediction", default="")
    parser.add_argument("-f", "--falsification", dest="falsification", default="")
    parser.add_argument("-w", "--weight", dest="weight", type=float, default=1.0)
    parser.add_argument("--tags", dest="tags", default="")
    parser.add_argument("--expiry-sessions", dest="expiry_sessions", type=int, default=15)
    parser.add_argument("--expiry-days", dest="expiry_days", type=int, default=60)
    parser.add_argument("--minimum-mode", dest="minimum_mode", default="")
    parser.add_argument("-n", "--name", "--id", dest="cell_id", default="")
    parser.add_argument("--effector", action="store_true", default=False)
    parser.add_argument("--memory", action="store_true", default=False)
    parser.add_argument("--target-paths", dest="target_paths", default="")
    parser.add_argument("--from-description", dest="description", default="")
    parser.add_argument("-d", "--domain", dest="domain", default="correctness")

    args = parser.parse_args(argv)

    if args.help:
        print("Usage: cell_create.py --type <type> --hypothesis <hypothesis> [options]")
        return 0

    if args.cell_id:
        validate_cell_id(args.cell_id)

    if args.description:
        # Delegate to cell_create_nl
        script_dir = Path(__file__).resolve().parent
        nl_script = script_dir / "cell_create_nl.py"
        extra_args = []
        if args.cell_id:
            extra_args.extend(["--id", args.cell_id])
        if args.cell_type:
            extra_args.extend(["--type", args.cell_type])
        if args.domain:
            extra_args.extend(["--domain", args.domain])

        cmd = [sys.executable, str(nl_script), args.description, *extra_args]
        import subprocess
        res = subprocess.run(cmd)
        return res.returncode

    if not args.cell_type or not args.hypothesis:
        print("Error: Missing required arguments.", file=sys.stderr)
        print("Usage: cell_create.py --type <type> --hypothesis <hypothesis> [--prediction <prediction>]", file=sys.stderr)
        return 1

    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    target_paths_list = [p.strip() for p in args.target_paths.split(",") if p.strip()] if args.target_paths else []

    created_path = create_cell(
        cell_type=args.cell_type,
        hypothesis=args.hypothesis,
        prediction=args.prediction,
        falsification=args.falsification,
        weight=args.weight,
        tags=tags_list,
        expiry_sessions=args.expiry_sessions,
        expiry_days=args.expiry_days,
        minimum_mode=args.minimum_mode,
        id_override=args.cell_id or None,
        effector=args.effector,
        memory=args.memory,
        target_paths=target_paths_list,
        domain=args.domain,
    )
    print(f"Created: {created_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
