"""soma status — Show active rules and stats."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime
import json
from pathlib import Path

from soma_cli import resolve_root

import yaml


def _repo_root(args: argparse.Namespace) -> Path:
    """Find the Soma install root (where genome/ lives)."""
    return resolve_root(args, default=Path(__file__).resolve().parent.parent)


def _project_root(args: argparse.Namespace) -> Path:
    """Find the project root (where .soma/ lives)."""
    return resolve_root(args)


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter if present."""
    stripped = content.lstrip()
    if stripped.startswith("---"):
        end = stripped.find("---", 3)
        if end != -1:
            try:
                fm = yaml.safe_load(stripped[3:end])
                if isinstance(fm, dict):
                    return fm
            except Exception:
                pass
    return {}


def _parse_created_date(created_val) -> date | None:
    """Parse a created date from frontmatter."""
    if created_val is None:
        return None
    if isinstance(created_val, datetime):
        return created_val.date()
    if isinstance(created_val, date):
        return created_val
    if isinstance(created_val, (int, float)):
        try:
            return datetime.fromtimestamp(created_val).date()
        except Exception:
            return None
    if isinstance(created_val, str):
        s = created_val.strip().rstrip("Z")
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            pass
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    return None


def _format_adaptive_expiry(created_val, expiry_days_val) -> str:
    """Calculate remaining days for an adaptive rule."""
    if expiry_days_val is None or created_val is None:
        return "—"
    try:
        expiry_days = int(expiry_days_val)
    except (ValueError, TypeError):
        return "—"

    created_date = _parse_created_date(created_val)
    if created_date is None:
        return "—"

    days_elapsed = (date.today() - created_date).days
    remaining_days = expiry_days - days_elapsed
    if remaining_days < 0:
        return "expired"
    return f"{remaining_days}d"


def _read_trigger_counts(fitness_file: Path) -> dict[str, int]:
    """Read trigger counts per cell_id from fitness.jsonl."""
    counts: dict[str, int] = defaultdict(int)
    if not fitness_file.is_file():
        return counts

    try:
        with open(fitness_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if isinstance(data, dict):
                        cid = data.get("cell_id")
                        if cid:
                            counts[str(cid)] += 1
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception:
        pass

    return counts


def run_status(args: argparse.Namespace) -> int:
    """Show active rules and stats."""
    root = _repo_root(args)
    proj = _project_root(args)

    # 1. Count core rules: .md files in genome/ and genome/.oracles/ (exclude README.md)
    core_files: list[Path] = []
    genome_dir = root / "genome"
    if genome_dir.is_dir():
        for p in sorted(genome_dir.glob("*.md")):
            if p.is_file() and p.name.lower() != "readme.md":
                core_files.append(p)
    oracles_dir = genome_dir / ".oracles"
    if oracles_dir.is_dir():
        for p in sorted(oracles_dir.glob("*.md")):
            if p.is_file() and p.name.lower() != "readme.md":
                core_files.append(p)

    # 2. Count adaptive rules: .md files in .soma/cells/ recursively (exclude README.md)
    adaptive_files: list[Path] = []
    cells_dir = proj / ".soma" / "cells"
    if cells_dir.is_dir():
        for p in sorted(cells_dir.rglob("*.md")):
            if p.is_file() and p.name.lower() != "readme.md":
                adaptive_files.append(p)

    # 3. Read trigger counts from .soma/evidence/fitness.jsonl
    fitness_file = proj / ".soma" / "evidence" / "fitness.jsonl"
    trigger_counts = _read_trigger_counts(fitness_file)

    # 4. Process all rules and calculate character overhead
    total_chars = 0
    all_rules: list[dict] = []

    for f in core_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            content = ""
        total_chars += len(content)
        fm = _parse_frontmatter(content)
        rule_name = str(fm.get("id") or f.stem)
        triggers = trigger_counts.get(rule_name, trigger_counts.get(f.stem, 0))
        all_rules.append({
            "name": rule_name,
            "triggers": triggers,
            "expiry": "∞ (core)",
            "is_core": True,
        })

    for f in adaptive_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            content = ""
        total_chars += len(content)
        fm = _parse_frontmatter(content)
        rule_name = str(fm.get("id") or f.stem)
        triggers = trigger_counts.get(rule_name, trigger_counts.get(f.stem, 0))
        expiry_str = _format_adaptive_expiry(fm.get("created"), fm.get("expiry_days"))
        all_rules.append({
            "name": rule_name,
            "triggers": triggers,
            "expiry": expiry_str,
            "is_core": False,
        })

    # Context load: total characters / 4
    estimated_tokens = total_chars // 4

    # Print summary
    print("📊 Soma Status\n")
    print(f"  {'Core rules:':<16}{len(core_files)} active")
    print(f"  {'Adaptive rules:':<16}{len(adaptive_files)} (traps/patterns)")
    print(f"  {'Context load:':<16}~{estimated_tokens:,} tokens (estimated)\n")

    if not all_rules:
        print("  No rules found. Run 'soma init' to set up governance rules.")
        return 0

    # Sort rules: triggers descending, then core rules first, then name
    all_rules.sort(key=lambda r: (-r["triggers"], not r["is_core"], r["name"]))

    # Table formatting
    rule_width = max(25, max((len(r["name"]) + 2 for r in all_rules), default=25))
    sep_len = max(42, rule_width + 17)

    print(f"  {'Rule':<{rule_width}}{'Triggers':<10}Expiry")
    print(f"  {'─' * sep_len}")
    for r in all_rules:
        print(f"  {r['name']:<{rule_width}}{str(r['triggers']):<10}{r['expiry']}")

    return 0
