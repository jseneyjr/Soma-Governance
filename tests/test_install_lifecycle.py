"""Install/uninstall lifecycle regression tests.

Every test runs against an isolated HOME under tmp_path, so the real user
configuration is never touched. These cover the findings that only appear when
the installer actually runs.
"""
import json
import os
import subprocess

import pytest

from conftest import REPO_ROOT, read, run

INSTALL = os.path.join(REPO_ROOT, "install", "install.sh")
UNINSTALL = os.path.join(REPO_ROOT, "install", "uninstall.sh")

pytestmark = pytest.mark.skipif(
    not os.path.exists(INSTALL),
    reason="legacy shell installers purged in v0.97.0 in favor of soma install/uninstall",
)


def install(home, platform="kiro", *args, bash="/bin/bash"):
    env = {"HOME": str(home), "USERPROFILE": str(home)}
    return run([bash, INSTALL, platform, *args], env=env)


def uninstall(home, platform="kiro", *args, bash="/bin/bash"):
    env = {"HOME": str(home), "USERPROFILE": str(home)}
    return run([bash, UNINSTALL, platform, *args], env=env)


def manifest_of(home):
    path = os.path.join(str(home), ".soma", "manifest.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def home_with_user_content(fake_home):
    """An isolated HOME that already contains user-authored Kiro content,
    mimicking a real machine where Soma is not the only thing installed."""
    steering = fake_home / ".kiro" / "steering"
    skills = fake_home / ".kiro" / "skills" / "my-own-skill"
    hooks = fake_home / ".kiro" / "hooks"
    for d in (steering, skills, hooks):
        d.mkdir(parents=True, exist_ok=True)
    (steering / "my-own-rule.md").write_text("user authored rule\n", encoding="utf-8")
    (skills / "SKILL.md").write_text("user authored skill\n", encoding="utf-8")
    (hooks / "my-own.kiro.hook").write_text("{}\n", encoding="utf-8")
    return fake_home


# ── SOMA-C04 ────────────────────────────────────────────────────────────

def test_manifest_excludes_preexisting_user_files(home_with_user_content, bash):
    """SOMA-C04: the manifest was built by scanning the destination, so it
    enrolled third-party skills and hand-written hooks for deletion."""
    proc = install(home_with_user_content, "kiro", bash=bash)
    assert proc.returncode == 0, proc.stderr[-800:]

    data = manifest_of(home_with_user_content)
    recorded = data["files"] + data["organs"] + data["hooks"]

    foreign = [p for p in recorded if "my-own" in p]
    assert not foreign, f"manifest enrolled user-authored paths: {foreign}"

    backups = [p for p in recorded if ".bak." in p]
    assert not backups, f"manifest enrolled backup artifacts: {backups}"

    assert data["platform"] == "kiro"
    assert len(data["files"]) > 0 and len(data["organs"]) > 0


def test_uninstall_leaves_user_files_intact(home_with_user_content, bash):
    """SOMA-C04 + SOMA-C10: a full round trip must remove only what was installed."""
    assert install(home_with_user_content, "kiro", bash=bash).returncode == 0
    proc = uninstall(home_with_user_content, "kiro", "--force", "--no-restore", bash=bash)
    assert proc.returncode == 0, proc.stderr[-800:]

    steering = home_with_user_content / ".kiro" / "steering"
    assert (steering / "my-own-rule.md").exists(), "user rule was deleted"
    assert (home_with_user_content / ".kiro" / "skills" / "my-own-skill").exists(), \
        "user skill was deleted"
    assert (home_with_user_content / ".kiro" / "hooks" / "my-own.kiro.hook").exists(), \
        "user hook was deleted"

    # And Soma's own rules are gone.
    remaining = {p.name for p in steering.glob("*.md")}
    assert remaining == {"my-own-rule.md"}, f"soma rules left behind: {remaining}"


# ── SOMA-C07 ────────────────────────────────────────────────────────────

def test_wrong_platform_uninstall_is_refused(fake_home, bash):
    """SOMA-C07: the manifest branch ignored $PLATFORM, so `uninstall.sh mcp`
    against a kiro manifest deleted the kiro install."""
    assert install(fake_home, "kiro", bash=bash).returncode == 0
    before = len(list((fake_home / ".kiro" / "steering").glob("*.md")))
    assert before > 0

    proc = uninstall(fake_home, "mcp", "--no-restore", bash=bash)
    assert proc.returncode != 0, "platform mismatch was not refused"
    assert "MISMATCH" in (proc.stdout + proc.stderr).upper()

    after = len(list((fake_home / ".kiro" / "steering").glob("*.md")))
    assert after == before, "files were removed despite the platform mismatch"


def test_platform_mismatch_can_be_overridden_with_force(fake_home, bash):
    """The guard must be overridable, but only explicitly."""
    assert install(fake_home, "kiro", bash=bash).returncode == 0
    proc = uninstall(fake_home, "mcp", "--force", "--no-restore", bash=bash)
    assert proc.returncode == 0
    assert "MISMATCH" in (proc.stdout + proc.stderr).upper()


# ── SOMA-C09 ────────────────────────────────────────────────────────────

def test_malformed_manifest_aborts_without_deleting(fake_home, bash):
    """SOMA-C09: process-substitution failures are invisible to `set -e`, so a
    broken manifest produced an empty plan, deleted the manifest, and reported
    'Uninstall complete.'"""
    assert install(fake_home, "kiro", bash=bash).returncode == 0
    manifest_path = fake_home / ".soma" / "manifest.json"
    manifest_path.write_text("{ not valid json", encoding="utf-8")

    before = len(list((fake_home / ".kiro" / "steering").glob("*.md")))
    proc = uninstall(fake_home, "kiro", "--force", "--no-restore", bash=bash)

    assert proc.returncode != 0, "malformed manifest did not abort the uninstall"
    after = len(list((fake_home / ".kiro" / "steering").glob("*.md")))
    assert after == before, "files were removed despite an unreadable manifest"
    assert manifest_path.exists(), "the unreadable manifest was deleted anyway"


# ── SOMA-C06 ────────────────────────────────────────────────────────────

def test_multiple_backup_generations_are_retained(fake_home, bash):
    """SOMA-C06: `rm -rf .soma/backup` before each install left one generation,
    so after the second install the pre-Soma state was unrecoverable."""
    import time
    for _ in range(3):
        assert install(fake_home, "kiro", bash=bash).returncode == 0
        time.sleep(1.1)  # backup dirs are second-resolution timestamps

    generations = sorted((fake_home / ".soma" / "backup").iterdir())
    assert len(generations) >= 2, (
        f"expected multiple retained generations, found {len(generations)}"
    )


# ── SOMA-C08 ────────────────────────────────────────────────────────────

def test_claude_install_records_claude_md(fake_home, bash, tmp_path):
    """SOMA-C08: the manifest elif chain matched TARGET_DIR before TARGET_FILE,
    so CLAUDE.md was never recorded and `uninstall.sh claude` was a no-op."""
    project = tmp_path / "project"
    project.mkdir()
    proc = run([bash, INSTALL, "claude"], cwd=str(project), env={"HOME": str(fake_home)})
    assert proc.returncode == 0, proc.stderr[-800:]

    data = manifest_of(fake_home)
    recorded = " ".join(data["files"])
    assert "CLAUDE.md" in recorded, (
        f"CLAUDE.md missing from the manifest; recorded: {data['files']}"
    )


# ── SOMA-C10 ────────────────────────────────────────────────────────────

def test_uninstall_preserves_cells_without_purge_flag(fake_home, bash, tmp_path):
    """SOMA-C10: cells are user-authored governance data. Uninstalling the tool
    must not delete them."""
    project = tmp_path / "proj"
    cells = project / ".soma" / "cells" / "vacuoles"
    cells.mkdir(parents=True)
    marker = cells / "trap-precious.md"
    marker.write_text("---\ntype: vacuole\n---\n## Precious\n", encoding="utf-8")

    proc = run([bash, INSTALL, "mcp"], cwd=str(project), env={"HOME": str(fake_home)})
    assert proc.returncode == 0, proc.stderr[-800:]
    proc = run([bash, UNINSTALL, "mcp", "--force", "--no-restore"],
               cwd=str(project), env={"HOME": str(fake_home)})
    assert proc.returncode == 0, proc.stderr[-800:]

    assert marker.exists(), "user-authored cell was deleted by uninstall"

# ── SOMA-C05 (runtime) ──────────────────────────────────────────────────

def test_backup_restore_cycle_preserves_preexisting_rules(fake_home, bash):
    """SOMA-C05: backup writes genome/organs but restore read rules/skills,
    so restore was dead code.  This verifies end-to-end: install over existing
    rules, uninstall with restore, and check pre-existing content is back."""
    rules_dir = fake_home / ".kiro" / "steering"
    rules_dir.mkdir(parents=True)
    sentinel = rules_dir / "user-rule.md"
    sentinel.write_text("# My precious rule\n", encoding="utf-8")

    # Install overwrites/merges into the target
    assert install(fake_home, "kiro", bash=bash).returncode == 0

    # Uninstall WITH restore (no --no-restore flag)
    proc = run([bash, UNINSTALL, "kiro", "--force"],
               env={"HOME": str(fake_home)}, timeout=120)
    assert proc.returncode == 0, f"uninstall failed: {proc.stderr[-500:]}"

    assert sentinel.exists(), (
        "pre-existing rule was not restored after uninstall"
    )
    assert sentinel.read_text(encoding="utf-8").strip() == "# My precious rule", (
        "restored rule content does not match original"
    )


# ── SOMA-H07 ────────────────────────────────────────────────────────────


def test_uninstall_does_not_hang_or_abort_without_a_tty(fake_home, bash):
    """SOMA-H07: `read -p` returns 1 at EOF, so under `set -e` the uninstaller
    died with a bare exit 1 in CI, containers and `curl | bash`."""
    assert install(fake_home, "kiro", bash=bash).returncode == 0
    proc = run([bash, UNINSTALL, "kiro"], env={"HOME": str(fake_home)},
               stdin=subprocess.DEVNULL, timeout=120)
    combined = proc.stdout + proc.stderr
    # Must exit deliberately with an explanation, not crash on a failed read.
    assert proc.returncode in (0, 2), f"unexpected exit {proc.returncode}: {combined[-500:]}"
    assert "not a terminal" in combined.lower() or "aborting" in combined.lower(), (
        f"no explanation for the non-interactive abort: {combined[-500:]}"
    )


# ── Dry run must not mutate anything ────────────────────────────────────

@pytest.mark.parametrize("platform", ["gemini", "kiro", "copilot", "claude", "mcp"])
def test_dry_run_install_writes_nothing(fake_home, bash, tmp_path, platform):
    """CI only ever exercised `gemini --dry-run`; every other platform branch was
    never executed at all (SOMA-H06)."""
    project = tmp_path / f"proj-{platform}"
    project.mkdir()
    proc = run([bash, INSTALL, platform, "--dry-run"],
               cwd=str(project), env={"HOME": str(fake_home)})
    assert proc.returncode == 0, f"{platform} dry-run failed: {proc.stderr[-600:]}"

    created = list(fake_home.rglob("*")) + list(project.rglob("*"))
    assert not created, f"dry-run created files for {platform}: {created[:5]}"


# ── Starter Pack ────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTER_PACK = os.path.join(REPO_ROOT, "install", "starter_pack.txt")


def test_starter_pack_file_exists():
    """The starter_pack.txt manifest must exist."""
    assert os.path.isfile(STARTER_PACK), f"Missing: {STARTER_PACK}"


def test_starter_pack_has_five_entries():
    """Exactly 5 rules in the starter pack."""
    with open(STARTER_PACK) as f:
        entries = [line.strip() for line in f if line.strip()]
    assert len(entries) == 5, f"Expected 5 entries, got {len(entries)}: {entries}"


def test_starter_pack_files_exist():
    """Every file listed in starter_pack.txt must exist in the repo."""
    with open(STARTER_PACK) as f:
        entries = [line.strip() for line in f if line.strip()]
    for entry in entries:
        path = os.path.join(REPO_ROOT, entry)
        assert os.path.isfile(path), f"Starter rule not found: {entry} ({path})"


def test_starter_rules_match_init():
    """Starter pack manifest matches STARTER_RULES_LEGACY in soma_cli/init.py."""
    from soma_cli.init import STARTER_RULES_LEGACY
    with open(STARTER_PACK) as f:
        manifest = {line.strip() for line in f if line.strip()}
    init_paths = set(STARTER_RULES_LEGACY.values())
    assert manifest == init_paths, (
        f"Manifest and STARTER_RULES_LEGACY diverge:\n"
        f"  manifest only: {manifest - init_paths}\n"
        f"  init.py only: {init_paths - manifest}"
    )

# ── install_hooks: encoding and atomic render ──────────────────────────────

ENZYMES = os.path.join(REPO_ROOT, "enzymes")

def _fake_repo(tmp_path, template_text):
    repo = tmp_path / "repo"
    (repo / "install").mkdir(parents=True)
    (repo / "enzymes").mkdir()
    tpl = repo / "install" / "hooks.json.template"
    tpl.write_text(template_text, encoding="utf-8")
    return repo, tpl

def _env(tmp_path, **extra):
    import sys
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"HOME": str(home), "USERPROFILE": str(home), "SOMA_PYTHON": sys.executable,
           "SOMA_PYTHON_RESOLVED": ""}
    env.update(extra)
    return env

