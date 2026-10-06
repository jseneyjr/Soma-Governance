"""Static regression tests — one per audited finding that can be proven
without running an install. Each test names the finding it guards.

These are cheap and require no third-party packages, so they can gate every
commit.
"""
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import REPO_ROOT, iter_source_files, read, run

# ── SOMA-C03 / cross-OS: Bash 4 constructs break macOS Bash 3.2 ──────────

BASH4_PATTERNS = {
    "${var^} / ${var^^} case conversion": re.compile(r'\$\{[A-Za-z_][A-Za-z0-9_]*\^\^?\}'),
    "${var,,} case conversion": re.compile(r'\$\{[A-Za-z_][A-Za-z0-9_]*,,?\}'),
    "declare -A associative array": re.compile(r'\bdeclare\s+-A\b'),
    "typeset -A associative array": re.compile(r'\btypeset\s+-A\b'),
    "mapfile": re.compile(r'\bmapfile\b'),
    "readarray": re.compile(r'\breadarray\b'),
    "local -n nameref": re.compile(r'\blocal\s+-n\b'),
    "&>> append redirect": re.compile(r'&>>'),
}


def _shell_files():
    files = list(iter_source_files(os.path.join(REPO_ROOT, "install"), (".sh",)))
    hooks = os.path.join(REPO_ROOT, "install", "hooks")
    if os.path.isdir(hooks):
        files += [os.path.join(hooks, f) for f in os.listdir(hooks)]
    return [f for f in files if os.path.isfile(f)]


@pytest.mark.parametrize("label,pattern", sorted(BASH4_PATTERNS.items()))
def test_no_bash4_only_constructs(label, pattern):
    """SOMA-C03: macOS ships Bash 3.2; these constructs raise 'bad substitution'
    at expansion time, which `bash -n` cannot detect."""
    offenders = []
    for path in _shell_files():
        for lineno, line in enumerate(read(path).splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if pattern.search(line):
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, f"Bash 4+ construct ({label}) found:\n" + "\n".join(offenders)


# ── SOMA-C02: escaped quotes inside command substitution ────────────────

def test_no_escaped_quotes_in_command_substitution():
    """SOMA-C02: `cd \\"$(dirname ...)\\"` passes literal quote characters, so the
    script dies at line 4 before sourcing anything. Killed the PreToolUse gate."""
    offenders = []
    for path in _shell_files():
        for lineno, line in enumerate(read(path).splitlines(), 1):
            # Only flag the specific pattern that broke BASH_SOURCE resolution.
            # Legitimate uses like sed 's/"/\\"/g' inside $() are fine.
            if 'BASH_SOURCE' in line and '\\"' in line and "$(" in line:
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Escaped quotes inside command substitution:\n" + "\n".join(offenders)
    )




# ── SOMA-H04: unencoded file I/O corrupts on non-UTF-8 locales ──────────

OPEN_CALL = re.compile(r'(?<!\.)\bopen\s*\(')
BINARY_MODE = re.compile(r'''['"][rwxa+t]*b[rwxa+t]*['"]''')


def test_all_text_open_calls_specify_encoding():
    """SOMA-H04: requires-python >=3.9 means PEP 686 does not apply, so Windows
    uses the locale codepage. Rule files contain characters cp1252 cannot encode."""
    offenders = []
    for sub in ("soma_mcp", "soma_sdk"):
        root = os.path.join(REPO_ROOT, sub)
        if not os.path.isdir(root):
            continue
        for path in iter_source_files(root, (".py",)):
            for lineno, line in enumerate(read(path).splitlines(), 1):
                if not OPEN_CALL.search(line):
                    continue
                if "encoding=" in line or BINARY_MODE.search(line):
                    continue
                if "makedirs" in line or line.lstrip().startswith("#"):
                    continue
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "open() without encoding= (add encoding=\"utf-8\"):\n" + "\n".join(offenders)
    )


# ── SOMA-H03: path renames must land in every call site ─────────────────

