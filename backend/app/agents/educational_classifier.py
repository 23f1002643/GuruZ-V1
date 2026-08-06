"""Agent 2: Educational Classifier — determine subject, grade, difficulty, etc."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.parser import ParsedDocument
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an educational content classifier. 
Analyze the provided subject-matter content and extract precise metadata.
Only use information present in the content. 
If a field is not determinable from the content, use a reasonable default.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Respond ONLY with valid JSON — no preamble, no explanation."""

PROMPT_TEMPLATE = """Analyze this educational material and classify it.

SOURCE MATERIAL:
{context}

SOURCE MATERIAL NAME: {filename}

Return a JSON object with exactly these fields:
{{
  "subject": "e.g. Mathematics, Physics, History, Literature",
  "topic": "specific topic within the subject",
  "chapter": "chapter name or null",
  "grade": "e.g. Grade 9, University, High School",
  "difficulty": "beginner | intermediate | advanced",
  "category": "STEM | Humanities | Social Sciences | Arts | Physical Education | Other",
  "key_themes": ["theme1", "theme2"],
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}"""


class EducationalClassifierAgent(BaseAgent):
    name = "educational_classifier"
    temperature = 0.1
    max_tokens = 1024

    async def run(
        self, parsed_doc: ParsedDocument, language: str, job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> DocumentMetadata:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        if progress_cb:
            progress_cb(20, "Retrieving document sample...")

        # Retrieve broad sample of document
        chunks = retrieve(job_id, "subject topic grade level educational content overview", top_k=10)
        context = self.build_rag_context(chunks)

        if progress_cb:
            progress_cb(50, "Classifying subject, grade, and difficulty...")

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            filename=parsed_doc.filename,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        if progress_cb:
            progress_cb(80, "Building metadata...")

        metadata = DocumentMetadata(
            subject=data.get("subject", "Unknown"),
            topic=data.get("topic", "Unknown"),
            chapter=data.get("chapter"),
            grade=data.get("grade", "General"),
            difficulty=data.get("difficulty", "intermediate"),
            category=data.get("category", "Other"),
            language=language,
            total_pages=parsed_doc.page_count,
            word_count=parsed_doc.word_count,
            key_themes=data.get("key_themes", []),
            keywords=data.get("keywords", []),
        )

        if progress_cb:
            progress_cb(100, f"Subject: {metadata.subject}, Grade: {metadata.grade}")

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    subject=metadata.subject, topic=metadata.topic)
        return metadata
