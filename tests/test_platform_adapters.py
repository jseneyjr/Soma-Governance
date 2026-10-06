"""Behavioral tests for pure Python PlatformAdapters."""
from pathlib import Path
import pytest

from soma_cli.platforms import (
    PlatformAdapter,
    PlatformInstallResult,
    GeminiAdapter,
    ClaudeAdapter,
    get_adapter,
)


def test_get_adapter_registry():
    """Verify registry returns correct adapter instances."""
    gemini = get_adapter("gemini")
    assert isinstance(gemini, GeminiAdapter)
    assert gemini.name == "gemini"

    claude = get_adapter("claude")
    assert isinstance(claude, ClaudeAdapter)
    assert claude.name == "claude"

    with pytest.raises(ValueError, match="Unknown platform"):
        get_adapter("unknown-platform-xyz")


def test_gemini_adapter_install_and_uninstall(tmp_path):
    """Verify GeminiAdapter installs rules, skills, and hooks in isolated environment."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    # Create dummy genome and organs in workspace
    genome = workspace / "genome"
    genome.mkdir()
    (genome / "providence.md").write_text("# Providence", encoding="utf-8")

    organs = workspace / "organs" / "test-skill"
    organs.mkdir(parents=True)
    (organs / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    adapter = GeminiAdapter(workspace=workspace, home=home)

    # 1. Install global
    res = adapter.install(local=False, dry_run=False)
    assert res.success
    assert res.scope == "global"
    assert (home / ".gemini" / "config" / "rules" / "providence.md").is_file()
    assert (home / ".gemini" / "config" / "skills" / "test-skill" / "SKILL.md").is_file()
    assert (home / ".gemini" / "config" / "plugins" / "governance" / "hooks.json").is_file()
    assert adapter.verify(local=False)

    # 2. Uninstall global
    un_res = adapter.uninstall(local=False, dry_run=False)
    assert un_res.success
    assert not (home / ".gemini" / "config" / "rules" / "providence.md").exists()
    assert not (home / ".gemini" / "config" / "plugins" / "governance" / "hooks.json").exists()


def test_claude_adapter_install_and_uninstall(tmp_path):
    """Verify ClaudeAdapter writes CLAUDE.md integration instructions."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    adapter = ClaudeAdapter(workspace=workspace, home=home)
    res = adapter.install(local=True, dry_run=False)
    assert res.success
    claude_md = workspace / "CLAUDE.md"
    assert claude_md.is_file()
    assert adapter.verify(local=True)

    un_res = adapter.uninstall(local=True, dry_run=False)
    assert un_res.success
    assert not claude_md.exists()
