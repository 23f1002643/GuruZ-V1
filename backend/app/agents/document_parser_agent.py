"""Agent 1: Document Parser — parse file, detect language, index chunks."""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional
from app.agents.base_agent import BaseAgent
from app.rag.parser import ParsedDocument, parse_document
from app.rag.chunker import TextChunk, chunk_text
from app.rag.retriever import index_chunks
from app.utils.logger import get_logger
from app.utils.language_utils import detect_language

logger = get_logger(__name__)


class DocumentParserAgent(BaseAgent):
    name = "document_parser"

    async def run(
        self,
        file_path: Path,
        job_id: str,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[ParsedDocument, list[TextChunk], str]:
        """
        Parse the uploaded document, detect its language, chunk it, and index.

        Returns (parsed_doc, chunks, language) for use by downstream agents.
        Language is detected here (before chunking/embeddings) and reused
        everywhere downstream.
        """
        logger.info("agent_start", agent=self.name, job_id=job_id, file=str(file_path))

        if progress_cb:
            progress_cb(10, "Reading document file...")

        # Parse document (parser already cleans OCR garbage and retries).
        parsed = parse_document(file_path)

        if progress_cb:
            progress_cb(40, f"Parsed {parsed.page_count} pages, {parsed.word_count} words")

        # Detect language from the cleaned text — reliable script-aware detection.
        language = detect_language(parsed.full_text)
        logger.info("language_detected", agent=self.name, job_id=job_id,
                    language=language, chars=len(parsed.full_text))

        if progress_cb:
            progress_cb(60, f"Detected language: {language}")

        # Chunk the cleaned full text.
        chunks = chunk_text(parsed.full_text, source_id=job_id)

        if progress_cb:
            progress_cb(80, f"Created {len(chunks)} text chunks")

        # Index into ChromaDB.
        index_chunks(job_id, chunks)

        if progress_cb:
            progress_cb(100, f"Indexed {len(chunks)} chunks")

        logger.info(
            "agent_complete",
            agent=self.name,
            job_id=job_id,
            pages=parsed.page_count,
            chunks=len(chunks),
            language=language,
        )
        return parsed, chunks, language
