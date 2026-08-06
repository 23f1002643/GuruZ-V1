"""Pydantic schemas for Teacher Knowledge Package and all sub-components."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
import uuid


class Concept(BaseModel):
    name: str
    explanation: str
    importance: Literal["core", "supporting", "supplementary"] = "core"
    source_chunks: list[str] = Field(default_factory=list)


class Definition(BaseModel):
    term: str
    definition: str
    source_chunks: list[str] = Field(default_factory=list)


class Formula(BaseModel):
    name: str
    expression: str
    description: str
    variables: list[str] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)


class Example(BaseModel):
    title: str
    description: str
    source_chunks: list[str] = Field(default_factory=list)


class Application(BaseModel):
    domain: str
    description: str
    source_chunks: list[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    subject: str
    topic: str
    chapter: Optional[str] = None
    grade: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    category: Literal["STEM", "Humanities", "Social Sciences", "Arts", "Physical Education", "Other"] = "Other"
    language: str = "English"
    total_pages: Optional[int] = None
    word_count: Optional[int] = None
    key_themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class PeriodSummary(BaseModel):
    period_number: int
    title: str
    objectives: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class TeachingPlan(BaseModel):
    total_periods: int
    period_duration_minutes: int = 40
    overview: str
    period_plan: list[PeriodSummary] = Field(default_factory=list)


class BlackboardNotes(BaseModel):
    main_definition: str = ""
    formulas: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    diagrams: list[str] = Field(default_factory=list)
    additional: dict[str, Any] = Field(default_factory=dict)


class Lesson(BaseModel):
    period_number: int
    title: str
    duration_minutes: int = 40

    objectives: list[str] = Field(default_factory=list)

    entry_ticket: str = ""
    teacher_script: str = ""

    blackboard_notes: BlackboardNotes | str = Field(default_factory=BlackboardNotes)

    classroom_activities: list[str] = Field(default_factory=list)
    checkpoint_questions: list[str] = Field(default_factory=list)

    exit_ticket: str = ""
    homework: str = ""
    mentor_moment: str = ""


class Activity(BaseModel):
    title: str
    activity_type: Literal[
        "demonstration", "role_play", "experiment", "discussion",
        "project", "game", "field_work", "group_work"
    ] = "discussion"
    duration_minutes: int = 30
    materials: list[str] = Field(default_factory=list)
    teacher_instructions: str = ""
    student_instructions: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)


class MCQ(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: int  # 0-indexed
    explanation: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class ShortAnswer(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    model_answer: str
    rubric: str
    marks: int = 2
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class LongAnswer(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    model_answer: str
    rubric: str
    marks: int = 5
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class NumericalProblem(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    solution_steps: list[str] = Field(default_factory=list)
    final_answer: str
    marks: int = 3
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class CaseStudy(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario: str
    questions: list[str] = Field(default_factory=list)
    model_answer: str = ""
    marks: int = 5
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class HOTQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    model_answer: str = ""
    level: str = "analysis"
    marks: int = 4
    difficulty: Literal["easy", "medium", "hard"] = "hard"
    source_chunks: list[str] = Field(default_factory=list)


class DiagramQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    diagram_prompt: str = ""
    model_answer: str = ""
    marks: int = 3
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    source_chunks: list[str] = Field(default_factory=list)


class AssessmentConfig(BaseModel):
    """User-selected configuration for assessment generation."""
    mcq_count: int = 6
    include_mcq: bool = True
    include_short_answer: bool = True
    include_long_answer: bool = True
    include_numerical: bool = True
    include_case_study: bool = False
    include_hots: bool = False
    include_diagram: bool = False
    include_answer_key: bool = True


class AssessmentBank(BaseModel):
    total_questions: int = 0
    mcqs: list[MCQ] = Field(default_factory=list)
    short_answers: list[ShortAnswer] = Field(default_factory=list)
    long_answers: list[LongAnswer] = Field(default_factory=list)
    numerical: list[NumericalProblem] = Field(default_factory=list)
    case_studies: list[CaseStudy] = Field(default_factory=list)
    hots: list[HOTQuestion] = Field(default_factory=list)
    diagram_questions: list[DiagramQuestion] = Field(default_factory=list)
    config: Optional[AssessmentConfig] = None

    def compute_total(self) -> "AssessmentBank":
        self.total_questions = (
            len(self.mcqs) + len(self.short_answers) +
            len(self.long_answers) + len(self.numerical) +
            len(self.case_studies) + len(self.hots) +
            len(self.diagram_questions)
        )
        return self


class Misconception(BaseModel):
    misconception: str
    correct_understanding: str
    severity: Literal["low", "medium", "high"] = "medium"
    diagnostic_question: str
    remedial_action: str
    source_chunks: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    field: str
    message: str


class ValidationReport(BaseModel):
    is_valid: bool = False
    overall_score: float = 0.0
    hallucination_score: float = 0.0
    schema_valid: bool = False
    all_objectives_covered: bool = False
    source_chunks_verified: bool = False
    issues: list[ValidationIssue] = Field(default_factory=list)
    regeneration_count: int = 0


class TeacherKnowledgePackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    filename: str
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    metadata: DocumentMetadata
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)
    formulae: list[Formula] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)
    applications: list[Application] = Field(default_factory=list)
    teaching_plan: Optional[TeachingPlan] = None
    lessons: list[Lesson] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    assessments: Optional[AssessmentBank] = None
    misconceptions: list[Misconception] = Field(default_factory=list)
    validation_report: Optional[ValidationReport] = None

    lesson_plan_pdf_path: Optional[str] = None
    teacher_guide_pdf_path: Optional[str] = None
    assessment_book_pdf_path: Optional[str] = None