def _install_hooks(bash, tmp_path, repo, target, **extra):
    common_sh = os.path.join(ENZYMES, "common.sh")
    if not os.path.exists(common_sh):
        pytest.skip("enzymes directory purged in v0.97.0")
    script = (f'source "{ENZYMES}/common.sh"; '
              f'install_hooks "{repo}" "{target}"')
    return run([bash, "-c", script], env=_env(tmp_path, **extra))

def test_install_hooks_renders_utf8_template_under_ascii_locale(tmp_path, bash):
    repo, _ = _fake_repo(
        tmp_path, '{"hooks": [{"name": "gate \u2705", "cmd": "{{SCRIPTS_DIR}}/x.sh"}]}')
    target = tmp_path / "out"
    proc = _install_hooks(bash, tmp_path, repo, target, LC_ALL="C", LANG="C",
                          PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
                          PYTHONIOENCODING="")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(read(str(target / "hooks.json")))
    assert data["hooks"][0]["name"] == "gate \u2705"
    assert data["hooks"][0]["cmd"].replace("\\", "/") == (str(repo / "enzymes") + "/x.sh").replace("\\", "/")

ORIGINAL_HOOKS = '{"hooks": "original"}\n'

def _existing_target(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    (target / "hooks.json").write_text(ORIGINAL_HOOKS, encoding="utf-8")
    return target

def test_install_hooks_invalid_render_keeps_existing_hooks(tmp_path, bash):
    repo, _ = _fake_repo(tmp_path, '{ not json {{SCRIPTS_DIR}}')
    target = _existing_target(tmp_path)
    proc = _install_hooks(bash, tmp_path, repo, target)
    assert proc.returncode != 0
    assert read(str(target / "hooks.json")) == ORIGINAL_HOOKS
    assert os.listdir(str(target)) == ["hooks.json"], "temp file left behind"

def test_install_hooks_failed_render_keeps_existing_hooks(tmp_path, bash):
    if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
        pytest.skip("needs POSIX permissions enforced for this user")
    repo, tpl = _fake_repo(tmp_path, '{"cmd": "{{SCRIPTS_DIR}}"}')
    tpl.chmod(0)  # rendering (the read) fails; the -f existence check passes
    target = _existing_target(tmp_path)
    try:
        proc = _install_hooks(bash, tmp_path, repo, target)
    finally:
        tpl.chmod(0o644)
    assert proc.returncode != 0
    assert read(str(target / "hooks.json")) == ORIGINAL_HOOKS
    assert os.listdir(str(target)) == ["hooks.json"], "temp file left behind"

# ── BUG-043: manifestless uninstall fails closed without Python ────────────

STORE_STUB_EXIT = 49

def _write_exe(path, body):
    import stat
    path.write_bytes(("#!/bin/sh\n" + body + "\n").encode("utf-8"))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def _snapshot(root):
    out = {}
    for dirpath, _dirs, files in os.walk(str(root)):
        for name in files:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, str(root))] = fh.read()
    return out

