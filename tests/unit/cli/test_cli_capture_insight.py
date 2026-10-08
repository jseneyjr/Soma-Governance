"""TDD tests for `soma capture-insight` CLI porcelain command."""
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import pytest

import argparse
from soma_cli.capture_insight import run_capture_insight, CaptureInsightCommand
from soma_cli.cli import _build_parser, main


class TestCaptureInsightCLI:
    def test_parser_registration(self):
        """Parser recognizes capture-insight and required flags."""
        cmd = CaptureInsightCommand()
        assert cmd.name == "capture-insight"
        parser = argparse.ArgumentParser()
        cmd.configure_parser(parser)

        args = parser.parse_args([
            "--insight", "Avoid raw socket allocations",
            "--context-files", "net/tcp.py", "net/udp.py",
            "--category", "networking",
            "--scaffold-wall",
            "--wall-id", "socket-safety",
            "--source-conversation", "conv-42",
        ])
        assert args.insight == "Avoid raw socket allocations"
        assert args.context_files == ["net/tcp.py", "net/udp.py"]
        assert args.category == "networking"
        assert args.scaffold_wall is True
        assert args.wall_id == "socket-safety"
        assert args.source_conversation == "conv-42"

        # Also test short flags (-i, -c)
        args_short = parser.parse_args([
            "-i", "Short insight",
            "-c", "net/tcp.py",
        ])
        assert args_short.insight == "Short insight"
        assert args_short.context_files == ["net/tcp.py"]

        # Also verify through full CLI parser
        cli_parser = _build_parser()
        cli_args = cli_parser.parse_args([
            "capture-insight",
            "--insight", "Avoid raw socket allocations",
            "--context-files", "net/tcp.py", "net/udp.py",
            "--category", "networking",
            "--scaffold-wall",
            "--wall-id", "socket-safety",
        ])
        assert cli_args.command == "capture-insight"

    def test_parser_requires_insight_and_context_files(self):
        """Missing --insight or --context-files causes parse failure."""
        cmd = CaptureInsightCommand()
        parser = argparse.ArgumentParser()
        cmd.configure_parser(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["--insight", "Something"])
        with pytest.raises(SystemExit):
            parser.parse_args(["--context-files", "foo.py"])

    def test_command_execute(self, tmp_path):
        """CaptureInsightCommand.execute delegates to run_capture_insight and executes successfully."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "core").mkdir(parents=True)
        (ws / "core" / "app.py").write_text("code", encoding="utf-8")

        cmd = CaptureInsightCommand()
        args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="Test command execute",
            context_files=["core/app.py"],
            source_conversation="conv-test",
            category="arch",
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            ret = cmd.execute(args)
        assert ret == 0
        assert "Captured insight for 1 files." in stdout.getvalue()

        # Check failure return code on invalid workspace/args
        bad_args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="",
            context_files=[],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            bad_ret = cmd.execute(bad_args)
        assert bad_ret == 1

    def test_run_capture_insight_basic(self, tmp_path):
        """Executing soma capture-insight appends to human_insights.jsonl."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "core").mkdir(parents=True)
        (ws / "core" / "app.py").write_text("code", encoding="utf-8")

        args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="Check connection timeout",
            context_files=["core/app.py"],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_insight(args)

        assert exit_code == 0
        assert "Captured insight" in stdout.getvalue()

        jsonl_path = ws / ".soma" / "human_insights.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["insight"] == "Check connection timeout"
        assert record["context_files"] == ["core/app.py"]
        assert "wall_file" not in record

        # Test with ws object possessing .root attribute
        class FakeWS:
            root = ws
        args_with_ws = argparse.Namespace(
            ws=FakeWS(),
            workspace=None,
            _project_root=None,
            insight="Check connection timeout 2",
            context_files=["core/app.py"],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stdout2 = io.StringIO()
        with redirect_stdout(stdout2):
            assert run_capture_insight(args_with_ws) == 0

        # Test fallback to _project_root when workspace is None
        args_fallback = argparse.Namespace(
            ws=None,
            workspace=None,
            _project_root=str(ws),
            insight="Check fallback",
            context_files=["core/app.py"],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stdout3 = io.StringIO()
        with redirect_stdout(stdout3):
            assert run_capture_insight(args_fallback) == 0

    def test_run_capture_insight_scaffold_wall(self, tmp_path):
        """Executing with --scaffold-wall and --wall-id creates wall markdown."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "auth").mkdir(parents=True)
        (ws / "auth" / "jwt.py").write_text("token", encoding="utf-8")

        args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="Enforce asymmetric signatures for JWT verification",
            context_files=["auth/jwt.py"],
            source_conversation=None,
            category="security",
            scaffold_wall=True,
            wall_id="jwt-asymmetric",
            json=False,
            format="text",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_insight(args)

        assert exit_code == 0
        assert "scaffolded" in stdout.getvalue()
        wall_file = ws / ".soma" / "cells" / "walls" / "wall-jwt-asymmetric.md"
        assert wall_file.exists()
        content = wall_file.read_text(encoding="utf-8")
        assert "id: wall-jwt-asymmetric" in content
        assert "type: wall" in content
        assert "Enforce asymmetric signatures" in content

    def test_run_capture_insight_json_output(self, tmp_path):
        """Executing with --json outputs valid 2-space indented JSON record."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "lib").mkdir(parents=True)
        (ws / "lib" / "math.py").write_text("def add(): pass", encoding="utf-8")

        args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="Float division precision loss",
            context_files=["lib/math.py"],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=True,
            format="text",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_insight(args)

        assert exit_code == 0
        raw = stdout.getvalue()
        assert raw.startswith("{\n  \""), f"Expected 2-space indent, got {raw[:20]}"
        output_json = json.loads(raw)
        assert output_json["insight"] == "Float division precision loss"
        assert output_json["context_files"] == ["lib/math.py"]

    def test_run_capture_insight_format_json(self, tmp_path):
        """Executing with --format json outputs valid 2-space indented JSON record."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "lib").mkdir(parents=True)
        (ws / "lib" / "math.py").write_text("def add(): pass", encoding="utf-8")

        args = argparse.Namespace(
            ws=None,
            workspace=str(ws),
            _project_root=str(ws),
            insight="Float division precision loss",
            context_files=["lib/math.py"],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="json",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_insight(args)

        assert exit_code == 0
        raw = stdout.getvalue()
        assert raw.startswith("{\n  \""), f"Expected 2-space indent, got {raw[:20]}"
        output_json = json.loads(raw)
        assert output_json["insight"] == "Float division precision loss"

    def test_run_capture_insight_omitted_flags_defaults(self, tmp_path):
        """When optional flags are omitted from namespace, defaults evaluate to False and plain text."""
        ws = tmp_path
        (ws / ".soma").mkdir(parents=True)
        (ws / "lib").mkdir(parents=True)
        (ws / "lib" / "math.py").write_text("def add(): pass", encoding="utf-8")

        # Omit json, format, and scaffold_wall from args namespace
        args = argparse.Namespace(
            workspace=str(ws),
            insight="Omitted flags test",
            context_files=["lib/math.py"],
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_insight(args)

        assert exit_code == 0
        out = stdout.getvalue()
        assert "Captured insight for 1 files." in out
        assert not out.startswith("{")
        assert "scaffolded" not in out
        # Confirm no wall cell was scaffolded
        walls_dir = ws / ".soma" / "cells" / "walls"
        assert not walls_dir.exists() or len(list(walls_dir.glob("*.md"))) == 0

        # Also test with format="text" and json=False explicitly
        args_text = argparse.Namespace(
            workspace=str(ws),
            insight="Plain text format",
            context_files=["lib/math.py"],
            json=False,
            format="text",
        )
        stdout_text = io.StringIO()
        with redirect_stdout(stdout_text):
            assert run_capture_insight(args_text) == 0
        assert "Captured insight for 1 files." in stdout_text.getvalue()
        assert not stdout_text.getvalue().startswith("{")

    def test_run_capture_insight_failure(self, tmp_path):
        """Failure inside capture_insight outputs error to stderr and returns 1."""
        args = argparse.Namespace(
            ws=None,
            workspace=str(tmp_path),
            _project_root=str(tmp_path),
            insight="",
            context_files=[],
            source_conversation=None,
            category=None,
            scaffold_wall=False,
            wall_id=None,
            json=False,
            format="text",
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = run_capture_insight(args)
        assert exit_code == 1
        assert "Error:" in stderr.getvalue()

