"""Application configuration loaded from environment variables."""
import os
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Configuration
    llm_provider: Literal["auto", "nvidia", "groq"] = "nvidia"

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.3-70b-instruct"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # RAG settings
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Processing
    max_retry_attempts: int = 3
    period_duration_minutes: int = 40
    default_language: str = "English"

    # Storage
    upload_dir: str = "./data/uploads"
    packages_dir: str = "./data/packages"

    # Server
    port: int = 8080
    base_path: str = "/api"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
