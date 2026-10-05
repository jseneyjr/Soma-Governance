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
