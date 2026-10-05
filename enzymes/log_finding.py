#!/usr/bin/env python3
"""log_finding.py: Single entry point for governance finding logging.

Replaces ad-hoc shell redirects. Routes critical findings to pending_critical.md.

Usage:
    python enzymes/log_finding.py --severity <critical|warning|nit> --rule <rule> --change <change> --source <source>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def log_finding(
    severity: str,
    rule: str,
    change: str,
    source: str,
    logs_dir: Path | None = None,
) -> int:
    severity_lower = severity.lower()
    if severity_lower not in ("critical", "warning", "nit", "info"):
        print(f"Warning: Unknown severity '{severity}', defaulting to warning", file=sys.stderr)

    resolved_home = Path.home()
    if logs_dir:
        base_logs = logs_dir
    elif os.environ.get("SOMA_LOGS_DIR"):
        base_logs = Path(os.environ["SOMA_LOGS_DIR"])
    else:
        base_logs = resolved_home / ".gemini" / "antigravity" / "scratch" / "ai-conversation-logs"

    gov_dir = base_logs / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)

    auto_log = gov_dir / "auto_applied_log.jsonl"
    critical_file = gov_dir / "pending_critical.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = {
        "timestamp": timestamp,
        "severity": severity_lower,
        "rule": rule,
        "change": change,
        "source": source,
    }

    try:
        with open(auto_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"Error writing to audit log {auto_log}: {e}", file=sys.stderr)
        return 1

    if severity_lower == "critical":
        try:
            entry = f"\n### 🔴 CRITICAL: {rule} ({timestamp})\n- **Change**: {change}\n- **Source**: {source}\n"
            with open(critical_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"Error writing to critical findings file {critical_file}: {e}", file=sys.stderr)
            return 1

    print(f"✅ Logged {severity_lower} finding for {rule}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Log governance findings")
    parser.add_argument("--severity", required=True, help="Severity: critical, warning, nit, info")
    parser.add_argument("--rule", required=True, help="Rule ID")
    parser.add_argument("--change", required=True, help="Description of change")
    parser.add_argument("--source", required=True, help="Source of finding")
    args = parser.parse_args(argv)

    return log_finding(
        severity=args.severity,
        rule=args.rule,
        change=args.change,
        source=args.source,
    )


if __name__ == "__main__":
    sys.exit(main())
