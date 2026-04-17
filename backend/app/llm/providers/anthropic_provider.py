"""
Anthropic (Claude) LLM provider.

Handles:
- API 400 errors (prompt too long, invalid request) with clear messages
- API 429/529 rate limits with exponential backoff retry
- API 500/overloaded errors with retry
- JSON parsing from response
- Token budget estimation before sending
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.llm.base import ExtractionResult, LLMProvider
from app.llm.schema import (
    build_extraction_prompt,
    parse_llm_response,
    CHARS_PER_TOKEN,
    MAX_TEXT_CHARS,
)

log = logging.getLogger(__name__)

# Retry config
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]  # seconds between retries

# Known Anthropic 400 sub-errors and human-readable fixes
_400_HINTS = {
    "prompt is too long": (
        "The combined paper text + prompt exceeded the model's context limit. "
        "The text should have been auto-truncated — this is a bug. "
        "Please report which PDF caused this."
    ),
    "max_tokens": (
        "max_tokens setting is too high for this model. "
        "Try lowering LLM_MAX_TOKENS in backend/.env (e.g. 4096)."
    ),
    "invalid model": (
        "The LLM_MODEL in backend/.env is not recognised by Anthropic. "
        "Valid values: claude-sonnet-4-5, claude-3-5-haiku-20241022, "
        "claude-3-opus-20240229, claude-3-sonnet-20240229"
    ),
    "credit": (
        "Your Anthropic account has no credits remaining. "
        "Add credits at https://console.anthropic.com/settings/billing"
    ),
    "api_key": (
        "The ANTHROPIC_API_KEY in backend/.env is invalid or expired. "
        "Check it at https://console.anthropic.com/settings/api-keys"
    ),
}


def _classify_400(error_body: str) -> str:
    """Return a human-readable explanation for a 400 error."""
    body_lower = error_body.lower()
    for keyword, hint in _400_HINTS.items():
        if keyword in body_lower:
            return hint
    return (
        f"Anthropic API rejected the request (400). Raw error: {error_body[:500]}"
    )


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: int,
    ):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        self._anthropic = _anthropic
        self._client = _anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        log.info(
            f"AnthropicProvider ready — model={model}, "
            f"max_tokens={max_tokens}, timeout={timeout}s"
        )

    def extract(self, text: str, custom_parameters: list[dict]) -> ExtractionResult:
        """
        Extract structured data from paper text.
        Retries on rate-limit / overload errors. Raises with clear message on 400.
        """
        # Pre-check: estimate token count before sending
        estimated_tokens = int(len(text) / CHARS_PER_TOKEN)
        log.info(
            f"Paper text: {len(text):,} chars (~{estimated_tokens:,} tokens). "
            f"Budget: {MAX_TEXT_CHARS:,} chars. "
            f"{'Truncation will apply.' if len(text) > MAX_TEXT_CHARS else 'Within budget.'}"
        )

        system_prompt, user_prompt = build_extraction_prompt(text, custom_parameters)

        prompt_chars = len(system_prompt) + len(user_prompt)
        log.info(
            f"Total prompt: {prompt_chars:,} chars "
            f"(~{int(prompt_chars/CHARS_PER_TOKEN):,} tokens)"
        )

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = RETRY_DELAYS[attempt - 1]
                    log.warning(f"Retry {attempt}/{MAX_RETRIES-1} after {delay}s...")
                    time.sleep(delay)

                log.info(
                    f"Calling Anthropic {self.model} "
                    f"(attempt {attempt+1}/{MAX_RETRIES})..."
                )

                message = self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    timeout=float(self.timeout),
                )

                raw_text = message.content[0].text
                log.info(
                    f"Anthropic response: {len(raw_text)} chars, "
                    f"stop_reason={message.stop_reason}, "
                    f"input_tokens={message.usage.input_tokens}, "
                    f"output_tokens={message.usage.output_tokens}"
                )

                if message.stop_reason == "max_tokens":
                    log.warning(
                        "Response hit max_tokens limit — output may be truncated. "
                        "Attempting to parse partial JSON."
                    )

                raw_json = _extract_json(raw_text)
                return parse_llm_response(raw_json)

            except self._anthropic.BadRequestError as e:
                # 400 — do NOT retry, these are permanent errors
                error_body = str(e)
                human_msg = _classify_400(error_body)
                log.error(f"Anthropic 400 BadRequest: {human_msg}")
                raise ValueError(f"Anthropic API error (400): {human_msg}") from e

            except self._anthropic.AuthenticationError as e:
                # 401 — bad API key, no point retrying
                log.error("Anthropic authentication failed — check ANTHROPIC_API_KEY in .env")
                raise ValueError(
                    "Invalid ANTHROPIC_API_KEY. "
                    "Check backend/.env and verify at https://console.anthropic.com/settings/api-keys"
                ) from e

            except self._anthropic.PermissionDeniedError as e:
                log.error(f"Anthropic permission denied: {e}")
                raise ValueError(
                    "Anthropic API permission denied. "
                    "Your key may not have access to this model."
                ) from e

            except self._anthropic.RateLimitError as e:
                log.warning(f"Anthropic rate limit (attempt {attempt+1}): {e}")
                last_error = e
                # Continue to retry

            except self._anthropic.InternalServerError as e:
                log.warning(f"Anthropic server error (attempt {attempt+1}): {e}")
                last_error = e
                # Continue to retry

            except self._anthropic.APITimeoutError as e:
                log.warning(
                    f"Anthropic timeout after {self.timeout}s (attempt {attempt+1}). "
                    "Consider increasing LLM_TIMEOUT_SECONDS in backend/.env"
                )
                last_error = e
                # Continue to retry

            except self._anthropic.APIConnectionError as e:
                log.warning(f"Anthropic connection error (attempt {attempt+1}): {e}")
                last_error = e
                # Continue to retry

            except Exception as e:
                # Unexpected error — raise immediately
                log.error(f"Unexpected Anthropic error: {e}", exc_info=True)
                raise

        # All retries exhausted
        raise RuntimeError(
            f"Anthropic API failed after {MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        ) from last_error


def _extract_json(text: str) -> dict:
    """
    Extract JSON from LLM response.
    Handles: plain JSON, markdown fences, partial/truncated JSON.
    """
    text = text.strip()

    # 1. Direct parse (most common case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # 4. Try to recover truncated JSON by finding the last complete field
    # (happens when stop_reason == max_tokens)
    if start != -1:
        candidate = text[start:]
        # Walk backwards from end, trying progressively smaller substrings
        for trim_end in range(len(candidate), 0, -100):
            attempt = candidate[:trim_end].rstrip(",\n\r\t ") + "\n}"
            try:
                partial = json.loads(attempt)
                log.warning(
                    "Recovered partial JSON from truncated response. "
                    "Some fields may be missing."
                )
                return partial
            except json.JSONDecodeError:
                pass

    raise ValueError(
        f"Could not parse JSON from LLM response. "
        f"Response starts with: {text[:300]!r}"
    )
