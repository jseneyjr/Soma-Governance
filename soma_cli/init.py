"""soma init — Set up governance for this project.

Detects platform and project type, installs starter rules.
"""
from __future__ import annotations

import argparse
import importlib.resources
import shutil
from pathlib import Path


# ── Starter Pack ────────────────────────────────────────────────────────────
# The 5 rules that deliver immediate value on any project, any language.
# Keys are the rule stems — files are bundled in soma_cli/starter_rules/.

STARTER_RULES = [
    "providence",
    "destructive-ops",
    "testing",
    "cost-optimization",
    "git-workflow",
]

# Legacy mapping for manifest cross-validation (starter_pack.txt)
STARTER_RULES_LEGACY = {
    "providence": "genome/providence.md",
    "destructive-ops": "genome/destructive-ops.md",
    "testing": "genome/.oracles/testing.md",
    "cost-optimization": "genome/cost-optimization.md",
    "git-workflow": "genome/.oracles/git-workflow.md",
}


def _get_starter_rule_path(name: str) -> Path | None:
    """Resolve the path to a bundled starter rule file.

    Uses importlib.resources to find files inside the soma_cli package,
    working in both editable installs and wheel distributions.
    """
    try:
        ref = importlib.resources.files("soma_cli") / "starter_rules" / f"{name}.md"
        # Materialize to a real path (works for both installed and editable)
        path = Path(str(ref))
        if path.is_file():
            return path
    except (TypeError, FileNotFoundError):
        pass
    return None


# ── Detection ───────────────────────────────────────────────────────────────

def detect_platform(project_root: Path) -> str:
    """Detect the AI platform from directory markers.

    Returns: 'gemini' | 'claude' | 'cursor' | 'copilot' | 'unknown'
    """
    project_root = Path(project_root)

    if (project_root / ".gemini").is_dir():
        return "gemini"
    if (project_root / ".claude").is_dir():
        return "claude"
    if (project_root / ".cursor").is_dir() or (project_root / ".cursorrules").is_file():
        return "cursor"
    if (project_root / ".github" / "copilot").is_dir() or (project_root / ".github" / "copilot-instructions.md").is_file():
        return "copilot"

    return "unknown"


def detect_project_type(project_root: Path) -> str:
    """Detect the project type from config files.

    Returns: 'python' | 'javascript' | 'rust' | 'go' | 'dotnet' | 'unknown'
    """
    project_root = Path(project_root)
    checks = [
        (["pyproject.toml", "setup.py", "setup.cfg"], "python"),
        (["package.json"], "javascript"),
        (["Cargo.toml"], "rust"),
        (["go.mod"], "go"),
    ]
    for files, lang in checks:
        for f in files:
            if (project_root / f).exists():
                return lang
    return "unknown"


# ── Rules directory per platform ────────────────────────────────────────────

def get_rules_dir(platform: str, home: Path | None = None,
                  project_root: Path | None = None) -> Path:
    """Return the target rules directory for the given platform.

    Args:
        platform: One of 'gemini', 'claude', 'cursor', 'copilot'.
        home: Home directory override (for testing).
        project_root: Project directory override (for copilot, which is project-relative).

    Returns:
        Path to the platform's rules directory.

    Raises:
        ValueError: If platform is unsupported.
    """
    if home is None:
        home = Path.home()
    home = Path(home)
    if project_root is None:
        project_root = Path.cwd()
    project_root = Path(project_root)

    dirs = {
        "gemini": home / ".gemini" / "config" / "rules",
        "claude": home / ".claude",
        "cursor": home / ".cursor" / "rules",
        "copilot": project_root / ".github" / "copilot",
    }
    if platform not in dirs:
        raise ValueError(
            f"Unsupported platform: '{platform}'. "
            f"Supported: {', '.join(sorted(dirs))}"
        )
    return dirs[platform]


# ── Installation ────────────────────────────────────────────────────────────

def check_existing_install(project_root: Path) -> bool:
    """Check if Soma is already installed in this project."""
    return (Path(project_root) / ".soma").is_dir()


def install_starter_rules(
    rules_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> list[str]:
    """Install the 5 starter rules to the target directory.

    Args:
        rules_dir: Target directory for rules.
        dry_run: If True, don't create files.
        force: If True, overwrite existing rules.

    Returns:
        List of installed rule names.
    """
    installed = []

    for name in STARTER_RULES:
        source = _get_starter_rule_path(name)
        if source is None:
            print(f"  ⚠️  {name}: source not found")
            continue

        dest = rules_dir / f"{name}.md"

        # Security: reject symlink destinations to prevent arbitrary
        # file overwrite (e.g. symlink pointing to ~/.bashrc)
        if dest.is_symlink():
            print(f"  ⚠️  {name}: skipped (destination is a symlink)")
            continue

        # Don't overwrite user-customized rules unless forced
        if dest.exists() and not force:
            print(f"  ℹ️  {name}: already exists, skipping (use --force to overwrite)")
            installed.append(name)
            continue

        if not dry_run:
            rules_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)

        installed.append(name)

    return installed


# ── Main flow ───────────────────────────────────────────────────────────────

