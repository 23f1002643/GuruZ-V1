"""ChromaDB vector store: index chunks and retrieve by semantic similarity."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from app.config import get_settings
from app.rag.chunker import TextChunk
from app.rag.embedder import embed_texts, embed_query
from app.utils.logger import get_logger

logger = get_logger(__name__)

_chroma_client = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb  # type: ignore
        settings = get_settings()
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        logger.info("chromadb_initialized", persist_dir=str(persist_dir))
    return _chroma_client


def get_chroma_status() -> str:
    try:
        client = _get_client()
        client.heartbeat()
        return "available"
    except Exception as e:
        return f"unavailable: {e}"


def index_chunks(job_id: str, chunks: list[TextChunk]) -> str:
    """Index all chunks from a document into a dedicated ChromaDB collection."""
    collection_name = f"doc_{job_id.replace('-', '_')}"
    client = _get_client()

    # Delete existing collection for this job (re-index)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    if not chunks:
        return collection_name

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)
    ids = [c.chunk_id for c in chunks]
    metadatas = [
        {"char_start": c.char_start, "char_end": c.char_end, "page_hint": c.page_hint}
        for c in chunks
    ]

    # ChromaDB has a max batch size
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],  # type: ignore[arg-type]
            documents=texts[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    logger.info("chunks_indexed", collection=collection_name, count=len(chunks))
    return collection_name


def retrieve(job_id: str, query: str, top_k: int = 8) -> list[str]:
    """Retrieve the top-k most relevant chunks for a query."""
    collection_name = f"doc_{job_id.replace('-', '_')}"
    client = _get_client()

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        logger.warning("collection_not_found", collection=collection_name)
        return []

    query_embedding = embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],  # type: ignore[arg-type]
        n_results=min(top_k, collection.count()),
    )

    documents: list[str] = []
    if results and results.get("documents"):
        for doc_list in results["documents"]:
            documents.extend(doc_list)

    return documents


def retrieve_all(job_id: str, max_chunks: int = 60) -> list[str]:
    """Return a large sample of all chunks (for broad knowledge extraction)."""
    collection_name = f"doc_{job_id.replace('-', '_')}"
    client = _get_client()
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()
        results = collection.get(limit=min(max_chunks, count))
        return results.get("documents", []) or []
    except Exception as e:
        logger.warning("retrieve_all_failed", error=str(e))
        return []


def delete_collection(job_id: str) -> None:
    """Remove a job's ChromaDB collection."""
    collection_name = f"doc_{job_id.replace('-', '_')}"
    try:
        _get_client().delete_collection(collection_name)
    except Exception:
        pass
