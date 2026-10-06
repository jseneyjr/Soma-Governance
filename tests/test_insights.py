"""Unit tests for soma_core.insights."""
import os
import json
import pytest

from soma_core.insights import (
    capture_insight,
    cluster_insights,
    generate_cell_candidates,
)


def test_capture_and_cluster_insights(tmp_path):
    ws = str(tmp_path)
    os.makedirs(os.path.join(ws, ".soma", "cells"), exist_ok=True)

    rec = capture_insight(
        workspace=ws,
        insight="Async timeout in event loop",
        context_files=["core/loop.py"],
        category="concurrency",
    )
    assert rec["insight"] == "Async timeout in event loop"
    assert rec["category"] == "concurrency"

    # Add 2 more to form a cluster
    capture_insight(workspace=ws, insight="Lock contention in threadpool", context_files=["core/loop.py"], category="concurrency")
    capture_insight(workspace=ws, insight="Deadlock on shutdown", context_files=["core/loop.py"], category="concurrency")

    clusters = cluster_insights(ws, min_cluster_size=3)
    assert len(clusters) == 1
    assert clusters[0]["common_category"] == "concurrency"

    candidates = generate_cell_candidates(clusters, ws)
    assert len(candidates) == 1
    assert "concurrency" in candidates[0]["hypothesis"]


def test_load_signal_weight_without_frontmatter(tmp_path):
    from soma_core.insights import _load_signal_weight

    ws = str(tmp_path)
    soma_dir = os.path.join(ws, ".soma")
    os.makedirs(soma_dir, exist_ok=True)
    with open(os.path.join(soma_dir, "config.yaml"), "w", encoding="utf-8") as f:
        f.write("insight_signal_weight: 0.85\n")
    assert _load_signal_weight(ws) == 0.85


def test_load_signal_weight_with_bom(tmp_path):
    from soma_core.insights import _load_signal_weight

    ws = str(tmp_path)
    soma_dir = os.path.join(ws, ".soma")
    os.makedirs(soma_dir, exist_ok=True)
    with open(os.path.join(soma_dir, "config.yaml"), "w", encoding="utf-8") as f:
        f.write("\ufeffinsight_signal_weight: 0.95\n")
    assert _load_signal_weight(ws) == 0.95
