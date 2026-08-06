"""File-based storage for Teacher Knowledge Packages."""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from typing import Optional
from app.schemas.teacher_package import TeacherKnowledgePackage
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _packages_dir() -> Path:
    settings = get_settings()
    path = Path(settings.packages_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_package(pkg: TeacherKnowledgePackage) -> Path:
    """Persist a TeacherKnowledgePackage as JSON."""
    dest = _packages_dir() / f"{pkg.package_id}.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(pkg.model_dump(), f, indent=2, ensure_ascii=False)
    logger.info("package_saved", package_id=pkg.package_id, path=str(dest))
    return dest


def load_package(package_id: str) -> Optional[TeacherKnowledgePackage]:
    """Load a package by ID from disk."""
    path = _packages_dir() / f"{package_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return TeacherKnowledgePackage(**data)


def list_packages(limit: int = 50, subject: Optional[str] = None) -> list[TeacherKnowledgePackage]:
    """List all saved packages."""
    packages = []
    for p in sorted(_packages_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            pkg = TeacherKnowledgePackage(**data)
            if subject and pkg.metadata.subject.lower() != subject.lower():
                continue
            packages.append(pkg)
            if len(packages) >= limit:
                break
        except Exception as e:
            logger.warning("package_load_error", path=str(p), error=str(e))
    return packages


def delete_package(package_id: str) -> bool:
    """Completely delete a package: JSON record, PDFs, artifacts, uploads, vector DB, logs."""
    settings = get_settings()
    deleted = False

    # Resolve the job_id once, before any records are removed.
    job_id = _get_job_from_package(package_id)

    # 1. Package JSON record
    path = _packages_dir() / f"{package_id}.json"
    if path.exists():
        path.unlink()
        deleted = True
        logger.info("package_deleted_json", package_id=package_id)

    # 2. Package directory containing generated PDFs/artifacts
    package_dir = _packages_dir() / package_id
    if package_dir.exists():
        try:
            shutil.rmtree(package_dir)
            deleted = True
            logger.info("package_deleted_dir", package_id=package_id, path=str(package_dir))
        except Exception as e:
            logger.warning("package_delete_dir_error", package_id=package_id, error=str(e))

    # 3. Uploaded source file (data/uploads/{job_id}_{filename})
    if job_id:
        try:
            upload_dir = Path(settings.upload_dir)
            if upload_dir.exists():
                for f in upload_dir.glob(f"{job_id}_*"):
                    f.unlink(missing_ok=True)
                    logger.info("package_deleted_upload", package_id=package_id, file=str(f))
        except Exception as e:
            logger.warning("package_delete_upload_error", package_id=package_id, error=str(e))

    # 4. Vector DB collection
    if job_id:
        try:
            from app.rag.retriever import delete_collection
            delete_collection(job_id)
            logger.info("package_deleted_vector", package_id=package_id, job_id=job_id)
        except Exception as e:
            logger.warning("package_delete_vector_error", package_id=package_id, error=str(e))

    # 5. Logs related to this package's jobs
    if job_id:
        try:
            delete_logs_for_job(job_id)
        except Exception as e:
            logger.warning("package_delete_logs_error", package_id=package_id, error=str(e))

    return deleted


def _get_job_from_package(package_id: str) -> Optional[str]:
    """Try to find the job_id associated with a package (from job store or package record)."""
    try:
        from app.services import job_service
        for j in job_service.list_jobs(limit=100000):
            if j.package_id == package_id:
                return j.job_id
    except Exception:
        pass
    try:
        json_path = _packages_dir() / f"{package_id}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("job_id")
    except Exception:
        pass
    return None


def delete_logs_for_job(job_id: str) -> None:
    """Remove all log entries associated with a job."""
    try:
        from app.utils.logger import clear_logs_for_job
        clear_logs_for_job(job_id)
    except Exception:
        pass


def get_stats() -> dict:
    """Return aggregate stats across all packages."""
    packages = list_packages(limit=1000)
    subjects = list({p.metadata.subject for p in packages})
    return {
        "total_packages": len(packages),
        "subjects": subjects,
        "recent_packages": [_summary(p) for p in packages[:5]],
    }


def _summary(pkg: TeacherKnowledgePackage) -> dict:
    return {
        "package_id": pkg.package_id,
        "job_id": pkg.job_id,
        "filename": pkg.filename,
        "created_at": pkg.created_at,
        "subject": pkg.metadata.subject,
        "topic": pkg.metadata.topic,
        "grade": pkg.metadata.grade,
        "difficulty": pkg.metadata.difficulty,
        "language": pkg.metadata.language,
        "total_periods": pkg.teaching_plan.total_periods if pkg.teaching_plan else None,
        "total_assessments": pkg.assessments.total_questions if pkg.assessments else None,
        "validation_score": pkg.validation_report.overall_score if pkg.validation_report else None,
    }
