"""Semantic chunking: split document text into meaningful chunks with overlap."""
from __future__ import annotations
from dataclasses import dataclass
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    page_hint: int = 0
    char_start: int = 0
    char_end: int = 0

    def __len__(self) -> int:
        return len(self.text)


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    source_id: str = "doc",
) -> list[TextChunk]:
    """
    Split text into overlapping chunks by sentence boundaries.

    Strategy:
    1. Split on paragraph/sentence boundaries.
    2. Accumulate sentences into chunks up to chunk_size words.
    3. Maintain overlap of chunk_overlap words between consecutive chunks.
    """
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # Split into sentences/paragraphs
    import re
    # Split on double newlines (paragraph) or sentence-ending punctuation
    segments = re.split(r"\n{2,}|(?<=[.!?])\s+", text)
    segments = [s.strip() for s in segments if s.strip()]

    chunks: list[TextChunk] = []
    current_words: list[str] = []
    char_cursor = 0
    chunk_idx = 0

    for seg in segments:
        seg_words = seg.split()
        if not seg_words:
            continue

        current_words.extend(seg_words)

        # Emit one or more chunks when we have enough words.
        while len(current_words) >= chunk_size:
            chunk_text_str = " ".join(current_words[:chunk_size])
            chunks.append(TextChunk(
                chunk_id=f"{source_id}_chunk_{chunk_idx}",
                text=chunk_text_str,
                char_start=char_cursor,
                char_end=char_cursor + len(chunk_text_str),
            ))
            chunk_idx += 1
            char_cursor += len(chunk_text_str)
            overlap_count = min(chunk_overlap, chunk_size)
            current_words = current_words[chunk_size - overlap_count:]

    # Flush remaining words as final chunk
    if current_words:
        chunk_text_str = " ".join(current_words)
        chunks.append(TextChunk(
            chunk_id=f"{source_id}_chunk_{chunk_idx}",
            text=chunk_text_str,
            char_start=char_cursor,
            char_end=char_cursor + len(chunk_text_str),
        ))

    logger.info(
        "text_chunked",
        source_id=source_id,
        total_chunks=len(chunks),
        chunk_size=chunk_size,
    )
    return chunks
