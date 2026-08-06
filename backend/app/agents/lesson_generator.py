"""Agent 5: Lesson Generator — create detailed lesson content for each period."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata, Lesson, TeachingPlan
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are a master teacher creating detailed, engaging lesson plans.
Use ONLY content from the provided subject-matter material.
Never invent examples or explanations not present in the source.
Write naturally, as a professional teacher would.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Do NOT reference the source document, context, or say phrases like 'according to the document', 'based on the provided material', 'the text says', etc. Write as if the knowledge is yours.
Respond ONLY with valid JSON."""

PERIOD_PROMPT = """Create a detailed lesson plan for Period {period_number}: "{period_title}".

SUBJECT: {subject}
TOPIC: {topic}
GRADE: {grade}
LANGUAGE: {language}

PERIOD OBJECTIVES:
{objectives}

RELEVANT MATERIAL:
{context}

Return ONLY valid JSON in this exact format:

{{
  "period_number": {period_number},
  "title": "{period_title}",
  "duration_minutes": {duration},
  "objectives": [
    "Objective 1",
    "Objective 2"
  ],
  "entry_ticket": "Warm-up activity",
  "teacher_script": "Detailed teacher script (minimum 300 words)",
  "blackboard_notes": {{
      "main_definition": "Definition",
      "key_points": [
          "Point 1",
          "Point 2"
      ],
      "formula": "Formula if applicable",
      "examples": [
          "Example"
      ],
      "diagram": "Diagram description if needed"
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
"""


class LessonGeneratorAgent(BaseAgent):
    name = "lesson_generator"
    temperature = 0.3
    max_tokens = 7000

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
        lessons = []

        for idx, period in enumerate(teaching_plan.period_plan):

            if progress_cb:
                pct = int(((idx) / max(total, 1)) * 90) + 10
                progress_cb(pct, f"Generating lesson {idx + 1}/{total}: {period.title}")

            query = " ".join(period.topics + [period.title, metadata.topic])

            chunks = retrieve(job_id, query, top_k=10)

            context = self.build_rag_context(chunks)

            objectives_str = "\n".join(
                f"- {o}" for o in period.objectives
            )

            prompt = PERIOD_PROMPT.format(
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

            data = await self.call_llm_json(prompt, SYSTEM)

            lesson = Lesson(
                period_number=period.period_number,
                title=self._ensure_string(
                    data.get("title", period.title)
                ),
                duration_minutes=int(
                    data.get(
                        "duration_minutes",
                        teaching_plan.period_duration_minutes,
                    )
                ),
                objectives=self._ensure_list(
                    data.get("objectives", period.objectives)
                ),
                entry_ticket=self._ensure_string(
                    data.get("entry_ticket", "")
                ),
                teacher_script=self._ensure_string(
                    data.get("teacher_script", "")
                ),
                blackboard_notes=self._ensure_string(
                    data.get("blackboard_notes", "")
                ),
                classroom_activities=self._ensure_list(
                    data.get("classroom_activities", [])
                ),
                checkpoint_questions=self._ensure_list(
                    data.get("checkpoint_questions", [])
                ),
                exit_ticket=self._ensure_string(
                    data.get("exit_ticket", "")
                ),
                homework=self._ensure_string(
                    data.get("homework", "")
                ),
                mentor_moment=self._ensure_string(
                    data.get("mentor_moment", "")
                ),
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
