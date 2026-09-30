#!/usr/bin/env python3
"""Soma CLI — governance commands for AI coding agents.

User-facing interface uses plain language (rules, automations, etc).
Internal code retains biological naming (genome, enzymes, cells).
"""
from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="soma",
        description="Soma Governance — make AI coding agents trustworthy",
    )
    sub = parser.add_subparsers(dest="command")

    # soma init
    p_init = sub.add_parser("init", help="Set up governance for this project")
    p_init.add_argument("--dry-run", action="store_true",
                        help="Show what would be installed without doing it")
    p_init.add_argument("--platform", choices=["gemini", "claude", "cursor", "copilot"],
                        help="Skip platform detection, force a platform")
    p_init.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompts")
    p_init.add_argument("--force", action="store_true",
                        help="Overwrite existing rules")

    # soma status
    sub.add_parser("status", help="Show active rules and stats")

    # soma report
    p_report = sub.add_parser("report", help="Session report card")
    p_report.add_argument("--session", type=int, default=-1,
                          help="Session index (default: latest)")

    # soma doctor
    sub.add_parser("doctor", help="System health check")

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    """Set up governance for this project."""
    from soma_cli.init import run_init
    return run_init(args)


def cmd_status(args: argparse.Namespace) -> int:
    """Show active rules and stats."""
    from soma_cli.status import run_status
    return run_status(args)


def cmd_report(args: argparse.Namespace) -> int:
    """Session report card."""
    from soma_cli.report import run_report
    return run_report(args)


def cmd_doctor(args: argparse.Namespace) -> int:
    """System health check."""
    from soma_cli.doctor import run_doctor
    return run_doctor(args)


COMMANDS = {
    "init": cmd_init,
    "status": cmd_status,
    "report": cmd_report,
    "doctor": cmd_doctor,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
