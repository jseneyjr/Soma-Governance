"""soma install and uninstall — Platform rule installation and removal."""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from soma_cli.base import CommandCategory, SomaCommand

__all__ = ["run_install", "run_uninstall", "InstallCommand", "UninstallCommand"]


def run_install(args: argparse.Namespace) -> int:
    """Install Soma rules and configuration for configured platform."""
    from soma_cli.platforms import get_adapter
    platform = getattr(args, "platform", None) or "gemini"
    local = getattr(args, "local", False)
    dry_run = getattr(args, "dry_run", False)
    workspace = getattr(args, "_project_root", None)
    try:
        adapter = get_adapter(platform, workspace=workspace)
        res = adapter.install(local=local, dry_run=dry_run)
        for msg in res.messages:
            print(msg)
        for err in res.errors:
            print(f"Error: {err}", file=sys.stderr)
        return 0 if res.success else 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def run_uninstall(args: argparse.Namespace) -> int:
    """Uninstall Soma rules and configuration for configured platform."""
    from soma_cli.platforms import get_adapter
    platform = getattr(args, "platform", None) or "gemini"
    local = getattr(args, "local", False)
    dry_run = getattr(args, "dry_run", False)
    workspace = getattr(args, "_project_root", None)
    try:
        adapter = get_adapter(platform, workspace=workspace)
        res = adapter.uninstall(local=local, dry_run=dry_run)
        for msg in res.messages:
            print(msg)
        for err in res.errors:
            print(f"Error: {err}", file=sys.stderr)
        return 0 if res.success else 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


class InstallCommand(SomaCommand):
    """Command to install Soma governance rules and configuration."""

    name = "install"
    category = CommandCategory.SETUP
    help = "Install Soma governance rules and configuration"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--platform",
            "-p",
            choices=["gemini", "kiro", "copilot", "claude", "mcp"],
            default=None,
            help="Target platform (default: auto-detected or gemini)",
        )
        parser.add_argument(
            "--local",
            action="store_true",
            help="Install to project-local directory",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be installed without writing files",
        )

    def execute(self, args: argparse.Namespace) -> int:
        return run_install(args)


class UninstallCommand(SomaCommand):
    """Command to uninstall Soma governance rules and configuration."""

    name = "uninstall"
    category = CommandCategory.SETUP
    help = "Uninstall Soma governance rules and configuration"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--platform",
            "-p",
            choices=["gemini", "kiro", "copilot", "claude", "mcp"],
            default=None,
            help="Target platform (default: auto-detected or gemini)",
        )
        parser.add_argument(
            "--local",
            action="store_true",
            help="Uninstall from project-local directory",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be uninstalled without deleting files",
        )

    def execute(self, args: argparse.Namespace) -> int:
        return run_uninstall(args)
