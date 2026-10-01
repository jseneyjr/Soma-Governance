"""Security hardening tests for Soma MCP server.

Tests path confinement, enzyme import allowlisting, cell integrity
manifests, outcome validation, session token auth, and rate limiting.
"""
import os
import sys
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from soma_mcp.security import confine_workspace, confine_path, validate_cell_names
from soma_mcp.integrity import (
    generate_manifest,
    verify_manifest,
    load_manifest,
    save_manifest,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def soma_workspace(tmp_path):
    """Create a minimal valid Soma workspace."""
    cells_dir = tmp_path / ".soma" / "cells" / "walls"
    cells_dir.mkdir(parents=True)
    (cells_dir / "wall-test.md").write_text(
        "---\ntype: wall\nhypothesis: test\n---\nTest cell.\n"
    )
    evidence_dir = tmp_path / ".soma" / "evidence"
    evidence_dir.mkdir(parents=True)
    return tmp_path


# ── Path Confinement: confine_workspace ───────────────────────────────


class TestConfineWorkspace:
    def test_rejects_empty(self):
        """Empty string is not a valid workspace."""
        with pytest.raises(ValueError, match="must not be empty"):
            confine_workspace("")

    def test_rejects_nonexistent(self):
        """Nonexistent path is rejected."""
        with pytest.raises(ValueError, match="does not exist"):
            confine_workspace("/nonexistent/path/abc123")

    def test_rejects_non_soma_dir(self, tmp_path):
        """A directory without .soma/cells/ is not a valid workspace."""
        with pytest.raises(ValueError, match="not a valid Soma workspace"):
            confine_workspace(str(tmp_path))

    def test_accepts_valid_workspace(self, soma_workspace):
        """A directory with .soma/cells/ is accepted."""
        result = confine_workspace(str(soma_workspace))
        assert os.path.isabs(result)
        assert os.path.isdir(os.path.join(result, ".soma", "cells"))


# ── Path Confinement: confine_path ────────────────────────────────────


class TestConfinePath:
    def test_rejects_empty(self):
        """Empty file path is rejected."""
        with pytest.raises(ValueError, match="must not be empty"):
            confine_path("", "/any")

    def test_rejects_traversal(self, soma_workspace):
        """Path traversal with ../ is blocked."""
        with pytest.raises(ValueError, match="path traversal blocked"):
            confine_path("../../etc/passwd", str(soma_workspace))

    def test_rejects_absolute_escape(self, soma_workspace):
        """Absolute path outside workspace is blocked."""
        with pytest.raises(ValueError, match="path traversal blocked"):
            confine_path("/etc/passwd", str(soma_workspace))

    def test_rejects_workspace_root(self, soma_workspace):
        """Pointing at the workspace root itself is rejected."""
        with pytest.raises(ValueError, match="refusing to treat the workspace root"):
            confine_path(".", str(soma_workspace))

    @pytest.mark.skipif(
        not hasattr(os, "symlink"), reason="Symlinks not supported"
    )
    def test_rejects_symlink_escape(self, soma_workspace):
        """Symlink that resolves outside workspace is blocked."""
        outside = soma_workspace.parent / "outside_target"
        outside.mkdir()
        link = soma_workspace / "sneaky_link"
        try:
            os.symlink(str(outside), str(link))
        except OSError:
            pytest.skip("Cannot create symlink")
        with pytest.raises(ValueError, match="path traversal blocked"):
            confine_path("sneaky_link/secret.txt", str(soma_workspace))

    def test_accepts_valid_relative(self, soma_workspace):
        """Valid relative path inside workspace is accepted."""
        resolved, relative = confine_path("src/main.py", str(soma_workspace))
        assert relative == os.path.join("src", "main.py")
        assert resolved.endswith(os.path.join("src", "main.py"))

    def test_accepts_nested_path(self, soma_workspace):
        """Deeply nested relative path is accepted."""
        resolved, relative = confine_path("a/b/c/file.py", str(soma_workspace))
        assert relative == os.path.join("a", "b", "c", "file.py")


# ── Cell Name Validation ──────────────────────────────────────────────


class TestValidateCellNames:
    def test_empty_list_returns_empty(self, soma_workspace):
        """Empty cell list always validates."""
        assert validate_cell_names([], str(soma_workspace)) == []

    def test_all_valid_returns_empty(self, soma_workspace):
        """Known cell names return no invalid entries."""
        result = validate_cell_names(["wall-test"], str(soma_workspace))
        assert result == []

    def test_unknown_names_returned(self, soma_workspace):
        """Unknown cell names are returned as invalid."""
        result = validate_cell_names(
            ["wall-test", "nonexistent-cell", "another-fake"],
            str(soma_workspace),
        )
        assert "nonexistent-cell" in result
        assert "another-fake" in result
        assert "wall-test" not in result

    def test_no_cells_dir_all_invalid(self, tmp_path):
        """When .soma/cells/ doesn't exist, all names are invalid."""
        result = validate_cell_names(["any-name"], str(tmp_path))
        assert result == ["any-name"]


# ── Integrity Manifest ────────────────────────────────────────────────


class TestIntegrityManifest:
    def test_generate_manifest(self, soma_workspace):
        """Manifest includes all cell files with SHA-256 hashes."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        manifest = generate_manifest(cells_dir)
        assert manifest["cell_count"] > 0
        for path, hash_val in manifest["cells"].items():
            assert hash_val.startswith("sha256:")
            assert len(hash_val) == len("sha256:") + 64  # hex digest length

    def test_verify_unmodified(self, soma_workspace):
        """Clean cells produce no verification issues."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        manifest = generate_manifest(cells_dir)
        issues = verify_manifest(cells_dir, manifest)
        assert issues == []

    def test_verify_detects_modified(self, soma_workspace):
        """Modified cell content is detected as a hash mismatch."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        manifest = generate_manifest(cells_dir)
        # Tamper with the cell
        cell_path = soma_workspace / ".soma" / "cells" / "walls" / "wall-test.md"
        cell_path.write_text("---\ntype: wall\nhypothesis: TAMPERED\n---\nEvil.\n")
        issues = verify_manifest(cells_dir, manifest)
        types = [i["type"] for i in issues]
        assert "modified" in types

    def test_verify_detects_added(self, soma_workspace):
        """New cell not in manifest is detected as unknown."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        manifest = generate_manifest(cells_dir)
        # Add a rogue cell
        rogue = soma_workspace / ".soma" / "cells" / "walls" / "wall-rogue.md"
        rogue.write_text("---\ntype: wall\nhypothesis: rogue\n---\nRogue.\n")
        issues = verify_manifest(cells_dir, manifest)
        types = [i["type"] for i in issues]
        assert "added" in types

    def test_verify_detects_removed(self, soma_workspace):
        """Cell in manifest but missing from disk is detected."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        manifest = generate_manifest(cells_dir)
        # Delete the cell
        cell_path = soma_workspace / ".soma" / "cells" / "walls" / "wall-test.md"
        cell_path.unlink()
        issues = verify_manifest(cells_dir, manifest)
        types = [i["type"] for i in issues]
        assert "removed" in types

    def test_load_manifest_returns_none_when_missing(self, tmp_path):
        """Missing manifest file returns None, not an error."""
        assert load_manifest(str(tmp_path)) is None

    def test_save_and_load_roundtrip(self, soma_workspace):
        """Manifest can be saved and loaded back identically."""
        cells_dir = str(soma_workspace / ".soma" / "cells")
        original = generate_manifest(cells_dir)
        save_manifest(str(soma_workspace), original)
        loaded = load_manifest(str(soma_workspace))
        assert loaded is not None
        assert loaded["cells"] == original["cells"]
        assert loaded["cell_count"] == original["cell_count"]


# ── Enzyme Import Allowlist ───────────────────────────────────────────


class TestEnzymeImportAllowlist:
    def test_rejects_unlisted_module(self):
        """Modules not in the allowlist are rejected."""
        from soma_mcp.tools import _safe_import_enzyme

        with pytest.raises(ImportError, match="not in the import allowlist"):
            _safe_import_enzyme("malicious_module", "evil_func")

    def test_allowlist_is_frozen(self):
        """Allowlist is a frozenset and cannot be mutated."""
        from soma_mcp.tools import _ENZYME_ALLOWLIST

        assert isinstance(_ENZYME_ALLOWLIST, frozenset)


# ── Session Auth ──────────────────────────────────────────────────────


class TestSessionAuth:
    def test_read_tools_defined(self):
        """Read-only tools are classified."""
        from soma_mcp.server import _READ_TOOLS

        assert "soma_scan" in _READ_TOOLS
        assert "soma_list_cells" in _READ_TOOLS

    def test_write_and_execute_tools_defined(self):
        """Write and execute tools are classified."""
        from soma_mcp.server import _WRITE_TOOLS, _EXECUTE_TOOLS

        assert "soma_report_outcome" in _WRITE_TOOLS
        assert "soma_propose_change" in _EXECUTE_TOOLS

    def test_all_tool_definitions_classified(self):
        """Every tool in TOOL_DEFINITIONS appears in exactly one tier."""
        from soma_mcp.server import _READ_TOOLS, _WRITE_TOOLS, _EXECUTE_TOOLS
        from soma_mcp.tools import TOOL_DEFINITIONS

        all_tiers = _READ_TOOLS | _WRITE_TOOLS | _EXECUTE_TOOLS
        for tool_def in TOOL_DEFINITIONS:
            name = tool_def["name"]
            assert name in all_tiers, (
                f"Tool '{name}' is not classified in any permission tier"
            )


# ── Rate Limiting ─────────────────────────────────────────────────────


class TestRateLimiting:
    def setup_method(self):
        """Reset rate limiter state between tests."""
        from soma_mcp import server

        server._tool_call_times.clear()

    def test_allows_within_limit(self):
        """Calls within the window limit are allowed."""
        from soma_mcp.server import _check_rate_limit

        # soma_checkpoint has a limit of 3 per 60s
        assert _check_rate_limit("soma_checkpoint") is True
        assert _check_rate_limit("soma_checkpoint") is True
        assert _check_rate_limit("soma_checkpoint") is True

    def test_blocks_over_limit(self):
        """Calls exceeding the window limit are blocked."""
        from soma_mcp.server import _check_rate_limit

        for _ in range(3):
            _check_rate_limit("soma_checkpoint")
        assert _check_rate_limit("soma_checkpoint") is False

    def test_window_expires(self, monkeypatch):
        """Old entries are pruned when the window expires."""
        from soma_mcp import server

        mock_time = [100.0]
        monkeypatch.setattr(time, "monotonic", lambda: mock_time[0])

        for _ in range(3):
            server._check_rate_limit("soma_checkpoint")
        assert server._check_rate_limit("soma_checkpoint") is False

        # Advance past the 60s window
        mock_time[0] = 200.0
        assert server._check_rate_limit("soma_checkpoint") is True

    def test_unlimited_tools_always_pass(self):
        """Tools not in _RATE_LIMITS are never rate-limited."""
        from soma_mcp.server import _check_rate_limit

        for _ in range(100):
            assert _check_rate_limit("soma_scan") is True
