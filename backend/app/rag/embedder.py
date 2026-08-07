"""Embedding generation using sentence-transformers (local, no API key needed)."""
from __future__ import annotations
import hashlib
import math
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"
_FALLBACK_DIMENSIONS = 384


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ModuleNotFoundError:
            logger.warning("sentence_transformers_unavailable_using_hash_embeddings")
            return None
        logger.info("loading_embedding_model", model=_MODEL_NAME)

        logger.info("creating_sentence_transformer")  # temp
        
        _model = SentenceTransformer(_MODEL_NAME)

        logger.info("sentence_transformer_created")   #temp
        logger.info("embedding_model_loaded", model=_MODEL_NAME)
    return _model


def _hash_embed(text: str) -> list[float]:
    """Create a stable, lightweight embedding when the ML model is unavailable."""
    vector = [0.0] * _FALLBACK_DIMENSIONS
    for token in text.lower().split():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % _FALLBACK_DIMENSIONS
        vector[index] += 1.0 if value & 1 else -1.0

    magnitude = math.sqrt(sum(component * component for component in vector))
    return [component / magnitude for component in vector] if magnitude else vector


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts."""
    model = _get_model()
    if model is None:
        return [_hash_embed(text) for text in texts]
    logger.info("encoding_started", chunks=len(texts)) #temp
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_list=True)
    logger.info("encoding_finished")  #temp
    return embeddings  # type: ignore[return-value]


def embed_query(query: str) -> list[float]:
    """Return embedding for a single query string."""
    model = _get_model()
    if model is None:
        return _hash_embed(query)
    embedding = model.encode([query], show_progress_bar=False, convert_to_list=True)
    return embedding[0]  # type: ignore[return-value]
