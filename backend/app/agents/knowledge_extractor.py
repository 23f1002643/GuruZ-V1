"""Agent 3: Knowledge Extractor — extract concepts, definitions, formulae, examples, applications."""
from __future__ import annotations
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve, retrieve_all
from app.schemas.teacher_package import (
    Concept, Definition, Formula, Example, Application, DocumentMetadata
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an expert educational knowledge engineer.
Extract structured knowledge from the provided subject-matter content.
ONLY extract information that is explicitly present in the provided content.
Never add information from your own prior knowledge.
If something is not found, omit it or note 'Not found in the provided material'.
Write ALL content in the language specified in LANGUAGE field. Do NOT mix languages.
Do NOT reference the source document, context, or say phrases like 'according to the document', 'based on the provided material', 'the text says', etc. Write as if the knowledge is yours.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Extract all educational knowledge from the given material.

SUBJECT: {subject}
TOPIC: {topic}
LANGUAGE: {language}

SOURCE MATERIAL:
{context}

Return a JSON object with exactly these fields:
{{
  "learning_objectives": [
    "By the end of this lesson, students will be able to..."
  ],
  "prerequisites": ["prerequisite topic 1", "prerequisite topic 2"],
  "concepts": [
    {{
      "name": "concept name",
      "explanation": "full explanation",
      "importance": "core | supporting | supplementary"
    }}
  ],
  "definitions": [
    {{
      "term": "technical term",
      "definition": "exact definition"
    }}
  ],
  "formulae": [
    {{
      "name": "formula name",
      "expression": "mathematical or symbolic expression",
      "description": "what it represents",
      "variables": ["variable and its meaning"]
    }}
  ],
  "examples": [
    {{
      "title": "example title",
      "description": "full example"
    }}
  ],
  "applications": [
    {{
      "domain": "application domain",
      "description": "how the concept is applied"
    }}
  ]
}}

Important: Extract ONLY from the provided material. If formulae or examples are not present, return empty arrays."""


class KnowledgeExtractorAgent(BaseAgent):
    name = "knowledge_extractor"
    temperature = 0.1
    max_tokens = 6000

    async def run(
        self, metadata: DocumentMetadata, language: str, job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> dict:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        if progress_cb:
            progress_cb(15, "Retrieving comprehensive document chunks...")

        # Retrieve comprehensive chunks for knowledge extraction
        query = f"{metadata.subject} {metadata.topic} concepts definitions formulae examples applications"
        chunks = retrieve_all(job_id, max_chunks=40)
        if not chunks:
            chunks = retrieve(job_id, query, top_k=15)

        context = self.build_rag_context(chunks)

        if progress_cb:
            progress_cb(40, "Extracting concepts and definitions...")

        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            language=language,
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        if progress_cb:
            progress_cb(75, "Structuring knowledge fields...")

        result = {
            "learning_objectives": data.get("learning_objectives", []),
            "prerequisites": data.get("prerequisites", []),
            "concepts": [Concept(**c) for c in data.get("concepts", [])],
            "definitions": [Definition(**d) for d in data.get("definitions", [])],
            "formulae": [Formula(**f) for f in data.get("formulae", [])],
            "examples": [Example(**e) for e in data.get("examples", [])],
            "applications": [Application(**a) for a in data.get("applications", [])],
        }

        if progress_cb:
            progress_cb(100, f"{len(result['concepts'])} concepts, {len(result['definitions'])} definitions")

        logger.info(
            "agent_complete", agent=self.name, job_id=job_id,
            concepts=len(result["concepts"]),
            definitions=len(result["definitions"]),
        )
        return result
