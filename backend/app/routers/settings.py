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
    llm_provider: Optional[Literal["auto", "gemini", "ollama"]] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    gemini_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    max_retry_attempts: Optional[int] = None
    period_duration_minutes: Optional[int] = None
    default_language: Optional[str] = None


@router.get("")
async def get_settings_endpoint():
    """Return current platform settings."""
    s = get_settings()
    return {
        "llm_provider": _overrides.get("llm_provider", s.llm_provider),
        "ollama_model": _overrides.get("ollama_model", s.ollama_model),
        "ollama_base_url": _overrides.get("ollama_base_url", s.ollama_base_url),
        "gemini_model": _overrides.get("gemini_model", s.gemini_model),
        "chunk_size": _overrides.get("chunk_size", s.chunk_size),
        "chunk_overlap": _overrides.get("chunk_overlap", s.chunk_overlap),
        "max_retry_attempts": _overrides.get("max_retry_attempts", s.max_retry_attempts),
        "period_duration_minutes": _overrides.get("period_duration_minutes", s.period_duration_minutes),
        "default_language": _overrides.get("default_language", s.default_language),
    }


@router.patch("")
async def update_settings_endpoint(update: SettingsUpdate):
    """Partially update platform settings (runtime only, not persisted to disk)."""
    data = update.model_dump(exclude_none=True)
    _overrides.update(data)

    # If LLM provider changed, reset the router so it re-detects
    if "llm_provider" in data:
        get_settings().llm_provider = data["llm_provider"]  # type: ignore[assignment]
        get_llm_router().reset()
        logger.info("settings_updated", changes=data)

    return await get_settings_endpoint()
