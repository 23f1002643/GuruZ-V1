"""LLM Router: Groq (primary) → Ollama (fallback)."""
from __future__ import annotations
import asyncio
from typing import Any, Optional
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_llm_status: dict[str, str] = {
    "groq": "unknown",
    "ollama": "unknown",
    "active": "unknown",
}


def get_llm_status() -> dict[str, str]:
    return dict(_llm_status)


async def _check_groq() -> bool:
    """Return True if Groq API key is configured and reachable."""
    settings = get_settings()
    if not settings.groq_api_key:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning("groq_check_failed", error=str(e))
        return False


async def _check_ollama() -> bool:
    """Return True if Ollama is running locally."""
    settings = get_settings()
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception as e:
        logger.warning("ollama_check_failed", error=str(e))
        return False


async def _list_ollama_models() -> list[str]:
    """List models available from the local Ollama instance."""
    settings = get_settings()
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
            data = r.json()
            return [
                model["name"]
                for model in data.get("models", [])
                if isinstance(model, dict) and "name" in model
            ]
    except Exception as e:
        logger.warning("ollama_list_models_failed", error=str(e))
        return []


async def _select_ollama_model() -> Optional[str]:
    settings = get_settings()
    available_models = await _list_ollama_models()
    if not available_models:
        return None
    if settings.ollama_model in available_models:
        return settings.ollama_model

    preferred_aliases = [
        ["llama3", "llama3:latest"],
        ["qwen3", "qwen3:latest"],
        ["gemma3", "gemma3:latest"],
        ["mistral", "mistral:latest"],
    ]
    for alias_group in preferred_aliases:
        for alias in alias_group:
            if alias in available_models:
                return alias

    return available_models[0]


async def resolve_provider() -> str:
    """Determine the active LLM provider: Groq primary, Ollama fallback."""
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "groq":
        ok = await _check_groq()
        _llm_status["groq"] = "available" if ok else "unavailable"
        _llm_status["active"] = "groq"
        return "groq"

    if provider == "ollama":
        ok = await _check_ollama()
        _llm_status["ollama"] = "available" if ok else "unavailable"
        _llm_status["active"] = "ollama"
        return "ollama"

    # auto: try Groq first, then Ollama
    groq_ok, ollama_ok = await asyncio.gather(_check_groq(), _check_ollama())
    _llm_status["groq"] = "available" if groq_ok else "unavailable"
    _llm_status["ollama"] = "available" if ollama_ok else "unavailable"

    if groq_ok:
        _llm_status["active"] = "groq"
        return "groq"
    if ollama_ok:
        _llm_status["active"] = "ollama"
        return "ollama"

    logger.error("no_llm_available")
    _llm_status["active"] = "none"
    return "none"


class LLMRouter:
    """Async LLM client: Groq primary, Ollama fallback."""

    def __init__(self) -> None:
        self._provider: Optional[str] = None

    async def _ensure_provider(self) -> str:
        if self._provider is None:
            self._provider = await resolve_provider()
        return self._provider

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        retries: int = 3,
    ) -> str:
        """Generate text from the active LLM with retry + fallback logic."""
        provider = await self._ensure_provider()
        last_error: Exception = RuntimeError("No LLM available")

        for attempt in range(retries):
            try:
                if provider == "groq":
                    return await self._call_groq(prompt, system, temperature, max_tokens)
                elif provider == "ollama":
                    return await self._call_ollama(prompt, system, temperature, max_tokens)
                else:
                    raise RuntimeError(
                        "No LLM provider available. Configure GROQ_API_KEY or start Ollama."
                    )
            except Exception as e:
                last_error = e
                logger.warning(
                    "llm_attempt_failed",
                    attempt=attempt + 1,
                    provider=provider,
                    error=str(e),
                )
                if attempt < retries - 1:
                    # Groq failed → fall back to Ollama
                    if provider == "groq":
                        ollama_ok = await _check_ollama()
                        if ollama_ok:
                            provider = "ollama"
                            self._provider = "ollama"
                            logger.info("llm_fallback", from_provider="groq", to_provider="ollama")
                    await asyncio.sleep(1.5 ** attempt)

        raise RuntimeError(f"LLM generation failed after {retries} attempts: {last_error}")

    async def _call_groq(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        """Call Groq via its OpenAI-compatible API."""
        settings = get_settings()
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("Groq returned an empty response.")
        return content

    async def _call_ollama(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        settings = get_settings()
        import httpx

        available_models = await _list_ollama_models()
        model_name = settings.ollama_model
        if model_name not in available_models:
            selected_model = await _select_ollama_model()
            if selected_model:
                logger.warning(
                    "ollama_model_selection",
                    requested=model_name,
                    selected=selected_model,
                )
                settings.ollama_model = selected_model
                model_name = selected_model
            else:
                raise RuntimeError("No Ollama models are available locally.")

        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{settings.ollama_base_url}/api/generate", json=payload
            )
            if r.status_code == 404:
                fallback_model = await _select_ollama_model()
                if fallback_model and fallback_model != model_name:
                    logger.warning(
                        "ollama_model_fallback",
                        requested=model_name,
                        fallback=fallback_model,
                    )
                    settings.ollama_model = fallback_model
                    payload["model"] = fallback_model
                    r = await client.post(
                        f"{settings.ollama_base_url}/api/generate", json=payload
                    )
            r.raise_for_status()
            data = r.json()
            response = data.get("response", "")
            if not response or not response.strip():
                raise RuntimeError(
                    f"Ollama returned an empty response for model '{model_name}'."
                )
            return response

    def reset(self) -> None:
        """Force re-detection of provider on next call."""
        self._provider = None


# Module-level singleton
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
