"""Contract and behavioral invariants for SomaCommand protocol and CommandRegistry."""
from __future__ import annotations

import argparse
import pytest

from soma_cli.base import CommandCategory, SomaCommand
from soma_cli.registry import CommandRegistry


class DummyInitCommand(SomaCommand):
    name = "dummy-init"
    aliases = ("d-init", "di")
    category = CommandCategory.SETUP
    help = "Dummy initialization command"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--flag", action="store_true", help="Sample flag")

    def execute(self, args: argparse.Namespace) -> int:
        return 42 if getattr(args, "flag", False) else 0


class DummyVerifyCommand(SomaCommand):
    name = "dummy-verify"
    aliases = ("dv",)
    category = CommandCategory.WORKFLOW
    help = "Dummy verification command"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--strict", action="store_true")

    def execute(self, args: argparse.Namespace) -> int:
        return 1 if getattr(args, "strict", False) else 0


def test_command_abstract_contract():
    # Attempting to instantiate incomplete subclass should fail
    class IncompleteCommand(SomaCommand):
        pass

    with pytest.raises(TypeError):
        IncompleteCommand()


def test_command_attributes():
    cmd = DummyInitCommand()
    assert cmd.name == "dummy-init"
    assert "d-init" in cmd.aliases
    assert cmd.category == CommandCategory.SETUP
    assert cmd.help == "Dummy initialization command"
    assert cmd.get_names() == ("dummy-init", "d-init", "di")


def test_registry_registration_and_lookup():
    reg = CommandRegistry()
    init_cmd = DummyInitCommand()
    verify_cmd = DummyVerifyCommand()

    reg.register(init_cmd)
    reg.register(verify_cmd)

    # Lookup by primary name
    assert reg.get("dummy-init") is init_cmd
    assert reg.get("dummy-verify") is verify_cmd

    # Lookup by alias
    assert reg.get("d-init") is init_cmd
    assert reg.get("di") is init_cmd
    assert reg.get("dv") is verify_cmd

    # Lookup missing
    assert reg.get("nonexistent") is None


def test_registry_category_filtering():
    reg = CommandRegistry()
    init_cmd = DummyInitCommand()
    verify_cmd = DummyVerifyCommand()
    reg.register(init_cmd)
    reg.register(verify_cmd)

    setup_cmds = reg.get_by_category(CommandCategory.SETUP)
    assert init_cmd in setup_cmds
    assert verify_cmd not in setup_cmds

    workflow_cmds = reg.get_by_category(CommandCategory.WORKFLOW)
    assert verify_cmd in workflow_cmds
    assert init_cmd not in workflow_cmds


def test_registry_populates_argparse_subparsers():
    parser = argparse.ArgumentParser(prog="soma")
    sub = parser.add_subparsers(dest="command")

    reg = CommandRegistry()
    reg.register(DummyInitCommand())

    subparsers = reg.populate_subparsers(sub)
    assert "dummy-init" in subparsers

    # Test argument parsing
    args = parser.parse_args(["dummy-init", "--flag"])
    assert args.command == "dummy-init"
    assert args.flag is True

    # Test alias parsing
    args_alias = parser.parse_args(["d-init", "--flag"])
    assert args_alias.command in ("dummy-init", "d-init")
    assert args_alias.flag is True


def test_registry_formatted_help():
    reg = CommandRegistry()
    reg.register(DummyInitCommand())
    reg.register(DummyVerifyCommand())

    help_text = reg.format_categorized_help(prog="soma")
    assert "Setup & Environment:" in help_text
    assert "dummy-init" in help_text
    assert "Daily Workflow & Verification:" in help_text
    assert "dummy-verify" in help_text


def test_category_1_setup_commands():
    from soma_cli.init import InitCommand
    from soma_cli.detect import DetectCommand
    from soma_cli.doctor import DoctorCommand
    from soma_cli.install import InstallCommand, UninstallCommand

    cmds = [InitCommand(), DetectCommand(), DoctorCommand(), InstallCommand(), UninstallCommand()]
    reg = CommandRegistry()

    for cmd in cmds:
        assert cmd.category == CommandCategory.SETUP
        assert cmd.name in ("init", "detect", "doctor", "install", "uninstall")
        reg.register(cmd)

    # Verify alias resolution
    assert reg.get("languages").name == "detect"
    assert reg.get("drivers").name == "detect"
    assert reg.get("audit").name == "doctor"

    # Verify subparser creation
    parser = argparse.ArgumentParser(prog="soma")
    sub = parser.add_subparsers(dest="command")
    reg.populate_subparsers(sub)

    args = parser.parse_args(["detect", "--dry-run"])
    assert args.command == "detect"
    assert args.dry_run is True

    args_alias = parser.parse_args(["languages", "--fix"])
    assert args_alias.command in ("detect", "languages")
    assert args_alias.fix is True


