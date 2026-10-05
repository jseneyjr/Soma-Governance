"""Asynchronous verification job manager for Soma MCP and Core.

Provides thread-safe job tracking, background execution, and status polling
for slow verification pipelines (Layer 1 + Layer 2 mutation and arbiter checks).
"""
from __future__ import annotations

import datetime
import os
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional


JOB_STATUS_QUEUED = "QUEUED"
JOB_STATUS_RUNNING = "RUNNING"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_FAILED = "FAILED"
JOB_STATUS_CANCELLED = "CANCELLED"


@dataclass
class VerificationJob:
    """Record representing a verification job."""
    job_id: str
    status: str
    created_at: str
    workspace: str
    files: list[str] = field(default_factory=list)
    layer1_only: bool = True
    task_plan: str = ""
    receipt: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_JOBS: dict[str, VerificationJob] = {}
_JOBS_LOCK = threading.Lock()
JOB_TTL_SECONDS = 3600  # 1 hour TTL


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_job(
    workspace: str,
    files: list[str],
    layer1_only: bool = True,
    task_plan: str = "",
    receipt: Optional[str] = None,
) -> VerificationJob:
    """Create and register a new verification job in QUEUED status."""
    clean_expired_jobs()
    job_id = f"vjob_{uuid.uuid4().hex[:12]}"
    now = _utc_now_iso()
    job = VerificationJob(
        job_id=job_id,
        status=JOB_STATUS_QUEUED,
        created_at=now,
        workspace=workspace,
        files=list(files),
        layer1_only=layer1_only,
        task_plan=task_plan,
        receipt=receipt,
    )
    with _JOBS_LOCK:
        _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Optional[VerificationJob]:
    """Retrieve a job by its ID, or None if not found or expired."""
    clean_expired_jobs()
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def list_jobs(active_only: bool = False) -> list[VerificationJob]:
    """List jobs, optionally filtering for only active (QUEUED/RUNNING) jobs."""
    clean_expired_jobs()
    with _JOBS_LOCK:
        jobs = list(_JOBS.values())
    if active_only:
        return [j for j in jobs if j.status in (JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)]
    return jobs


def clean_expired_jobs(max_age_seconds: int = JOB_TTL_SECONDS) -> int:
    """Remove completed or failed jobs older than max_age_seconds."""
    now = datetime.datetime.now(datetime.timezone.utc)
    removed = 0
    with _JOBS_LOCK:
        to_del = []
        for jid, job in _JOBS.items():
            if job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED):
                timestamp_str = job.completed_at or job.created_at
                try:
                    ts = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=datetime.timezone.utc
                    )
                    if (now - ts).total_seconds() > max_age_seconds:
                        to_del.append(jid)
                except ValueError:
                    pass
        for jid in to_del:
            del _JOBS[jid]
            removed += 1
    return removed


def clear_all_jobs() -> None:
    """Clear all jobs from memory (useful for test resets)."""
    with _JOBS_LOCK:
        _JOBS.clear()


def _run_verification_pipeline(job: VerificationJob, llm_backend: Optional[Callable[[str], str]] = None) -> None:
    """Worker logic executing Layer 1 (and optionally Layer 2) verification."""
    with _JOBS_LOCK:
        job.status = JOB_STATUS_RUNNING
        job.started_at = _utc_now_iso()

    try:
        from immune_system.verification import runner
    except ImportError as exc:
        with _JOBS_LOCK:
            job.status = JOB_STATUS_FAILED
            job.error = f"immune_system.verification import error: {exc}"
            job.completed_at = _utc_now_iso()
        return

    try:
        # Run Layer 1 checks
        layer1_results = runner.run_layer1(
            changed_files=job.files,
            repo_root=job.workspace,
        )
        l1_verdict = runner.gate_verdict(layer1_results)
        l1_summary = runner.format_summary(layer1_results)
        l1_evidence = [
            {"tool": r.tool, "target": r.target, "verdict": r.verdict, "detail": r.detail}
            for r in layer1_results
        ]

        result_payload: dict[str, Any] = {
            "status": "PASS" if l1_verdict else "FAIL",
            "summary": l1_summary,
            "layer1_only": job.layer1_only,
            "evidence": l1_evidence,
        }

        # Run Layer 2 if requested and backend is available
        if not job.layer1_only and llm_backend is not None and job.task_plan:
            try:
                l2_res = runner.run_layer2(
                    changed_files=job.files,
                    repo_root=job.workspace,
                    task_plan=job.task_plan,
                    layer1_evidence=layer1_results,
                    llm_backend=llm_backend,
                )
                result_payload["layer2"] = {
                    "verdict": l2_res.verdict.name,
                    "divergences": [d.to_dict() if hasattr(d, "to_dict") else str(d) for d in l2_res.divergences],
                    "convergences": [c.to_dict() if hasattr(c, "to_dict") else str(c) for c in l2_res.convergences],
                }
                if l2_res.verdict.name != "SHIP":
                    result_payload["status"] = "FAIL"
            except Exception as exc:
                result_payload["layer2_error"] = str(exc)

        with _JOBS_LOCK:
            job.status = JOB_STATUS_COMPLETED
            job.result = result_payload
            job.completed_at = _utc_now_iso()

    except Exception as exc:
        with _JOBS_LOCK:
            job.status = JOB_STATUS_FAILED
            job.error = str(exc)
            job.completed_at = _utc_now_iso()


def submit_verification_job(
    workspace: str,
    files: list[str],
    layer1_only: bool = True,
    task_plan: str = "",
    receipt: Optional[str] = None,
    llm_backend: Optional[Callable[[str], str]] = None,
) -> VerificationJob:
    """Enqueues and spawns a background thread to execute verification."""
    job = create_job(
        workspace=workspace,
        files=files,
        layer1_only=layer1_only,
        task_plan=task_plan,
        receipt=receipt,
    )
    thread = threading.Thread(
        target=_run_verification_pipeline,
        args=(job, llm_backend),
        daemon=True,
        name=f"verification-worker-{job.job_id}",
    )
    thread.start()
    return job
