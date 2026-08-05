"""Agent 7: Assessment Generator — create MCQs, short/long answers, numerical problems."""
from __future__ import annotations
import uuid
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve_all, retrieve
from app.schemas.teacher_package import (
    DocumentMetadata, AssessmentBank, MCQ, ShortAnswer, LongAnswer, NumericalProblem
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an expert assessment designer and psychometrician.
Create rigorous, fair assessments based solely on the provided document content.
Never create questions about topics not covered in the document.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Create a comprehensive assessment bank for: {subject} — {topic}

GRADE LEVEL: {grade}
CATEGORY: {category}
DIFFICULTY: {difficulty}
LEARNING OBJECTIVES:
{objectives}

DOCUMENT CONTENT:
{context}

Generate a balanced assessment with questions at varying difficulty levels.
Base ALL questions strictly on the provided document content.

Return a JSON object:
{{
  "mcqs": [
    {{
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_option": 0,
      "explanation": "Why this is correct, based on the document",
      "difficulty": "easy | medium | hard",
      "source_chunks": ["brief reference to source"]
    }}
  ],
  "short_answers": [
    {{
      "question": "Short answer question?",
      "model_answer": "Expected answer in 2-4 sentences",
      "rubric": "Award marks for: point 1 (1 mark), point 2 (1 mark)",
      "marks": 2,
      "difficulty": "easy | medium | hard",
      "source_chunks": ["reference"]
    }}
  ],
  "long_answers": [
    {{
      "question": "Explain in detail...",
      "model_answer": "Comprehensive model answer with all key points",
      "rubric": "Marking scheme with criteria and marks",
      "marks": 5,
      "difficulty": "medium | hard",
      "source_chunks": ["reference"]
    }}
  ],
  "numerical": []
}}

For STEM subjects: include numerical problems with step-by-step solutions in the numerical array.
For Humanities/Social Sciences: keep numerical array empty and focus on analytical questions.
Generate at least: 6 MCQs, 3 short answers, 2 long answers."""


class AssessmentGeneratorAgent(BaseAgent):
    name = "assessment_generator"
    temperature = 0.2
    max_tokens = 6000

    async def run(
        self, metadata: DocumentMetadata, knowledge: dict, job_id: str
    ) -> AssessmentBank:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        chunks = retrieve_all(job_id, max_chunks=35)
        if not chunks:
            chunks = retrieve(job_id, f"assessment questions {metadata.topic}", top_k=12)
        context = self.build_rag_context(chunks)
        objectives_str = "\n".join(f"- {o}" for o in knowledge.get("learning_objectives", []))

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            grade=metadata.grade,
            category=metadata.category,
            difficulty=metadata.difficulty,
            objectives=objectives_str or "Not specified",
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

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

        bank = AssessmentBank(
            mcqs=mcqs,
            short_answers=short_answers,
            long_answers=long_answers,
            numerical=numerical,
        )
        bank.compute_total()

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    total=bank.total_questions)
        return bank
