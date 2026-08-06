"""Platform settings endpoints — runtime read and partial update."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Literal
from app.config import get_settings
from app.models.llm_router import get_llm_router
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

# In-memory overrides (persist within process lifetime)
_overrides: dict = {}


class SettingsUpdate(BaseModel):
    llm_provider: Optional[Literal["auto", "nvidia", "groq"]] = None
    nvidia_model: Optional[str] = None
    groq_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    max_retry_attempts: Optional[int] = None
    period_duration_minutes: Optional[int] = None
    default_language: Optional[str] = None
    max_generation_tokens: Optional[int] = None
    top_k_retrieval_chunks: Optional[int] = None
    max_context_chars: Optional[int] = None
    teacher_script_length: Optional[Literal["short", "medium", "long"]] = None
    lesson_detail_level: Optional[Literal["concise", "balanced", "detailed"]] = None
    creativity_temperature: Optional[float] = None
    strict_rag_mode: Optional[bool] = None
    enable_mentor_story: Optional[bool] = None
    enable_diagrams: Optional[bool] = None
    enable_formulas: Optional[bool] = None


@router.get("")
async def get_settings_endpoint():
    """Return current platform settings."""
    s = get_settings()
    return {
        "llm_provider": _overrides.get("llm_provider", s.llm_provider),
        "nvidia_model": _overrides.get("nvidia_model", s.nvidia_model),
        "groq_model": _overrides.get("groq_model", s.groq_model),
        "chunk_size": _overrides.get("chunk_size", s.chunk_size),
        "chunk_overlap": _overrides.get("chunk_overlap", s.chunk_overlap),
        "max_retry_attempts": _overrides.get("max_retry_attempts", s.max_retry_attempts),
        "period_duration_minutes": _overrides.get("period_duration_minutes", s.period_duration_minutes),
        "default_language": _overrides.get("default_language", s.default_language),
        "max_generation_tokens": _overrides.get("max_generation_tokens", s.max_generation_tokens),
        "top_k_retrieval_chunks": _overrides.get("top_k_retrieval_chunks", s.top_k_retrieval_chunks),
        "max_context_chars": _overrides.get("max_context_chars", s.max_context_chars),
        "teacher_script_length": _overrides.get("teacher_script_length", s.teacher_script_length),
        "lesson_detail_level": _overrides.get("lesson_detail_level", s.lesson_detail_level),
        "creativity_temperature": _overrides.get("creativity_temperature", s.creativity_temperature),
        "strict_rag_mode": _overrides.get("strict_rag_mode", s.strict_rag_mode),
        "enable_mentor_story": _overrides.get("enable_mentor_story", s.enable_mentor_story),
        "enable_diagrams": _overrides.get("enable_diagrams", s.enable_diagrams),
        "enable_formulas": _overrides.get("enable_formulas", s.enable_formulas),
    }


@router.patch("")
async def update_settings_endpoint(update: SettingsUpdate):
    """Partially update platform settings (runtime only, not persisted to disk)."""
    data = update.model_dump(exclude_none=True)
    _overrides.update(data)

    # Apply runtime updates directly to the in-memory settings object.
    settings = get_settings()
    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    # If LLM provider changed, reset the router so it re-detects
    if "llm_provider" in data:
        get_llm_router().reset()

    logger.info("settings_updated", changes=data)
    return await get_settings_endpoint()
