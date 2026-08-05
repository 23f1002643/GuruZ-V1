"""Document parser: extracts text and structure from PDF, DOCX, PPTX, TXT."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    full_text: str
    pages: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0

    def __post_init__(self) -> None:
        self.word_count = len(self.full_text.split())


def _parse_pdf(path: Path) -> ParsedDocument:
    pages: list[str] = []
    metadata: dict = {}

    try:
        import fitz  # PyMuPDF
    except ModuleNotFoundError:
        # Keep PDF uploads working in environments where PyMuPDF's native
        # wheel is unavailable. pypdf is pure Python and already bundled.
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        raw_meta = reader.metadata or {}
        metadata = {
            "title": raw_meta.get("/Title", "") or "",
            "author": raw_meta.get("/Author", "") or "",
            "subject": raw_meta.get("/Subject", "") or "",
            "creator": raw_meta.get("/Creator", "") or "",
        }
        pages = [page.extract_text() or "" for page in reader.pages]
        logger.warning("pymupdf_unavailable_using_pypdf", filename=path.name)
    else:
        doc = fitz.open(str(path))
        raw_meta = doc.metadata or {}
        metadata = {
            "title": raw_meta.get("title", ""),
            "author": raw_meta.get("author", ""),
            "subject": raw_meta.get("subject", ""),
            "creator": raw_meta.get("creator", ""),
        }
        pages = [page.get_text("text") for page in doc]
        doc.close()

    full_text_parts = pages
    full_text = "\n\n".join(full_text_parts)
    return ParsedDocument(
        filename=path.name,
        file_type="pdf",
        full_text=full_text,
        pages=pages,
        metadata=metadata,
        page_count=len(pages),
    )


def _parse_docx(path: Path) -> ParsedDocument:
    from docx import Document  # type: ignore
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    return ParsedDocument(
        filename=path.name,
        file_type="docx",
        full_text=full_text,
        pages=[full_text],
        metadata={},
        page_count=1,
    )


def _parse_pptx(path: Path) -> ParsedDocument:
    from pptx import Presentation  # type: ignore
    prs = Presentation(str(path))
    slides = []
    for slide in prs.slides:
        texts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                texts.append(shape.text)
        slides.append("\n".join(texts))
    full_text = "\n\n".join(slides)
    return ParsedDocument(
        filename=path.name,
        file_type="pptx",
        full_text=full_text,
        pages=slides,
        metadata={},
        page_count=len(slides),
    )


def _parse_txt(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ParsedDocument(
        filename=path.name,
        file_type="txt",
        full_text=text,
        pages=[text],
        metadata={},
        page_count=1,
    )


PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".pptx": _parse_pptx,
    ".ppt": _parse_pptx,
    ".txt": _parse_txt,
}


def parse_document(path: Path) -> ParsedDocument:
    """Parse a document file and return structured text content."""
    ext = path.suffix.lower()
    parser = PARSERS.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(PARSERS)}")
    logger.info("parsing_document", filename=path.name, file_type=ext)
    doc = parser(path)
    logger.info(
        "document_parsed",
        filename=path.name,
        pages=doc.page_count,
        words=doc.word_count,
    )
    return doc
