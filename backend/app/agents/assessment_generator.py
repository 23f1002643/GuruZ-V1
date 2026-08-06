"""Agent 7: Assessment Generator — create MCQs, short/long answers, numerical problems."""
from __future__ import annotations
import uuid
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve_all, retrieve
from app.schemas.teacher_package import (
    DocumentMetadata, AssessmentBank, AssessmentConfig,
    MCQ, ShortAnswer, LongAnswer, NumericalProblem,
    CaseStudy, HOTQuestion, DiagramQuestion,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an expert assessment designer and psychometrician.
Create rigorous, fair assessments based solely on the provided document content.
Never create questions about topics not covered in the document.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Respond ONLY with valid JSON.
Do NOT use phrases like 'according to the document', 'based on the context',
'source text', 'retrieved content', or 'provided document'. Write naturally."""

PROMPT_TEMPLATE = """Create an assessment bank for: {subject} — {topic}

GRADE LEVEL: {grade}
CATEGORY: {category}
DIFFICULTY: {difficulty}
LANGUAGE: {language}
LEARNING OBJECTIVES:
{objectives}

SOURCE MATERIAL:
{context}

Generate ONLY the requested question types. Counts are approximate.

{section_instructions}

Return a JSON object with ONLY these fields (include only the sections listed as required above):
{{
  "mcqs": [
    {{
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_option": 0,
      "explanation": "Why this is correct",
      "difficulty": "easy | medium | hard"
    }}
  ],
  "short_answers": [
    {{
      "question": "Short answer question?",
      "model_answer": "Expected answer (2-4 sentences)",
      "rubric": "Point 1 (1 mark), point 2 (1 mark)",
      "marks": 2,
      "difficulty": "easy | medium | hard"
    }}
  ],
  "long_answers": [
    {{
      "question": "Explain in detail...",
      "model_answer": "Comprehensive model answer",
      "rubric": "Marking scheme",
      "marks": 5,
      "difficulty": "medium | hard"
    }}
  ],
  "numerical": [
    {{
      "question": "Problem statement",
      "solution_steps": ["Step 1", "Step 2"],
      "final_answer": "Answer",
      "marks": 3,
      "difficulty": "medium"
    }}
  ],
  "case_studies": [
    {{
      "scenario": "Real-world scenario",
      "questions": ["Q1", "Q2"],
      "model_answer": "Expected answer",
      "marks": 5,
      "difficulty": "hard"
    }}
  ],
  "hots": [
    {{
      "question": "Higher-order thinking question",
      "model_answer": "Expected answer",
      "level": "analysis | evaluation | creation",
      "marks": 4,
      "difficulty": "hard"
    }}
  ],
  "diagram_questions": [
    {{
      "question": "Question description",
      "diagram_prompt": "Diagram description",
      "model_answer": "Expected diagram/answer",
      "marks": 3,
      "difficulty": "medium"
    }}
  ]
}}

Write naturally - do not reference that this came from a document or source text."""


class AssessmentGeneratorAgent(BaseAgent):
    name = "assessment_generator"
    temperature = 0.2
    max_tokens = 6000

    def _build_section_instructions(self, config: AssessmentConfig | None) -> str:
        """Build the section instructions based on config."""
        if config is None:
            return "Include: 6 MCQs, 3 short answers, 2 long answers. For STEM subjects include numerical problems."

        parts = []
        if config.include_mcq:
            parts.append(f"Include {config.mcq_count} multiple choice questions.")
        if config.include_short_answer:
            parts.append("Include 3 short answer questions.")
        if config.include_long_answer:
            parts.append("Include 2 long answer questions.")
        if config.include_numerical:
            parts.append("Include numerical problems (for STEM subjects).")
        if config.include_case_study:
            parts.append("Include 1-2 case studies with real-world scenarios.")
        if config.include_hots:
            parts.append("Include 2-3 higher-order thinking questions (analysis/evaluation/creation level).")
        if config.include_diagram:
            parts.append("Include 1-2 diagram-based questions.")

        if not parts:
            parts.append("Include: 6 MCQs, 3 short answers, 2 long answers.")

        return "\n".join(parts)

    async def run(
        self, metadata: DocumentMetadata, knowledge: dict, language: str, job_id: str,
        assessment_config: AssessmentConfig | None = None,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> AssessmentBank:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        config = assessment_config or AssessmentConfig()

        if progress_cb:
            progress_cb(10, "Retrieving assessment context...")

        chunks = retrieve_all(job_id, max_chunks=35)
        if not chunks:
            chunks = retrieve(job_id, f"assessment questions {metadata.topic}", top_k=12)
        context = self.build_rag_context(chunks)
        objectives_str = "\n".join(f"- {o}" for o in knowledge.get("learning_objectives", []))
        section_instructions = self._build_section_instructions(config)

        if progress_cb:
            progress_cb(30, "Generating assessment questions...")

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            grade=metadata.grade,
            category=metadata.category,
            difficulty=metadata.difficulty,
            language=language,
            objectives=objectives_str or "Not specified",
            context=context,
            section_instructions=section_instructions,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        if progress_cb:
            progress_cb(60, "Parsing MCQs and short answers...")

        # Parse MCQs
        mcqs = []
        if config.include_mcq:
            mcqs = [
                MCQ(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    options=item["options"],
                    correct_option=item["correct_option"],
                    explanation=item.get("explanation", ""),
                    difficulty=item.get("difficulty", "medium"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("mcqs", [])
            ]

        # Parse short answers
        short_answers = []
        if config.include_short_answer:
            short_answers = [
                ShortAnswer(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    model_answer=item.get("model_answer", ""),
                    rubric=item.get("rubric", ""),
                    marks=item.get("marks", 2),
                    difficulty=item.get("difficulty", "medium"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("short_answers", [])
            ]

        if progress_cb:
            progress_cb(75, "Parsing long answers and numerical problems...")

        # Parse long answers
        long_answers = []
        if config.include_long_answer:
            long_answers = [
                LongAnswer(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    model_answer=item.get("model_answer", ""),
                    rubric=item.get("rubric", ""),
                    marks=item.get("marks", 5),
                    difficulty=item.get("difficulty", "medium"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("long_answers", [])
            ]

        # Parse numerical problems
        numerical = []
        if config.include_numerical:
            numerical = [
                NumericalProblem(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    solution_steps=item.get("solution_steps", []),
                    final_answer=item.get("final_answer", ""),
                    marks=item.get("marks", 3),
                    difficulty=item.get("difficulty", "medium"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("numerical", [])
            ]

        if progress_cb:
            progress_cb(85, "Parsing case studies and higher-order questions...")

        # Parse case studies
        case_studies = []
        if config.include_case_study:
            case_studies = [
                CaseStudy(
                    question_id=str(uuid.uuid4())[:8],
                    scenario=item.get("scenario", item.get("question", "")),
                    questions=item.get("questions", []),
                    model_answer=item.get("model_answer", ""),
                    marks=item.get("marks", 5),
                    difficulty=item.get("difficulty", "hard"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("case_studies", [])
            ]

        # Parse HOTS questions
        hots = []
        if config.include_hots:
            hots = [
                HOTQuestion(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    model_answer=item.get("model_answer", ""),
                    level=item.get("level", "analysis"),
                    marks=item.get("marks", 4),
                    difficulty=item.get("difficulty", "hard"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("hots", [])
            ]

        # Parse diagram questions
        diagram_questions = []
        if config.include_diagram:
            diagram_questions = [
                DiagramQuestion(
                    question_id=str(uuid.uuid4())[:8],
                    question=item["question"],
                    diagram_prompt=item.get("diagram_prompt", ""),
                    model_answer=item.get("model_answer", ""),
                    marks=item.get("marks", 3),
                    difficulty=item.get("difficulty", "medium"),
                    source_chunks=item.get("source_chunks", []),
                )
                for item in data.get("diagram_questions", [])
            ]

        bank = AssessmentBank(
            mcqs=mcqs,
            short_answers=short_answers,
            long_answers=long_answers,
            numerical=numerical,
            case_studies=case_studies,
            hots=hots,
            diagram_questions=diagram_questions,
            config=config,
        )
        bank.compute_total()

        if progress_cb:
            progress_cb(100, f"{bank.total_questions} questions created")

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    total=bank.total_questions)
        return bank
