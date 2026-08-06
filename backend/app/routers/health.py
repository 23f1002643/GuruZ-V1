"""Health check endpoints."""
import time
from fastapi import APIRouter
from app.models.llm_router import get_llm_status, resolve_provider
from app.rag.retriever import get_chroma_status
from app.services.job_service import list_jobs
from app.config import get_settings

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/healthz")
async def health_check():
    return {"status": "ok"}


@router.get("/health/detailed")
async def detailed_health():
    settings = get_settings()
    llm_status = get_llm_status()
    chroma_status = get_chroma_status()
    all_jobs = list_jobs(limit=10000)
    active_jobs = [j for j in all_jobs if j.status == "processing"]

    return {
        "status": "ok",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
        "llm_status": llm_status.get("active", "unknown"),
        "nvidia_status": llm_status.get("nvidia", "unknown"),
        "groq_status": llm_status.get("groq", "unknown"),
        "chromadb_status": chroma_status,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "total_jobs": len(all_jobs),
        "active_jobs": len(active_jobs),
    }
