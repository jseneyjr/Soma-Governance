"""Tests for soma genesis polyglot language detection and driver provisioning."""
import argparse
from pathlib import Path
import pytest

from soma_cli.genesis import run_genesis
from soma_core.skills.slots import SlotRegistry
from soma_core.workspace import Workspace


def test_genesis_provisions_ast_drivers_on_rust_project(tmp_path: Path):
    # Setup Rust project with some code
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rust_app'\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.rs").write_text("fn main() { println!(\"hello\"); }\n", encoding="utf-8")
    (src / "lib.rs").write_text("pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")

    args = argparse.Namespace(
        ws=Workspace.resolve(tmp_path),
        workspace=str(tmp_path),
        min_confidence=0.1,
        dry_run=False,
        json=True,
        force=True,
        yes=True,
        install_hooks=False,
        no_hooks=True,
    )

    exit_code = run_genesis(args)
    assert exit_code == 0

    # Verify slots.yaml exists with ast_driver_rs
    slots_path = tmp_path / ".soma" / "slots.yaml"
    assert slots_path.is_file()

    registry = SlotRegistry.load(tmp_path)
    assert registry.get_ast_driver(".rs") is not None
    assert (tmp_path / ".soma" / "drivers" / "rust_ast.py").is_file()


def test_genesis_provisions_ast_drivers_on_polyglot_project(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "app"}', encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "index.ts").write_text("export function run() {}\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
    (tmp_path / "main.go").write_text("package main\nfunc main() {}\n", encoding="utf-8")

    args = argparse.Namespace(
        ws=Workspace.resolve(tmp_path),
        workspace=str(tmp_path),
        min_confidence=0.1,
        dry_run=False,
        json=True,
        force=True,
        yes=True,
        install_hooks=False,
        no_hooks=True,
    )

    exit_code = run_genesis(args)
    assert exit_code == 0

    registry = SlotRegistry.load(tmp_path)
    assert registry.get_ast_driver(".ts") is not None
    assert registry.get_ast_driver(".go") is not None
    assert (tmp_path / ".soma" / "drivers" / "ts_ast.js").is_file()
    assert (tmp_path / ".soma" / "drivers" / "go_ast.go").is_file()
