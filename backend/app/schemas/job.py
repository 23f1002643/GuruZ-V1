"""Job and progress tracking schemas."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid


class StageProgress(BaseModel):
    stage: str
    stage_index: int
    total_stages: int = 10
    progress: int = 0  # 0-100
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


STAGES = [
    "document_parsing",
    "educational_classification",
    "knowledge_extraction",
    "teaching_planning",
    "lesson_generation",
    "activity_generation",
    "assessment_generation",
    "misconception_detection",
    "validation",
    "publishing",
]

STAGE_LABELS = {
    "document_parsing": "Document Intelligence",
    "educational_classification": "Educational Classification",
    "knowledge_extraction": "Knowledge Extraction",
    "teaching_planning": "Teaching Planner",
    "lesson_generation": "Lesson Generation",
    "activity_generation": "Activity Generation",
    "assessment_generation": "Assessment Generation",
    "misconception_detection": "Misconception Detection",
    "validation": "Validation",
    "publishing": "Publishing",
}


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: Literal["pending", "processing", "completed", "failed", "cancelled"] = "pending"
    filename: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    current_stage: Optional[str] = None
    overall_progress: int = 0
    stages: list[StageProgress] = Field(default_factory=list)
    error: Optional[str] = None
    package_id: Optional[str] = None
    processing_time_seconds: Optional[float] = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_stage(self, stage_name: str) -> Optional[StageProgress]:
        for s in self.stages:
            if s.stage == stage_name:
                return s
        return None

    def update_stage(self, stage_name: str, progress: int, message: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.current_stage = stage_name
        for s in self.stages:
            if s.stage == stage_name:
                s.progress = progress
                s.message = message
                if not s.started_at:
                    s.started_at = now
                if progress >= 100:
                    s.completed_at = now
                break
        # Calculate overall progress
        completed = sum(1 for s in self.stages if s.progress >= 100)
        current_stage_progress = next(
            (s.progress for s in self.stages if s.stage == stage_name), 0
        )
        total = len(self.stages)
        if total > 0:
            self.overall_progress = int(
                ((completed / total) * 100 * 0.9) +
                (current_stage_progress / total * 0.1)
            )
        self.touch()


def create_job(filename: str, file_size: Optional[int] = None,
               file_type: Optional[str] = None) -> Job:
    """Create a new job with all stages initialized."""
    stages = [
        StageProgress(
            stage=name,
            stage_index=i,
            total_stages=len(STAGES),
            progress=0,
            message="Pending",
        )
        for i, name in enumerate(STAGES)
    ]
    return Job(
        filename=filename,
        file_size=file_size,
        file_type=file_type,
        stages=stages,
        status="pending",
    )
