"""Abstract base class and models for platform installation adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
from typing import Any, Optional


@dataclass
class PlatformInstallResult:
    """Result of a platform installation or uninstallation operation."""
    platform: str
    success: bool
    scope: str = "global"  # "global" or "local"
    installed_files: list[Path] = field(default_factory=list)
    uninstalled_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


class PlatformAdapter(ABC):
    """Abstract platform adapter providing pure-Python installation and verification."""

    name: str = "base"

    def __init__(
        self,
        workspace: Path | str | None = None,
        home: Path | str | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.home = Path(home).resolve() if home else Path.home().resolve()

    def get_source_rules(self) -> list[Path]:
        """Locate genome rules in repository workspace."""
        genome_dir = self.workspace / "genome"
        if not genome_dir.is_dir():
            return []
        rules = [p for p in genome_dir.glob("*.md") if p.name not in {"META.md", "README.md"}]
        oracles_dir = genome_dir / ".oracles"
        if oracles_dir.is_dir():
            rules.extend([p for p in oracles_dir.glob("*.md") if p.name not in {"META.md", "README.md"}])
        return sorted(rules)

    def get_source_skills(self) -> list[Path]:
        """Locate organs/skills in repository workspace."""
        organs_dir = self.workspace / "organs"
        if not organs_dir.is_dir():
            return []
        skills = []
        for d in organs_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").is_file():
                skills.append(d)
        return sorted(skills)

    @abstractmethod
    def install(self, local: bool = False, dry_run: bool = False) -> PlatformInstallResult:
        """Install rules, skills, and configuration for this platform."""
        raise NotImplementedError

    @abstractmethod
    def uninstall(self, local: bool = False, dry_run: bool = False) -> PlatformInstallResult:
        """Uninstall rules, skills, and configuration for this platform."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, local: bool = False) -> bool:
        """Verify that platform rules and configuration are correctly installed."""
        raise NotImplementedError

    @abstractmethod
    def render_config(self) -> dict[str, Any] | str:
        """Render the platform-specific configuration."""
        raise NotImplementedError
