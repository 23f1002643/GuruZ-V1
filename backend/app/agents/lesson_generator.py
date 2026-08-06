"""Agent 5: Lesson Generator — create detailed lesson content for each period."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata, Lesson, TeachingPlan
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are a master teacher creating detailed, engaging lesson plans.
Use only content from the provided subject-matter material.
Never invent examples, explanations, formulas, or diagrams that are not present in the source.
Write naturally, as a professional teacher would.
Write all output in the LANGUAGE specified. Do not mix languages.
Do not mention the source document, context labels, or phrases like 'according to the document'.
Respond only with valid JSON."""

PROMPT_TEMPLATE = """Generate a single lesson plan for Period {period_number}: \"{period_title}\".

SUBJECT: {subject}
TOPIC: {topic}
GRADE: {grade}
LANGUAGE: {language}

PERIOD OBJECTIVES:
{objectives}

RELEVANT SOURCE PASSAGES:
{context}

Return exactly one valid JSON object in this format:
{{
  "period_number": {period_number},
  "title": "{period_title}",
  "duration_minutes": {duration},
  "objectives": [
    "Objective 1",
    "Objective 2"
  ],
  "entry_ticket": "Warm-up activity",
  "teacher_script": "Concise, classroom-ready teacher script.",
  "blackboard_notes": {{
      "main_definition": "Definition",
      "key_points": [
          "Point 1",
          "Point 2"
      ],
      "formulas": [
          "Formula if applicable"
      ],
      "examples": [
          "Example"
      ],
      "diagrams": [
          "Diagram description if directly supported by the source"
      ]
  }},
  "classroom_activities": [
      "Activity 1",
      "Activity 2"
  ],
  "checkpoint_questions": [
      "Question 1",
      "Question 2"
  ],
  "exit_ticket": "Exit ticket",
  "homework": "Homework",
  "mentor_moment": "Motivational story"
}}

Rules:
- Use only the information in RELEVANT SOURCE PASSAGES.
- If the source does not explicitly provide a definition, formula, example, or diagram, use an empty string or empty list.
- Keep teacher_script practical and classroom-ready, around 200-250 words.
- Keep blackboard_notes concise and directly tied to the source.
- Return JSON only. Do not include markdown fences, commentary, or additional keys.
"""

MAX_CONTEXT_CHUNKS = 4
MAX_CONTEXT_CHARS = 1000
TOP_K_CHUNKS = 5


class LessonGeneratorAgent(BaseAgent):
    name = "lesson_generator"
    temperature = 0.2
    max_tokens = 2500

    def _ensure_string(self, value: Any) -> str:
        """Convert any value into a readable string."""
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return "\n".join(str(v) for v in value)

        if isinstance(value, dict):
            lines = []
            for key, val in value.items():
                title = key.replace("_", " ").title()
                if isinstance(val, list):
                    lines.append(f"{title}:")
                    lines.extend(f"• {x}" for x in val)
                else:
                    lines.append(f"{title}: {val}")
            return "\n".join(lines)

        return str(value)

    def _ensure_list(self, value: Any) -> list[str]:
        """Convert any value into list[str]."""
        if value is None:
            return []

        if isinstance(value, list):
            return [str(v) for v in value]

        if isinstance(value, str):
            return [value]

        if isinstance(value, dict):
            return [f"{k}: {v}" for k, v in value.items()]

        return [str(value)]

    def _normalize_blackboard_notes(self, value: Any) -> dict[str, Any]:
        """Normalize blackboard note output into the expected schema shape."""
        if not isinstance(value, dict):
            return {
                "main_definition": "",
                "key_points": [],
                "formulas": [],
                "examples": [],
                "diagrams": [],
            }

        return {
            "main_definition": str(value.get("main_definition") or ""),
            "key_points": [str(x) for x in (value.get("key_points") or []) if x],
            "formulas": [str(x) for x in (value.get("formulas") or []) if x],
            "examples": [str(x) for x in (value.get("examples") or []) if x],
            "diagrams": [str(x) for x in (value.get("diagrams") or []) if x],
        }

    def build_rag_context(self, chunks: list[str]) -> str:
        """Trim and format retrieved chunks for a smaller prompt footprint."""
        if not chunks:
            return "No relevant source passages are available."

        passages: list[str] = []
        for index, chunk in enumerate(chunks[:MAX_CONTEXT_CHUNKS]):
            text = chunk.strip().replace("\n", " ")
            if len(text) > MAX_CONTEXT_CHARS:
                text = text[:MAX_CONTEXT_CHARS].rsplit(" ", 1)[0] + "..."
            passages.append(f"[Passage {index + 1}]\n{text}")

        return "\n\n".join(passages)

    async def run(
        self,
        metadata: DocumentMetadata,
        teaching_plan: TeachingPlan,
        language: str,
        job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> list[Lesson]:

        logger.info(
            "agent_start",
            agent=self.name,
            job_id=job_id,
            total_periods=teaching_plan.total_periods,
        )

        total = len(teaching_plan.period_plan)
        lessons: list[Lesson] = []

        for idx, period in enumerate(teaching_plan.period_plan):
            if progress_cb:
                pct = int(((idx) / max(total, 1)) * 90) + 10
                progress_cb(pct, f"Generating lesson {idx + 1}/{total}: {period.title}")

            query = " ".join(
                [metadata.subject, metadata.topic, period.title, *period.topics]
            )
            chunks = retrieve(job_id, query, top_k=TOP_K_CHUNKS)
            logger.info(
                "retrieval_context",
                job_id=job_id,
                period=period.period_number,
                chunks=len(chunks),
            )

            context = self.build_rag_context(chunks)
            objectives_str = "\n".join(f"- {o}" for o in period.objectives)
            prompt = PROMPT_TEMPLATE.format(
                period_number=period.period_number,
                period_title=period.title,
                subject=metadata.subject,
                topic=metadata.topic,
                grade=metadata.grade,
                language=language,
                duration=teaching_plan.period_duration_minutes,
                objectives=objectives_str,
                context=context,
            )

            try:
                data = await self.call_llm_json(prompt, SYSTEM)
            except Exception as exc:
                logger.error(
                    "lesson_generation_failed",
                    job_id=job_id,
                    period=period.period_number,
                    error=str(exc),
                )
                raise

            lesson = Lesson(
                period_number=period.period_number,
                title=self._ensure_string(data.get("title", period.title)),
                duration_minutes=int(
                    data.get(
                        "duration_minutes",
                        teaching_plan.period_duration_minutes,
                    )
                ),
                objectives=self._ensure_list(
                    data.get("objectives", period.objectives)
                ),
                entry_ticket=self._ensure_string(data.get("entry_ticket", "")),
                teacher_script=self._ensure_string(data.get("teacher_script", "")),
                blackboard_notes=self._normalize_blackboard_notes(
                    data.get("blackboard_notes", {})
                ),
                classroom_activities=self._ensure_list(
                    data.get("classroom_activities", [])
                ),
                checkpoint_questions=self._ensure_list(
                    data.get("checkpoint_questions", [])
                ),
                exit_ticket=self._ensure_string(data.get("exit_ticket", "")),
                homework=self._ensure_string(data.get("homework", "")),
                mentor_moment=self._ensure_string(data.get("mentor_moment", "")),
            )

            lessons.append(lesson)
            logger.info(
                "lesson_generated",
                period=period.period_number,
                job_id=job_id,
            )

        logger.info(
            "agent_complete",
            agent=self.name,
            job_id=job_id,
            lessons=len(lessons),
        )

        return lessons
