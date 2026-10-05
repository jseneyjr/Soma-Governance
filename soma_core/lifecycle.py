"""soma_core.lifecycle — Canonical cell lifecycle state machine, genetics, and promotion engine.

Consolidates:
- Cell lifecycle status evaluation (NEW, SURVIVE, ADAPT, EXTINCT, APOPTOSIS, DORMANT)
- Boundary thresholds for promotion and extinction
- Exponential fitness decay with idempotency fencing
- Protected core rules enforcement
- Structural transitions (vacuole -> wall -> genome) and demotions
- Programmatic cell creation (formerly enzymes/cell_create.py)
- Cross-project cell transfer (formerly enzymes/cell_transfer.py)
- Local and team promotion engine (formerly enzymes/cell_promote.py)
- Rule demotion engine (formerly enzymes/cell_demote.py)
- Cell metamorphosis (formerly enzymes/cell_metamorphose.py)
- Cell adaptation and refinement (formerly enzymes/cell_adapt.py)
- Selection pressure and archiving (formerly enzymes/cell_selection.py)
- Cell crossover and hypothesis merging (formerly enzymes/cell_crossover.py)
- Comprehensive fitness evaluation (formerly enzymes/cell_fitness.py)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import yaml
except ImportError:
    yaml = None

from soma_core.workspace import resolve_workspace
from soma_core.frontmatter import parse_frontmatter, dump_frontmatter
from soma_core.locking import workspace_lock
from soma_core.scoring import laplace_score, bayesian_score, bayesian_posterior

STATUS_NEW = "NEW"
STATUS_SURVIVE = "SURVIVE"
STATUS_ADAPT = "ADAPT"
STATUS_EXTINCT = "EXTINCT"
STATUS_APOPTOSIS = "APOPTOSIS"
STATUS_APOPTOSIS_WARNING = "APOPTOSIS_WARNING"
STATUS_DORMANT = "DORMANT"

# The 11 protected core genome rules that must never be demoted
PROTECTED_RULES = frozenset({
    "providence",
    "cost-optimization",
    "subagent-delegation",
    "architectural-tenets",
    "polyglot-standards",
    "feature-specs",
    "testing",
    "documentation",
    "destructive-ops",
    "git-workflow",
    "desktop-automation",
})

PROMOTION_PATH = {"vacuole": "wall", "wall": "genome"}
DEMOTION_PATH = {"genome": "wall", "wall": "vacuole"}
TYPE_TO_DIR = {"vacuole": "vacuoles", "wall": "walls"}

EXTINCTION_THRESHOLD = 0.15
PROMOTION_THRESHOLD = 0.85
MIN_PROMOTION_TRIGGERS = 20
DEFAULT_DECAY_FACTOR = 0.95

VALID_TYPES = {
    "vacuole": "vacuoles",
    "chloroplast": "chloroplasts",
    "wall": "walls",
    "membrane": "membranes",
    "plasmodesmata": "plasmodesmata",
}

METAMORPHOSIS_PATHS = {
    "vacuole": [
        {"target": "wall", "min_fitness": 0.8, "min_sessions": 20},
        {"target": "membrane", "min_fitness": 0.7, "min_sessions": 15},
    ],
    "chloroplast": [
        {"target": "rule", "min_fitness": 0.9, "min_sessions": 30},
    ],
    "wall": [
        {"target": "rule", "min_fitness": 0.85, "min_sessions": 25},
    ],
}


# ── Lifecycle Evaluation & Status ──────────────────────────────────────────

def calculate_fitness_status(
    cell_type: str,
    tp: int,
    fp: int,
    triggers: int,
    dec_score: Optional[float] = None,
    is_unobserved: bool = False,
    created_str: Optional[str] = None,
    expiry_days: Optional[int] = None,
) -> str:
    """Evaluate canonical cell lifecycle status from observations, score, and age."""
    if fp > 0 and (tp == 0 or fp > 2 * tp):
        return STATUS_APOPTOSIS_WARNING if cell_type == "wall" else STATUS_APOPTOSIS

    if not is_unobserved and dec_score is not None:
        if dec_score > 0.7:
            return STATUS_SURVIVE
        elif dec_score > EXTINCTION_THRESHOLD:
            return STATUS_ADAPT
        else:
            return STATUS_EXTINCT

    if expiry_days and created_str:
        try:
            fmt = "%Y-%m-%dT%H:%M:%SZ" if "T" in created_str else "%Y-%m-%d"
            created_date = datetime.strptime(created_str, fmt)
            current_date = datetime.now(timezone.utc).replace(tzinfo=None)
            days_since_created = (current_date - created_date).days
            if days_since_created > expiry_days:
                return STATUS_DORMANT
            return STATUS_NEW
        except Exception:
            return STATUS_NEW

    return STATUS_NEW


def is_promotable(
    tp: int,
    triggers: int,
    min_triggers: int = MIN_PROMOTION_TRIGGERS,
    threshold: float = PROMOTION_THRESHOLD,
) -> bool:
    """Determine if cell metrics qualify for promotion."""
    if triggers < min_triggers:
        return False
    score = laplace_score(tp, triggers)
    return score > threshold


def is_extinct(
    tp: int,
    triggers: int,
    threshold: float = EXTINCTION_THRESHOLD,
) -> bool:
    """Determine if cell metrics fall at or below extinction boundary."""
    if triggers <= 0:
        return False
    score = laplace_score(tp, triggers)
    return score <= threshold


def apply_exponential_decay(
    fitness: Dict[str, Any],
    decay_factor: float = DEFAULT_DECAY_FACTOR,
    min_interval_seconds: int = 3600,
) -> Dict[str, Any]:
    """Decay historical fitness data so recent signals carry greater weight."""
    if not isinstance(fitness, dict):
        return {}

    now = int(time.time())
    last_decay = fitness.get("last_decay_epoch", 0)
    if min_interval_seconds > 0 and (now - last_decay < min_interval_seconds):
        return fitness

    triggers = fitness.get("triggers", 0)
    tp = fitness.get("true_positives", 0)
    fp = fitness.get("false_positives", 0)

    updated = dict(fitness)
    if triggers <= 0:
        updated["last_decay_epoch"] = now
        return updated

    updated["triggers"] = max(1, int(triggers * decay_factor))
    updated["true_positives"] = max(0, int(tp * decay_factor))
    updated["false_positives"] = max(0, int(fp * decay_factor))
    updated["last_decay_epoch"] = now
    updated["score"] = round(laplace_score(updated["true_positives"], updated["triggers"]), 4)
    return updated


def sanitize_cell_id(cell_id: str) -> Optional[str]:
    """Validate cell identifier to prevent path traversal."""
    if not cell_id or "/" in cell_id or "\\" in cell_id or ".." in cell_id:
        return None
    cleaned = cell_id.strip()
    if cleaned.endswith(".md"):
        cleaned = cleaned[:-3]
    return cleaned if cleaned else None


def find_cell_file(workspace: Path, cell_id: str) -> Tuple[Optional[Path], Optional[str]]:
    """Locate a cell across vacuoles/, walls/, and genome/ directories."""
    clean_id = sanitize_cell_id(cell_id)
    if not clean_id:
        return None, None

    cells_dir = workspace / ".soma" / "cells"
    genome_dir = workspace / "genome"

    for type_name, dir_name in TYPE_TO_DIR.items():
        candidate = cells_dir / dir_name / f"{clean_id}.md"
        if candidate.is_file():
            return candidate, type_name

    candidate = genome_dir / f"{clean_id}.md"
    if candidate.is_file():
        return candidate, "genome"

    return None, None


def _transform_frontmatter_type(content: str, new_type: str) -> str:
    """Update type field in cell frontmatter preserving body and comments."""
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return content

    frontmatter = content[3:end_idx]
    body = content[end_idx:]

    lines = frontmatter.splitlines()
    new_lines = []
    type_updated = False
    enforcement_updated = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("type:"):
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}type: {new_type}")
            type_updated = True
        elif stripped.startswith("enforcement:"):
            if new_type == "wall":
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}enforcement: gate")
                enforcement_updated = True
            elif new_type == "vacuole":
                pass
            else:
                new_lines.append(line)
        elif stripped.startswith("enforcement_artifact:"):
            if new_type == "vacuole":
                pass
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not type_updated:
        new_lines.append(f"type: {new_type}")

    if new_type == "wall" and not enforcement_updated:
        new_lines.append("enforcement: gate")

    return "---\n" + "\n".join(new_lines).strip() + "\n" + body


def _update_frontmatter_type(file_path: Path, new_type: str) -> None:
    content = file_path.read_text(encoding="utf-8")
    new_content = _transform_frontmatter_type(content, new_type)
    file_path.write_text(new_content, encoding="utf-8")


def _atomic_write_and_unlink(
    source_path: Path,
    target_path: Path,
    new_content: str,
) -> None:
    """Write new_content to target_path atomically and unlink source_path with rollback."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}")
    try:
        with open(tmp_target, "w", encoding="utf-8") as fh:
            fh.write(new_content)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.replace(tmp_target, target_path)
        except OSError:
            shutil.move(str(tmp_target), str(target_path))
        try:
            if source_path != target_path and source_path.exists():
                source_path.unlink()
        except Exception:
            if target_path.exists() and source_path.exists():
                try:
                    os.remove(target_path)
                except Exception as ex:
                    raise RuntimeError(f"Rollback failed: duplicate cell remains at {target_path}") from ex
            raise
    except Exception:
        if tmp_target.exists():
            try:
                os.remove(tmp_target)
            except OSError:
                pass
        raise


