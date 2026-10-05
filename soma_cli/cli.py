#!/usr/bin/env python3
"""Soma CLI — governance commands for AI coding agents.

User-facing interface uses plain language (rules, automations, etc).
Internal code retains biological naming (genome, enzymes, cells).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.is_file():
        try:
            val = version_file.read_text(encoding="utf-8").strip()
            if val:
                return val
        except OSError:
            pass
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("soma-governance")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass
    return "unknown"


class SomaParser(argparse.ArgumentParser):
    """ArgumentParser ensuring global flags like plumbing default properly."""

    def parse_args(self, args=None, namespace=None):
        ns = super().parse_args(args=args, namespace=namespace)
        if not hasattr(ns, "plumbing"):
            ns.plumbing = False
        return ns


def _build_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--plumbing", "--internal", action="store_true",
                               default=argparse.SUPPRESS,
                               help="Display raw internal biological terms")

    parser = SomaParser(
        prog="soma",
        description="Soma Governance — make AI coding agents trustworthy",
        parents=[common_parser],
    )
    parser.add_argument("--version", action="version",
                        version=f"soma {_version()}")

    sub = parser.add_subparsers(dest="command")

    # soma init
    p_init = sub.add_parser("init", parents=[common_parser], help="Set up governance for this project")
    p_init.add_argument("--dry-run", action="store_true",
                        help="Show what would be installed without doing it")
    p_init.add_argument("--platform", choices=["gemini", "claude", "cursor", "copilot", "kiro"],
                        help="Skip platform detection, force a platform")
    p_init.add_argument("--rules", choices=["minimal", "standard", "full"],
                        default="standard",
                        help="Rule set to install (default: standard)")
    p_init.add_argument("--mcp", action="store_true",
                        help="Generate .mcp.json for JIT cell matching")
    p_init.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompts")
    p_init.add_argument("--force", action="store_true",
                        help="Overwrite existing rules")

    # soma status
    p_status = sub.add_parser("status", aliases=["rules"], parents=[common_parser], help="Show active rules and stats")

    # soma report
    p_report = sub.add_parser("report", parents=[common_parser], help="Session report card")
    p_report.add_argument("--session", type=int, default=-1,
                          help="Session index (default: latest)")

    # soma doctor
    p_doctor = sub.add_parser("doctor", parents=[common_parser], help="System health check")
    p_doctor.add_argument("--fix-path", action="store_true",
                          help="Add soma's scripts directory to your shell startup file "
                               "(dry run unless confirmed or --yes; zsh/bash/fish only)")
    p_doctor.add_argument("--yes", "-y", action="store_true",
                          help="With --fix-path: apply without asking")

    # soma verify
    p_verify = sub.add_parser("verify", parents=[common_parser], help="Run verification on changed files")
    p_verify.add_argument("--files", nargs="*", default=None,
                          help="Explicit list of files to verify")
    p_verify.add_argument("--layer1-only", action="store_true",
                          help="Skip Layer 2 (fast deterministic checks only)")
    p_verify.add_argument("--dry-run", action="store_true",
                          help="Show what would be checked without running")
    p_verify.add_argument("--repo-root", default=None,
                          help="Override repository root path")

    # soma sync
    p_sync = sub.add_parser("sync", parents=[common_parser], help="Reconcile evidence JSONL with cell frontmatter")
    p_sync.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    p_sync.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON output")

    # soma checkpoint
    p_checkpoint = sub.add_parser("checkpoint", parents=[common_parser], help="Run deterministic quality checks")
    p_checkpoint.add_argument("--pre-commit", action="store_true",
                              help="Warn mode: exit 0 even if issues found (unless --strict)")
    p_checkpoint.add_argument("--strict", action="store_true",
                              help="In pre-commit mode, exit 1 on issues")
    p_checkpoint.add_argument("--json", action="store_true",
                              help="Emit machine-readable JSON output")
    p_checkpoint.add_argument("--workspace", default=None,
                              help="Override target workspace directory")

    # soma oracle
    p_oracle = sub.add_parser("oracle", parents=[common_parser], help="Cell health classification and recommendations")
    p_oracle.add_argument("--json", action="store_true",
                          help="Emit machine-readable JSON output")
    p_oracle.add_argument("--session-count", type=int, default=None,
                          help="Override session count for expiry calculation")

    # soma promote
    p_promote = sub.add_parser("promote", parents=[common_parser], help="Evaluate cell promotion candidates")
    p_promote.add_argument("--dry-run", action="store_true",
                           help="Show candidates without performing promotions")
    p_promote.add_argument("--json", action="store_true",
                           help="Emit machine-readable JSON output")
    p_promote.add_argument("--force", action="store_true",
                           help="Force promotion of --cell, bypassing evidence thresholds")
    p_promote.add_argument("--cell", type=str, default=None,
                           help="Target cell ID for --force promotion")

    # soma demote
    p_demote = sub.add_parser("demote", parents=[common_parser], help="Evaluate cell demotion candidates")
    p_demote.add_argument("--dry-run", action="store_true",
                          help="Show candidates without performing demotions")
    p_demote.add_argument("--json", action="store_true",
                          help="Emit machine-readable JSON output")
    p_demote.add_argument("--force", action="store_true",
                          help="Force demotion of --cell, bypassing evidence thresholds")
    p_demote.add_argument("--cell", type=str, default=None,
                          help="Target cell ID for --force demotion")

    # soma genesis
    p_genesis = sub.add_parser("genesis", aliases=["analyze"], parents=[common_parser], help="Analyze codebase and generate governance cells")
    p_genesis.add_argument("--dry-run", action="store_true",
                           help="Show candidates without writing files")
    p_genesis.add_argument("--json", action="store_true",
                           help="Emit machine-readable JSON output")
    p_genesis.add_argument("--min-confidence", type=float, default=0.5,
                           help="Minimum confidence threshold (default: 0.5)")
    p_genesis.add_argument("--force", action="store_true",
                           help="Overwrite existing cells with same name")
    p_genesis.add_argument("--yes", "-y", action="store_true",
                           help="Skip confirmation prompts")
    p_genesis.add_argument("--project-root", default=None,
                           help="Override project root path")

    # soma completion
    from soma_cli.completion import SHELLS
    p_completion = sub.add_parser("completion", parents=[common_parser], help="Print a shell completion script")
    p_completion.add_argument("shell", choices=list(SHELLS),
                              help="Target shell")

    # soma hook
    p_hook = sub.add_parser("hook", parents=[common_parser], help="Run cross-platform lifecycle hooks")
    p_hook.add_argument(
        "phase",
        choices=[
            "pre-commit",
            "safety-gate",
            "pre-invocation",
            "session-close",
            "post-session",
            "governance-monitor",
            "immune-init",
            "stop",
        ],
        help="Hook lifecycle phase to execute",
    )
    p_hook.add_argument("--cmd", type=str, default=None,
                        help="Command line string for safety-gate check")
    p_hook.add_argument("--strict", action="store_true",
                        help="In pre-commit, exit 1 on issues")
    p_hook.add_argument("--workspace", default=None,
                        help="Target workspace path")
    p_hook.add_argument("--json", action="store_true",
                        help="Emit JSON output")

    # soma transfer
    p_transfer = sub.add_parser("transfer", parents=[common_parser], help="Transfer a cell to another project with fitness reset")
    p_transfer.add_argument("cell_id", nargs="?", default="", help="ID of cell to transfer")
    p_transfer.add_argument("--to", dest="target_dir", default="", help="Path to target project")

    # soma quarantine
    p_quarantine = sub.add_parser("quarantine", parents=[common_parser], help="Inspect and manage quarantined corrupt files")
    p_quarantine_sub = p_quarantine.add_subparsers(dest="quarantine_action")

    p_q_list = p_quarantine_sub.add_parser("list", parents=[common_parser], help="List all quarantined files")
    p_q_list.add_argument("--json", action="store_true", help="Emit JSON output")

    p_q_inspect = p_quarantine_sub.add_parser("inspect", parents=[common_parser], help="Inspect a quarantined file")
    p_q_inspect.add_argument("target", nargs="?", default="", help="Filename or path of quarantined file")
    p_q_inspect.add_argument("--json", action="store_true", help="Emit JSON output")

    p_q_prune = p_quarantine_sub.add_parser("prune", parents=[common_parser], help="Prune old quarantined files")
    p_q_prune.add_argument("--older-than-days", type=int, default=30, help="Prune files older than N days (default 30)")

    # soma prune
    p_prune = sub.add_parser("prune", parents=[common_parser], help="Prune extinct or apoptotic rules")
    p_prune.add_argument("--execute", action="store_true", help="Execute pruning decisions (archive expired rules)")
    p_prune.add_argument("--workspace", type=str, default="", help="Path to workspace root")

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


def cmd_verify(args: argparse.Namespace) -> int:
    """Run verification on changed files."""
    from soma_cli.verify import run_verify
    return run_verify(args)


def cmd_checkpoint(args: argparse.Namespace) -> int:
    """Run deterministic quality checks."""
    from soma_cli.checkpoint import run_checkpoint
    return run_checkpoint(args)


def cmd_oracle(args: argparse.Namespace) -> int:
    """Cell health classification and recommendations."""
    from soma_cli.oracle import run_oracle
    return run_oracle(args)


def cmd_promote(args: argparse.Namespace) -> int:
    """Evaluate cell promotion candidates."""
    from soma_cli.promote import run_promote
    return run_promote(args)


def cmd_sync(args: argparse.Namespace) -> int:
    """Reconcile evidence with cell frontmatter."""
    from soma_cli.sync import run_sync
    return run_sync(args)


def cmd_demote(args: argparse.Namespace) -> int:
    """Evaluate cell demotion candidates."""
    from soma_cli.demote import run_demote
    return run_demote(args)


def cmd_genesis(args: argparse.Namespace) -> int:
    """Analyze codebase and generate governance cells."""
    from soma_cli.genesis import run_genesis
    return run_genesis(args)


def cmd_completion(args: argparse.Namespace) -> int:
    """Print a shell completion script."""
    from soma_cli.completion import run_completion
    return run_completion(args)


def cmd_hook(args: argparse.Namespace) -> int:
    """Run lifecycle hooks natively across platforms."""
    from soma_cli.hooks import run_hook
    return run_hook(args)


def cmd_transfer(args: argparse.Namespace) -> int:
    """Transfer a cell to another project with fitness reset."""
    from soma_cli.transfer import run_transfer
    return run_transfer(args)


def cmd_quarantine(args: argparse.Namespace) -> int:
    """Inspect and manage quarantined corrupt files."""
    from soma_cli.quarantine import run_quarantine
    return run_quarantine(args)


def cmd_prune(args: argparse.Namespace) -> int:
    """Prune extinct or apoptotic rules."""
    from soma_core.lifecycle import prune_cells
    execute = getattr(args, "execute", False)
    workspace = getattr(args, "workspace", None)
    return prune_cells(workspace=workspace, execute=execute)


COMMANDS = {
    "init": cmd_init,
    "status": cmd_status,
    "rules": cmd_status,
    "report": cmd_report,
    "doctor": cmd_doctor,
    "verify": cmd_verify,
    "checkpoint": cmd_checkpoint,
    "sync": cmd_sync,
    "oracle": cmd_oracle,
    "promote": cmd_promote,
    "demote": cmd_demote,
    "genesis": cmd_genesis,
    "analyze": cmd_genesis,
    "completion": cmd_completion,
    "hook": cmd_hook,
    "transfer": cmd_transfer,
    "quarantine": cmd_quarantine,
    "prune": cmd_prune,
}


def main(argv: list[str] | None = None) -> int:
    # Output uses emoji. On a cp1252 stdout (Windows, redirected) printing
    # one raised UnicodeEncodeError and the command exited 1 (BUG-012).
    # stderr already defaults to errors="backslashreplace".
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "plumbing"):
        args.plumbing = False

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
