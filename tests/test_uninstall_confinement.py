"""Uninstall path-confinement regression tests.

uninstall.sh used a lexical prefix check, so a manifest entry such as
``$HOME/safe/../../outside/victim`` or ``$HOME/link/victim`` (``link`` being a
symlink out of HOME) passed and was deleted. Unsafe entries were also skipped
silently, and ``backup_dir`` (a restore *source*) was never checked at all.

Every hostile manifest here must fail closed: nonzero exit, nothing outside
the allowed roots touched, the legitimate entries in the same manifest left in
place (validation happens before any mutation), and the manifest retained.

All runs use an isolated HOME and an isolated project cwd under tmp_path.
"""
import json
import os
import re

import pytest

from conftest import REPO_ROOT, read, require_bash, run, symlink_or_skip

UNINSTALL_SH = os.path.join(REPO_ROOT, "install", "uninstall.sh")
UNINSTALL_PS1 = os.path.join(REPO_ROOT, "install", "uninstall.ps1")

SENTINEL_BYTES = b"outside sentinel - must survive\n"


@pytest.fixture
def layout(tmp_path):
    """home/, project/ and outside/ as siblings, so outside/ is under neither
    allowed root. Returns a dict of the paths plus prepared content."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    for d in (home, project, outside):
        d.mkdir()

    victim = outside / "victim"
    victim.write_bytes(SENTINEL_BYTES)
    victim_dir = outside / "victim-dir"
    victim_dir.mkdir()
    (victim_dir / "inner").write_bytes(SENTINEL_BYTES)

    # A legitimate installed file + skill dir under HOME.
    steering = home / ".kiro" / "steering"
    steering.mkdir(parents=True)
    legit_file = steering / "soma-rule.md"
    legit_file.write_text("soma rule\n", encoding="utf-8")
    legit_skill = home / ".kiro" / "skills" / "soma-skill"
    legit_skill.mkdir(parents=True)
    (legit_skill / "SKILL.md").write_text("soma skill\n", encoding="utf-8")

    backup_dir = home / ".soma" / "backup" / "2026-01-01T00-00-00"
    backup_dir.mkdir(parents=True)

    return {
        "home": home, "project": project, "outside": outside,
        "victim": victim, "victim_dir": victim_dir,
        "legit_file": legit_file, "legit_skill": legit_skill,
        "backup_dir": backup_dir,
    }


def write_manifest(path, files=(), organs=(), hooks=(), backup_dir=None,
                   platform="kiro", scope="global"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": "test",
        "platform": platform,
        "scope": scope,
        "backup_dir": None if backup_dir is None else str(backup_dir),
        "files": [str(p) for p in files],
        "organs": [str(p) for p in organs],
        "hooks": [str(p) for p in hooks],
    }), encoding="utf-8")
    return path


def home_manifest(layout, **kw):
    return write_manifest(layout["home"] / ".soma" / "manifest.json", **kw)


def uninstall(layout, platform="kiro", *extra):
    return run(
        [require_bash(), UNINSTALL_SH, platform, "--force", "--no-restore",
         "--keep-config", *extra],
        cwd=str(layout["project"]),
        env={"HOME": str(layout["home"]), "USERPROFILE": str(layout["home"])},
    )


def snapshot_outside(layout):
    out = {}
    for root, _dirs, files in os.walk(layout["outside"]):
        for fn in files:
            p = os.path.join(root, fn)
            with open(p, "rb") as f:
                out[p] = f.read()
    return out


def assert_failed_closed(proc, layout, manifest, before, offending):
    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        f"unsafe manifest was accepted (exit 0):\n{combined[-1500:]}"
    )
    assert snapshot_outside(layout) == before, "files outside the allowed roots changed"
    assert layout["legit_file"].exists(), (
        "legitimate in-root file was deleted: validation did not run before mutation"
    )
    assert layout["legit_skill"].is_dir(), "legitimate in-root skill dir was deleted"
    assert manifest.exists(), "manifest was deleted despite failing validation"
    assert offending in combined, (
        f"offending entry {offending!r} was not reported:\n{combined[-1500:]}"
    )


# ── Hostile manifests ───────────────────────────────────────────────────

def test_dotdot_escape_is_refused(layout):
    # `safe` must exist, or the kernel cannot traverse the `..` and rm fails anyway.
    (layout["home"] / "safe").mkdir()
    hostile = f"{layout['home']}/safe/../../outside/victim"
    manifest = home_manifest(layout, files=[layout["legit_file"], hostile],
                             organs=[layout["legit_skill"]])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_absolute_path_outside_roots_is_refused(layout):
    hostile = str(layout["victim"])
    manifest = home_manifest(layout, files=[layout["legit_file"], hostile],
                             organs=[layout["legit_skill"]])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_outside_dir_in_organs_is_refused(layout):
    hostile = str(layout["victim_dir"])
    manifest = home_manifest(layout, files=[layout["legit_file"]],
                             organs=[layout["legit_skill"], hostile])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_intermediate_symlink_escape_is_refused(layout):
    link = layout["home"] / "link"
    symlink_or_skip(str(layout["outside"]), str(link))
    hostile_file = f"{link}/victim"
    hostile_dir = f"{link}/victim-dir"
    manifest = home_manifest(layout, files=[layout["legit_file"], hostile_file],
                             organs=[layout["legit_skill"], hostile_dir])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile_file)
    assert hostile_dir in proc.stdout + proc.stderr, "every offender must be reported"


def test_symlinked_hook_parent_is_refused(layout):
    link = layout["home"] / ".git-link"
    symlink_or_skip(str(layout["outside"]), str(link))
    hostile = f"{link}/victim"
    manifest = home_manifest(layout, files=[layout["legit_file"]],
                             organs=[layout["legit_skill"]], hooks=[hostile])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_backup_dir_outside_roots_is_refused(layout):
    hostile = str(layout["outside"])
    manifest = home_manifest(layout, files=[layout["legit_file"]],
                             organs=[layout["legit_skill"]], backup_dir=hostile)
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_relative_entry_is_refused(layout):
    hostile = "outside/victim"
    manifest = home_manifest(layout, files=[layout["legit_file"], hostile],
                             organs=[layout["legit_skill"]])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_root_itself_is_refused(layout):
    hostile = str(layout["home"])
    manifest = home_manifest(layout, files=[layout["legit_file"]],
                             organs=[layout["legit_skill"], hostile])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert_failed_closed(proc, layout, manifest, before, hostile)


def test_project_manifest_cannot_reach_into_home(layout):
    """A project-local manifest is confined to the project directory."""
    manifest = write_manifest(
        layout["project"] / ".soma" / "manifest.json",
        files=[layout["project"] / ".mcp.json", layout["legit_file"]],
        platform="mcp", scope="local",
    )
    (layout["project"] / ".mcp.json").write_text('{"soma": 1}\n', encoding="utf-8")
    before = snapshot_outside(layout)
    proc = uninstall(layout, "mcp")
    assert_failed_closed(proc, layout, manifest, before, str(layout["legit_file"]))
    assert (layout["project"] / ".mcp.json").exists(), "in-root file removed before validation"


def test_dry_run_also_refuses(layout):
    hostile = str(layout["victim"])
    manifest = home_manifest(layout, files=[layout["legit_file"], hostile])
    before = snapshot_outside(layout)
    proc = uninstall(layout, "kiro", "--dry-run")
    assert_failed_closed(proc, layout, manifest, before, hostile)


# ── Legitimate manifests ────────────────────────────────────────────────

def test_legitimate_home_manifest_is_removed(layout):
    hook = layout["home"] / ".kiro" / "hooks" / "hooks.json"
    hook.parent.mkdir(parents=True)
    hook.write_text("{}\n", encoding="utf-8")
    project_file = layout["project"] / ".kiro" / "settings" / "mcp.json"
    project_file.parent.mkdir(parents=True)
    project_file.write_text("{}\n", encoding="utf-8")
    manifest = home_manifest(
        layout, files=[layout["legit_file"], project_file],
        organs=[layout["legit_skill"]], hooks=[hook],
        backup_dir=layout["backup_dir"],
    )
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-1500:]
    assert not layout["legit_file"].exists()
    assert not layout["legit_skill"].exists()
    assert not hook.exists()
    assert not project_file.exists(), "project-dir entry in a home manifest not removed"
    assert not manifest.exists()
    assert layout["backup_dir"].is_dir(), "--no-restore must leave the backup in place"
    assert snapshot_outside(layout) == before


def test_legitimate_project_manifest_is_removed(layout):
    """install.sh writes local manifests to $(pwd)/.soma but always records a
    backup_dir under $HOME/.soma/backup — that must stay accepted."""
    mcp = layout["project"] / ".mcp.json"
    mcp.write_text('{"soma": 1}\n', encoding="utf-8")
    manifest = write_manifest(
        layout["project"] / ".soma" / "manifest.json",
        files=[mcp], platform="mcp", scope="local",
        backup_dir=layout["backup_dir"],
    )
    proc = uninstall(layout, "mcp")
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-1500:]
    assert not mcp.exists()
    assert not manifest.exists()
    assert layout["legit_file"].exists(), "home content touched by a project uninstall"


def test_final_component_symlink_is_unlinked_not_followed(layout):
    """A symlink as the final component is removed itself; its target survives."""
    link = layout["home"] / ".kiro" / "steering" / "linked.md"
    symlink_or_skip(str(layout["victim"]), str(link))
    dir_link = layout["home"] / ".kiro" / "skills" / "linked-skill"
    symlink_or_skip(str(layout["victim_dir"]), str(dir_link))
    manifest = home_manifest(layout, files=[link], organs=[dir_link])
    before = snapshot_outside(layout)
    proc = uninstall(layout)
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-1500:]
    assert not os.path.lexists(str(link))
    assert not os.path.lexists(str(dir_link))
    assert snapshot_outside(layout) == before, "symlink target was followed"
    assert not manifest.exists()


# ── Sink re-check ───────────────────────────────────────────────────────

def _path_check(kind, target, *roots):
    """Run the checker that uninstall.sh's guard_sink uses, in path mode."""
    src = read(UNINSTALL_SH)
    m = re.search(r"^PATH_CHECK_PY='(.*?)^'$", src, re.S | re.M)
    assert m, "PATH_CHECK_PY block not found in uninstall.sh"
    import subprocess, sys
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", m.group(1), "path", kind, target, *map(str, roots)],
        capture_output=True, text=True,
    )