def promote_cell(
    workspace: Path,
    cell_id: str,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute structural promotion for a cell (vacuole -> wall -> genome)."""
    cell_path, current_type = find_cell_file(workspace, cell_id)
    if cell_path is None or current_type is None:
        return {
            "status": "not_found",
            "message": f"Cell '{cell_id}' not found in workspace",
        }

    next_type = PROMOTION_PATH.get(current_type)
    if next_type is None:
        return {
            "status": "already_terminal",
            "current_type": current_type,
            "message": f"Cell '{cell_id}' is already at terminal level ('{current_type}')",
        }

    if not force:
        try:
            metadata = parse_frontmatter(cell_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            return {"status": "error", "message": f"Failed to parse cell frontmatter: {exc}"}

        fitness = metadata.get("fitness") or {}
        tp = int(fitness.get("true_positives", 0))
        triggers = int(fitness.get("triggers", 0))
        if not is_promotable(tp, triggers):
            return {
                "status": "ineligible",
                "current_type": current_type,
                "triggers": triggers,
                "tp": tp,
                "message": f"Cell '{cell_id}' does not meet promotion threshold (>0.85 with >=20 triggers)",
            }

    clean_id = sanitize_cell_id(cell_id) or cell_path.stem
    rule_base = clean_id[:-3] if clean_id.endswith(".md") else clean_id
    if rule_base.startswith("rule-"):
        rule_base = rule_base[5:]
    if clean_id in PROTECTED_RULES or rule_base in PROTECTED_RULES:
        return {
            "status": "protected_rule_immutable",
            "message": f"Cannot promote cell into protected core rule namespace: '{cell_id}'",
        }

    if next_type == "genome":
        target_dir = workspace / "genome"
    else:
        target_dir = workspace / ".soma" / "cells" / TYPE_TO_DIR[next_type]

    target_path = target_dir / f"{clean_id}.md"
    if target_path.exists():
        return {
            "status": "target_exists",
            "message": f"Target already exists: {target_path}",
        }

    if dry_run:
        return {
            "status": "dry_run",
            "from_type": current_type,
            "to_type": next_type,
            "source_path": str(cell_path),
            "target_path": str(target_path),
        }

    with workspace_lock(workspace, "cells"):
        content = cell_path.read_text(encoding="utf-8")
        new_content = _transform_frontmatter_type(content, next_type)
        _atomic_write_and_unlink(cell_path, target_path, new_content)

    return {
        "status": "promoted",
        "from_type": current_type,
        "to_type": next_type,
        "source_path": str(cell_path),
        "target_path": str(target_path),
    }


def demote_cell(
    workspace: Path,
    cell_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute structural demotion for a cell (wall -> vacuole)."""
    clean_id = sanitize_cell_id(cell_id)
    if not clean_id:
        return {"status": "invalid_id", "message": f"Invalid cell ID: '{cell_id}'"}

    rule_base = clean_id
    if rule_base.startswith("rule-"):
        rule_base = rule_base[5:]

    if clean_id in PROTECTED_RULES or rule_base in PROTECTED_RULES:
        raise ValueError(f"Cannot demote protected core rule: '{cell_id}'")

    cell_path, current_type = find_cell_file(workspace, clean_id)
    if cell_path is None or current_type is None:
        return {
            "status": "not_found",
            "message": f"Cell '{clean_id}' not found in workspace",
        }

    next_type = DEMOTION_PATH.get(current_type)
    if next_type is None:
        return {
            "status": "already_base",
            "current_type": current_type,
            "message": f"Cell '{clean_id}' is at base level ('{current_type}') and cannot be demoted further",
        }

    target_dir = workspace / ".soma" / "cells" / TYPE_TO_DIR[next_type]
    target_path = target_dir / f"{clean_id}.md"
    if target_path.exists():
        return {
            "status": "target_exists",
            "message": f"Target already exists: {target_path}",
        }

    if dry_run:
        return {
            "status": "dry_run",
            "from_type": current_type,
            "to_type": next_type,
            "source_path": str(cell_path),
            "target_path": str(target_path),
        }

    with workspace_lock(workspace, "cells"):
        content = cell_path.read_text(encoding="utf-8")
        new_content = _transform_frontmatter_type(content, next_type)
        _atomic_write_and_unlink(cell_path, target_path, new_content)

        if current_type == "wall" and next_type == "vacuole":
            for pfx in ("check-", "gate-"):
                for sfx in (".sh", ".py"):
                    art = workspace / ".soma" / "enforcement" / f"{pfx}{clean_id}{sfx}"
                    if art.exists():
                        try:
                            art.unlink()
                        except Exception:
                            pass

    return {
        "status": "demoted",
        "from_type": current_type,
        "to_type": next_type,
        "source_path": str(cell_path),
        "target_path": str(target_path),
    }


# ── Cell Creation ──────────────────────────────────────────────────────────

def validate_cell_id(cell_id: str | None) -> None:
    """Validate cell ID to prevent path traversal attacks."""
    if not cell_id:
        return
    if "/" in cell_id or "\\" in cell_id or ".." in cell_id:
        raise ValueError(f"Invalid ID_OVERRIDE contains path traversal characters: {cell_id!r}")


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
    workspace: Path | str | None = None,
) -> Path:
    """Create a new Soma cell file with validated frontmatter and body."""
    validate_cell_id(id_override)

    type_lower = cell_type.lower()
    if type_lower not in VALID_TYPES:
        raise ValueError(
            f"Invalid type '{cell_type}'. Must be one of: vacuole, chloroplast, wall, membrane, plasmodesmata."
        )

    if effector and memory:
        raise ValueError("--effector and --memory are mutually exclusive.")

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

    ws = Path(workspace).resolve() if workspace else Path(resolve_workspace()).resolve()
    type_plural = VALID_TYPES[type_lower]
    target_dir = ws / ".soma" / "cells" / type_plural
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = generate_slug(hypothesis, id_override)
    file_path = target_dir / f"{slug}.md"

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

    if not file_path.is_file() or file_path.stat().st_size == 0:
        if file_path.exists():
            file_path.unlink()
        raise RuntimeError(f"Cell was not written correctly (empty file): {file_path}")

    read_back = file_path.read_text(encoding="utf-8")
    if read_back.count("---") < 2:
        raise ValueError(f"Cell frontmatter is malformed (missing closing '---'): {file_path}")

    return file_path


