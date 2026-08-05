"""Agent 3: Knowledge Extractor — extract concepts, definitions, formulae, examples, applications."""
from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.rag.retriever import retrieve, retrieve_all
from app.schemas.teacher_package import (
    Concept, Definition, Formula, Example, Application, DocumentMetadata
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are an expert educational knowledge engineer.
Extract structured knowledge from the retrieved document excerpts.
ONLY extract information that is explicitly present in the provided document excerpts.
Never add information from your own prior knowledge.
If something is not found, omit it or note 'Not found in uploaded document'.
Respond ONLY with valid JSON."""

PROMPT_TEMPLATE = """Extract all educational knowledge from this document.

SUBJECT: {subject}
TOPIC: {topic}

DOCUMENT EXCERPTS:
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
      "explanation": "full explanation from the document",
      "importance": "core | supporting | supplementary",
      "source_chunks": ["chunk_id or excerpt reference"]
    }}
  ],
  "definitions": [
    {{
      "term": "technical term",
      "definition": "exact definition from document",
      "source_chunks": ["reference"]
    }}
  ],
  "formulae": [
    {{
      "name": "formula name",
      "expression": "mathematical or symbolic expression",
      "description": "what it represents",
      "variables": ["variable and its meaning"],
      "source_chunks": ["reference"]
    }}
  ],
  "examples": [
    {{
      "title": "example title",
      "description": "full example from document",
      "source_chunks": ["reference"]
    }}
  ],
  "applications": [
    {{
      "domain": "application domain",
      "description": "how the concept is applied",
      "source_chunks": ["reference"]
    }}
  ]
}}

Important: Extract ONLY from the provided excerpts. If formulae or examples are not in the document, return empty arrays."""


class KnowledgeExtractorAgent(BaseAgent):
    name = "knowledge_extractor"
    temperature = 0.1
    max_tokens = 6000

    async def run(
        self, metadata: DocumentMetadata, job_id: str
    ) -> dict:
        logger.info("agent_start", agent=self.name, job_id=job_id)

        # Retrieve comprehensive chunks for knowledge extraction
        query = f"{metadata.subject} {metadata.topic} concepts definitions formulae examples applications"
        chunks = retrieve_all(job_id, max_chunks=40)
        if not chunks:
            chunks = retrieve(job_id, query, top_k=15)

        context = self.build_rag_context(chunks)
        prompt = PROMPT_TEMPLATE.format(
            subject=metadata.subject,
            topic=metadata.topic,
            context=context,
        )

        data = await self.call_llm_json(prompt, SYSTEM)

        result = {
            "learning_objectives": data.get("learning_objectives", []),
            "prerequisites": data.get("prerequisites", []),
            "concepts": [Concept(**c) for c in data.get("concepts", [])],
            "definitions": [Definition(**d) for d in data.get("definitions", [])],
            "formulae": [Formula(**f) for f in data.get("formulae", [])],
            "examples": [Example(**e) for e in data.get("examples", [])],
            "applications": [Application(**a) for a in data.get("applications", [])],
        }

        logger.info(
            "agent_complete", agent=self.name, job_id=job_id,
            concepts=len(result["concepts"]),
            definitions=len(result["definitions"]),
        )
        return result
