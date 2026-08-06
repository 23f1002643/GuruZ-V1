"""LangGraph pipeline orchestrating all 10 AI agents."""
from __future__ import annotations
import asyncio
import traceback
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END  # type: ignore

from app.agents.document_parser_agent import DocumentParserAgent
from app.agents.educational_classifier import EducationalClassifierAgent
from app.agents.knowledge_extractor import KnowledgeExtractorAgent
from app.agents.teaching_planner import TeachingPlannerAgent
from app.agents.lesson_generator import LessonGeneratorAgent
from app.agents.activity_generator import ActivityGeneratorAgent
from app.agents.assessment_generator import AssessmentGeneratorAgent
from app.agents.misconception_detector import MisconceptionDetectorAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.publisher import PublisherAgent
from app.schemas.teacher_package import TeacherKnowledgePackage, AssessmentConfig
from app.schemas.job import STAGES
from app.services import job_service
from app.utils.logger import get_logger, log_to_buffer

logger = get_logger(__name__)

MAX_VALIDATION_RETRIES = 2


class PipelineState(TypedDict, total=False):
    job_id: str
    file_path: str
    language: str
    parsed_doc: Any
    chunks: list
    metadata: Any
    knowledge: dict
    teaching_plan: Any
    lessons: list
    activities: list
    assessments: Any
    misconceptions: list
    validation_report: Any
    package: Any
    error: str
    assessment_config: Any


def _stage_progress(job_id: str, stage: str, pct: int, msg: str = "") -> None:
    job_service.update_job_stage(job_id, stage, pct, msg)
    log_to_buffer("info", msg or f"{stage} {pct}%", job_id=job_id, stage=stage)


