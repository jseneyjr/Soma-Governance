"""AST Driver Runner and Registry for polyglot NormalizedAST execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Dict, List, Mapping, Optional, Union

from soma_core.ast.drivers.python import parse_python_ast
from soma_core.ast.schema import NormalizedAST
from soma_core.errors import SomaError, SomaValidationError
from soma_core.workspace import Workspace, as_workspace


class ASTDriverError(SomaError):
    """Raised when an external AST driver execution fails."""


class ASTDriverTimeoutError(ASTDriverError):
    """Raised when an external AST driver exceeds its execution timeout."""


class NoDriverConfiguredError(ASTDriverError):
    """Raised when no AST driver is available for a requested file extension."""


class ASTDriverRegistry:
    """Registry mapping file extensions to driver commands."""

    def __init__(self, drivers: Optional[Mapping[str, str]] = None):
        self._drivers: Dict[str, str] = {}
        if drivers:
            for ext, cmd in drivers.items():
                self.register_driver(ext, cmd)

    def register_driver(self, extension: str, command: str) -> None:
        clean_ext = extension if extension.startswith(".") else f".{extension}"
        self._drivers[clean_ext.lower()] = str(command).strip()

    def get_registered_driver(self, extension: str) -> Optional[str]:
        clean_ext = extension if extension.startswith(".") else f".{extension}"
        return self._drivers.get(clean_ext.lower())

    def resolve_driver(
        self,
        extension: str,
        workspace_root: Optional[Union[Path, str, Workspace]] = None,
    ) -> Optional[str]:
        """Resolve driver command for extension from registry or .soma/slots.yaml."""
        clean_ext = extension if extension.startswith(".") else f".{extension}"
        clean_ext = clean_ext.lower()

        # 1. Registered drivers take precedence
        if clean_ext in self._drivers:
            return self._drivers[clean_ext]

        # 2. Check workspace slots.yaml if available
        if workspace_root:
            ws = as_workspace(workspace_root)
            from soma_core.skills.slots import SlotRegistry

            slot_reg = SlotRegistry.load(ws.root)
            driver_from_slot = slot_reg.get_ast_driver(clean_ext)
            if driver_from_slot:
                return driver_from_slot

        return None


class ASTDriverRunner:
    """Dispatches AST parsing to native Python or external driver subprocesses."""

    def __init__(self, registry: Optional[ASTDriverRegistry] = None):
        self.registry = registry or ASTDriverRegistry()

    def parse_file(
        self,
        file_path: Union[Path, str],
        workspace_root: Optional[Union[Path, str, Workspace]] = None,
        timeout: float = 3.0,
    ) -> NormalizedAST:
        """Parse source file into NormalizedAST, failing closed on driver defects."""
        ws_root = Path(as_workspace(workspace_root).root) if isinstance(workspace_root, Workspace) else Path(workspace_root or Path.cwd()).resolve()
        target_path = Path(file_path)
        if not target_path.is_absolute():
            target_path = (ws_root / target_path).resolve()
        else:
            target_path = target_path.resolve()

        if workspace_root:
            if isinstance(workspace_root, Workspace):
                workspace_root.confine_path(target_path)
            else:
                try:
                    target_path.relative_to(ws_root)
                except ValueError as exc:
                    from soma_core.errors import PathTraversalError
                    raise PathTraversalError(f"File {target_path} escapes workspace {ws_root}") from exc

        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")

        ext = target_path.suffix.lower()

        # Fast path: Native Python driver
        if ext == ".py":
            return parse_python_ast(target_path)

        # Resolve driver command
        driver_cmd = self.registry.resolve_driver(ext, workspace_root=ws_root)
        if not driver_cmd:
            raise NoDriverConfiguredError(
                f"No AST driver configured for extension '{ext}' on {target_path.name}"
            )

        cmd_parts = shlex.split(driver_cmd)
        if not cmd_parts:
            raise ASTDriverError(f"Empty driver command for extension '{ext}'")

        full_cmd = cmd_parts + [str(target_path)]

        try:
            proc = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(ws_root),
            )
        except subprocess.TimeoutExpired as exc:
            raise ASTDriverTimeoutError(
                f"AST driver '{driver_cmd}' timed out after {timeout}s on {target_path.name}"
            ) from exc
        except Exception as exc:
            raise ASTDriverError(
                f"Failed to execute AST driver '{driver_cmd}': {exc}"
            ) from exc

        if proc.returncode != 0:
            err_output = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
            raise ASTDriverError(
                f"AST driver '{driver_cmd}' failed with exit code {proc.returncode}: {err_output}"
            )

        try:
            return NormalizedAST.from_json(proc.stdout)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            raise ASTDriverError(
                f"AST driver '{driver_cmd}' returned invalid NormalizedAST JSON: {exc}\nOutput: {proc.stdout[:300]}"
            ) from exc
