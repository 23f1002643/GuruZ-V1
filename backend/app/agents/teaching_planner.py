"""Agent 4: Teaching Planner — create multi-period teaching strategy."""
from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata, TeachingPlan, PeriodSummary
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an experienced curriculum designer and master teacher.
Design a comprehensive, pedagogically sound teaching plan based only on the provided document content.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Design a complete teaching plan for this educational content.

SUBJECT: {subject}
TOPIC: {topic}
GRADE: {grade}
DIFFICULTY: {difficulty}
LEARNING OBJECTIVES: {objectives}
PERIOD DURATION: {period_duration} minutes

DOCUMENT EXCERPTS:
{context}

Design the optimal number of periods needed to thoroughly cover this content.
Each period should have clear objectives and build on the previous one.

Return a JSON object:
{{
  "total_periods": 5,
  "period_duration_minutes": {period_duration},
  "overview": "A brief paragraph describing the overall teaching strategy",
  "period_plan": [
    {{
      "period_number": 1,
      "title": "Introduction to ...",
      "objectives": ["Students will understand...", "Students will be able to..."],
      "topics": ["topic 1 to cover", "topic 2 to cover"]
    }}
  ]
}}"""


class TeachingPlannerAgent(BaseAgent):
    name = "teaching_planner"
    temperature = 0.2
    max_tokens = 3000

    async def run(
        self, metadata: DocumentMetadata, knowledge: dict, job_id: str
    ) -> TeachingPlan:
        logger.info("agent_start", agent=self.name, job_id=job_id)
        settings = get_settings()

        chunks = retrieve(
            job_id,
            f"teaching sequence curriculum structure {metadata.topic}",
            top_k=8,
        )
        context = self.build_rag_context(chunks)
        objectives_str = "\n".join(f"- {o}" for o in knowledge.get("learning_objectives", []))

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            grade=metadata.grade,
            difficulty=metadata.difficulty,
            objectives=objectives_str or "Not specified",
            period_duration=settings.period_duration_minutes,
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        period_plan = [
            PeriodSummary(
                period_number=p["period_number"],
                title=p.get("title", f"Period {p['period_number']}"),
                objectives=p.get("objectives", []),
                topics=p.get("topics", []),
            )
            for p in data.get("period_plan", [])
        ]

        plan = TeachingPlan(
            total_periods=data.get("total_periods", len(period_plan)),
            period_duration_minutes=data.get("period_duration_minutes", settings.period_duration_minutes),
            overview=data.get("overview", ""),
            period_plan=period_plan,
        )

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    total_periods=plan.total_periods)
        return plan
