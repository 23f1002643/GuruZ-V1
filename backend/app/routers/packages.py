"""Teacher Knowledge Package endpoints."""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.services.storage import (
    list_packages, load_package, delete_package, get_stats, _summary
)
from app.services.job_service import list_jobs
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("/stats/summary")
async def package_stats():
    """Get aggregated statistics across all packages."""
    stats = get_stats()
    all_jobs = list_jobs(limit=100000)
    completed = [j for j in all_jobs if j.status == "completed"]
    failed = [j for j in all_jobs if j.status == "failed"]

    import statistics
    times = [j.processing_time_seconds for j in completed if j.processing_time_seconds]
    avg_time = statistics.mean(times) if times else None

    return {
        "total_packages": stats["total_packages"],
        "total_jobs": len(all_jobs),
        "completed_jobs": len(completed),
        "failed_jobs": len(failed),
        "avg_processing_time_seconds": round(avg_time, 1) if avg_time else None,
        "subjects": stats["subjects"],
        "recent_packages": stats["recent_packages"],
    }


@router.get("")
async def list_packages_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    subject: Optional[str] = Query(default=None),
):
    """List all Teacher Knowledge Packages."""
    packages = list_packages(limit=limit, subject=subject)
    return [_summary(p) for p in packages]


@router.get("/{package_id}")
async def get_package_endpoint(package_id: str):
    """Get a full Teacher Knowledge Package by ID."""
    pkg = load_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg.model_dump()


@router.delete("/{package_id}")
async def delete_package_endpoint(package_id: str):
    """Delete a Teacher Knowledge Package."""
    deleted = delete_package(package_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Package not found")
    return {"error": None, "detail": f"Package {package_id} deleted successfully"}


@router.get("/{package_id}/download/{doc_type}")
async def download_package_document(package_id: str, doc_type: str):
    """Download a generated package PDF."""
    pkg = load_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    doc_map = {
        "lesson_plan": pkg.lesson_plan_pdf_path,
        "teacher_guide": pkg.teacher_guide_pdf_path,
        "assessment_book": pkg.assessment_book_pdf_path,
    }
    if doc_type not in doc_map:
        raise HTTPException(status_code=400, detail="Invalid document type")

    file_path = doc_map[doc_type]
    if not file_path:
        raise HTTPException(status_code=404, detail="Document not generated yet")

    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")

    return FileResponse(path, filename=path.name)