async def node_document_parsing(state: PipelineState) -> PipelineState:
    job_id = state["job_id"]
    _stage_progress(job_id, "document_parsing", 5, "Parsing document...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "document_parsing", pct, msg)

    try:
        agent = DocumentParserAgent()
        parsed_doc, chunks, language = await agent.run(
            Path(state["file_path"]), job_id, progress_cb=_cb
        )

        job_service.update_job_language(job_id, language)
        _stage_progress(
            job_id,
            "document_parsing",
            100,
            f"Parsed {parsed_doc.page_count} pages, {len(chunks)} chunks. Detected language: {language}",
        )
        return {
            **state,
            "parsed_doc": parsed_doc,
            "chunks": chunks,
            "language": language,
        }
    except Exception as e:
        logger.error("node_error", node="document_parsing", error=str(e), exc_info=True)
        return {**state, "error": f"Document parsing failed: {e}"}


async def node_educational_classification(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "educational_classification", 5, "Classifying document...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "educational_classification", pct, msg)

    try:
        agent = EducationalClassifierAgent()
        metadata = await agent.run(state["parsed_doc"], state["language"], job_id, progress_cb=_cb)
        _stage_progress(job_id, "educational_classification", 100,
                        f"Subject: {metadata.subject}, Grade: {metadata.grade}")
        return {**state, "metadata": metadata}
    except Exception as e:
        logger.error("node_error", node="educational_classification", error=str(e))
        return {**state, "error": f"Classification failed: {e}"}


async def node_knowledge_extraction(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "knowledge_extraction", 5, "Extracting knowledge...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "knowledge_extraction", pct, msg)

    try:
        agent = KnowledgeExtractorAgent()
        knowledge = await agent.run(state["metadata"], state["language"], job_id, progress_cb=_cb)
        _stage_progress(job_id, "knowledge_extraction", 100,
                        f"{len(knowledge['concepts'])} concepts, "
                        f"{len(knowledge['learning_objectives'])} objectives")
        return {**state, "knowledge": knowledge}
    except Exception as e:
        logger.error("node_error", node="knowledge_extraction", error=str(e))
        return {**state, "error": f"Knowledge extraction failed: {e}"}


async def node_teaching_planning(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "teaching_planning", 5, "Designing teaching plan...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "teaching_planning", pct, msg)

    try:
        agent = TeachingPlannerAgent()
        teaching_plan = await agent.run(state["metadata"], state["knowledge"], state["language"], job_id, progress_cb=_cb)
        _stage_progress(job_id, "teaching_planning", 100,
                        f"{teaching_plan.total_periods} periods planned")
        return {**state, "teaching_plan": teaching_plan}
    except Exception as e:
        logger.error("node_error", node="teaching_planning", error=str(e))
        return {**state, "error": f"Teaching planning failed: {e}"}


async def node_lesson_generation(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    plan = state["teaching_plan"]

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "lesson_generation", pct, msg)

    _stage_progress(job_id, "lesson_generation", 5,
                    f"Generating {plan.total_periods} lessons...")
    try:
        agent = LessonGeneratorAgent()
        lessons = await agent.run(
            state["metadata"], plan, state["language"], job_id, progress_cb=_cb
        )
        _stage_progress(job_id, "lesson_generation", 100,
                        f"{len(lessons)} lessons generated")
        return {**state, "lessons": lessons}
    except Exception as e:
        logger.error("node_error", node="lesson_generation", error=str(e))
        return {**state, "error": f"Lesson generation failed: {e}"}


async def node_activity_generation(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "activity_generation", 5, "Generating activities...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "activity_generation", pct, msg)

    try:
        agent = ActivityGeneratorAgent()
        activities = await agent.run(
            state["metadata"], state["knowledge"], state["teaching_plan"], state["language"], job_id,
            progress_cb=_cb,
        )
        _stage_progress(job_id, "activity_generation", 100,
                        f"{len(activities)} activities designed")
        return {**state, "activities": activities}
    except Exception as e:
        logger.error("node_error", node="activity_generation", error=str(e))
        return {**state, "error": f"Activity generation failed: {e}"}


async def node_assessment_generation(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "assessment_generation", 5, "Creating assessments...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "assessment_generation", pct, msg)

    try:
        agent = AssessmentGeneratorAgent()
        config = state.get("assessment_config")
        assessments = await agent.run(
            state["metadata"], state["knowledge"], state["language"], job_id, config,
            progress_cb=_cb,
        )
        assessments.config = config
        _stage_progress(job_id, "assessment_generation", 100,
                        f"{assessments.total_questions} questions created")
        return {**state, "assessments": assessments}
    except Exception as e:
        logger.error("node_error", node="assessment_generation", error=str(e))
        return {**state, "error": f"Assessment generation failed: {e}"}


async def node_misconception_detection(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "misconception_detection", 5, "Detecting misconceptions...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "misconception_detection", pct, msg)

    try:
        agent = MisconceptionDetectorAgent()
        misconceptions = await agent.run(state["metadata"], state["knowledge"], state["language"], job_id, progress_cb=_cb)
        _stage_progress(job_id, "misconception_detection", 100,
                        f"{len(misconceptions)} misconceptions identified")
        return {**state, "misconceptions": misconceptions}
    except Exception as e:
        logger.error("node_error", node="misconception_detection", error=str(e))
        return {**state, "error": f"Misconception detection failed: {e}"}


async def node_validation(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "validation", 5, "Validating package...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "validation", pct, msg)

    try:
        # Assemble preliminary package for validation
        knowledge = state.get("knowledge", {})
        package = TeacherKnowledgePackage(
            job_id=job_id,
            filename=state["parsed_doc"].filename,
            metadata=state["metadata"],
            learning_objectives=knowledge.get("learning_objectives", []),
            prerequisites=knowledge.get("prerequisites", []),
            concepts=knowledge.get("concepts", []),
            definitions=knowledge.get("definitions", []),
            formulae=knowledge.get("formulae", []),
            examples=knowledge.get("examples", []),
            applications=knowledge.get("applications", []),
            teaching_plan=state.get("teaching_plan"),
            lessons=state.get("lessons", []),
            activities=state.get("activities", []),
            assessments=state.get("assessments"),
            misconceptions=state.get("misconceptions", []),
        )

        agent = ValidationAgent()
        validation_report = await agent.run(package, state["language"], job_id, progress_cb=_cb)
        package.validation_report = validation_report

        _stage_progress(job_id, "validation", 100,
                        f"Score: {validation_report.overall_score:.2f}, "
                        f"Valid: {validation_report.is_valid}")
        return {**state, "validation_report": validation_report, "package": package}
    except Exception as e:
        logger.error("node_error", node="validation", error=str(e))
        return {**state, "error": f"Validation failed: {e}"}


async def node_publishing(state: PipelineState) -> PipelineState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    _stage_progress(job_id, "publishing", 5, "Publishing package...")

    def _cb(pct: int, msg: str) -> None:
        _stage_progress(job_id, "publishing", pct, msg)

    try:
        agent = PublisherAgent()
        package = await agent.run(state["package"], job_id, progress_cb=_cb)
        _stage_progress(job_id, "publishing", 100,
                        f"Package {package.package_id} published")
        return {**state, "package": package}
    except Exception as e:
        logger.error("node_error", node="publishing", error=str(e))
        return {**state, "error": f"Publishing failed: {e}"}


def _build_graph():
    """Construct and compile the LangGraph pipeline."""
    builder = StateGraph(PipelineState)

    builder.add_node("document_parsing", node_document_parsing)
    builder.add_node("educational_classification", node_educational_classification)
    builder.add_node("knowledge_extraction", node_knowledge_extraction)
    builder.add_node("teaching_planning", node_teaching_planning)
    builder.add_node("lesson_generation", node_lesson_generation)
    builder.add_node("activity_generation", node_activity_generation)
    builder.add_node("assessment_generation", node_assessment_generation)
    builder.add_node("misconception_detection", node_misconception_detection)
    builder.add_node("validation", node_validation)
    builder.add_node("publishing", node_publishing)

    builder.set_entry_point("document_parsing")
    builder.add_edge("document_parsing", "educational_classification")
    builder.add_edge("educational_classification", "knowledge_extraction")
    builder.add_edge("knowledge_extraction", "teaching_planning")
    builder.add_edge("teaching_planning", "lesson_generation")
    builder.add_edge("lesson_generation", "activity_generation")
    builder.add_edge("activity_generation", "assessment_generation")
    builder.add_edge("assessment_generation", "misconception_detection")
    builder.add_edge("misconception_detection", "validation")
    builder.add_edge("validation", "publishing")
    builder.add_edge("publishing", END)

    return builder.compile()


async def run_pipeline(job_id: str, file_path: str, assessment_config=None) -> str:
    """
    Execute the full 10-stage pipeline for a document.
    Returns the package_id on success, raises on failure.
    """
    logger.info("pipeline_start", job_id=job_id, file_path=file_path)
    job_service.update_job_status(job_id, "processing")

    graph = _build_graph()

    initial_state: PipelineState = {
        "job_id": job_id,
        "file_path": file_path,
        "assessment_config": assessment_config,
    }

    try:
        final_state = await graph.ainvoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        package = final_state.get("package")
        if not package:
            raise RuntimeError("Pipeline completed but no package was produced")

        job_service.set_job_package(job_id, package.package_id)
        job_service.update_job_status(job_id, "completed")
        logger.info("pipeline_complete", job_id=job_id, package_id=package.package_id)
        return package.package_id

    except Exception as e:
        error_msg = str(e)
        logger.error("pipeline_failed", job_id=job_id, error=error_msg,
                     traceback=traceback.format_exc())
        job_service.update_job_status(job_id, "failed", error=error_msg)
        raise
