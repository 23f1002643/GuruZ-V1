"""Agent 1: Document Parser — parse file and index chunks into ChromaDB."""
from __future__ import annotations
from pathlib import Path
from app.agents.base_agent import BaseAgent
from app.rag.parser import ParsedDocument, parse_document
from app.rag.chunker import TextChunk, chunk_text
from app.rag.retriever import index_chunks
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentParserAgent(BaseAgent):
    name = "document_parser"

    async def run(self, file_path: Path, job_id: str) -> tuple[ParsedDocument, list[TextChunk]]:
        """
        Parse the uploaded document, chunk it, and index in ChromaDB.

        Returns (parsed_doc, chunks) for use by downstream agents.
        """
        logger.info("agent_start", agent=self.name, job_id=job_id, file=str(file_path))

        # Parse document
        parsed = parse_document(file_path)

        # Chunk the full text
        chunks = chunk_text(parsed.full_text, source_id=job_id)

        # Index into ChromaDB
        index_chunks(job_id, chunks)

        logger.info(
            "agent_complete",
            agent=self.name,
            job_id=job_id,
            pages=parsed.page_count,
            chunks=len(chunks),
        )
        return parsed, chunks
