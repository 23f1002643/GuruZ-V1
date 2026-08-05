"""File-based storage for Teacher Knowledge Packages."""
from __future__ import annotations
import json
import os
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
    """Delete a package file. Returns True if deleted."""
    path = _packages_dir() / f"{package_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


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
