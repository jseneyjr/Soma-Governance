"""soma doctor — System health check."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def _check_python_version() -> bool:
    """Check Python >= 3.9."""
    ok = sys.version_info >= (3, 9)
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if ok:
        print(f"  ✅ Python {ver} (≥ 3.9)")
    else:
        print(f"  ❌ Python {ver} (requires ≥ 3.9)")
    return ok


def _check_pyyaml() -> bool:
    """Check that pyyaml is importable."""
    try:
        import yaml  # noqa: F401
        print("  ✅ pyyaml installed")
        return True
    except ImportError:
        print("  ❌ pyyaml not installed")
        return False


def _check_platform() -> str | None:
    """Detect AI platform; return platform name or None on failure."""
    from soma_cli.init import detect_platform

    platform = detect_platform(Path.cwd())
    # Fallback: check home directory for global AI configs
    if platform == "unknown":
        platform = detect_platform(Path.home())
    if platform != "unknown":
        print(f"  ✅ Platform detected: {platform}")
        return platform
    print("  ❌ No AI platform detected")
    return None


def _check_rules(platform: str | None) -> bool:
    """Check that rules directory has ≥1 .md file."""
    if platform is None:
        print("  ❌ Rules check skipped (no platform)")
        return False
    from soma_cli.init import get_rules_dir

    rules_dir = get_rules_dir(platform)
    md_files = [
        p for p in rules_dir.glob("*.md")
        if p.name.lower() not in ("readme.md", "claude.md")
    ] if rules_dir.is_dir() else []
    if md_files:
        print(f"  ✅ Rules installed ({len(md_files)} .md files in {rules_dir})")
        return True
    print(f"  ❌ No .md rules found in {rules_dir}")
    return False


def _check_evidence_dir() -> bool:
    """Check .soma/evidence/ exists and is writable (read-only check)."""
    evidence = Path.cwd() / ".soma" / "evidence"
    if evidence.is_dir():
        if os.access(str(evidence), os.W_OK):
            print(f"  ✅ Evidence directory writable ({evidence})")
            return True
        print(f"  ❌ Evidence directory not writable ({evidence})")
        return False
    # Directory doesn't exist — check if parent is writable
    parent = evidence.parent
    if parent.is_dir() and os.access(str(parent), os.W_OK):
        print(f"  ✅ Evidence directory can be created ({evidence})")
        return True
    print(f"  ❌ Evidence directory does not exist ({evidence})")
    return False


def _check_cli_resolvable() -> bool:
    """Check that 'soma' CLI is on PATH."""
    path = shutil.which("soma")
    if path:
        print(f"  ✅ soma CLI resolvable ({path})")
        return True
    print("  ❌ soma CLI not found on PATH")
    from soma_cli.pathcheck import build_hint
    hint = build_hint()
    if hint:
        print("\n".join("    " + line for line in hint.splitlines()))
    return False


def run_doctor(args: argparse.Namespace) -> int:
    """Run all health checks. Returns 0 if all pass, 1 otherwise."""
    print("soma doctor — running health checks:\n")
    results: list[bool] = []

    results.append(_check_python_version())
    results.append(_check_pyyaml())
    platform = _check_platform()
    results.append(platform is not None)
    results.append(_check_rules(platform))
    results.append(_check_evidence_dir())
    results.append(_check_cli_resolvable())

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed.")
    return 0 if all(results) else 1
