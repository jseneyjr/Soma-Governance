#!/usr/bin/env python3
"""Governance Sweep — Periodic lower-priority governance check (pure Python).

Checks:
  1. Unreviewed sessions (>100 steps, no metrics)
  2. Warning-level finding trends
  3. Metrics recomputation
  4. Active session monitoring (>50 steps, modified recently)
  5. Gate event summary

Usage:
  python3 enzymes/immune_sweep.py               # Full sweep
  python3 enzymes/immune_sweep.py --active-only # Only check active sessions
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

# Ensure enzymes directory is on sys.path for sweep_session import
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from sweep_session import scan_transcript, to_session_metrics
except ImportError:
    scan_transcript = None
    to_session_metrics = None


def resolve_home() -> Path:
    home_str = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if home_str:
        return Path(home_str)
    return Path.home()


def run_sweep(active_only: bool = False, soma_data_dir: Path | None = None) -> int:
    resolved_home = resolve_home()
    if soma_data_dir is None:
        env_data = os.environ.get("SOMA_DATA_DIR")
        if env_data:
            soma_data_dir = Path(env_data)
        else:
            soma_data_dir = resolved_home / ".gemini" / "antigravity"

    governance_dir = soma_data_dir / "scratch" / "ai-conversation-logs" / "governance"
    brain_dir = soma_data_dir / "brain"
    metrics_dir = governance_dir / "session_metrics"
    sweep_log = governance_dir / "sweep_log.jsonl"
    proposals = governance_dir / "pending_proposals.md"
    audit_log = governance_dir / "auto_applied_log.jsonl"
    gate_log = governance_dir / "gate_events.jsonl"

    metrics_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sessions_scanned = 0
    metrics_generated = 0
    warnings_tallied = 0
    active_flagged = 0

    print(f"🔄 Governance Sweep — {timestamp}")
    print()

    # ── Check 1: Unreviewed Sessions ──────────────────────────────────────────
    if not active_only:
        print("📋 Check 1: Scanning for unreviewed sessions (>100 steps)...")
        if brain_dir.is_dir():
            for child in brain_dir.iterdir():
                if not child.is_dir():
                    continue

                session_id = child.name
                short_id = session_id[:8]
                transcript = child / ".system_generated" / "logs" / "transcript.jsonl"
                metrics_file = metrics_dir / f"{short_id}.json"

                if not transcript.is_file():
                    continue
                if metrics_file.is_file():
                    continue

                try:
                    with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
                        step_count = sum(1 for _ in fh)
                except OSError:
                    step_count = 0

                if step_count > 100:
                    print(f"  🔍 {short_id} ({step_count} steps) — generating metrics...")
                    if scan_transcript and to_session_metrics:
                        try:
                            result = scan_transcript(str(transcript))
                            if result:
                                metrics = to_session_metrics(short_id, result)
                                with open(metrics_file, "w", encoding="utf-8") as out_f:
                                    json.dump(metrics, out_f, indent=2)
                                metrics_generated += 1
                                print(f"  ✅ {short_id}: metrics generated")
                            else:
                                print(f"  ⚠️  {short_id}: scan failed")
                        except Exception:
                            print(f"  ⚠️  {short_id}: scan failed")
                            if metrics_file.exists():
                                metrics_file.unlink(missing_ok=True)
                    sessions_scanned += 1

        print(f"  Done: {sessions_scanned} scanned, {metrics_generated} metrics generated")
        print()

    # ── Check 2: Warning Trends ──────────────────────────────────────────────
    print("📋 Check 2: Tallying warning-level findings...")
    warning_report = ""

    if audit_log.is_file() and audit_log.stat().st_size > 0:
        counts: Counter[str] = Counter()
        try:
            with open(audit_log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("severity") == "warning":
                            counts[entry.get("rule", "unknown")] += 1
                    except json.JSONDecodeError:
                        continue

            hardening_candidates = []
            for rule, count in counts.most_common():
                flag = "⚠️  CONSIDER HARDENING" if count >= 3 else ""
                line_str = f"  {count}x {rule} {flag}".rstrip()
                print(line_str)
                warnings_tallied += 1
                if count >= 3:
                    hardening_candidates.append(line_str)

            if hardening_candidates:
                warning_report = "\n".join(hardening_candidates)
        except OSError:
            print("  (parse error)")
    else:
        print("  (no audit log entries)")
    print()

    # ── Check 3: Metrics Recomputation ───────────────────────────────────────
    print("📋 Check 3: Recomputing aggregate metrics...")
    total_steps = 0
    total_waste = 0
    session_count = 0
    deep_sessions = 0
    sweep_sessions = 0

    if metrics_dir.is_dir():
        for f in sorted(metrics_dir.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    m = json.load(fh)
                if "total_steps" not in m:
                    continue
                steps = int(m.get("total_steps", 0))
                flat_waste = m.get("wasted_steps")
                nested_waste = None
                if isinstance(m.get("waste"), dict):
                    nested_waste = m["waste"].get("total_wasted_steps")

                if nested_waste is not None and (flat_waste is None or flat_waste == 0):
                    waste = int(nested_waste)
                elif flat_waste is not None:
                    waste = int(flat_waste)
                else:
                    waste = 0

                is_sweep = m.get("scan_type") == "lightweight_sweep" or m.get("review_tier") == "heuristic_sweep"
                if is_sweep:
                    sweep_sessions += 1
                else:
                    deep_sessions += 1

                total_steps += steps
                total_waste += waste
                session_count += 1
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
                continue

    rate = round(total_waste / total_steps * 100, 1) if total_steps > 0 else 0
    print(f"  Sessions: {session_count} (deep: {deep_sessions}, sweep: {sweep_sessions})")
    print(f"  Total steps: {total_steps:,}")
    print(f"  Total waste: {total_waste:,} ({rate}%)")
    print()

    # ── Check 4: Active Session Monitoring ───────────────────────────────────
    print("📋 Check 4: Checking active sessions (modified in last 2 hours)...")
    active_report_lines: list[str] = []
    now_ts = time.time()
    two_hours_ago = now_ts - (120 * 60)

    if brain_dir.is_dir():
        for transcript_path in brain_dir.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                st = transcript_path.stat()
                if st.st_mtime < two_hours_ago:
                    continue
            except OSError:
                continue

            try:
                with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
                    step_count = sum(1 for _ in f)
            except OSError:
                step_count = 0

            if step_count > 50:
                session_id = transcript_path.parent.parent.parent.name
                short_id = session_id[:8]

                waste_pct = 0
                top_pattern = "unknown"
                if scan_transcript:
                    try:
                        res = scan_transcript(str(transcript_path))
                        if res:
                            waste_pct = int(float(res.get("estimated_waste_rate", 0)) * 100)
                            top_patterns = res.get("top_patterns", [])
                            top_pattern = top_patterns[0]["pattern"] if top_patterns else "clean"
                    except Exception:
                        pass

                if waste_pct > 15:
                    print(f"  ⚠️  {short_id}: {step_count} steps, ~{waste_pct}% waste, top: {top_pattern}")
                    active_flagged += 1
                    active_report_lines.append(f"  ⚠️  {short_id}: {waste_pct}% waste ({top_pattern})")
                else:
                    print(f"  ✅ {short_id}: {step_count} steps, ~{waste_pct}% waste")

    if active_flagged == 0:
        print("  All active sessions clean.")
    print()

    # ── Check 5: Gate Event Summary ──────────────────────────────────────────
    if gate_log.is_file() and not active_only:
        print("📋 Check 5: Gate event summary...")
        try:
            with open(gate_log, "r", encoding="utf-8", errors="replace") as gf:
                lines = gf.readlines()
            gate_count = len(lines)
            blocked = sum(1 for l in lines if '"BLOCKED"' in l)
            print(f"  Total events: {gate_count}")
            print(f"  Blocked: {blocked}")
            print()
        except OSError:
            pass

    # ── Generate Sweep Report ────────────────────────────────────────────────
    has_actionable = metrics_generated > 0 or bool(warning_report) or active_flagged > 0

    if has_actionable:
        proposals_content = [
            "",
            f"## Governance Sweep — {timestamp}",
            "",
        ]
        if metrics_generated > 0:
            proposals_content.extend([
                f"### New Session Metrics ({metrics_generated} generated)",
                "Run `staff-review` post-mortem for deep analysis on high-waste sessions.",
                "",
            ])
        if warning_report:
            proposals_content.extend([
                "### Warning Trends — Hardening Candidates",
                warning_report,
                "",
            ])
        if active_flagged > 0:
            proposals_content.extend([
                "### Active Session Alerts",
                "\n".join(active_report_lines),
                "",
            ])

        try:
            with open(proposals, "a", encoding="utf-8") as pf:
                pf.write("\n".join(proposals_content) + "\n")
            print("📝 Sweep report appended to pending_proposals.md")
        except OSError:
            pass

    # ── Log Sweep ────────────────────────────────────────────────────────────
    sweep_entry = {
        "timestamp": timestamp,
        "sessions_scanned": sessions_scanned,
        "metrics_generated": metrics_generated,
        "warnings_tallied": warnings_tallied,
        "active_flagged": active_flagged,
        "has_actionable": has_actionable,
    }
    try:
        with open(sweep_log, "a", encoding="utf-8") as sf:
            sf.write(json.dumps(sweep_entry) + "\n")
    except OSError:
        pass

    print()
    print("✅ Governance sweep complete.")
    print(
        f"   Scanned: {sessions_scanned} | Generated: {metrics_generated} | "
        f"Warnings: {warnings_tallied} | Active flags: {active_flagged}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Governance Sweep (pure Python)")
    parser.add_argument("--active-only", action="store_true", help="Only check active sessions")
    args = parser.parse_args(argv)
    return run_sweep(active_only=args.active_only)


if __name__ == "__main__":
    sys.exit(main())
