"""LLM Router: Grok (primary) → Gemini → Ollama with auto-detection."""
from __future__ import annotations
import asyncio
from typing import Any, Optional
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_llm_status: dict[str, str] = {
    "grok": "unknown",
    "gemini": "unknown",
    "ollama": "unknown",
    "active": "unknown",
}


def get_llm_status() -> dict[str, str]:
    return dict(_llm_status)


async def _check_grok() -> bool:
    """Return True if Grok (xAI) API key is configured and reachable."""
    settings = get_settings()
    if not settings.grok_api_key:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.x.ai/v1/models",
                headers={"Authorization": f"Bearer {settings.grok_api_key}"},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning("grok_check_failed", error=str(e))
        return False


async def _check_gemini() -> bool:
    """Return True if Gemini API is reachable."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return False
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        response = model.generate_content(
            "Say 'ok'",
            generation_config=genai.GenerationConfig(max_output_tokens=5),
        )
        return bool(response.text)
    except Exception as e:
        logger.warning("gemini_check_failed", error=str(e))
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
            return [model["name"] for model in data.get("models", []) if isinstance(model, dict) and "name" in model]
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

    supported_aliases = [
        ["qwen3", "qwen3:latest", "qwen3:all"],
        ["gemma3", "gemma3:latest", "gemma3:all"],
        ["llama3", "llama3:latest", "llama3:all"],
    ]

    for alias_group in supported_aliases:
        for alias in alias_group:
            if alias in available_models:
                return alias

    # Fall back to the first available local Ollama model
    return available_models[0]


async def resolve_provider() -> str:
    """Determine the active LLM provider based on config and availability."""
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "grok":
        ok = await _check_grok()
        _llm_status["grok"] = "available" if ok else "unavailable"
        _llm_status["active"] = "grok"
        return "grok"

    if provider == "gemini":
        ok = await _check_gemini()
        _llm_status["gemini"] = "available" if ok else "unavailable"
        _llm_status["active"] = "gemini"
        return "gemini"

    if provider == "ollama":
        ok = await _check_ollama()
        _llm_status["ollama"] = "available" if ok else "unavailable"
        _llm_status["active"] = "ollama"
        return "ollama"

    # auto: try Grok first, then Gemini, then Ollama
    grok_ok, gemini_ok, ollama_ok = await asyncio.gather(
        _check_grok(), _check_gemini(), _check_ollama()
    )
    _llm_status["grok"] = "available" if grok_ok else "unavailable"
    _llm_status["gemini"] = "available" if gemini_ok else "unavailable"
    _llm_status["ollama"] = "available" if ollama_ok else "unavailable"

    if grok_ok:
        _llm_status["active"] = "grok"
        return "grok"
    if gemini_ok:
        _llm_status["active"] = "gemini"
        return "gemini"
    if ollama_ok:
        _llm_status["active"] = "ollama"
        return "ollama"

    logger.error("no_llm_available")
    _llm_status["active"] = "none"
    return "none"


class LLMRouter:
    """Async LLM client that routes to Grok, Gemini, or Ollama transparently."""

    def __init__(self) -> None:
        self._provider: Optional[str] = None

    async def _ensure_provider(self) -> str:
        if self._provider is None:
            self._provider = await resolve_provider()
        return self._provider

    async def generate(self, prompt: str, system: str = "",
                       temperature: float = 0.1, max_tokens: int = 4096,
                       retries: int = 3) -> str:
        """Generate text from the active LLM with retry logic."""
        provider = await self._ensure_provider()
        last_error: Exception = RuntimeError("No LLM available")

        for attempt in range(retries):
            try:
                if provider == "grok":
                    result = await self._call_grok(prompt, system, temperature, max_tokens)
                    return result
                elif provider == "gemini":
                    result = await self._call_gemini(prompt, system, temperature, max_tokens)
                    return result
                elif provider == "ollama":
                    result = await self._call_ollama(prompt, system, temperature, max_tokens)
                    return result
                else:
                    raise RuntimeError("No LLM provider available. Configure GROK_API_KEY, GEMINI_API_KEY, or start Ollama.")
            except Exception as e:
                last_error = e
                logger.warning("llm_attempt_failed", attempt=attempt + 1,
                               provider=provider, error=str(e))
                if attempt < retries - 1:
                    # Try switching provider on failure (Grok -> Gemini -> Ollama)
                    if provider == "grok":
                        gemini_ok, ollama_ok = await asyncio.gather(
                            _check_gemini(), _check_ollama()
                        )
                        if gemini_ok:
                            provider = "gemini"
                            self._provider = "gemini"
                        elif ollama_ok:
                            provider = "ollama"
                            self._provider = "ollama"
                    elif provider == "gemini":
                        ollama_ok = await _check_ollama()
                        if ollama_ok:
                            provider = "ollama"
                            self._provider = "ollama"
                    await asyncio.sleep(1.5 ** attempt)

        raise RuntimeError(f"LLM generation failed after {retries} attempts: {last_error}")

    async def _call_grok(self, prompt: str, system: str,
                         temperature: float, max_tokens: int) -> str:
        """Call Grok via xAI's OpenAI-compatible API."""
        settings = get_settings()
        import httpx

        url = "https://api.x.ai/v1/chat/completions"
        payload = {
            "model": settings.grok_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.grok_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("Grok returned an empty response.")
        return content

    async def _call_gemini(self, prompt: str, system: str,
                            temperature: float, max_tokens: int) -> str:
        settings = get_settings()
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=settings.gemini_api_key)

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        model = genai.GenerativeModel(settings.gemini_model)
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    async def _call_ollama(self, prompt: str, system: str,
                            temperature: float, max_tokens: int) -> str:
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