def test_sink_check_rejects_component_swapped_for_symlink(layout):
    """Simulates the window between validation and rm: a directory that was
    real at validation time is replaced by a symlink out of the root."""
    target = layout["home"] / ".kiro" / "steering" / "soma-rule.md"
    assert _path_check("remove", str(target), layout["home"]).returncode == 0
    steering = layout["home"] / ".kiro" / "steering"
    os.rename(str(steering), str(layout["home"] / "steering-moved"))
    symlink_or_skip(str(layout["outside"]), str(steering))
    proc = _path_check("remove", str(target), layout["home"])
    assert proc.returncode == 1 and "symlink" in proc.stdout


def test_sink_check_rejects_backup_source_symlink(layout):
    link = layout["home"] / ".soma" / "backup" / "evil"
    symlink_or_skip(str(layout["outside"]), str(link))
    proc = _path_check("source", str(link), layout["home"] / ".soma" / "backup")
    assert proc.returncode == 1, "restore source symlink was accepted"
    assert _path_check("source", str(layout["backup_dir"]),
                       layout["home"] / ".soma" / "backup").returncode == 0


def test_every_sink_is_guarded():
    """Each rm/sed after the plan must be preceded by guard_sink."""
    src = read(UNINSTALL_SH)
    execute = src[src.index("# Inventory in-place backups BEFORE removing anything"):]
    execute = execute[:execute.index("# Clean soma hooks from claude settings.json")]
    execute += src[src.index('if [ -f "$MANIFEST_PATH" ]; then\n  guard_sink'):][:200]
    lines = execute.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"(rm -r?f|sed -i)", stripped):
            window = "\n".join(lines[max(0, i - 15):i])
            assert "guard_sink" in window, f"unguarded sink: {stripped}"


