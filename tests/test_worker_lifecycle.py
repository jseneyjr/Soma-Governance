"""Tests for worker daemon lifecycle, shutdown, and persistence (soma_core.verification_jobs)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from soma_core.verification_jobs import (
    create_job,
    get_job,
    list_jobs,
    shutdown_verification_engine,
    persist_jobs_state,
    restore_jobs_state,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_FAILED,
)


class TestWorkerLifecycleAndPersistence:
    """Test suite for clean shutdown and job queue persistence."""

    def test_shutdown_marks_queued_jobs_failed_and_cleans_up(self, tmp_path: Path):
        """Shutting down marks queued/running jobs as server_shutdown."""
        job = create_job(workspace=str(tmp_path), files=["a.py"])
        assert job.status in (JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)

        shutdown_verification_engine(grace_period=1.0)

        updated = get_job(job.job_id)
        assert updated is not None
        assert updated.status == JOB_STATUS_FAILED
        assert "server_shutdown" in (updated.error or "")

    def test_persist_and_restore_jobs_state(self, tmp_path: Path):
        """State of completed and failed jobs can be saved and restored across restarts."""
        job = create_job(workspace=str(tmp_path), files=["b.py"])
        job.status = JOB_STATUS_FAILED
        job.error = "test error"

        saved_path = persist_jobs_state(str(tmp_path))
        assert Path(saved_path).exists()

        loaded_jobs = restore_jobs_state(str(tmp_path))
        assert any(j.job_id == job.job_id for j in loaded_jobs)

    def test_shutdown_during_running_pipeline_preserves_failed_status(self, tmp_path: Path, monkeypatch):
        """Worker thread completing pipeline cannot overwrite status if shutdown already occurred."""
        import threading
        from soma_core.verification_jobs import submit_verification_job
        from immune_system.verification import runner

        started_evt = threading.Event()
        proceed_evt = threading.Event()

        def synchronized_run_layer1(*args, **kwargs):
            started_evt.set()
            proceed_evt.wait(timeout=2.0)
            return []

        monkeypatch.setattr(runner, "run_layer1", synchronized_run_layer1)

        job = submit_verification_job(workspace=str(tmp_path), files=[], layer1_only=True)
        assert started_evt.wait(timeout=2.0)

        # Worker is now actively running the pipeline
        shutdown_verification_engine(grace_period=0.1)
        proceed_evt.set()

        # Wait for worker thread to complete
        for _ in range(50):
            time.sleep(0.05)
            j = get_job(job.job_id)
            if j and j.completed_at and j.status != JOB_STATUS_RUNNING:
                break

        updated = get_job(job.job_id)
        assert updated is not None
        assert updated.status == JOB_STATUS_FAILED
        assert "server_shutdown" in (updated.error or "")

