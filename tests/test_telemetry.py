"""Unit tests for soma_core.telemetry."""
import os
import tempfile
import pytest

from soma_core.telemetry import (
    append_signal,
    read_signals,
    current_generation,
    increment_generation,
    detect_test_runner,
    letter_grade,
    compute_credit_weights,
    evaluate_quorum,
)


def test_telemetry_append_and_read_signals(tmp_path):
    ws = str(tmp_path)
    rec = append_signal(ws, "cell-1", "tp", "ci", metadata={"test": True})
    assert rec["cell"] == "cell-1"
    assert rec["signal"] == "tp"

    signals = read_signals(ws)
    assert len(signals) == 1
    assert signals[0]["cell"] == "cell-1"


def test_telemetry_generation_increment(tmp_path):
    ws = str(tmp_path)
    assert current_generation(ws) == 1
    gen = increment_generation(ws)
    assert gen == 2
    assert current_generation(ws) == 2


def test_telemetry_letter_grade():
    assert letter_grade(98) == "A+"
    assert letter_grade(85) == "B"
    assert letter_grade(50) == "F"


def test_telemetry_credit_weights():
    cells = [
        {"id": "cell-a", "target_paths": ["src/*.py"]},
        {"id": "cell-b", "target_paths": ["tests/*.py"]},
    ]
    weights = compute_credit_weights(cells, ["src/app.py"])
    assert weights["cell-a"] == 1.0
    assert weights["cell-b"] == 0.0
