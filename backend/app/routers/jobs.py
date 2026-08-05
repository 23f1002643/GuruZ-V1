"""Job management and SSE streaming endpoints."""
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.job_service import (
    get_job, list_jobs, cancel_job, subscribe, unsubscribe
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs_endpoint(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    """List all processing jobs, optionally filtered by status."""
    jobs = list_jobs(status=status, limit=limit)
    return [j.model_dump() for j in jobs]


@router.get("/{job_id}")
async def get_job_endpoint(job_id: str):
    """Get detailed information about a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.delete("/{job_id}")
async def cancel_job_endpoint(job_id: str):
    """Cancel a running or pending job."""
    job = cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.get("/{job_id}/events")
async def stream_job_events(job_id: str):
    """
    Server-Sent Events (SSE) stream for real-time job progress.
    Connect with: new EventSource('/api/jobs/{id}/events')
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Send current state immediately
        current = get_job(job_id)
        if current:
            yield _sse_event({"type": "state", "job": current.model_dump()})

        # If already terminal, close immediately
        if current and current.status in ("completed", "failed", "cancelled"):
            yield _sse_event({"type": "done"})
            return

        q = subscribe(job_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield _sse_event(event)

                    if event.get("type") in ("status",) and event.get("status") in (
                        "completed", "failed", "cancelled"
                    ):
                        yield _sse_event({"type": "done"})
                        break

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield ": ping\n\n"

                    # Check if job finished while we were waiting
                    current_job = get_job(job_id)
                    if current_job and current_job.status in ("completed", "failed", "cancelled"):
                        yield _sse_event({"type": "done", "status": current_job.status})
                        break
        finally:
            unsubscribe(job_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
