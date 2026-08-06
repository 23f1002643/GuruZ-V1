"""Document upload endpoint — accepts file, creates job, starts background processing."""
import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from typing import Optional
from app.config import get_settings
from app.schemas.teacher_package import AssessmentConfig
from app.services.job_service import create_new_job, update_job_status
from app.workflows.pipeline import run_pipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".ppt", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _run_pipeline_background(job_id: str, file_path: str, config=None) -> None:
    """Background task wrapper with error handling."""
    try:
        await run_pipeline(job_id, file_path, assessment_config=config)
    except Exception as e:
        logger.error("background_pipeline_error", job_id=job_id, error=str(e))
        update_job_status(job_id, "failed", error=str(e))
    finally:
        # Clean up the uploaded file after processing
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


def _parse_assessment_config(raw: Optional[str]) -> Optional[AssessmentConfig]:
    """Parse the assessment config JSON string from the upload form."""
    if not raw:
        return None
    try:
        import json
        data = json.loads(raw)
        return AssessmentConfig(**data)
    except Exception:
        return None


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    assessment_config: Optional[str] = Form(default=None),
):
    """
    Upload an educational document for AI processing.
    Returns a job_id for tracking progress.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Read and size-check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Parse assessment configuration (optional)
    config = _parse_assessment_config(assessment_config)

    # Create job first
    job = create_new_job(
        filename=file.filename,
        file_size=len(content),
        file_type=suffix.lstrip("."),
    )

    # Save file with job_id prefix to avoid collisions
    dest_path = upload_dir / f"{job.job_id}_{file.filename}"
    with open(dest_path, "wb") as f:
        f.write(content)

    logger.info("upload_received", job_id=job.job_id, filename=file.filename,
                size=len(content), assessment_config=config.model_dump() if config else None)

    # Start pipeline in background (asyncio task, not thread)
    asyncio.create_task(
        _run_pipeline_background(job.job_id, str(dest_path), config)
    )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": f"Document '{file.filename}' accepted. Processing started.",
        "filename": file.filename,
    }
