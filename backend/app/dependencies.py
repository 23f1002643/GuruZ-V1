"""FastAPI dependency injection."""
from app.models.llm_router import get_llm_router, LLMRouter
from app.config import get_settings, Settings


def get_llm() -> LLMRouter:
    return get_llm_router()


def get_app_settings() -> Settings:
    return get_settings()