# ── PowerShell (static; pwsh is not available in this test environment) ─

def _ps1():
    return read(UNINSTALL_PS1)


def test_ps1_defines_safe_manifest_path_check():
    src = _ps1()
    m = re.search(r"function Test-SafeManifestPath\s*\{(.*?)\n\}", src, re.S)
    assert m, "Test-SafeManifestPath is not defined"
    body = m.group(1)
    assert "GetFullPath" in body, "must canonicalise with [IO.Path]::GetFullPath"
    assert "'..'" in body or '".."' in body, "must reject '..' segments"
    assert "OrdinalIgnoreCase" in body, "root prefix compare must be case-insensitive"
    assert "ReparsePoint" in body, "must reject reparse-point (symlink/junction) ancestors"
    assert "UserHome" in src and "WorkDir" in src


def test_ps1_validates_every_manifest_field_before_planning():
    src = _ps1()
    start = src.index("# ── Manifest Confinement")
    plan_idx = src.index("# ── Build the Removal Plan")
    assert start < plan_idx, "manifest confinement must run before the plan is built"
    validate = src[start:plan_idx]
    for field in ("files", "organs", "hooks", "backup_dir"):
        assert re.search(rf'"{field}"', validate), (
            f"manifest field {field!r} is not validated before the plan is built"
        )
    assert validate.count("Test-SafeManifestPath") >= 2, (
        "both the list fields and backup_dir must go through Test-SafeManifestPath"
    )
    assert "-RejectFinalReparsePoint" in validate, "backup_dir is a restore source"
    assert re.search(r"Test-SafeManifestPath[\s\S]*?exit 1", validate), (
        "validation failure must exit 1 before any removal"
    )
    # The manifest-derived plan must not be built from unvalidated data.
    assert src.index("Get-ManifestPathList -Object $Manifest") > start


def test_ps1_rechecks_before_every_removal():
    src = _ps1()
    execute = src[src.index("# ── Execute"):]
    removals = [m.start() for m in re.finditer(r"Remove-Item -LiteralPath \$(f|d|c) ", execute)]
    assert removals, "expected Remove-Item calls in the execute block"
    for pos in removals:
        window = execute[max(0, pos - 600):pos]
        assert "Assert-SafeSinkPath" in window or "Test-SafeManifestPath" in window, (
            "Remove-Item is not preceded by a sink re-check:\n" + execute[pos:pos + 80]
        )
    remove_section = src[src.index("function Remove-SomaSection"):]
    remove_section = remove_section[:remove_section.index("\n}\n")]
    assert "Assert-SafeSinkPath" in remove_section or "Test-SafeManifestPath" in remove_section, (
        "Remove-SomaSection writes/removes without a sink re-check"
    )
