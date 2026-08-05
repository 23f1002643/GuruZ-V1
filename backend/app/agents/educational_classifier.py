"""Agent 2: Educational Classifier — determine subject, grade, difficulty, etc."""
from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.rag.parser import ParsedDocument
from app.rag.retriever import retrieve
from app.schemas.teacher_package import DocumentMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an educational content classifier. 
Analyze the provided document excerpts and extract precise metadata.
Only use information present in the document. 
If a field is not determinable from the document, use a reasonable default.
Respond ONLY with valid JSON — no preamble, no explanation."""

PROMPT_TEMPLATE = """Analyze this educational document and classify it.

DOCUMENT EXCERPTS:
{context}

DOCUMENT FILENAME: {filename}

Return a JSON object with exactly these fields:
{{
  "subject": "e.g. Mathematics, Physics, History, Literature",
  "topic": "specific topic within the subject",
  "chapter": "chapter name or null",
  "grade": "e.g. Grade 9, University, High School",
  "difficulty": "beginner | intermediate | advanced",
  "category": "STEM | Humanities | Social Sciences | Arts | Physical Education | Other",
  "language": "e.g. English, Spanish",
  "key_themes": ["theme1", "theme2"],
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}"""


class EducationalClassifierAgent(BaseAgent):
    name = "educational_classifier"
    temperature = 0.1
    max_tokens = 1024

    async def run(self, parsed_doc: ParsedDocument, job_id: str) -> DocumentMetadata:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        # Retrieve broad sample of document
        chunks = retrieve(job_id, "subject topic grade level educational content overview", top_k=10)
        context = self.build_rag_context(chunks)

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            filename=parsed_doc.filename,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        metadata = DocumentMetadata(
            subject=data.get("subject", "Unknown"),
            topic=data.get("topic", "Unknown"),
            chapter=data.get("chapter"),
            grade=data.get("grade", "General"),
            difficulty=data.get("difficulty", "intermediate"),
            category=data.get("category", "Other"),
            language=data.get("language", "English"),
            total_pages=parsed_doc.page_count,
            word_count=parsed_doc.word_count,
            key_themes=data.get("key_themes", []),
            keywords=data.get("keywords", []),
        )

        logger.info("agent_complete", agent=self.name, job_id=job_id,
                    subject=metadata.subject, topic=metadata.topic)
        return metadata
