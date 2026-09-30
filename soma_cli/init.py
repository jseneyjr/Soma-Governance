"""soma init — Set up governance for this project.

Detects platform and project type, installs starter rules,
and wires up the post-session hook.
"""
import argparse
import os
import shutil
from pathlib import Path


# ── Starter Pack ────────────────────────────────────────────────────────────
# The 5 rules that deliver immediate value on any project, any language.
# Keys are the rule stems, values are the source paths relative to repo root.

STARTER_RULES = {
    "providence": "genome/providence.md",
    "destructive-ops": "genome/destructive-ops.md",
    "testing": "genome/.oracles/testing.md",
    "cost-optimization": "genome/cost-optimization.md",
    "git-workflow": "genome/.oracles/git-workflow.md",
}


def _repo_root() -> Path:
    """Resolve the Soma repo root (where genome/ lives)."""
    return Path(__file__).resolve().parent.parent


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
    if (project_root / ".github" / "copilot").is_dir():
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

def get_rules_dir(platform: str, home: Path | None = None) -> Path:
    """Return the target rules directory for the given platform.

    Args:
        platform: One of 'gemini', 'claude', 'cursor', 'copilot'.
        home: Home directory override (for testing).

    Returns:
        Path to the platform's rules directory.

    Raises:
        ValueError: If platform is unsupported.
    """
    if home is None:
        home = Path.home()
    home = Path(home)

    dirs = {
        "gemini": home / ".gemini" / "config" / "rules",
        "claude": home / ".claude",
        "cursor": home / ".cursor" / "rules",
        "copilot": home / ".github" / "copilot",
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
) -> list[str]:
    """Install the 5 starter rules to the target directory.

    Args:
        rules_dir: Target directory for rules.
        dry_run: If True, don't create files.

    Returns:
        List of installed rule names.
    """
    repo = _repo_root()
    installed = []

    for name, source_rel in STARTER_RULES.items():
        source = repo / source_rel
        if not source.exists():
            print(f"  ⚠️  {name}: source not found at {source}")
            continue

        if not dry_run:
            rules_dir.mkdir(parents=True, exist_ok=True)
            dest = rules_dir / f"{name}.md"
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
        rules_dir = get_rules_dir(platform, home=home)
    except ValueError as e:
        print(f"  ❌ {e}")
        return 1

    # 5. Install starter rules
    if dry_run:
        print("  Installing 5 starter rules (dry run)...")
    else:
        print("  Installing 5 starter rules...")

    installed = install_starter_rules(rules_dir, dry_run=dry_run)

    for name in installed:
        print(f"    ✅ {name}")

    print()

    if dry_run:
        print("  Dry run complete. No files were created.")
        print(f"  Target: {rules_dir}")
    else:
        print("  Done! Your next agent session will be governed.")
        print(f"  Rules installed to: {rules_dir}")

    print()
    print("  After a session, run: soma report")
    print()

    return 0
