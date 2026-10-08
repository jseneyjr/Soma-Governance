"""Unit tests for AST Driver Runner, confinement, and external driver invocation."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import sys

from soma_core.ast.runner import (
    ASTDriverError,
    ASTDriverRegistry,
    ASTDriverRunner,
    ASTDriverTimeoutError,
    NoDriverConfiguredError,
)
from soma_core.ast.schema import NormalizedAST
from soma_core.skills.slots import SlotRegistry


def test_native_python_fast_path(tmp_path):
    py_file = tmp_path / "hello.py"
    py_file.write_text("def greet(): return 'hi'", encoding="utf-8")

    runner = ASTDriverRunner()
    result = runner.parse_file(py_file, workspace_root=tmp_path)
    assert isinstance(result, NormalizedAST)
    assert result.language == "python"
    assert len(result.definitions) == 1
    assert result.definitions[0].name == "greet"


def test_external_driver_subprocess_invocation(tmp_path):
    # Create a mock driver script that outputs valid NormalizedAST JSON
    driver_script = tmp_path / "mock_driver.py"
    driver_code = """
import sys, json

target = sys.argv[1]
result = {
    "version": "1.0",
    "language": "typescript",
    "file_path": target,
    "definitions": [{"name": "mockFunc", "kind": "function", "line": 5, "is_exported": True}],
    "call_sites": [],
    "imports": [],
    "mutation_points": []
}
print(json.dumps(result))
"""
    driver_script.write_text(driver_code, encoding="utf-8")

    target_ts = tmp_path / "app.ts"
    target_ts.write_text("export function mockFunc() {}", encoding="utf-8")

    registry = ASTDriverRegistry()
    registry.register_driver(".ts", f"{sys.executable} {driver_script}")

    runner = ASTDriverRunner(registry=registry)
    result = runner.parse_file(target_ts, workspace_root=tmp_path)

    assert isinstance(result, NormalizedAST)
    assert result.language == "typescript"
    assert result.definitions[0].name == "mockFunc"


def test_external_driver_timeout(tmp_path):
    driver_script = tmp_path / "sleep_driver.py"
    driver_script.write_text("import time; time.sleep(5)", encoding="utf-8")

    target_ts = tmp_path / "slow.ts"
    target_ts.write_text("// slow", encoding="utf-8")

    registry = ASTDriverRegistry()
    registry.register_driver(".ts", f"{sys.executable} {driver_script}")

    runner = ASTDriverRunner(registry=registry)
    with pytest.raises(ASTDriverTimeoutError, match="timed out"):
        runner.parse_file(target_ts, workspace_root=tmp_path, timeout=0.2)


def test_external_driver_crash_fails_closed(tmp_path):
    driver_script = tmp_path / "failing_driver.py"
    driver_script.write_text("import sys; sys.stderr.write('Fatal crash'); sys.exit(2)", encoding="utf-8")

    target_ts = tmp_path / "fail.ts"
    target_ts.write_text("// fail", encoding="utf-8")

    registry = ASTDriverRegistry()
    registry.register_driver(".ts", f"{sys.executable} {driver_script}")

    runner = ASTDriverRunner(registry=registry)
    with pytest.raises(ASTDriverError, match="failed with exit code 2"):
        runner.parse_file(target_ts, workspace_root=tmp_path)


def test_no_driver_configured_raises_expected_error(tmp_path):
    target_rs = tmp_path / "main.rs"
    target_rs.write_text("fn main() {}", encoding="utf-8")

    runner = ASTDriverRunner()
    with pytest.raises(NoDriverConfiguredError, match="No AST driver configured for extension '.rs'"):
        runner.parse_file(target_rs, workspace_root=tmp_path)


def test_slot_registry_driver_resolution(tmp_path):
    slots_file = tmp_path / ".soma" / "slots.yaml"
    slots_file.parent.mkdir(parents=True)
    slots_file.write_text("""
slots:
  ast_driver_go: "go run ./ast_parser.go"
  ast_driver: "generic-driver"
""", encoding="utf-8")

    slot_reg = SlotRegistry.load(tmp_path)
    assert slot_reg.get_ast_driver(".go") == "go run ./ast_parser.go"
    assert slot_reg.get_ast_driver(".rs") == "generic-driver"
    assert slot_reg.get_ast_driver(".py") is None  # Python is native


def test_split_command_windows(monkeypatch):
    from soma_core.ast.runner import _split_command
    with monkeypatch.context() as m:
        m.setattr("soma_core.ast.runner.os.name", "nt")
        cmd = r'"C:\Program Files\nodejs\node.exe" "D:\my project\driver.js"'
        parts = _split_command(cmd)
        assert parts == [r"C:\Program Files\nodejs\node.exe", r"D:\my project\driver.js"]

        cmd_unquoted = r"C:\Python312\python.exe D:\driver.py"
        parts2 = _split_command(cmd_unquoted)
        assert parts2 == [r"C:\Python312\python.exe", r"D:\driver.py"]
