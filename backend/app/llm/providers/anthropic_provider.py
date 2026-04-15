"""
Anthropic (Claude) LLM provider.
Uses the Messages API with JSON mode via a structured system prompt.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.base import ExtractionResult, LLMProvider
from app.llm.schema import build_extraction_prompt, parse_llm_response

log = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float, timeout: int):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self._client = _anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    def extract(self, text: str, custom_parameters: list[dict]) -> ExtractionResult:
        system_prompt, user_prompt = build_extraction_prompt(text, custom_parameters)

        log.info(f"Calling Anthropic {self.model} for extraction…")
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=float(self.timeout),
            )
            raw_text = message.content[0].text
            log.debug(f"Anthropic raw response length: {len(raw_text)}")
        except Exception as e:
            log.error(f"Anthropic API call failed: {e}")
            raise

        raw_json = _extract_json(raw_text)
        return parse_llm_response(raw_json)


def _extract_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code fences."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:500]}")
