"""System logs endpoint."""
from typing import Optional
from fastapi import APIRouter, Query
from app.utils.logger import get_logs

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
