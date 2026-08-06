"""System logs endpoint."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.utils.logger import get_logs, delete_log, clear_logs

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def get_logs_endpoint(
    limit: int = Query(default=100, ge=1, le=1000),
    level: Optional[str] = Query(default=None),
    job_id: Optional[str] = Query(default=None),
):
    """Return recent system log entries."""
    logs = get_logs(limit=limit, level=level, job_id=job_id)
    return list(reversed(logs))  # Most recent first


@router.delete("")
async def delete_all_logs_endpoint():
    """Delete all system log entries."""
    removed = clear_logs()
    return {"error": None, "detail": f"Deleted {removed} log entries"}


@router.delete("/{index}")
async def delete_log_endpoint(index: int):
    """Delete a single log entry by index."""
    deleted = delete_log(index)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return {"error": None, "detail": f"Deleted log entry {index}"}


@router.get("/download")
async def download_logs_endpoint(
    limit: int = Query(default=1000, ge=1, le=10000),
    level: Optional[str] = Query(default=None),
    job_id: Optional[str] = Query(default=None),
):
    """Download logs as plain text."""
    logs = get_logs(limit=limit, level=level, job_id=job_id)
    lines = []
    for log in reversed(logs):
        ts = log.get("timestamp", "")
        lvl = log.get("level", "info")
        jid = log.get("job_id") or "-"
        stage = log.get("stage") or "-"
        msg = log.get("message", "")
        lines.append(f"{ts}\t{lvl.upper()}\t{jid}\t{stage}\t{msg}")
    content = "\n".join(lines) + ("\n" if lines else "")
    return PlainTextResponse(content, media_type="text/plain")
