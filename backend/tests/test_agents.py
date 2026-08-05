"""Unit tests for agent schemas and job service."""
import pytest
from app.schemas.job import create_job, STAGES
from app.schemas.teacher_package import (
    TeacherKnowledgePackage, DocumentMetadata, AssessmentBank, MCQ
)
from app.services import job_service


def test_create_job_has_all_stages():
    job = create_job("test.pdf", file_size=1000, file_type="pdf")
    assert len(job.stages) == len(STAGES)
    assert job.status == "pending"
    assert job.overall_progress == 0


def test_job_stage_update():
    job = create_job("test.pdf")
    job.update_stage("document_parsing", 50, "Halfway")
    stage = job.get_stage("document_parsing")
    assert stage is not None
    assert stage.progress == 50
    assert stage.message == "Halfway"
    assert stage.started_at is not None


def test_job_stage_completion():
    job = create_job("test.pdf")
    job.update_stage("document_parsing", 100, "Done")
    stage = job.get_stage("document_parsing")
    assert stage.completed_at is not None


def test_assessment_bank_totals():
    mcq = MCQ(
        question="What is 2+2?",
        options=["1", "2", "4", "8"],
        correct_option=2,
        explanation="Basic arithmetic",
        difficulty="easy",
    )
    bank = AssessmentBank(mcqs=[mcq])
    bank.compute_total()
    assert bank.total_questions == 1


def test_teacher_knowledge_package_creation():
    meta = DocumentMetadata(
        subject="Physics",
        topic="Kinematics",
        grade="Grade 11",
        difficulty="intermediate",
        category="STEM",
        language="English",
    )
    pkg = TeacherKnowledgePackage(
        job_id="test-job-123",
        filename="physics.pdf",
        metadata=meta,
    )
    assert pkg.package_id  # auto-generated UUID
    assert pkg.job_id == "test-job-123"
    assert pkg.metadata.subject == "Physics"


def test_job_service_create_and_retrieve():
    job = job_service.create_new_job("sample.pdf", file_size=500, file_type="pdf")
    fetched = job_service.get_job(job.job_id)
    assert fetched is not None
    assert fetched.filename == "sample.pdf"


def test_job_service_list_and_filter():
    job = job_service.create_new_job("filter_test.pdf")
    jobs = job_service.list_jobs(status="pending")
    assert any(j.job_id == job.job_id for j in jobs)


def test_job_service_cancel():
    job = job_service.create_new_job("cancel_test.pdf")
    cancelled = job_service.cancel_job(job.job_id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"
