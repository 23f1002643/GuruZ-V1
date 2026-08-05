"""Base agent class providing prompt execution and JSON extraction utilities."""
from __future__ import annotations
import json
import re
from typing import Any
from app.models.llm_router import LLMRouter, get_llm_router
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _try_parse_json(candidate: str) -> Any:
    candidate = candidate.strip()
    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    try:
        result, _ = decoder.raw_decode(candidate)
        return result
    except (ValueError, json.JSONDecodeError):
        pass

    # Try a simple cleanup for trailing commas before a closing object or array.
    repaired = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    try:
        result, _ = decoder.raw_decode(repaired)
        return result
    except (ValueError, json.JSONDecodeError):
        pass

    # Attempt to close truncated JSON structures.
    repaired = _close_json_candidate(candidate)
    if repaired != candidate:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    return None


def _close_json_candidate(candidate: str) -> str:
    candidate = candidate.strip()
    if not candidate:
        return candidate

    def is_escaped(text: str, index: int) -> bool:
        slash_count = 0
        i = index - 1
        while i >= 0 and text[i] == "\\":
            slash_count += 1
            i -= 1
        return slash_count % 2 == 1

    stack: list[str] = []
    in_string = False
    for index, char in enumerate(candidate):
        if char == '"' and not is_escaped(candidate, index):
            in_string = not in_string
            continue

        if in_string:
            continue

        if char in "[{":
            stack.append(char)
        elif char in "]}":
            if not stack:
                continue
            opener = stack[-1]
            if (opener == "{" and char == "}") or (opener == "[" and char == "]"):
                stack.pop()
            else:
                stack.clear()
                break

    if in_string:
        candidate += '"'

    while stack:
        opener = stack.pop()
        candidate += "}" if opener == "{" else "]"

    return candidate


def _find_json_blocks(text: str) -> list[str]:
    blocks: list[str] = []

    # Extract fenced JSON blocks first, allowing missing closing backticks.
    for fence_match in re.finditer(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", text, re.IGNORECASE):
        candidate = fence_match.group(1).strip()
        if candidate:
            blocks.append(candidate)

    # Extract balanced JSON objects/arrays as fallback, ignoring braces inside strings.
    def is_escaped(text: str, index: int) -> bool:
        # Count preceding backslashes.
        slash_count = 0
        i = index - 1
        while i >= 0 and text[i] == "\\":
            slash_count += 1
            i -= 1
        return slash_count % 2 == 1

    stack: list[str] = []
    start_index = None
    in_string = False
    for index, char in enumerate(text):
        if char == '"' and not is_escaped(text, index):
            in_string = not in_string
            continue

        if in_string:
            continue

        if char in "[{":
            if start_index is None:
                start_index = index
            stack.append(char)
        elif char in "]}":
            if not stack:
                continue
            opener = stack.pop()
            if (opener == "{" and char == "}") or (opener == "[" and char == "]"):
                if not stack and start_index is not None:
                    blocks.append(text[start_index:index + 1].strip())
                    start_index = None
            else:
                stack.clear()
                start_index = None

    return blocks


def _cleanup_json_text(text: str) -> str:
    """Normalize and trim an LLM response into a JSON-like candidate."""
    candidate = text.strip()

    # Remove surrounding markdown fences and leading text.
    if "```" in candidate:
        candidate = re.sub(r"```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = candidate.replace("```", "")

    first_json = re.search(r"[\[{]", candidate)
    if first_json:
        candidate = candidate[first_json.start():]

    last_closer = max(candidate.rfind("}"), candidate.rfind("]"))
    if last_closer != -1:
        candidate = candidate[: last_closer + 1]

    return candidate.strip()


def extract_json(text: str) -> Any:
    """Extract the first valid JSON object or array from LLM output."""
    stripped = text.strip()

    # Try direct parse first.
    result = _try_parse_json(stripped)
    if result is not None:
        return result

    # Try fenced and balanced JSON blocks.
    for block in _find_json_blocks(stripped):
        result = _try_parse_json(block)
        if result is not None:
            return result

    # Attempt a cleanup pass for common model formatting issues.
    cleaned = _cleanup_json_text(stripped)
    if cleaned != stripped:
        result = _try_parse_json(cleaned)
        if result is not None:
            return result

    raise ValueError(f"No valid JSON found in LLM output. Output starts with: {stripped[:200]!r}")


class BaseAgent:
    """Shared utilities for all pipeline agents."""

    name: str = "base_agent"
    temperature: float = 0.1
    max_tokens: int = 4096

    def __init__(self) -> None:
        self._router: LLMRouter = get_llm_router()

    async def call_llm(self, prompt: str, system: str = "") -> str:
        """Call the active LLM with retry logic built in."""
        logger.info("agent_call_llm", agent=self.name)
        return await self._router.generate(
            prompt=prompt,
            system=system,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def call_llm_json(self, prompt: str, system: str = "") -> Any:
        """Call LLM and parse the response as JSON."""
        raw = await self.call_llm(prompt, system)
        try:
            return extract_json(raw)
        except ValueError as exc:
            logger.warning(
                "json_parse_failure",
                agent=self.name,
                error=str(exc),
                raw_output=raw[:2000],
            )
            raise

    def build_rag_context(self, chunks: list[str]) -> str:
        """Format retrieved chunks as a context block for prompts."""
        if not chunks:
            return "No relevant content found in the document."
        context_parts = [f"[Chunk {i + 1}]\n{chunk}" for i, chunk in enumerate(chunks)]
        return "\n\n---\n\n".join(context_parts)
