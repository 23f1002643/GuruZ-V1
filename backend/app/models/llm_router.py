"""LLM Router: NVIDIA NIM (primary) → Groq (fallback)."""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

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
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.nvidia_base_url}/models",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
            )
            return response.status_code == 200
    except Exception as exc:
        logger.warning("nvidia_check_failed", error=str(exc))
        return False


async def _check_groq() -> bool:
    """Return True if the Groq API key is configured and reachable."""
    settings = get_settings()
    if not settings.groq_api_key:
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            return response.status_code == 200
    except Exception as exc:
        logger.warning("groq_check_failed", error=str(exc))
        return False


async def resolve_provider() -> str:
    """Determine the active provider from current configuration.

    NVIDIA is preferred in auto mode, but Groq is selected only if NVIDIA is unavailable.
    """
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "nvidia":
        nvidia_ok = await _check_nvidia()
        _llm_status["nvidia"] = "available" if nvidia_ok else "unavailable"
        _llm_status["groq"] = "unknown"
        _llm_status["active"] = "nvidia" if nvidia_ok else "none"
        if not nvidia_ok:
            logger.warning("nvidia_unavailable", active_provider="none")
            return "none"
        return "nvidia"

    if provider == "groq":
        groq_ok = await _check_groq()
        _llm_status["groq"] = "available" if groq_ok else "unavailable"
        _llm_status["nvidia"] = "unknown"
        _llm_status["active"] = "groq" if groq_ok else "none"
        if not groq_ok:
            logger.warning("groq_unavailable", active_provider="none")
            return "none"
        return "groq"

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
    """Async LLM router with NVIDIA primary and Groq fallback."""

    _NVIDIA_RETRIES = 3
    _NVIDIA_RETRY_BASE = 1.5
    _NVIDIA_MIN_PROMPT_LENGTH = 64
    _NVIDIA_SHRINK_FACTOR = 0.7

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        retries: int = 3,
    ) -> str:
        """Generate text with the configured provider and fallback rules."""
        provider = await resolve_provider()
        logger.info("calling_provider", provider=provider)

        if provider == "none":
            raise RuntimeError("No LLM provider is available. Check NVIDIA or Groq configuration.")

        if provider == "nvidia":
            try:
                return await self._generate_with_nvidia(
                    prompt, system, temperature, max_tokens, retries
                )
            except Exception as exc:
                if self._should_fallback_to_groq(exc):
                    groq_ok = await _check_groq()
                    if groq_ok:
                        logger.info(
                            "provider_fallback",
                            from_provider="nvidia",
                            to_provider="groq",
                        )
                        return await self._generate_with_groq(
                            prompt, system, temperature, max_tokens, retries
                        )
                raise

        if provider == "groq":
            return await self._generate_with_groq(
                prompt, system, temperature, max_tokens, retries
            )

        raise RuntimeError(f"Unsupported LLM provider: {provider}")

    async def _generate_with_nvidia(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        retries: int,
    ) -> str:
        """Retry NVIDIA for 429/413 and only fall back for network/auth/5xx failures."""
        current_prompt = prompt

        for attempt in range(retries):
            try:
                return await self._call_nvidia(current_prompt, system, temperature, max_tokens)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                logger.info("provider_response", provider="nvidia", status=status)

                if status == 429:
                    delay = self._get_retry_delay(exc.response.headers, attempt)
                    logger.warning(
                        "provider_retry",
                        provider="nvidia",
                        reason=f"rate_limit retry_after={delay}",
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(delay)
                    continue

                if status == 413:
                    next_prompt = self._shrink_prompt(current_prompt)
                    if next_prompt is None:
                        raise RuntimeError(
                            "NVIDIA payload too large and prompt cannot be reduced further."
                        ) from exc
                    logger.warning(
                        "provider_retry",
                        provider="nvidia",
                        reason="payload_too_large reducing_prompt_size",
                        attempt=attempt + 1,
                    )
                    current_prompt = next_prompt
                    continue

                raise
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                logger.warning(
                    "provider_retry",
                    provider="nvidia",
                    reason=str(exc),
                    attempt=attempt + 1,
                )
                raise

        raise RuntimeError("NVIDIA generation failed after repeated retry attempts.")

    async def _generate_with_groq(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        retries: int,
    ) -> str:
        """Use Groq when NVIDIA has failed over or when Groq is the configured provider."""
        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                return await self._call_groq(prompt, system, temperature, max_tokens)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "provider_retry",
                    provider="groq",
                    reason=str(exc),
                    attempt=attempt + 1,
                )
                await asyncio.sleep(self._get_retry_delay({}, attempt))

        raise RuntimeError(f"Groq generation failed after {retries} attempts: {last_error}")

    async def _call_nvidia(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call NVIDIA's /chat/completions endpoint using the configured NVIDIA base URL."""
        settings = get_settings()
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json",
        }

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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.nvidia_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            logger.info(
                "provider_response",
                provider="nvidia",
                status=response.status_code,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("NVIDIA returned an empty response.")
        return content

    async def _call_groq(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Groq's OpenAI-compatible /chat/completions endpoint."""
        settings = get_settings()
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }

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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            logger.info(
                "provider_response",
                provider="groq",
                status=response.status_code,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("Groq returned an empty response.")
        return content

    def _get_retry_delay(self, headers: dict[str, str], attempt: int) -> float:
        """Compute delay by honoring Retry-After or using exponential backoff."""
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.5, float(retry_after))
            except ValueError:
                pass

        delay = self._NVIDIA_RETRY_BASE * (2 ** attempt)
        return min(delay, 10.0)

    def _shrink_prompt(self, prompt: str) -> Optional[str]:
        """Reduce prompt length when NVIDIA returns payload-too-large."""
        if len(prompt) <= self._NVIDIA_MIN_PROMPT_LENGTH:
            return None

        next_length = max(
            self._NVIDIA_MIN_PROMPT_LENGTH,
            int(len(prompt) * self._NVIDIA_SHRINK_FACTOR),
        )
        if next_length >= len(prompt):
            return None

        return f"...{prompt[-next_length:]}"

    def _should_fallback_to_groq(self, exc: Exception) -> bool:
        """Fall back to Groq only on network/auth/5xx failures, not 413/429."""
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.RequestError):
            return True

        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status in {401, 403}:
                return True
            if 500 <= status < 600:
                return True
        return False

    def reset(self) -> None:
        """Reset is a no-op because no persistent provider is cached."""
        return None


# Module-level singleton
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
