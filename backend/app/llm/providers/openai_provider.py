"""
OpenAI (GPT-4o / GPT-4o-mini) LLM provider.
Uses the Chat Completions API with JSON mode.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.base import ExtractionResult, LLMProvider
from app.llm.schema import build_extraction_prompt, parse_llm_response

log = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float, timeout: int):
        try:
            from openai import OpenAI as _OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self._client = _OpenAI(api_key=api_key, timeout=float(timeout))
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def extract(self, text: str, custom_parameters: list[dict]) -> ExtractionResult:
        system_prompt, user_prompt = build_extraction_prompt(text, custom_parameters)

        log.info(f"Calling OpenAI {self.model} for extraction…")
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            raw_text = response.choices[0].message.content or ""
            log.debug(f"OpenAI raw response length: {len(raw_text)}")
        except Exception as e:
            log.error(f"OpenAI API call failed: {e}")
            raise

        raw_json = _extract_json(raw_text)
        return parse_llm_response(raw_json)


def _extract_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code fences."""
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