def run_init(args: argparse.Namespace) -> int:
    """Main init flow. Returns exit code."""
    # Allow test override of project root
    project_root = getattr(args, "_project_root", Path.cwd())
    project_root = Path(project_root)

    dry_run = args.dry_run
    forced_platform = args.platform

    print()
    print("  🧬 Soma Governance — Setup")
    print()

    # 1. Detect platform
    if forced_platform:
        platform = forced_platform
        print(f"  Platform: {platform} (forced)")
    else:
        platform = detect_platform(project_root)
        # Fallback: check home directory if project-level detection fails
        if platform == "unknown" and not getattr(args, "_project_root", None):
            platform = detect_platform(Path.home())
        if platform == "unknown":
            print("  ⚠️  Could not detect platform.")
            print("     Use --platform to specify: gemini, claude, cursor, copilot")
            return 1
        print(f"  Detected platform: {platform}")

    # 2. Detect project type
    project_type = detect_project_type(project_root)
    if project_type != "unknown":
        print(f"  Detected project: {project_type}")
    else:
        print("  Project type: unknown (rules are language-agnostic)")

    # 3. Check existing install
    if check_existing_install(project_root):
        print()
        print("  ℹ️  Existing Soma installation detected (.soma/ directory).")
        print("     Starter rules will be added alongside existing rules.")

    print()

    # 4. Resolve target directory
    try:
        # Use project_root as home override for testing
        home = getattr(args, "_project_root", None)
        rules_dir = get_rules_dir(platform, home=home, project_root=project_root)
    except ValueError as e:
        print(f"  ❌ {e}")
        return 1

    # 5. Confirmation prompt (unless --yes or --dry-run)
    skip_confirm = getattr(args, "yes", False) or dry_run
    if not skip_confirm:
        print(f"  Will install 5 starter rules to: {rules_dir}")
        try:
            answer = input("  Proceed? [Y/n] ").strip().lower()
            if answer and answer not in ("y", "yes"):
                print("  Aborted.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\n  Aborted.")
            return 0
    print()

    # 6. Install starter rules
    if dry_run:
        print("  Installing 5 starter rules (dry run)...")
    else:
        print("  Installing 5 starter rules...")

    force = getattr(args, 'force', False)
    installed = install_starter_rules(rules_dir, dry_run=dry_run, force=force)

    for name in installed:
        print(f"    ✅ {name}")

    print()

    # 7. Claude-specific: concatenate rules into CLAUDE.md
    if platform == "claude" and installed and not dry_run:
        _install_claude_md(rules_dir, force=force)

    if dry_run:
        print("  Dry run complete. No files were created.")
        print(f"  Target: {rules_dir}")
    elif not installed:
        print("  ❌ No rules were installed. Check that Soma source files exist.")
        return 1
    else:
        print("  Done! Your next agent session will be governed.")
        print(f"  Rules installed to: {rules_dir}")

    print()
    print("  After a session, run: soma report")
    print()

    return 0


# ── Claude helpers ──────────────────────────────────────────────────────────

SOMA_MARKER_START = "<!-- SOMA:START -->"
SOMA_MARKER_END = "<!-- SOMA:END -->"


def _install_claude_md(rules_dir: Path, force: bool = False) -> None:
    """Concatenate installed rules into CLAUDE.md for Claude Code.

    Claude Code reads CLAUDE.md, not individual .md files. We concatenate
    all installed rules between SOMA markers so we can update them later.
    """
    claude_md = rules_dir / "CLAUDE.md"  # ~/.claude/CLAUDE.md

    # Build the soma governance section
    sections = []
    for rule_file in sorted(rules_dir.glob("*.md")):
        if rule_file.is_file() and rule_file.name != "CLAUDE.md":
            content = rule_file.read_text(encoding="utf-8").strip()
            sections.append(f"## {rule_file.stem}\n\n{content}")

    if not sections:
        return

    soma_block = (
        f"{SOMA_MARKER_START}\n"
        f"# Soma Governance Rules\n\n"
        + "\n\n---\n\n".join(sections)
        + f"\n{SOMA_MARKER_END}\n"
    )

    if claude_md.exists():
        existing = claude_md.read_text(encoding="utf-8")
        has_start = SOMA_MARKER_START in existing
        has_end = SOMA_MARKER_END in existing

        if has_start and has_end:
            start_idx = existing.index(SOMA_MARKER_START)
            end_idx = existing.index(SOMA_MARKER_END) + len(SOMA_MARKER_END)
            # Guard against inverted markers
            if start_idx >= end_idx:
                print("  ⚠️  CLAUDE.md has corrupted SOMA markers, skipping")
                return
            if not force:
                print("  ℹ️  CLAUDE.md already has Soma rules (use --force to update)")
                return
            # Replace existing section
            updated = existing[:start_idx] + soma_block + existing[end_idx:]
            claude_md.write_text(updated, encoding="utf-8")
        elif has_start or has_end:
            # Partial markers — refuse without --force to avoid corruption
            if not force:
                print("  ⚠️  CLAUDE.md has partial SOMA markers (use --force to replace)")
                return
            # Force: remove the orphan marker line and append fresh block
            lines = existing.splitlines(True)
            lines = [l for l in lines if SOMA_MARKER_START not in l and SOMA_MARKER_END not in l]
            claude_md.write_text("".join(lines).rstrip() + "\n\n" + soma_block, encoding="utf-8")
        else:
            # No markers — append
            claude_md.write_text(existing.rstrip() + "\n\n" + soma_block, encoding="utf-8")
    else:
        claude_md.write_text(soma_block, encoding="utf-8")

    print(f"  📝 Updated {claude_md}")