def cli_cell_create(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.help:
        print("Usage: cell_create.py --type <type> --hypothesis <hypo> [options]")
        return 0

    if args.cell_id:
        try:
            validate_cell_id(args.cell_id)
        except ValueError as e:
            print(f"Error: Invalid ID_OVERRIDE contains path traversal characters.", file=sys.stderr)
            return 1

    if args.description:
        script_dir = Path(__file__).resolve().parent.parent / "enzymes"
        nl_script = script_dir / "cell_create_nl.py"
        extra_args = []
        if args.cell_id:
            extra_args.extend(["--id", args.cell_id])
        if args.cell_type:
            extra_args.extend(["--type", args.cell_type])
        if args.domain:
            extra_args.extend(["--domain", args.domain])
        cmd = [sys.executable, str(nl_script), args.description, *extra_args]
        res = subprocess.run(cmd)
        return res.returncode

    if not args.cell_type or not args.hypothesis:
        print("Error: Missing required arguments --type and --hypothesis", file=sys.stderr)
        return 1

    hypo = args.hypothesis
    tag_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
    paths = [p.strip() for p in args.target_paths.split(",") if p.strip()] if args.target_paths else None

    try:
        created = create_cell(
            cell_type=args.cell_type,
            hypothesis=hypo,
            prediction=args.prediction,
            falsification=args.falsification,
            weight=args.weight,
            tags=tag_list,
            expiry_sessions=args.expiry_sessions,
            expiry_days=args.expiry_days,
            minimum_mode=args.minimum_mode,
            id_override=args.cell_id or None,
            effector=args.effector,
            memory=args.memory,
            target_paths=paths,
            domain=args.domain,
        )
        print(f"Created cell: {created}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Execution failed: {e}", file=sys.stderr)
        return 1


# ── Cell Transfer ──────────────────────────────────────────────────────────

def transfer_cell(
    cell_id: str,
    target_dir_str: str,
    source_workspace: Path | None = None,
) -> int:
    """Transfer a cell from source workspace to target directory with fitness reset."""
    repo_dir = source_workspace or Path(resolve_workspace()).resolve()
    if not (repo_dir / ".soma" / "cells").is_dir():
        print(f"Error: No Soma project found: no .soma/cells/ in {repo_dir or os.getcwd()} or any parent directory.", file=sys.stderr)
        print("Run from inside the source project, or set SOMA_ROOT to its root.", file=sys.stderr)
        return 1

    target_dir = Path(target_dir_str).resolve()
    if not (target_dir / ".soma").is_dir():
        print(f"Error: Target directory does not have a .soma/ directory: {target_dir}", file=sys.stderr)
        return 1

    source_path = None
    cells_dir = repo_dir / ".soma" / "cells"
    for cand in cells_dir.rglob("*.md"):
        if cand.name == "README.md":
            continue
        if cand.stem == cell_id or cell_id in cand.name:
            source_path = cand
            break

    if not source_path:
        print(f"Error: Could not find cell '{cell_id}' in {cells_dir}", file=sys.stderr)
        return 1

    try:
        content = source_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content) or {}
    except Exception as exc:
        print(f"Error reading cell {source_path}: {exc}", file=sys.stderr)
        return 1

    meta["fitness"] = {
        "triggers": 0,
        "true_positives": 0,
        "false_positives": 0,
        "score": None,
    }
    lineage = meta.get("lineage") or {}
    if isinstance(lineage, dict):
        lineage["parent_id"] = source_path.stem
        lineage["generation"] = int(lineage.get("generation", 0)) + 1
        lineage["created_by"] = "transfer"
        meta["lineage"] = lineage

    target_sub = source_path.parent.name
    dest_dir = target_dir / ".soma" / "cells" / target_sub
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source_path.name

    if yaml is not None:
        new_fm = yaml.dump(meta, sort_keys=False, default_flow_style=False)
    else:
        new_fm = dump_frontmatter(meta)

    end_idx = content.find("---", 3)
    body = content[end_idx + 3:].lstrip() if end_idx != -1 else ""
    new_content = f"---\n{new_fm.strip()}\n---\n\n{body}\n" if body else f"---\n{new_fm.strip()}\n---\n"
    dest_path.write_text(new_content, encoding="utf-8")

    metrics_dir = repo_dir / ".soma" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    log_file = metrics_dir / "transfers.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cell": source_path.name,
            "target": str(target_dir),
        }) + "\n")

    print(f"Transferred: {source_path.name} -> {dest_path}")
    return 0