def test_manifestless_uninstall_without_python_removes_nothing(tmp_path, bash):
    if os.name == "nt":
        pytest.skip("POSIX shebang shims; the stub is simulated, not native")
    proj = tmp_path / "proj"
    proj.mkdir()
    home = tmp_path / "home"
    env = _env(tmp_path)
    proc = run([bash, os.path.join(REPO_ROOT, "install", "install.sh"), "kiro"],
               cwd=str(proj), env=env)
    assert proc.returncode == 0, proc.stderr[-800:]
    (home / ".soma" / "manifest.json").unlink()
    hooks = home / ".kiro" / "hooks" / "hooks.json"
    assert hooks.exists()
    before = _snapshot(home)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name in ("python3", "python", "py"):
        _write_exe(fake_bin / name, f"exit {STORE_STUB_EXIT}")
    env = dict(env, SOMA_PYTHON="",
               PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))
    proc = run([bash, os.path.join(REPO_ROOT, "install", "uninstall.sh"), "kiro",
                "--force", "--no-restore", "--keep-config"], cwd=str(proj), env=env)
    assert proc.returncode != 0, "uninstall proceeded without a confinement check"
    assert "SOMA_PYTHON" in proc.stderr, proc.stderr
    assert _snapshot(home) == before, "files were removed"
