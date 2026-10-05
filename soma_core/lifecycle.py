"""soma_core.lifecycle — Canonical cell lifecycle state machine and promotion engine.

Single source of truth for:
- Cell lifecycle status evaluation (NEW, SURVIVE, ADAPT, EXTINCT, APOPTOSIS, DORMANT)
- Boundary thresholds for promotion and extinction
- Exponential fitness decay with idempotency fencing
- Protected core rules enforcement
- Structural transitions (vacuole -> wall -> genome) and demotions
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from soma_core.frontmatter import parse_frontmatter
from soma_core.locking import workspace_lock
from soma_sdk.scoring import laplace_score

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
    # Apoptosis: immediate eviction or warning if false positives dominate (including tp == 0)
    if fp > 0 and (tp == 0 or fp > 2 * tp):
        return STATUS_APOPTOSIS_WARNING if cell_type == "wall" else STATUS_APOPTOSIS

    if not is_unobserved and dec_score is not None:
        if dec_score > 0.7:
            return STATUS_SURVIVE
        elif dec_score > EXTINCTION_THRESHOLD:
            return STATUS_ADAPT
        else:
            return STATUS_EXTINCT

    # Unobserved cell: determine if fresh (NEW) or stale (DORMANT)
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
    """Decay historical fitness data so recent signals carry greater weight.

    Prevents Beta-locking while guarding idempotency via last_decay_epoch.
    """
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
                # Strip enforcement when demoting to vacuole
                pass
            else:
                new_lines.append(line)
        elif stripped.startswith("enforcement_artifact:"):
            if new_type == "vacuole":
                # Strip enforcement artifact when demoting to vacuole
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
    """Update type field in cell frontmatter preserving body and comments."""
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

    # Evaluate fitness criteria unless force is specified
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

        # Clean up gate enforcement artifacts when demoting from wall to vacuole
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
