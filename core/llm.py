"""Anthropic Claude client with retries, JSON extraction, and token logging."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.logging_setup import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class LLMError(RuntimeError):
    """Raised when the LLM call or response validation fails."""


class ClaudeClient:
    """Thin production wrapper around the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        temperature: float = 0.4,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.timeout_seconds = timeout_seconds
        self._client: Any = None

    @property
    def available(self) -> bool:
        return bool(self.api_key.strip())

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.available:
                raise LLMError(
                    "ANTHROPIC_API_KEY is not set. Add it to .env or the environment."
                )
            try:
                import anthropic
            except ImportError as exc:
                raise LLMError("anthropic package is not installed") from exc
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
            )
        return self._client

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return assistant text content."""
        client = self._get_client()
        last_err: Exception | None = None
        use_model = model or self.model

        for attempt in range(1, self.max_retries + 1):
            try:
                log.debug(
                    "Claude request model=%s attempt=%d/%d",
                    use_model,
                    attempt,
                    self.max_retries,
                )
                msg = client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=self.temperature if temperature is None else temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = _extract_text(msg)
                usage = getattr(msg, "usage", None)
                if usage is not None:
                    log.info(
                        "Claude usage input_tokens=%s output_tokens=%s model=%s",
                        getattr(usage, "input_tokens", "?"),
                        getattr(usage, "output_tokens", "?"),
                        use_model,
                    )
                return text
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                name = type(exc).__name__
                # Do not retry auth errors
                if "Authentication" in name or "auth" in str(exc).lower() and "api" in str(exc).lower():
                    raise LLMError(f"Claude authentication failed: {exc}") from exc
                if attempt >= self.max_retries:
                    break
                sleep_for = self.retry_backoff_seconds * (2 ** (attempt - 1))
                log.warning(
                    "Claude call failed (%s): %s — retry in %.1fs",
                    name,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)

        raise LLMError(f"Claude call failed after {self.max_retries} attempts: {last_err}")

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        repair_attempts: int = 1,
    ) -> T:
        """
        Call Claude and parse/validate the response as `schema`.

        On validation failure, optionally re-prompts once to repair the JSON.
        """
        raw = self.complete(
            system=system
            + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences, no commentary.",
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            data = extract_json_object(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError, ValueError) as first_err:
            if repair_attempts < 1:
                raise LLMError(f"Invalid JSON from Claude: {first_err}\nRaw: {raw[:800]}") from first_err
            log.warning("JSON validation failed; requesting repair: %s", first_err)
            repair_user = (
                "Your previous response was not valid for the required schema.\n"
                f"Error: {first_err}\n\n"
                "Original request:\n"
                f"{user}\n\n"
                "Previous response:\n"
                f"{raw[:4000]}\n\n"
                "Return corrected JSON only."
            )
            raw2 = self.complete(
                system=system
                + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences.",
                user=repair_user,
                model=model,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            try:
                data2 = extract_json_object(raw2)
                return schema.model_validate(data2)
            except (json.JSONDecodeError, ValidationError, ValueError) as second_err:
                raise LLMError(
                    f"Invalid JSON from Claude after repair: {second_err}\nRaw: {raw2[:800]}"
                ) from second_err


def _extract_text(msg: Any) -> str:
    parts: list[str] = []
    for block in getattr(msg, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "text" or hasattr(block, "text"):
            parts.append(str(getattr(block, "text", "")))
    text = "\n".join(parts).strip()
    if not text:
        raise LLMError("Claude returned empty content")
    return text


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output (raw or fenced)."""
    text = text.strip()
    if not text:
        raise ValueError("empty model output")

    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        raise ValueError(f"expected JSON object, got {type(data).__name__}")
    except json.JSONDecodeError:
        pass

    # Slice from first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
        raise ValueError(f"expected JSON object, got {type(data).__name__}")

    raise json.JSONDecodeError("No JSON object found", text, 0)


def client_from_config(config: Any) -> ClaudeClient:
    llm = config.llm
    return ClaudeClient(
        model=llm.model,
        max_tokens=llm.max_tokens,
        temperature=llm.temperature,
    )
