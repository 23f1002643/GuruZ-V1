"""LLM Router: NVIDIA NIM (primary) → Groq (fallback)."""
from __future__ import annotations
import asyncio
from typing import Optional
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_llm_status: dict[str, str] = {
    "nvidia": "unknown",
    "groq": "unknown",
    "active": "unknown",
}


def get_llm_status() -> dict[str, str]:
    return dict(_llm_status)


async def _check_nvidia() -> bool:
    """Return True if the NVIDIA API key is configured and reachable."""
    settings = get_settings()
    if not settings.nvidia_api_key:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{settings.nvidia_base_url}/models",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning("nvidia_check_failed", error=str(e))
        return False


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


async def resolve_provider() -> str:
    """Determine the active LLM provider: NVIDIA primary, Groq fallback."""
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "nvidia":
        ok = await _check_nvidia()
        _llm_status["nvidia"] = "available" if ok else "unavailable"
        _llm_status["active"] = "nvidia"
        return "nvidia"

    if provider == "groq":
        ok = await _check_groq()
        _llm_status["groq"] = "available" if ok else "unavailable"
        _llm_status["active"] = "groq"
        return "groq"

    # auto: try NVIDIA first, then Groq
    nvidia_ok, groq_ok = await asyncio.gather(_check_nvidia(), _check_groq())
    _llm_status["nvidia"] = "available" if nvidia_ok else "unavailable"
    _llm_status["groq"] = "available" if groq_ok else "unavailable"

    if nvidia_ok:
        _llm_status["active"] = "nvidia"
        return "nvidia"
    if groq_ok:
        _llm_status["active"] = "groq"
        return "groq"

    logger.error("no_llm_available")
    _llm_status["active"] = "none"
    return "none"


class LLMRouter:
    """Async LLM client: NVIDIA NIM primary, Groq fallback."""

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
                if provider == "nvidia":
                    return await self._call_nvidia(prompt, system, temperature, max_tokens)
                elif provider == "groq":
                    return await self._call_groq(prompt, system, temperature, max_tokens)
                else:
                    raise RuntimeError(
                        "No LLM provider available. Configure NVIDIA_API_KEY or GROQ_API_KEY."
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
                    # NVIDIA failed → fall back to Groq
                    if provider == "nvidia":
                        groq_ok = await _check_groq()
                        if groq_ok:
                            provider = "groq"
                            self._provider = "groq"
                            logger.info("llm_fallback", from_provider="nvidia", to_provider="groq")
                    await asyncio.sleep(1.5 ** attempt)

        raise RuntimeError(f"LLM generation failed after {retries} attempts: {last_error}")

    async def _call_nvidia(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        """Call NVIDIA NIM via its OpenAI-compatible API."""
        settings = get_settings()
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.nvidia_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{settings.nvidia_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("NVIDIA returned an empty response.")
        return content

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
