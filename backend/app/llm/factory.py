"""
LLM provider factory.
Returns the correct provider based on LLM_PROVIDER setting.
Adding a new provider only requires:
  1. Create providers/myprovider.py implementing LLMProvider
  2. Add a branch here
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.llm.base import LLMProvider

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    from app.core.config import get_settings
    s = get_settings()

    provider = s.LLM_PROVIDER.lower()
    log.info(f"LLM provider: {provider}, model: {s.LLM_MODEL}")

    if provider == "anthropic":
        from app.llm.providers.anthropic_provider import AnthropicProvider
        if not s.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )
        return AnthropicProvider(
            api_key=s.ANTHROPIC_API_KEY,
            model=s.LLM_MODEL,
            max_tokens=s.LLM_MAX_TOKENS,
            temperature=s.LLM_TEMPERATURE,
            timeout=s.LLM_TIMEOUT_SECONDS,
        )

    elif provider == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        if not s.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")
        return OpenAIProvider(
            api_key=s.OPENAI_API_KEY,
            model=s.LLM_MODEL,
            max_tokens=s.LLM_MAX_TOKENS,
            temperature=s.LLM_TEMPERATURE,
            timeout=s.LLM_TIMEOUT_SECONDS,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Supported: 'anthropic', 'openai'."
        )