def test_category_2_workflow_commands():
    from soma_cli.verify import VerifyCommand
    from soma_cli.status import StatusCommand
    from soma_cli.checkpoint import CheckpointCommand
    from soma_cli.report import ReportCommand
    from soma_cli.sync import SyncCommand

    cmds = [VerifyCommand(), StatusCommand(), CheckpointCommand(), ReportCommand(), SyncCommand()]
    reg = CommandRegistry()

    for cmd in cmds:
        assert cmd.category == CommandCategory.WORKFLOW
        assert cmd.name in ("verify", "status", "checkpoint", "report", "sync")
        reg.register(cmd)

    # Verify alias resolution
    assert reg.get("check").name == "verify"
    assert reg.get("rules").name == "status"

    # Verify subparser creation
    parser = argparse.ArgumentParser(prog="soma")
    sub = parser.add_subparsers(dest="command")
    reg.populate_subparsers(sub)

    args = parser.parse_args(["verify", "--layer1-only"])
    assert args.command == "verify"
    assert args.layer1_only is True

    args_alias = parser.parse_args(["check", "--dry-run"])
    assert args_alias.command in ("verify", "check")
    assert args_alias.dry_run is True

    args_cp = parser.parse_args(["checkpoint", "--strict"])
    assert args_cp.command == "checkpoint"
    assert args_cp.strict is True


def test_category_3_lifecycle_commands():
    from soma_cli.genesis import GenesisCommand
    from soma_cli.oracle import OracleCommand
    from soma_cli.promote import PromoteCommand
    from soma_cli.demote import DemoteCommand
    from soma_cli.prune import PruneCommand
    from soma_cli.harvest import HarvestCommand
    from soma_cli.capture_insight import CaptureInsightCommand

    cmds = [
        GenesisCommand(),
        OracleCommand(),
        PromoteCommand(),
        DemoteCommand(),
        PruneCommand(),
        HarvestCommand(),
        CaptureInsightCommand(),
    ]
    reg = CommandRegistry()

    for cmd in cmds:
        assert cmd.category == CommandCategory.LIFECYCLE
        reg.register(cmd)

    # Verify alias resolution
    assert reg.get("analyze").name == "genesis"

    # Verify subparser creation
    parser = argparse.ArgumentParser(prog="soma")
    sub = parser.add_subparsers(dest="command")
    reg.populate_subparsers(sub)

    args = parser.parse_args(["genesis", "--dry-run", "--min-confidence", "0.8"])
    assert args.command == "genesis"
    assert args.dry_run is True
    assert args.min_confidence == 0.8

    args_alias = parser.parse_args(["analyze", "--force"])
    assert args_alias.command in ("genesis", "analyze")
    assert args_alias.force is True

    args_insight = parser.parse_args(["capture-insight", "-i", "Test insight", "-c", "file1.py", "--scaffold-wall"])
    assert args_insight.command == "capture-insight"
    assert args_insight.insight == "Test insight"
    assert args_insight.context_files == ["file1.py"]
    assert args_insight.scaffold_wall is True


def test_category_4_plumbing_commands():
    from soma_cli.hooks import HookCommand
    from soma_cli.skills import SkillCommand, HandoffCommand
    from soma_cli.transfer import TransferCommand
    from soma_cli.quarantine import QuarantineCommand
    from soma_cli.clean_rules import CleanRulesCommand
    from soma_cli.completion import CompletionCommand

    cmds = [
        HookCommand(),
        SkillCommand(),
        HandoffCommand(),
        TransferCommand(),
        QuarantineCommand(),
        CleanRulesCommand(),
        CompletionCommand(),
    ]
    reg = CommandRegistry()

    for cmd in cmds:
        assert cmd.category == CommandCategory.PLUMBING
        reg.register(cmd)

    parser = argparse.ArgumentParser(prog="soma")
    sub = parser.add_subparsers(dest="command")
    reg.populate_subparsers(sub)

    args_handoff = parser.parse_args([
        "handoff", "--from", "skillA", "--to", "skillB", "--artifact", "DiffProposal", "--payload", '{"foo": "bar"}'
    ])
    assert args_handoff.command == "handoff"
    assert args_handoff.from_skill == "skillA"
    assert args_handoff.to_skill == "skillB"

    args_clean = parser.parse_args(["clean-global-rules", "--force"])
    assert args_clean.command == "clean-global-rules"
    assert args_clean.force is True

    args_comp = parser.parse_args(["completion", "bash"])
    assert args_comp.command == "completion"
    assert args_comp.shell == "bash"


def test_default_registry_completeness():
    from soma_cli.registry import get_default_registry

    reg = get_default_registry()
    commands = reg.list_commands()
    assert len(commands) == 24

    expected_verbs = {
        "init", "status", "rules", "report", "doctor", "audit",
        "detect", "languages", "drivers", "verify", "check", "checkpoint",
        "sync", "oracle", "promote", "demote", "harvest", "genesis",
        "analyze", "completion", "hook", "transfer", "quarantine", "prune",
        "install", "uninstall", "clean-global-rules", "capture-insight",
        "skill", "handoff",
    }

    for verb in expected_verbs:
        cmd = reg.get(verb)
        assert cmd is not None, f"Verb '{verb}' missing from default registry"
        assert callable(cmd.execute)
