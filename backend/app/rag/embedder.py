"""Embedding generation — sentence-transformers (lazy-loaded, thread-safe).

KEY FIX FOR RENDER:
  The model (~90 MB) is loaded ONCE at startup via warm_up_embedder() called
  from the FastAPI lifespan.  Loading it mid-request caused a memory spike
  that triggered Render's OOM killer → server restart.

  Loading at startup:
    - happens before any request arrives
    - memory is stable and visible in Render dashboard
    - all subsequent embed_texts / embed_query calls are instant
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import threading
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_FALLBACK_DIMENSIONS = 384

_model = None
_model_lock = threading.Lock()
_load_attempted = False


def _load_model():
    """Load the SentenceTransformer model — blocking, safe to call from any thread."""
    global _model, _load_attempted
    with _model_lock:
        if _load_attempted:
            return _model
        _load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("loading_embedding_model", model=_MODEL_NAME)
            _model = SentenceTransformer(_MODEL_NAME)
            logger.info("embedding_model_loaded", model=_MODEL_NAME)
        except Exception as exc:
            logger.warning(
                "sentence_transformers_unavailable_using_hash_embeddings",
                error=str(exc),
            )
            _model = None
    return _model


def _hash_embed(text: str) -> list[float]:
    """Deterministic lightweight fallback when ML model is unavailable."""
    vector = [0.0] * _FALLBACK_DIMENSIONS
    for token in text.lower().split():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % _FALLBACK_DIMENSIONS
        vector[index] += 1.0 if value & 1 else -1.0
    magnitude = math.sqrt(sum(c * c for c in vector))
    return [c / magnitude for c in vector] if magnitude else vector


def _get_model():
    global _load_attempted
    if not _load_attempted:
        return _load_model()
    return _model


# ── Public API ──────────────────────────────────────────────────────────────

def warm_up_embedder() -> None:
    """
    Pre-load the embedding model at startup.
    Call once from FastAPI lifespan — never from a request handler.
    """
    _load_model()


async def warm_up_embedder_async() -> None:
    """Async wrapper — runs blocking load in the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, warm_up_embedder)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    if model is None:
        return [_hash_embed(t) for t in texts]
    return model.encode(texts, show_progress_bar=False, convert_to_list=True)  # type: ignore


def embed_query(query: str) -> list[float]:
    model = _get_model()
    if model is None:
        return _hash_embed(query)
    return model.encode([query], show_progress_bar=False, convert_to_list=True)[0]  # type: ignore
