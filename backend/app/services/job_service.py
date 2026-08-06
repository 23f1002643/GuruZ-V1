"""In-memory job store with SSE event broadcasting."""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from app.schemas.job import Job, create_job
from app.utils.logger import get_logger, log_to_buffer

logger = get_logger(__name__)

# In-memory job store: job_id -> Job
_jobs: dict[str, Job] = {}

# SSE subscribers: job_id -> list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue]] = {}


# ──────────────────────── Job CRUD ────────────────────────

def create_new_job(filename: str, file_size: Optional[int] = None,
                   file_type: Optional[str] = None) -> Job:
    job = create_job(filename, file_size, file_type)
    _jobs[job.job_id] = job
    log_to_buffer("info", f"Job created: {job.job_id}", job_id=job.job_id)
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def list_jobs(status: Optional[str] = None, limit: int = 50) -> list[Job]:
    jobs = list(_jobs.values())
    if status:
        jobs = [j for j in jobs if j.status == status]
    # Sort by created_at descending
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]


def update_job_status(job_id: str, status: str, error: Optional[str] = None) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    job.status = status  # type: ignore[assignment]
    if error:
        job.error = error
    if status in ("completed", "failed", "cancelled"):
        job.completed_at = datetime.now(timezone.utc).isoformat()
        if job.status == "completed":
            job.overall_progress = 100
        start = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
        end = datetime.now(timezone.utc)
        job.processing_time_seconds = (end - start).total_seconds()
    job.touch()
    log_to_buffer(
        "info" if status == "completed" else "error" if status == "failed" else "info",
        f"Job {job_id} status → {status}",
        job_id=job_id,
    )
    _broadcast(job_id, {"type": "status", "status": status, "error": error})


def update_job_stage(job_id: str, stage: str, progress: int,
                     message: str = "") -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    job.update_stage(stage, progress, message)
    log_to_buffer("info", f"[{stage}] {progress}% - {message}", job_id=job_id, stage=stage)
    _broadcast(job_id, {
        "type": "progress",
        "stage": stage,
        "progress": progress,
        "overall_progress": job.overall_progress,
        "message": message,
    })


def set_job_package(job_id: str, package_id: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.package_id = package_id
        job.touch()


def update_job_language(job_id: str, language: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.language = language
        job.touch()
        log_to_buffer("info", f"Job {job_id} language set to {language}", job_id=job_id)




def cancel_job(job_id: str) -> Optional[Job]:
    job = _jobs.get(job_id)
    if not job:
        return None
    if job.status in ("completed", "failed", "cancelled"):
        return job
    update_job_status(job_id, "cancelled")
    return job


# ──────────────────────── SSE ────────────────────────

def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    subscribers = _subscribers.get(job_id, [])
    if q in subscribers:
        subscribers.remove(q)


def _broadcast(job_id: str, event: dict) -> None:
    for q in _subscribers.get(job_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
