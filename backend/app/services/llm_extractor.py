"""
LLM-based extraction service using Claude (Anthropic).

SECURITY: The API key is loaded exclusively from server-side environment variables.
It is NEVER exposed to the frontend or logged.

Pipeline:
1. Load prompt templates from /prompts/
2. Chunk long PDFs if needed
3. Call Claude API with retry logic
4. Validate response against Pydantic schema
5. Merge chunk-level extractions into a final normalized record
6. Return LLMExtractionOutput or raise ExtractorError
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import List, Optional

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.extraction import (
    LLMExtractionOutput,
    MaterialEntitySchema,
    ProcessConditionSchema,
    ResultPropertySchema,
    MeasurementMethodSchema,
)
from app.services.pdf_parser import PDFParser, ParsedPDF

log = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class ExtractorError(Exception):
    """Raised when LLM extraction fails in an unrecoverable way."""
    pass


class LLMExtractor:
    """
    Handles LLM-based extraction of structured scientific data.
    All API calls are made server-side only.
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[anthropic.Anthropic] = None
        self._system_prompt: Optional[str] = None
        self._user_template: Optional[str] = None
        self._load_prompts()

    def _get_client(self) -> anthropic.Anthropic:
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            api_key = self.settings.ANTHROPIC_API_KEY
            if not api_key:
                raise ExtractorError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Please set it in your .env file (server-side only)."
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _load_prompts(self) -> None:
        system_file = PROMPTS_DIR / "extraction_system.txt"
        user_file = PROMPTS_DIR / "extraction_user.txt"
        try:
            self._system_prompt = system_file.read_text(encoding="utf-8")
            self._user_template = user_file.read_text(encoding="utf-8")
            log.info("Extraction prompts loaded", system=str(system_file))
        except FileNotFoundError as exc:
            raise ExtractorError(f"Prompt file not found: {exc}") from exc

    def extract(self, parsed_pdf: ParsedPDF) -> LLMExtractionOutput:
        """
        Main entry point: extract structured data from a parsed PDF.
        Handles chunking for long documents.
        """
        text = parsed_pdf.total_text
        chunks = PDFParser().chunk_text(text, self.settings.LLM_MAX_CHUNK_CHARS)

        log.info(
            "Starting LLM extraction",
            model=self.settings.ANTHROPIC_MODEL,
            chunks=len(chunks),
            total_chars=len(text),
        )

        if len(chunks) == 1:
            return self._extract_single(chunks[0])
        else:
            return self._extract_chunked(chunks, parsed_pdf)

    def _extract_single(self, text: str) -> LLMExtractionOutput:
        """Extract from a single-chunk document."""
        raw_json = self._call_llm(text)
        return self._parse_and_validate(raw_json)

    def _extract_chunked(
        self, chunks: List[str], parsed_pdf: ParsedPDF
    ) -> LLMExtractionOutput:
        """
        Multi-chunk extraction strategy:
        1. Extract from each chunk independently (focus on quantitative data).
        2. Run a final merge/consolidation pass.
        3. Return the merged result.
        """
        chunk_results: List[LLMExtractionOutput] = []

        for i, chunk in enumerate(chunks):
            log.info("Extracting chunk", chunk=i + 1, total=len(chunks))
            try:
                result = self._extract_single(chunk)
                chunk_results.append(result)
            except ExtractorError as exc:
                log.warning("Chunk extraction failed", chunk=i + 1, error=str(exc))
                continue

        if not chunk_results:
            raise ExtractorError("All chunks failed to extract")

        merged = self._merge_chunk_results(chunk_results, parsed_pdf)
        log.info("Chunk extraction merged", total_chunks=len(chunk_results))
        return merged

    def _merge_chunk_results(
        self, results: List[LLMExtractionOutput], parsed_pdf: ParsedPDF
    ) -> LLMExtractionOutput:
        """
        Merge multiple chunk-level extraction results into one normalized record.
        Strategy:
        - Use first non-null value for scalar fields (title, abstract, etc.)
        - Deduplicate and combine list fields (materials, process_conditions, etc.)
        - Concatenate summaries
        """
        if len(results) == 1:
            return results[0]

        primary = results[0]

        # Merge summaries
        summaries = [r.summary for r in results if r.summary]
        primary.summary = " ".join(summaries[:3])  # cap at 3 chunks for summary

        # Merge list fields (deduplication by name)
        all_materials = []
        seen_materials = set()
        for r in results:
            for m in r.materials:
                key = (m.name or "").lower()
                if key not in seen_materials:
                    seen_materials.add(key)
                    all_materials.append(m)
        primary.materials = all_materials

        all_conditions = []
        seen_conditions = set()
        for r in results:
            for c in r.process_conditions:
                key = (c.parameter_name or "").lower()
                if key not in seen_conditions:
                    seen_conditions.add(key)
                    all_conditions.append(c)
        primary.process_conditions = all_conditions

        all_methods = []
        seen_methods = set()
        for r in results:
            for m in r.measurement_methods:
                key = (m.technique_name or "").lower()
                if key not in seen_methods:
                    seen_methods.add(key)
                    all_methods.append(m)
        primary.measurement_methods = all_methods

        all_results = []
        seen_results = set()
        for r in results:
            for rp in r.result_properties:
                key = (rp.property_name or "").lower()
                if key not in seen_results:
                    seen_results.add(key)
                    all_results.append(rp)
        primary.result_properties = all_results

        # Merge warnings
        all_warnings = []
        for r in results:
            all_warnings.extend(r.extraction_warnings)
        primary.extraction_warnings = list(set(all_warnings))

        all_review = []
        for r in results:
            all_review.extend(r.fields_needing_review)
        primary.fields_needing_review = list(set(all_review))

        return primary

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIStatusError)),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_llm(self, paper_text: str) -> str:
        """
        Call Claude API. Returns raw JSON string.
        Retries on rate limit / transient errors.
        """
        user_prompt = self._user_template.format(paper_text=paper_text)
        client = self._get_client()

        start = time.time()
        try:
            message = client.messages.create(
                model=self.settings.ANTHROPIC_MODEL,
                max_tokens=self.settings.ANTHROPIC_MAX_TOKENS,
                temperature=self.settings.ANTHROPIC_TEMPERATURE,
                system=self._system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.AuthenticationError as exc:
            raise ExtractorError(
                "Anthropic API authentication failed. Check ANTHROPIC_API_KEY."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ExtractorError(f"Cannot connect to Anthropic API: {exc}") from exc

        elapsed = time.time() - start
        raw = message.content[0].text if message.content else ""

        log.info(
            "LLM call complete",
            model=self.settings.ANTHROPIC_MODEL,
            elapsed_s=round(elapsed, 2),
            input_tokens=message.usage.input_tokens if message.usage else 0,
            output_tokens=message.usage.output_tokens if message.usage else 0,
        )
        return raw

    def _parse_and_validate(self, raw: str) -> LLMExtractionOutput:
        """
        Parse raw LLM output (expected to be JSON) and validate against schema.
        Handles common failure modes gracefully.
        """
        # Strip markdown code fences if present
        json_text = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
        json_text = re.sub(r'```\s*$', '', json_text.strip(), flags=re.MULTILINE)
        json_text = json_text.strip()

        if not json_text:
            raise ExtractorError("LLM returned empty response")

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    raise ExtractorError(
                        f"LLM output is not valid JSON: {exc}. "
                        f"Raw output (first 500 chars): {raw[:500]}"
                    ) from exc
            else:
                raise ExtractorError(
                    f"No JSON found in LLM output. Raw (first 500 chars): {raw[:500]}"
                ) from exc

        try:
            return LLMExtractionOutput.model_validate(data)
        except Exception as exc:
            log.warning("LLM output failed validation, attempting partial recovery", error=str(exc))
            return self._partial_recovery(data, str(exc))

    def _partial_recovery(self, data: dict, error: str) -> LLMExtractionOutput:
        """
        Attempt to construct a partial extraction from malformed LLM output.
        Better to return partial data with warnings than to fail entirely.
        """
        warnings = [f"Validation error (partial extraction): {error}"]

        # Ensure required fields have defaults
        if "summary" not in data or not data.get("summary"):
            data["summary"] = "Extraction incomplete – manual review required."
            warnings.append("summary was missing from LLM output")

        # Sanitize lists that might be None
        for list_field in ["materials", "process_conditions", "measurement_methods",
                           "result_properties", "extraction_warnings", "fields_needing_review"]:
            if not isinstance(data.get(list_field), list):
                data[list_field] = []

        data.setdefault("extraction_warnings", [])
        data["extraction_warnings"].extend(warnings)
        data["fields_needing_review"] = data.get("fields_needing_review", [])
        data["fields_needing_review"].append("full_record")

        try:
            return LLMExtractionOutput.model_validate(data)
        except Exception:
            # Absolute fallback: minimal valid record
            return LLMExtractionOutput(
                summary="Extraction failed – manual review required.",
                extraction_warnings=warnings,
                fields_needing_review=["full_record"],
            )


_extractor: Optional[LLMExtractor] = None


def get_llm_extractor() -> LLMExtractor:
    global _extractor
    if _extractor is None:
        _extractor = LLMExtractor()
    return _extractor