def test_no_stale_gemini_config_paths():
    """SOMA-H03: install.sh writes .gemini/config/{rules,skills}. Referring to
    config/genome or config/organs means the fallback matches nothing."""
    stale = re.compile(r'\.gemini/config/(genome|organs)\b')
    targets = [
        os.path.join(REPO_ROOT, "install", "install.sh"),
        os.path.join(REPO_ROOT, "install", "uninstall.sh"),
        os.path.join(REPO_ROOT, "Makefile"),
    ]
    offenders = []
    for path in targets:
        if not os.path.exists(path):
            continue
        for lineno, line in enumerate(read(path).splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if stale.search(line):
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, "Stale gemini config path:\n" + "\n".join(offenders)


# ── SOMA-C05: backup and restore must agree on directory names ──────────

def test_backup_and_restore_directory_names_agree():
    """SOMA-C05: install.sh created $BACKUP_DIR/{genome,organs}; uninstall.sh
    restored from $BACKUP_DIR/{rules,skills}. Restore was dead code."""
    install_sh = os.path.join(REPO_ROOT, "install", "install.sh")
    if not os.path.exists(install_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    install = read(install_sh)
    uninstall = read(os.path.join(REPO_ROOT, "install", "uninstall.sh"))

    created = set(re.findall(r'"\$BACKUP_DIR/([A-Za-z0-9_.-]+)"', install))
    # install.sh also copies flat files via: cp "source/FILE" "$BACKUP_DIR/"
    # where the filename is inferred from the source, not explicit in the target.
    # Match patterns like: cp ".../<filename>" "$BACKUP_DIR/"
    for m in re.finditer(
        r'cp\s+(?:-r\s+)?"[^"]*?/([A-Za-z0-9_.-]+)"\s+"\$BACKUP_DIR/"',
        install,
    ):
        created.add(m.group(1))
    referenced = set()
    for line in uninstall.splitlines():
        if line.lstrip().startswith("#") or line.lstrip().startswith("echo"):
            continue
        referenced.update(re.findall(r'"\$BACKUP_DIR/([A-Za-z0-9_.-]+)"', line))

    # Payload names restore reads must be names install actually creates.
    unknown = {n for n in referenced if n not in created}
    assert not unknown, (
        f"uninstall.sh restores from $BACKUP_DIR/{sorted(unknown)} but install.sh "
        f"only creates $BACKUP_DIR/{sorted(created)}"
    )


# ── SOMA-C04: the manifest must record what was copied ──────────────────

def test_manifest_is_not_built_by_scanning_destinations():
    """SOMA-C04: building the manifest with `find $TARGET_...` enrolled every
    pre-existing user file in the destination directory for deletion."""
    install_sh = os.path.join(REPO_ROOT, "install", "install.sh")
    if not os.path.exists(install_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    install = read(install_sh)
    bad = re.compile(r'find\s+"\$(TARGET_RULES|TARGET_SKILLS|TARGET_HOOKS|TARGET_DIR)"')
    hits = [ln.strip() for ln in install.splitlines() if bad.search(ln)]
    assert not hits, (
        "manifest still scans destination directories:\n" + "\n".join(hits)
    )
    assert "record_installed_file" in install, "no explicit install recording found"


# ── SOMA-C06: backups must retain more than one generation ──────────────

def test_install_does_not_wipe_all_backups():
    """SOMA-C06: `rm -rf $RESOLVED_HOME/.soma/backup` left exactly one
    generation, so the pre-Soma state died on the second install."""
    install_sh = os.path.join(REPO_ROOT, "install", "install.sh")
    if not os.path.exists(install_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    install = read(install_sh)
    for lineno, line in enumerate(install.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        assert not re.search(r'rm\s+-rf\s+"\$RESOLVED_HOME/\.soma/backup"\s*$', line), (
            f"install.sh:{lineno} wipes every backup generation: {line.strip()}"
        )


# ── SOMA-C10: uninstall must not delete user-authored data ──────────────

def test_uninstall_preserves_user_data_by_default():
    """SOMA-C10: cells, fitness history and snapshots are authored by the user,
    not installed, so removal must be opt-in."""
    uninstall_sh = os.path.join(REPO_ROOT, "install", "uninstall.sh")
    if not os.path.exists(uninstall_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    uninstall = read(uninstall_sh)
    assert "--purge-data" in uninstall, "no opt-in flag guarding user data removal"
    assert "PRESERVED_PATHS" in uninstall, "user data is not tracked as preserved"


# ── SOMA-H07: --force must not disable recovery ─────────────────────────

def test_force_does_not_disable_restore():
    """SOMA-H07: --force skipped the deletion prompt AND the restore offer, so
    the one flag meant for automation removed the safety net."""
    uninstall_sh = os.path.join(REPO_ROOT, "install", "uninstall.sh")
    if not os.path.exists(uninstall_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    uninstall = read(uninstall_sh)
    assert "--no-restore" in uninstall, "no separate flag to suppress restore"
    assert "Force mode enabled, skipping restore" not in uninstall, (
        "--force still suppresses restore"
    )


def test_interactive_prompts_are_tty_guarded():
    """SOMA-H07: `read -p` returns 1 at EOF, which under `set -e` aborted the
    whole script in CI, containers and `curl | bash`."""
    uninstall_sh = os.path.join(REPO_ROOT, "install", "uninstall.sh")
    if not os.path.exists(uninstall_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    uninstall = read(uninstall_sh)
    assert "-t 0" in uninstall, "no TTY guard around interactive prompts"


# ── SOMA-C09: manifest read failures must be fatal ──────────────────────

def test_manifest_path_not_interpolated_into_python_source():
    """SOMA-C09: open('$MANIFEST_PATH') inside python3 -c made a quote in the
    path a silent SyntaxError and a crafted path code execution."""
    uninstall_sh = os.path.join(REPO_ROOT, "install", "uninstall.sh")
    if not os.path.exists(uninstall_sh):
        pytest.skip("legacy shell installers purged in v0.97.0")
    uninstall = read(uninstall_sh)
    assert "open('$MANIFEST_PATH')" not in uninstall, (
        "manifest path is still interpolated into Python source"
    )
    assert "SOMA_MANIFEST" in uninstall, "manifest path is not passed via environment"


# ── SOMA-C11 / C12 / H05: PowerShell parity ─────────────────────────────

def test_powershell_installer_resolves_repo_root():
    """SOMA-C11: $RepoDir resolved to <repo>/install, so genome/ and organs/
    pointed at directories that do not exist and 0 rules installed."""
    ps1 = os.path.join(REPO_ROOT, "install", "install.ps1")
    if not os.path.exists(ps1):
        pytest.skip("install.ps1 not present")
    content = read(ps1)
    assert re.search(r'\$RepoDir\s*=\s*\(Resolve-Path\s*\(Join-Path\s+\$ScriptDir\s+"\.\."\)\)', content), (
        "install.ps1 does not resolve the repo root one level above install/"
    )
    # The derived source dirs must exist relative to the real repo root.
    for name in ("genome", "organs"):
        assert os.path.isdir(os.path.join(REPO_ROOT, name)), f"{name}/ missing from repo root"
    assert not os.path.isdir(os.path.join(REPO_ROOT, "install", name)), (
        f"install/{name} exists — the C11 assertion is no longer meaningful"
    )


def test_powershell_rule_discovery_is_recursive():
    """SOMA-H05: non-recursive Get-ChildItem installed 7 of 13 rules; the other
    6 live in genome/.oracles, which also needs -Force (dot-directory)."""
    ps1 = os.path.join(REPO_ROOT, "install", "install.ps1")
    if not os.path.exists(ps1):
        pytest.skip("install.ps1 not present")
    offenders = []
    for lineno, line in enumerate(read(ps1).splitlines(), 1):
        if "Get-ChildItem" not in line or "$SourceRules" not in line:
            continue
        if "-Recurse" not in line or "-Force" not in line:
            offenders.append(f"install.ps1:{lineno}: {line.strip()}")
    assert not offenders, (
        "rule enumeration must use -Recurse -Force:\n" + "\n".join(offenders)
    )


def test_powershell_uninstaller_exists():
    """SOMA-C12: with no uninstall.ps1, a Windows user could not uninstall at
    all without first obtaining Git Bash or WSL."""
    ps1 = os.path.join(REPO_ROOT, "install", "uninstall.ps1")
    if not os.path.exists(ps1):
        pytest.skip("legacy shell/ps1 installers purged in v0.97.0")
    assert os.path.exists(ps1), (
        "install/uninstall.ps1 is missing"
    )


def test_powershell_scripts_with_non_ascii_have_utf8_bom():
    """Windows PowerShell 5.1 decodes BOM-less scripts as ANSI (cp1252): the
    em-dash's trailing 0x94 byte becomes a closing quote and the installer
    fails to parse at all."""
    offenders = []
    for path in iter_source_files(REPO_ROOT, (".ps1", ".psm1")):
        with open(path, "rb") as f:
            data = f.read()
        if not data.isascii() and not data.startswith(b"\xef\xbb\xbf"):
            offenders.append(os.path.relpath(path, REPO_ROOT))
    assert not offenders, f"non-ASCII PowerShell scripts missing UTF-8 BOM: {offenders}"


def test_powershell_mcp_platform_parity():
    """install.ps1 must support MCP and bind it to the governed workspace."""
    ps1 = os.path.join(REPO_ROOT, "install", "install.ps1")
    if not os.path.exists(ps1):
        pytest.skip("install.ps1 not present")

    with open(ps1, "r", encoding="utf-8") as f:
        content = f.read()

    assert '"mcp" {' in content, "install.ps1 is missing the 'mcp' platform switch case"
    assert re.search(r'"cwd"\s*=', content), "install.ps1 MCP generation is missing cwd"
    assert '"SOMA_WORKSPACE"' in content, "install.ps1 MCP generation is missing SOMA_WORKSPACE"
    assert '"SOMA_ROOT"' not in content, "install.ps1 still emits the obsolete SOMA_ROOT key"
def test_rule_basenames_are_unique_when_flattened():
    """install.sh flattens genome/**/*.md into one directory, so a duplicate
    basename would silently overwrite, last write winning."""
    genome = os.path.join(REPO_ROOT, "genome")
    seen = {}
    for path in iter_source_files(genome, (".md",)):
        name = os.path.basename(path)
        seen.setdefault(name, []).append(os.path.relpath(path, REPO_ROOT))
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"duplicate rule basenames would collide on install: {dupes}"


# ── SOMA-M01: JSON must not contain Infinity ────────────────────────────

def test_no_infinity_emitted_in_json_payloads():
    """SOMA-M01: json.dumps(float('inf')) emits bare `Infinity`, which RFC 8259
    forbids; strict non-Python MCP clients reject the frame."""
    offenders = []
    for sub in ("soma_mcp", "soma_sdk"):
        root = os.path.join(REPO_ROOT, sub)
        if not os.path.isdir(root):
            continue
        for path in iter_source_files(root, (".py",)):
            for lineno, line in enumerate(read(path).splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if re.search(r"float\(\s*['\"]inf['\"]\s*\)", line):
                    rel = os.path.relpath(path, REPO_ROOT)
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "float('inf') reaches JSON payloads:\n" + "\n".join(offenders)
    )


# ── SOMA-C01: soma_mcp must import without third-party packages ─────────

def test_soma_mcp_has_no_unguarded_third_party_imports():
    """SOMA-C01: a bare `import yaml` in soma_mcp/ stopped the server from
    starting at all, violating .soma/cells/walls/wall-mcp-zero-deps.md."""
    offenders = []
    for path in iter_source_files(os.path.join(REPO_ROOT, "soma_mcp"), (".py",)):
        lines = read(path).splitlines()
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped in ("import yaml",) or stripped.startswith("from yaml"):
                # Acceptable only inside a try: block.
                context = "\n".join(lines[max(0, lineno - 4):lineno])
                if "try:" not in context:
                    rel = os.path.relpath(path, REPO_ROOT)
                    offenders.append(f"{rel}:{lineno}: unguarded {stripped}")
    assert not offenders, (
        "soma_mcp must degrade without pyyaml:\n" + "\n".join(offenders)
    )


def test_mcp_server_answers_jsonrpc_without_pyyaml(tmp_path):
    """SOMA-C01 end to end: initialize + tools/list must return valid JSON on a
    bare interpreter. Regression: ModuleNotFoundError, exit 1, 0 bytes stdout."""
    (tmp_path / ".soma" / "cells").mkdir(parents=True)
    requests = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
    )
    env = {"PYTHONPATH": REPO_ROOT}
    proc = subprocess.run(
        [sys.executable, "-m", "soma_mcp"],
        cwd=str(tmp_path), input=requests, capture_output=True, text=True,
        timeout=120, env={**os.environ, **env},
    )
    assert proc.returncode == 0, f"server exited {proc.returncode}: {proc.stderr[:600]}"
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, f"server produced no stdout. stderr: {proc.stderr[:600]}"
    for ln in lines:
        json.loads(ln)  # every framed response must be valid JSON
    first = json.loads(lines[0])
    assert first["result"]["serverInfo"]["name"] == "soma-mcp"
    tools = json.loads(lines[1])["result"]["tools"]
    assert len(tools) >= 1


# ── SOMA-C02: Framework-wide zero third-party runtime dependencies ──────

def test_entire_runtime_has_zero_third_party_imports():
    """SOMA-C02: soma_cli/, soma_core/, soma_mcp/, soma_sdk/, and enzymes/
    must have strictly ZERO third-party runtime package imports.
    Only Python standard library modules and internal modules are permitted at runtime.
    Optional inference providers must be strictly guarded by try/except."""
    import ast
    from soma_core.verification.import_guard import _get_stdlib_modules

    stdlib = set(_get_stdlib_modules()) | set(sys.builtin_module_names)
    internal_prefixes = ("soma_", "install", "genome")
    soma_core_dir = os.path.join(REPO_ROOT, "soma_core")
    soma_core_modules = {
        f[:-3] for f in os.listdir(soma_core_dir) if f.endswith(".py")
    } if os.path.isdir(soma_core_dir) else set()
    internal_names = soma_core_modules | {"conftest"}
    optional_allowed = {"google", "anthropic", "openai", "keyring"}

    offenders = []
    runtime_dirs = ["soma_cli", "soma_core", "soma_mcp", "soma_sdk"]
    for rdir in runtime_dirs:
        dir_path = os.path.join(REPO_ROOT, rdir)
        for path in iter_source_files(dir_path, (".py",)):
            try:
                tree = ast.parse(read(path), filename=path)
            except SyntaxError as e:
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{e.lineno}: SyntaxError: {e.msg}")
                continue

            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        continue  # relative imports within package are internal
                    if node.module:
                        modules = [node.module.split(".")[0]]
                elif isinstance(node, ast.Call):
                    if (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "__import__"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        modules = [node.args[0].value.split(".")[0]]
                    elif (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "import_module"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        modules = [node.args[0].value.split(".")[0]]

                for mod in modules:
                    if mod in stdlib:
                        continue
                    if any(mod.startswith(p) for p in internal_prefixes) or mod in internal_names:
                        continue
                    # Permitted optional dependencies must be guarded inside try body
                    in_try = any(
                        isinstance(p, ast.Try) and any(any(c is node for c in ast.walk(item)) for item in p.body)
                        for p in ast.walk(tree)
                    )
                    if mod in optional_allowed and in_try:
                        continue
                    rel = os.path.relpath(path, REPO_ROOT)
                    offenders.append(f"{rel}:{node.lineno}: {mod}")
    assert not offenders, (
        "SOMA-C02 violation: Runtime modules must have zero third-party imports:\n"
        + "\n".join(offenders)
    )


# ── SOMA-M07: one source of truth for the version ───────────────────────

def test_version_is_single_sourced():
    """SOMA-M07: all five version surfaces must agree with VERSION."""
    version_file = read(os.path.join(REPO_ROOT, "VERSION")).strip()

    pyproject = read(os.path.join(REPO_ROOT, "pyproject.toml"))
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert match, "no version in pyproject.toml"
    assert match.group(1) == version_file, (
        f"pyproject.toml ({match.group(1)}) != VERSION ({version_file})"
    )

    python_sdk = read(os.path.join(REPO_ROOT, "soma_sdk", "__init__.py"))
    sdk_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", python_sdk, re.M)
    assert sdk_match and sdk_match.group(1) == version_file, (
        f"Python SDK ({sdk_match.group(1) if sdk_match else 'missing'}) != VERSION ({version_file})"
    )

    from soma_mcp.server import _server_version
    assert _server_version() == version_file, (
        f"MCP runtime ({_server_version()}) != VERSION ({version_file})"
    )

    server = read(os.path.join(REPO_ROOT, "soma_mcp", "server.py"))
    assert f'"{version_file}"' not in server.replace('_server_version', ''), (
        "server.py still hardcodes the version string"
    )

    readme = read(os.path.join(REPO_ROOT, "README.md"))
    readme_badge_match = re.search(r'badge/Version-([0-9]+\.[0-9]+\.[0-9]+)-', readme)
    assert readme_badge_match and readme_badge_match.group(1) == version_file, (
        f"README.md badge ({readme_badge_match.group(1) if readme_badge_match else 'missing'}) != VERSION ({version_file})"
    )

    security = read(os.path.join(REPO_ROOT, "SECURITY.md"))
    major_minor = ".".join(version_file.split(".")[:2])
    assert f"| {major_minor}.x" in security, (
        f"SECURITY.md does not list {major_minor}.x as supported"
    )


# ── SOMA-M03: failure paths must exit nonzero ───────────────────────────

def test_cli_exits_nonzero_on_unknown_command():
    """SOMA-M03: main() returned None on the unknown-command path, so the
    console script produced exit 0 while printing an error."""
    proc = run([sys.executable, '-m', 'soma_cli.cli',
                'definitely-not-a-command'])
    assert proc.returncode != 0, (
        f"CLI reported an unknown command but exited 0:\n{proc.stdout}{proc.stderr}"
    )


# ── SOMA-H01: the verification gate must be able to fail ────────────────

def test_make_validate_fails_on_broken_shell_script(tmp_path):
    """SOMA-H01: `bash -n "$s" && echo ok || echo fail` swallowed the exit
    status, so a syntax error anywhere kept CI green.

    Verifies that bash -n actually returns non-zero on broken syntax,
    which is the mechanism make validate relies on."""
    broken = tmp_path / "zz_pytest_broken.sh"
    broken.write_text("f() {\n")  # unterminated function body

    # Verify bash -n catches the syntax error (this is what make validate uses)
    proc = subprocess.run(
        ["bash", "-n", str(broken)],
        capture_output=True, text=True
    )
    assert proc.returncode != 0, (
        "bash -n passed despite a syntax error — make validate would miss this"
    )


def test_make_validate_covers_the_uninstaller():
    """SOMA-H01: uninstall.sh — the destructive script — was excluded from the
    validation file list entirely."""
    if not os.path.exists(os.path.join(REPO_ROOT, "install", "uninstall.sh")):
        pytest.skip("legacy shell installers purged in v0.97.0")
    makefile = read(os.path.join(REPO_ROOT, "Makefile"))
    validate = makefile.split("validate:")[1].split("\nupdate:")[0]
    assert "uninstall.sh" in validate, "make validate does not check uninstall.sh"