def cli_cell_transfer(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copies a cell to another project with fitness reset")
    parser.add_argument("cell_id", nargs="?", default="", help="ID of cell to transfer")
    parser.add_argument("--to", dest="target_dir", default="", help="Path to target project")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.cell_id or not args.target_dir:
        print("Error: Missing cell_id or --to directory", file=sys.stderr)
        return 1

    return transfer_cell(cell_id=args.cell_id, target_dir_str=args.target_dir)


# ── Cell Promotion & Demotion Engines ──────────────────────────────────────

def apply_decay(meta: dict) -> None:
    """Apply exponential decay to cell metadata in-place."""
    fitness = meta.get('fitness')
    if not isinstance(fitness, dict):
        return
    now = int(time.time())
    last_decay = fitness.get('last_decay_epoch', 0)
    if now - last_decay < 3600:
        return
    triggers = fitness.get('triggers', 0)
    tp = fitness.get('true_positives', 0)
    fp = fitness.get('false_positives', 0)
    if triggers > 0:
        fitness['triggers'] = max(1, int(triggers * 0.95))
        fitness['true_positives'] = max(0, int(tp * 0.95))
        fitness['false_positives'] = max(0, int(fp * 0.95))
    fitness['last_decay_epoch'] = now


def normalize_fitness(metadata: dict) -> dict:
    """Normalize fitness dictionary in cell metadata."""
    fitness = metadata.get('fitness', {})
    if isinstance(fitness, (int, float)):
        return {'score': float(fitness), 'impact_weight': 1.0}
    if isinstance(fitness, str):
        try:
            return {'score': float(fitness), 'impact_weight': 1.0}
        except ValueError:
            return {'score': None, 'impact_weight': 1.0}
    if not isinstance(fitness, dict):
        return {'score': None, 'impact_weight': 1.0}
    return fitness


def resolve_metrics_dir(workspace: Path | str) -> Path:
    from soma_core.telemetry import resolve_metrics_dir as _res_metrics
    return _res_metrics(workspace)


def cli_cell_promote(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote high-fitness cells to global rules.")
    parser.add_argument("--dry-run", action="store_true", help="Print promotion candidates without writing rules")
    parser.add_argument("--local", action="store_true", help="Promote locally based on current repo's cells")
    parser.add_argument("--enforce", action="store_true", help="Promote enforcement tier (advisory -> mechanical -> gate)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    ws_path = Path(workspace)

    if args.enforce:
        cells_dir = ws_path / ".soma" / "cells"
        for fpath in cells_dir.rglob("*.md"):
            if fpath.name == "README.md":
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
                meta = parse_frontmatter(content) or {}
            except Exception:
                continue

            fitness = normalize_fitness(meta)
            triggers = fitness.get("triggers", 0)
            tp = fitness.get("true_positives", 0)
            fp = fitness.get("false_positives", 0)
            tier = meta.get("enforcement", "advisory")

            new_tier = tier
            if triggers >= 10 and tp >= 8 and fp <= 1:
                new_tier = "gate"
            elif triggers >= 5 and tp >= 4:
                new_tier = "mechanical"

            if new_tier != tier and not args.dry_run:
                meta["enforcement"] = new_tier
                if yaml is not None:
                    nfm = yaml.dump(meta, sort_keys=False, default_flow_style=False)
                else:
                    nfm = dump_frontmatter(meta)
                end_idx = content.find("---", 3)
                body = content[end_idx + 3:].lstrip() if end_idx != -1 else ""
                fpath.write_text(f"---\n{nfm.strip()}\n---\n\n{body}\n" if body else f"---\n{nfm.strip()}\n---\n", encoding="utf-8")
                print(f"Promoted enforcement for {fpath.name}: {tier} -> {new_tier}")
        return 0

    cells_dir = ws_path / ".soma" / "cells"
    candidates = []
    for fpath in cells_dir.rglob("*.md"):
        if fpath.name == "README.md":
            continue
        try:
            content = fpath.read_text(encoding="utf-8")
            meta = parse_frontmatter(content) or {}
        except Exception:
            continue
        fitness = normalize_fitness(meta)
        meta["fitness"] = fitness
        apply_decay(meta)
        triggers = fitness.get("triggers", 0)
        tp = fitness.get("true_positives", 0)
        if triggers >= 20:
            score = laplace_score(tp, triggers)
            if score > 0.85:
                candidates.append((fpath, meta, score))

    if not candidates:
        print("No candidates found for promotion.")
        return 0

    print(f"Found {len(candidates)} candidate(s) for promotion.")
    for fpath, meta, score in candidates:
        res = promote_cell(ws_path, fpath.stem, dry_run=args.dry_run)
        print(f"Promotion {fpath.stem}: {res.get('status')} ({res.get('message', '')})")
    return 0


def cli_cell_demote(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demote a global rule back to a local cell.")
    parser.add_argument("rule_name", help="The name of the rule to demote (e.g. rule-trap-walls)")
    parser.add_argument("--reason", required=True, help="Reason for demotion")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    ws_path = Path(workspace)

    rule_name = args.rule_name[:-3] if args.rule_name.endswith(".md") else args.rule_name
    rule_base = rule_name[5:] if rule_name.startswith("rule-") else rule_name

    if rule_base in PROTECTED_RULES or rule_name in PROTECTED_RULES:
        print(f"Cannot demote core rule: {rule_name}. Only promoted cells can be demoted.", file=sys.stderr)
        return 1

    try:
        res = demote_cell(ws_path, rule_name)
        print(f"Demoted: {rule_name} -> {res.get('target_path')} (reason: {args.reason})")
        return 0
    except Exception as exc:
        print(f"Demotion failed: {exc}", file=sys.stderr)
        return 1


# ── Cell Metamorphosis & Adaptation ────────────────────────────────────────

def metamorphose_cell(workspace: Path | str, cell_id: str) -> dict:
    """Transforms cell between types based on maturity criteria."""
    ws = Path(workspace).resolve()
    cells_dir = ws / ".soma" / "cells"
    matches = list(cells_dir.rglob(f"*{cell_id}*.md"))
    if not matches:
        return {"status": "not_found", "message": f"Cell '{cell_id}' not found"}

    cell_path = matches[0]
    content = cell_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(content) or {}
    current_type = meta.get("type")
    if not current_type or current_type not in METAMORPHOSIS_PATHS:
        return {"status": "no_paths", "type": current_type}

    fitness = meta.get("fitness") or {}
    triggers = fitness.get("triggers", 0)
    tp = fitness.get("true_positives", 0)
    score = fitness.get("score") or (tp / triggers if triggers > 0 else 0)

    best_path = None
    for p in METAMORPHOSIS_PATHS[current_type]:
        if score >= p["min_fitness"] and triggers >= p["min_sessions"]:
            best_path = p
            break

    if not best_path:
        return {"status": "not_mature", "score": score, "triggers": triggers}

    new_type = best_path["target"]
    meta["type"] = new_type
    meta["metamorphosed_from"] = current_type
    meta["metamorphosis_date"] = datetime.now(timezone.utc).isoformat() + "Z"

    if new_type == "rule":
        target_dir = ws / "genome"
        target_path = target_dir / f"rule-{cell_path.name}"
    else:
        target_dir = cells_dir / f"{new_type}s"
        target_path = target_dir / cell_path.name

    target_dir.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        nfm = yaml.dump(meta, sort_keys=False, default_flow_style=False)
    else:
        nfm = dump_frontmatter(meta)

    end_idx = content.find("---", 3)
    body = content[end_idx + 3:].lstrip() if end_idx != -1 else ""
    target_path.write_text(f"---\n{nfm.strip()}\n---\n\n{body}\n" if body else f"---\n{nfm.strip()}\n---\n", encoding="utf-8")
    cell_path.unlink()

    return {
        "status": "metamorphosed",
        "cell": cell_path.name,
        "from_type": current_type,
        "to_type": new_type,
        "fitness_score": score,
        "triggers": triggers,
    }


def cli_cell_metamorphose(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transforms cells between types based on maturity criteria.")
    parser.add_argument("cell_id", help="The ID of the cell to metamorphose")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    res = metamorphose_cell(workspace, args.cell_id)
    if res["status"] == "metamorphosed":
        print(f"Metamorphosis: {res['cell']} ({res['from_type']} -> {res['to_type']}) [fitness: {res['fitness_score']:.2f}, triggers: {res['triggers']}]")
        return 0
    elif res["status"] == "not_mature":
        print(f"Not yet mature for metamorphosis (score: {res['score']:.2f}, triggers: {res['triggers']})")
        return 0
    else:
        print(f"Metamorphosis check: {res.get('message', res['status'])}")
        return 1


def adapt_cell(workspace: Path | str, generate: bool = False) -> list[dict]:
    """Scan and adapt cells with middling fitness scores."""
    ws = Path(workspace).resolve()
    cells_dir = ws / ".soma" / "cells"
    results = []

    for fpath in cells_dir.rglob("*.md"):
        if fpath.name == "README.md":
            continue
        try:
            content = fpath.read_text(encoding="utf-8")
            meta = parse_frontmatter(content) or {}
        except Exception:
            continue

        fitness = meta.get("fitness") or {}
        triggers = fitness.get("triggers", 0)
        tp = fitness.get("true_positives", 0)
        fp = fitness.get("false_positives", 0)
        impact = meta.get("impact_weight", 1.0)
        if triggers == 0:
            continue
        score = (tp / triggers) * impact

        if 0.3 <= score <= 0.7:
            suggestion = "narrowing the hypothesis scope" if fp > tp * 1.5 else (
                "broadening the trigger conditions" if triggers < 5 else "splitting into two more specific cells"
            )
            item = {
                "cell": fpath.name,
                "score": score,
                "tp": tp,
                "fp": fp,
                "suggestion": suggestion,
            }
            results.append(item)

            if generate:
                v2_name = f"{fpath.stem}_v2.md"
                v2_path = fpath.parent / v2_name
                meta_v2 = dict(meta)
                meta_v2["hypothesis"] = meta_v2.get("hypothesis", "") + " (Refined)"
                meta_v2["fitness"] = {"triggers": 0, "true_positives": 0, "false_positives": 0, "score": None}
                meta_v2["lineage"] = [fpath.name]
                meta_v2["created"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if yaml is not None:
                    nfm = yaml.dump(meta_v2, sort_keys=False, default_flow_style=False)
                else:
                    nfm = dump_frontmatter(meta_v2)
                end_idx = content.find("---", 3)
                body = content[end_idx + 3:].lstrip() if end_idx != -1 else ""
                v2_path.write_text(f"---\n{nfm.strip()}\n---\n\n{body}\n" if body else f"---\n{nfm.strip()}\n---\n", encoding="utf-8")
                item["generated"] = str(v2_path)

    return results


def cli_cell_adapt(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adapt immune cells based on fitness.")
    parser.add_argument("--generate", action="store_true", help="Generate v2 cells for adaptation candidates")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    adapts = adapt_cell(workspace, generate=args.generate)

    print(f"{'Cell':<30} | {'Score':<5} | {'TP/FP':<7} | {'Suggestion'}")
    print("-" * 80)
    for a in adapts:
        print(f"{a['cell']:<30} | {a['score']:<5.2f} | {a['tp']}/{a['fp']:<4} | Suggest {a['suggestion']}")
        if "generated" in a:
            print(f"  -> Generated {a['generated']}")
    return 0


# ── Cell Selection & Crossover ─────────────────────────────────────────────

def run_cell_selection(workspace: Path | str | None = None, execute: bool = False) -> int:
    """Selection pressure engine for Soma immune cells."""
    repo_root = Path(workspace).resolve() if workspace else Path(resolve_workspace()).resolve()
    cells_dir = repo_root / ".soma" / "cells"
    archive_dir = cells_dir / ".archive"
    evidence_dir = repo_root / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    fitness_log = evidence_dir / "lifecycle.jsonl"

    if not cells_dir.exists():
        print("No cells directory found.")
        return 0

    print(f"Running cell selection (execute={execute})...")
    if execute:
        archive_dir.mkdir(parents=True, exist_ok=True)

    for root_str, _dirs, files in os.walk(cells_dir):
        if ".archive" in root_str:
            continue
        for f in files:
            if not f.endswith(".md") or f == "README.md":
                continue
            fpath = Path(root_str) / f
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue

            fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)

            def get_val(key: str, default: float = 0.0) -> float:
                m = re.search(rf"{key}:\s*(\S+)", fm)
                if m and m.group(1) != "null":
                    try:
                        return float(m.group(1))
                    except ValueError:
                        return default
                return default

            triggers = get_val("triggers", 0.0)
            tp = get_val("true_positives", 0.0)
            fp = get_val("false_positives", 0.0)
            type_match = re.search(r"type:\s*([^\s\n]+)", fm)
            cell_type = type_match.group(1) if type_match else ""
            dormant = "dormant_since" in fm

            if triggers == 0:
                category = "DORMANT"
                score = 0.0
            else:
                score = tp / triggers
                if fp > 0 and tp > 0 and fp > 2 * tp:
                    category = "APOPTOSIS_WARNING" if cell_type == "wall" else "APOPTOSIS"
                elif score > 0.7:
                    category = "SURVIVE"
                elif score >= 0.3:
                    category = "ADAPT"
                else:
                    category = "EXTINCT"

            print(f"[{category}] {f} (Score: {score:.2f})")

            if execute:
                action = None
                if category in ("EXTINCT", "APOPTOSIS"):
                    if category == "APOPTOSIS":
                        last_gasp_dir = cells_dir / ".last_gasp_queue"
                        last_gasp_dir.mkdir(parents=True, exist_ok=True)
                        dest = last_gasp_dir / f
                        shutil.move(str(fpath), str(dest))
                        action = "last_gasp_requested"
                    else:
                        dest = archive_dir / f
                        shutil.move(str(fpath), str(dest))
                        action = "moved_to_archive"
                elif category == "DORMANT" and not dormant:
                    timestamp = datetime.now(timezone.utc).isoformat() + "Z"
                    new_content = content.replace("fitness:", f"dormant_since: {timestamp}\nfitness:")
                    fpath.write_text(new_content, encoding="utf-8")
                    action = "marked_dormant"

                if action:
                    with open(fitness_log, "a", encoding="utf-8") as log:
                        log.write(json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                            "cell": f,
                            "action": action,
                        }) + "\n")
    return 0


def cli_cell_selection(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Selection pressure engine for Soma immune cells")
    parser.add_argument("--execute", action="store_true", default=False, help="Execute selection decisions")
    parser.add_argument("--workspace", type=str, default="", help="Path to workspace root")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    ws = Path(args.workspace) if args.workspace else None
    return run_cell_selection(workspace=ws, execute=args.execute)


def find_cell(workspace: Path | str, cell_id: str) -> Optional[str]:
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    matches = glob.glob(os.path.join(cells_dir, '**', f'*{cell_id}*'), recursive=True)
    matches = [m for m in matches if os.path.isfile(m) and m.endswith('.md')]
    return matches[0] if matches else None


def parse_cell(file_path: Path | str) -> tuple[Optional[dict], str]:
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        end_idx = content.find("---", 3)
        body = content[end_idx + 3:].lstrip() if end_idx != -1 else ""
        return meta, body
    except Exception:
        return None, ""


def get_type_plural(cell_type: str) -> str:
    cell_type = cell_type.lower()
    return VALID_TYPES.get(cell_type, "vacuoles")


def crossover_cells(workspace: Path | str, cell_a_id: str, cell_b_id: str) -> tuple[str, str, str]:
    """Merge complementary hypotheses from two high-fitness cells."""
    cell_a_path = find_cell(workspace, cell_a_id)
    cell_b_path = find_cell(workspace, cell_b_id)

    if not cell_a_path or not cell_b_path:
        raise ValueError(f"Could not locate one or both parent cells: {cell_a_id}, {cell_b_id}")

    meta_a, body_a = parse_cell(cell_a_path)
    meta_b, body_b = parse_cell(cell_b_path)

    if not meta_a or not meta_b:
        raise ValueError("One or both parent cells lack valid YAML frontmatter.")

    hyp_a = meta_a.get('hypothesis', '').strip()
    hyp_b = meta_b.get('hypothesis', '').strip()
    merged_hypothesis = f"{hyp_a}, prioritizing {hyp_b}"

    pred_a = meta_a.get('prediction', '').strip()
    pred_b = meta_b.get('prediction', '').strip()
    merged_prediction = f"{pred_a}\n\n{pred_b}".strip()

    weight_a = meta_a.get('impact_weight', 1.0)
    weight_b = meta_b.get('impact_weight', 1.0)
    merged_weight = max(weight_a, weight_b)

    type_a = meta_a.get('type', 'vacuole')
    type_b = meta_b.get('type', 'vacuole')
    merged_type = type_a if type_a == type_b else 'vacuole'

    slug = re.sub(r'[^a-z0-9 ]', '', merged_hypothesis.lower())
    slug = re.sub(r'\s+', '-', slug)[:50].strip('-')

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    type_plural = get_type_plural(merged_type)
    out_dir = os.path.join(workspace, '.soma', 'cells', type_plural)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{slug}.md")

    tp_a = meta_a.get('target_paths', []) or []
    tp_b = meta_b.get('target_paths', []) or []
    if isinstance(tp_a, str): tp_a = [tp_a]
    if isinstance(tp_b, str): tp_b = [tp_b]
    merged_target_paths = sorted(set(tp_a + tp_b))

    tags_a = meta_a.get('tags', []) or []
    tags_b = meta_b.get('tags', []) or []
    if isinstance(tags_a, str): tags_a = [tags_a]
    if isinstance(tags_b, str): tags_b = [tags_b]
    merged_tags = sorted(set(tags_a + tags_b))

    gen_a = meta_a.get('lineage', {}).get('generation', 0) if isinstance(meta_a.get('lineage'), dict) else 0
    gen_b = meta_b.get('lineage', {}).get('generation', 0) if isinstance(meta_b.get('lineage'), dict) else 0
    merged_generation = max(gen_a, gen_b) + 1

    new_meta = {
        'type': merged_type,
        'hypothesis': merged_hypothesis,
        'prediction': merged_prediction,
        'falsification': "Falsification criteria combined or needs review.",
        'target_paths': merged_target_paths,
        'expiry_sessions': 15,
        'expiry_days': 60,
        'created': date_str,
        'impact_weight': merged_weight,
        'tags': merged_tags,
        'lineage': {
            'parent_id': f"{cell_a_id} × {cell_b_id}",
            'created_by': "crossover",
            'generation': merged_generation,
            'siblings': [],
        },
        'fitness': {
            'triggers': 0,
            'true_positives': 0,
            'false_positives': 0,
            'score': None,
        }
    }

    if yaml is not None:
        nfm = yaml.dump(new_meta, sort_keys=False, default_flow_style=False)
    else:
        nfm = dump_frontmatter(new_meta)

    content = f"---\n{nfm.strip()}\n---\n\n## {merged_type.capitalize()}: {merged_hypothesis[:60]}\n\n{merged_hypothesis}\n\n### Prediction\n{merged_prediction}\n"
    with open(out_path, 'w', encoding="utf-8") as f:
        f.write(content)

    return os.path.basename(cell_a_path), os.path.basename(cell_b_path), os.path.basename(out_path)


def cli_cell_crossover(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge complementary hypotheses from two high-fitness cells")
    parser.add_argument("cell_a_id", help="ID of the first parent cell")
    parser.add_argument("cell_b_id", help="ID of the second parent cell")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = resolve_workspace()
    try:
        pa, pb, out = crossover_cells(workspace, args.cell_a_id, args.cell_b_id)
        print(f"Crossover: {pa} × {pb} → {out}")
        return 0
    except Exception as exc:
        print(f"Crossover failed: {exc}", file=sys.stderr)
        return 1


# ── Cell Fitness Evaluation ────────────────────────────────────────────────

def bayesian_fitness(tp: int, fp: int, confidence: float = 0.90) -> dict:
    """Wilson-bounded posterior with Jeffrey's prior."""
    return bayesian_posterior(tp=tp, fp=fp, confidence=confidence)


def antifragile_bonus(metadata: dict) -> float:
    """Cells gain +5% fitness per survived high-intensity review."""
    stress_events = metadata.get('fitness', {}).get('stress_survived', 0)
    return 1.0 + (0.05 * min(stress_events, 10))


def format_snr(value: Any) -> str:
    """Render an SNR value for human-readable table output."""
    if value is None:
        return '\u221e'
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def decayed_fitness(raw_score: Optional[float], last_trigger_date: Any, telomere_days: float = 30) -> Optional[float]:
    if last_trigger_date is None or raw_score is None:
        return raw_score
    try:
        t_days = float(telomere_days)
    except (TypeError, ValueError):
        t_days = 30.0
    if t_days <= 0:
        return raw_score
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    trigger_utc = last_trigger_date.replace(tzinfo=None) if getattr(last_trigger_date, 'tzinfo', None) else last_trigger_date
    days_since = max(0, (now_utc - trigger_utc).days)
    decay_factor = 0.5 ** (days_since / t_days)
    return round(raw_score * decay_factor, 4)


def cli_cell_fitness(argv: list[str] | None = None, workspace: Optional[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Compute fitness of immune cells")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--prune", action="store_true", help="List cells recommended for removal")
    parser.add_argument("--promote", action="store_true", help="List cells ready for cross-repo promotion")
    parser.add_argument("--cross-repo", action="store_true", help="Aggregate fitness across multiple repos")
    parser.add_argument("--bayesian", action="store_true", help="Output bayesian estimates")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    ws = workspace or resolve_workspace(start=__file__)
    total_sessions = 30
    conf_path = os.path.join(ws, "soma.conf")
    if os.path.exists(conf_path):
        try:
            with open(conf_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("TOTAL_SESSIONS="):
                        total_sessions = int(line.strip().split("=", 1)[1])
        except Exception:
            pass

    cells_dir = os.path.join(ws, '.soma', 'cells')
    cell_files = glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)
    results = []

    for file_path in cell_files:
        if os.path.basename(file_path) == 'README.md':
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                metadata = parse_frontmatter(fh.read()) or {}
        except Exception:
            continue

        cell_name = os.path.basename(file_path)
        cell_type = metadata.get('type', 'unknown')
        fitness = metadata.get('fitness', {})
        if isinstance(fitness, (int, float)):
            fitness = {'score': float(fitness)}
            metadata['fitness'] = fitness

        triggers = fitness.get('triggers', 0)
        tp = fitness.get('true_positives', 0)
        fp = fitness.get('false_positives', 0)
        impact_weight = metadata.get('impact_weight', 1.0)

        if triggers == 0:
            score = bayesian_score(0, 0, impact_weight)
            snr_db = 0.0
            is_unobserved = True
        else:
            score = bayesian_score(tp, triggers, impact_weight)
            is_unobserved = False
            trigger_rate = triggers / max(total_sessions, 1)
            specificity_penalty = 1.0 - min(trigger_rate, 1.0)
            if trigger_rate > 0.8:
                score = score * specificity_penalty
            score = score * antifragile_bonus(metadata)

            if tp > 0 and fp > 0:
                snr_db = round(10 * math.log10(tp / fp), 1)
            elif tp > 0:
                snr_db = None
            else:
                snr_db = 0.0

        last_trigger_date_str = fitness.get('last_trigger_date')
        last_trigger_date = None
        if last_trigger_date_str:
            try:
                last_trigger_date = datetime.fromisoformat(last_trigger_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                pass

        hl_val = os.environ.get(f'CELL_TELOMERE_{cell_type.upper()}') or os.environ.get('CELL_TELOMERE_DAYS', '30')
        if hl_val == 'null':
            dec_score = score
        else:
            telomere_days = int(hl_val)
            dec_score = decayed_fitness(score, last_trigger_date, telomere_days)

        expiry_days = metadata.get('expiry_days')
        created_str = metadata.get('created')
        status = calculate_fitness_status(cell_type, tp, fp, triggers, dec_score, is_unobserved, created_str, expiry_days)

        enforcement = metadata.get('enforcement', 'advisory')
        tier_weights = {'advisory': 1.0, 'mechanical': 1.2, 'gate': 1.5}
        tier_weight = tier_weights.get(enforcement, 1.0)
        enhanced_score = round(score * tier_weight, 4) if score is not None else None

        res = {
            "cell": cell_name,
            "type": cell_type,
            "hypothesis": metadata.get('hypothesis', ''),
            "triggers": triggers,
            "tp": tp,
            "fp": fp,
            "score": score,
            "decayed_score": dec_score,
            "status": status,
            "snr_db": snr_db,
            "enforcement": enforcement,
            "enhanced_fitness": enhanced_score,
        }
        if args.bayesian:
            res['bayesian'] = bayesian_fitness(tp, fp)
        results.append(res)

    if args.prune:
        results = [r for r in results if r['status'] in ("EXTINCT", "DORMANT")]
    elif args.promote:
        results = [r for r in results if r['score'] is not None and r['score'] > 0.7 and r.get('triggers', 0) > 0]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'Cell':<20} | {'Type':<12} | {'Tier':<10} | {'Triggers':<8} | {'TP':<4} | {'FP':<4} | {'Esc':<3} | {'EnhFit':<6} | {'Raw':<6} | {'Status':<10} | {'SNR':<5}")
        print("-" * 110)
        for r in results:
            score_str = f"{r['score']:.2f}" if r['score'] is not None else "null"
            enh_str = f"{r['enhanced_fitness']:.2f}" if r['enhanced_fitness'] is not None else "null"
            snr_str = format_snr(r.get('snr_db', 0.0))
            print(f"{r['cell']:<20} | {r['type']:<12} | {r.get('enforcement', 'advisory'):<10} | {r['triggers']:<8} | {r['tp']:<4} | {r['fp']:<4} | 0   | {enh_str:<6} | {score_str:<6} | {r['status']:<10} | {snr_str:<5}")
    return 0


__all__ = [
    "STATUS_NEW",
    "STATUS_SURVIVE",
    "STATUS_ADAPT",
    "STATUS_EXTINCT",
    "STATUS_APOPTOSIS",
    "STATUS_APOPTOSIS_WARNING",
    "STATUS_DORMANT",
    "PROTECTED_RULES",
    "PROMOTION_PATH",
    "DEMOTION_PATH",
    "TYPE_TO_DIR",
    "EXTINCTION_THRESHOLD",
    "PROMOTION_THRESHOLD",
    "MIN_PROMOTION_TRIGGERS",
    "DEFAULT_DECAY_FACTOR",
    "VALID_TYPES",
    "METAMORPHOSIS_PATHS",
    "calculate_fitness_status",
    "is_promotable",
    "is_extinct",
    "apply_exponential_decay",
    "sanitize_cell_id",
    "find_cell_file",
    "promote_cell",
    "demote_cell",
    "validate_cell_id",
    "generate_slug",
    "create_cell",
    "cli_cell_create",
    "transfer_cell",
    "cli_cell_transfer",
    "apply_decay",
    "normalize_fitness",
    "resolve_metrics_dir",
    "cli_cell_promote",
    "cli_cell_demote",
    "metamorphose_cell",
    "cli_cell_metamorphose",
    "adapt_cell",
    "cli_cell_adapt",
    "run_cell_selection",
    "cli_cell_selection",
    "find_cell",
    "parse_cell",
    "get_type_plural",
    "crossover_cells",
    "cli_cell_crossover",
    "bayesian_fitness",
    "antifragile_bonus",
    "format_snr",
    "decayed_fitness",
    "cli_cell_fitness",
]
