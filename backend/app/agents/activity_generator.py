"""Agent 6: Activity Generator — design diverse classroom activities."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata, Activity, TeachingPlan
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an innovative educator specializing in active learning strategies.
Design engaging, practical activities based only on the provided subject-matter content.
Write naturally, as a professional teacher would.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Do NOT reference the source document, context, or say phrases like 'according to the document', 'based on the provided material', 'the text says', etc. Write as if the knowledge is yours.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Design diverse classroom activities for teaching: {subject} — {topic}

GRADE LEVEL: {grade}
CATEGORY: {category}
LANGUAGE: {language}
LEARNING OBJECTIVES:
{objectives}

SOURCE MATERIAL:
{context}

Create 4-6 varied activities using different pedagogical approaches.
Use ONLY content from the provided material for the subject matter.

Return a JSON array of activity objects:
[
  {{
    "title": "Activity title",
    "activity_type": "demonstration | role_play | experiment | discussion | project | game | field_work | group_work",
    "duration_minutes": 20,
    "materials": ["material 1", "material 2"],
    "teacher_instructions": "Step-by-step instructions for the teacher",
    "student_instructions": "Clear instructions for students",
    "success_criteria": ["Students can...", "Students demonstrate..."],
    "learning_objectives": ["Specific objective this activity addresses"]
  }}
]"""


class ActivityGeneratorAgent(BaseAgent):
    name = "activity_generator"
    temperature = 0.4
    max_tokens = 4000

    async def run(
        self, metadata: DocumentMetadata, knowledge: dict,
        teaching_plan: TeachingPlan, language: str, job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> list[Activity]:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        if progress_cb:
            progress_cb(20, "Retrieving activity context...")

        chunks = retrieve(job_id, f"practical application activities {metadata.topic}", top_k=8)
        context = self.build_rag_context(chunks)
        objectives_str = "\n".join(
            f"- {o}" for o in knowledge.get("learning_objectives", [])
        )

        if progress_cb:
            progress_cb(50, "Designing classroom activities...")

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            grade=metadata.grade,
            category=metadata.category,
            language=language,
            objectives=objectives_str or "Not specified",
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)
        if not isinstance(data, list):
            data = data.get("activities", [])

        if progress_cb:
            progress_cb(80, "Structuring activity details...")

        activities = []
        for item in data:
            try:
                activities.append(Activity(
                    title=item["title"],
                    activity_type=item.get("activity_type", "discussion"),
                    duration_minutes=item.get("duration_minutes", 30),
                    materials=item.get("materials", []),
                    teacher_instructions=item.get("teacher_instructions", ""),
                    student_instructions=item.get("student_instructions", ""),
                    success_criteria=item.get("success_criteria", []),
                    learning_objectives=item.get("learning_objectives", []),
                ))
            except Exception as e:
                logger.warning("activity_parse_error", error=str(e))

        if progress_cb:
            progress_cb(100, f"{len(activities)} activities designed")

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    activities=len(activities))
        return activities
