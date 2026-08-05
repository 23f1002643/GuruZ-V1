"""Agent 8: Misconception Detector — identify student learning gaps."""
from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata, Misconception
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an expert in educational psychology and learning science.
Identify likely student misconceptions based on the document content.
Ground each misconception in the actual content — never speculate beyond what's in the document.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Identify potential student misconceptions for: {subject} — {topic}

GRADE LEVEL: {grade}
KEY CONCEPTS: {concepts}

DOCUMENT CONTENT:
{context}

Identify 4-6 common misconceptions students might develop when learning this material.
Base these on the actual content in the document.

Return a JSON array:
[
  {{
    "misconception": "The incorrect belief or misunderstanding students often form",
    "correct_understanding": "The accurate understanding based on the document",
    "severity": "low | medium | high",
    "diagnostic_question": "A question that reveals if a student holds this misconception",
    "remedial_action": "Specific teaching strategy to correct this misconception",
    "source_chunks": ["brief reference to relevant document section"]
  }}
]"""


class MisconceptionDetectorAgent(BaseAgent):
    name = "misconception_detector"
    temperature = 0.3
    max_tokens = 3000

    async def run(
        self, metadata: DocumentMetadata, knowledge: dict, job_id: str
    ) -> list[Misconception]:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        chunks = retrieve(job_id, f"common errors mistakes misunderstanding {metadata.topic}", top_k=8)
        context = self.build_rag_context(chunks)
        concepts_str = ", ".join(c.name for c in knowledge.get("concepts", [])[:8])

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            grade=metadata.grade,
            concepts=concepts_str or "Not specified",
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)
        if not isinstance(data, list):
            data = data.get("misconceptions", [])

        misconceptions = []
        for item in data:
            try:
                misconceptions.append(Misconception(
                    misconception=item["misconception"],
                    correct_understanding=item.get("correct_understanding", ""),
                    severity=item.get("severity", "medium"),
                    diagnostic_question=item.get("diagnostic_question", ""),
                    remedial_action=item.get("remedial_action", ""),
                    source_chunks=item.get("source_chunks", []),
                ))
            except Exception as e:
                logger.warning("misconception_parse_error", error=str(e))

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    count=len(misconceptions))
        return misconceptions
