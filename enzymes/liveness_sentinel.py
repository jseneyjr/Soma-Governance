#!/usr/bin/env python3
"""liveness_sentinel.py: Subagent dispatch health monitor during multi-agent orchestration.

Detects stalled or deadlocked subagents that fail to report back within expected timeframes.

Usage:
    python enzymes/liveness_sentinel.py --check '{"agents": [...]}'
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def check_liveness(payload_str: str) -> int:
    try:
        data = json.loads(payload_str)
        now = datetime.now(timezone.utc)
        for agent in data.get("agents", []):
            name = agent.get("name", "Unknown")
            dispatch_str = agent.get("dispatched", "")
            timeout = agent.get("timeout_seconds", 0)

            try:
                if dispatch_str.endswith("Z"):
                    dispatch_str = dispatch_str[:-1] + "+00:00"
                dispatch_time = datetime.fromisoformat(dispatch_str)
            except ValueError:
                print(f"[{name}] INVALID_DATE: {dispatch_str}")
                continue

            elapsed = (now - dispatch_time).total_seconds()

            if elapsed > timeout:
                print(
                    f"[{name}] STALLED (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s) - Action suggested: kill or escalate"
                )
            elif elapsed > timeout * 0.8:
                print(
                    f"[{name}] WARNING (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s) - Action suggested: nudge"
                )
            else:
                print(f"[{name}] HEALTHY (Elapsed: {elapsed:.1f}s, Timeout: {timeout}s)")
        return 0
    except json.JSONDecodeError:
        print("Error: Invalid JSON provided.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Subagent liveness sentinel")
    parser.add_argument("--check", dest="payload", default="", help="JSON string with agent list")
    args = parser.parse_args(argv)

    if not args.payload:
        print("Usage: liveness_sentinel.py --check '{\"agents\": [...]}'")
        return 0

    return check_liveness(args.payload)


if __name__ == "__main__":
    sys.exit(main())
