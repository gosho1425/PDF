"""
Extraction prompt and schema builder.
Generates the system/user prompts used by all LLM providers.

Key design decisions:
- Text is chunked to stay within safe token limits (Anthropic 200k context,
  but we target <=80k tokens in the user message to leave room for output).
- We estimate tokens as chars/3.5 (conservative for academic English).
- If the paper is very long, we use the first chunk + last chunk strategy
  to capture abstract/intro AND conclusions/results sections.
- A two-pass approach is available for very large papers: first extract
  bibliographic info, then extract measurements.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

# ── Safe limits ────────────────────────────────────────────────────────────────
# Anthropic claude-sonnet context = 200k tokens. We reserve:
#   ~4k  for system prompt
#   ~4k  for schema + instructions in user prompt
#   ~8k  for output (max_tokens setting)
# That leaves ~184k tokens for text, but in practice very long papers cause
# malformed JSON output. 40k token budget for text is much more reliable.
CHARS_PER_TOKEN = 3.5          # conservative estimate for academic English
MAX_TEXT_TOKENS = 40_000       # token budget for the paper text portion
MAX_TEXT_CHARS  = int(MAX_TEXT_TOKENS * CHARS_PER_TOKEN)  # ~140_000 chars

# For 2-pass extraction, use a smaller chunk so both passes fit budget
MAX_TEXT_CHARS_PASS1 = 60_000  # bibliographic pass
MAX_TEXT_CHARS_PASS2 = 100_000 # parameters pass (needs experimental sections)


# ── Default parameters ─────────────────────────────────────────────────────────
DEFAULT_PARAMETERS: list[dict] = [
    # Material information
    {"name": "material",          "label": "Material / Compound",        "unit": "",      "role": "material",  "description": "Chemical formula or name of the main material studied"},
    {"name": "substrate",         "label": "Substrate",                  "unit": "",      "role": "material",  "description": "Substrate material (e.g. SrTiO3, MgO, Si, LAO)"},
    {"name": "crystal_structure", "label": "Crystal Structure / Phase",  "unit": "",      "role": "material",  "description": "Crystal structure or phase (e.g. perovskite, REBCO, infinite-layer)"},
    {"name": "film_geometry",     "label": "Film Geometry",              "unit": "",      "role": "material",  "description": "Thin film, bulk, wire, multilayer, etc."},

    # Input / controllable variables
    {"name": "deposition_method",      "label": "Deposition Method",           "unit": "",      "role": "input",   "description": "PLD, sputtering, MBE, CVD, ALD, etc."},
    {"name": "deposition_temperature", "label": "Deposition Temperature",      "unit": "C",     "role": "input",   "description": "Substrate temperature during deposition"},
    {"name": "sputtering_power",       "label": "Sputtering Power",            "unit": "W",     "role": "input",   "description": "RF or DC sputtering power"},
    {"name": "working_pressure",       "label": "Working Pressure",            "unit": "Pa",    "role": "input",   "description": "Chamber pressure during deposition"},
    {"name": "gas_composition",        "label": "Gas Composition / Ratio",     "unit": "",      "role": "input",   "description": "Gas mixture and ratios used (e.g. Ar:O2 = 4:1)"},
    {"name": "film_thickness",         "label": "Film Thickness",              "unit": "nm",    "role": "input",   "description": "Thickness of the deposited film"},
    {"name": "annealing_temperature",  "label": "Annealing Temperature",       "unit": "C",     "role": "input",   "description": "Post-deposition annealing temperature"},
    {"name": "annealing_atmosphere",   "label": "Annealing Atmosphere",        "unit": "",      "role": "input",   "description": "Atmosphere used during annealing (e.g. O2, N2, vacuum)"},
    {"name": "annealing_duration",     "label": "Annealing Duration",          "unit": "min",   "role": "input",   "description": "Duration of annealing"},
    {"name": "oxygen_pressure",        "label": "Oxygen Partial Pressure",     "unit": "Pa",    "role": "input",   "description": "Oxygen partial pressure during growth or annealing"},
    {"name": "laser_fluence",          "label": "Laser Fluence (PLD)",         "unit": "J/cm2", "role": "input",   "description": "Laser energy density for PLD"},
    {"name": "target_composition",     "label": "Target Composition",          "unit": "",      "role": "input",   "description": "Composition of sputtering or PLD target"},

    # Output / measured variables
    {"name": "Tc",                 "label": "Critical Temperature (Tc)",    "unit": "K",      "role": "output",  "description": "Superconducting critical temperature"},
    {"name": "Tc_onset",           "label": "Tc onset",                     "unit": "K",      "role": "output",  "description": "Onset of superconducting transition"},
    {"name": "delta_Tc",           "label": "Transition Width (dTc)",       "unit": "K",      "role": "output",  "description": "Width of the superconducting transition"},
    {"name": "Jc",                 "label": "Critical Current Density (Jc)","unit": "A/cm2",  "role": "output",  "description": "Critical current density at specified temperature/field"},
    {"name": "resistivity",        "label": "Normal-state Resistivity",     "unit": "uOhm cm","role": "output",  "description": "Electrical resistivity just above Tc"},
    {"name": "RRR",                "label": "Residual Resistivity Ratio",   "unit": "",       "role": "output",  "description": "RRR = R(300K)/R(Tc+)"},
    {"name": "surface_roughness",  "label": "Surface Roughness (RMS)",      "unit": "nm",     "role": "output",  "description": "RMS surface roughness from AFM"},
    {"name": "crystallinity",      "label": "Crystallinity / FWHM",         "unit": "deg",    "role": "output",  "description": "XRD rocking curve FWHM as measure of crystallinity"},
    {"name": "lattice_parameter",  "label": "Lattice Parameter",            "unit": "A",      "role": "output",  "description": "Out-of-plane or in-plane lattice constant"},
    {"name": "upper_critical_field","label": "Upper Critical Field (Hc2)",  "unit": "T",      "role": "output",  "description": "Upper critical magnetic field"},
    {"name": "coherence_length",   "label": "Coherence Length (xi)",        "unit": "nm",     "role": "output",  "description": "Superconducting coherence length"},
    {"name": "penetration_depth",  "label": "London Penetration Depth (L)", "unit": "nm",     "role": "output",  "description": "London penetration depth"},
    {"name": "band_gap",           "label": "Band Gap",                     "unit": "eV",     "role": "output",  "description": "Electronic band gap"},
]


def _truncate_text_smart(text: str, max_chars: int) -> tuple[str, bool]:
    """
    Truncate paper text intelligently.

    For short papers: return full text.
    For long papers: return first 70% + last 30% of the budget, separated
    by a marker. This captures abstract/intro AND conclusions/results.

    Returns (truncated_text, was_truncated).
    """
    if len(text) <= max_chars:
        return text, False

    # Keep first 70% (intro, methods) and last 30% (results, conclusions)
    head_chars = int(max_chars * 0.70)
    tail_chars = max_chars - head_chars

    head = text[:head_chars]
    tail = text[-tail_chars:]

    # Try to break on a newline boundary
    nl = head.rfind("\n", max(0, len(head) - 500))
    if nl > 0:
        head = head[:nl]

    nl2 = tail.find("\n", 0, 500)
    if nl2 >= 0:
        tail = tail[nl2:]

    truncated = (
        head
        + "\n\n[... middle of paper omitted for length ...]\n\n"
        + tail
    )
    log.info(
        f"Text truncated: {len(text):,} chars -> {len(truncated):,} chars "
        f"(~{len(truncated)/CHARS_PER_TOKEN:,.0f} tokens)"
    )
    return truncated, True


def _param_lines(params: list[dict]) -> str:
    lines = []
    for p in params:
        unit_str = f" [{p['unit']}]" if p.get("unit") else ""
        lines.append(f"  - {p['name']}{unit_str}: {p['description']}")
    return "\n".join(lines)


def _field_schema_compact(params: list[dict]) -> dict:
    """Compact field schema — omit verbose descriptions to save tokens."""
    props = {}
    for p in params:
        props[p["name"]] = {
            "type": "object",
            "properties": {
                "value":      {"type": ["string", "number", "null"]},
                "unit":       {"type": ["string", "null"]},
                "evidence":   {"type": ["string", "null"]},
                "page":       {"type": ["integer", "null"]},
                "confidence": {"type": "number"},
            },
        }
    return props


SYSTEM_PROMPT = (
    "You are an expert research assistant specializing in materials science, "
    "condensed matter physics, and thin-film superconductors. "
    "Extract structured scientific data from research papers with high accuracy. "
    "Return ONLY valid JSON. No markdown fences. No commentary. "
    "Use null for fields not found. "
    "Evidence must be a verbatim quote from the text. "
    "Confidence: 1.0=explicit, 0.7-0.9=clearly implied, 0.3-0.6=inferred."
)


def build_extraction_prompt(
    paper_text: str,
    custom_parameters: list[dict],
) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the extraction task.

    Automatically truncates paper_text to fit within the safe token budget.
    Logs a warning if truncation occurs.
    """
    all_params = DEFAULT_PARAMETERS + [
        p for p in custom_parameters
        if p["name"] not in {d["name"] for d in DEFAULT_PARAMETERS}
    ]

    input_params    = [p for p in all_params if p["role"] == "input"]
    output_params   = [p for p in all_params if p["role"] == "output"]
    material_params = [p for p in all_params if p["role"] == "material"]

    # Compact schema (avoids re-repeating long descriptions)
    schema = {
        "title":         "string|null",
        "authors":       ["string"],
        "journal":       "string|null",
        "year":          "integer|null",
        "doi":           "string|null",
        "abstract":      "string|null",
        "impact_factor": "number|null",
        "material_info": _field_schema_compact(material_params),
        "input_variables": _field_schema_compact(input_params),
        "output_variables": _field_schema_compact(output_params),
        "raw_summary":   "string (3-5 paragraph plain-English summary)",
    }

    # Estimate how many chars we can afford for text
    # System prompt ~400 chars, instructions+schema ~3000 chars
    overhead_chars = 400 + len(json.dumps(schema)) + 2000
    available_chars = MAX_TEXT_CHARS - overhead_chars
    available_chars = max(10_000, available_chars)  # floor at 10k

    text_chunk, was_truncated = _truncate_text_smart(paper_text, available_chars)

    truncation_note = ""
    if was_truncated:
        orig_tokens = int(len(paper_text) / CHARS_PER_TOKEN)
        used_tokens = int(len(text_chunk) / CHARS_PER_TOKEN)
        truncation_note = (
            f"\n[NOTE: Paper was {orig_tokens:,} tokens. "
            f"Showing {used_tokens:,} tokens (head+tail). "
            "Middle section omitted. Extract from visible text only.]\n"
        )

    user_prompt = f"""Extract structured information from this research paper.

MATERIAL PARAMETERS to extract:
{_param_lines(material_params)}

INPUT VARIABLES (controllable experimental parameters):
{_param_lines(input_params)}

OUTPUT VARIABLES (measured results):
{_param_lines(output_params)}

Return JSON matching this structure exactly (use null for missing fields):
{json.dumps(schema, indent=2)}
{truncation_note}
PAPER TEXT:
{text_chunk}"""

    return SYSTEM_PROMPT, user_prompt


def parse_llm_response(raw: dict) -> "ExtractionResult":
    """Convert raw LLM JSON dict -> ExtractionResult dataclass."""
    from app.llm.base import ExtractionResult, FieldValue

    def parse_fv(d: Any) -> FieldValue:
        if not isinstance(d, dict):
            return FieldValue(value=d)
        return FieldValue(
            value=d.get("value"),
            unit=d.get("unit"),
            evidence=d.get("evidence"),
            page=d.get("page"),
            confidence=float(d.get("confidence", 1.0)),
        )

    def parse_section(obj: Any) -> dict[str, FieldValue]:
        if not isinstance(obj, dict):
            return {}
        return {k: parse_fv(v) for k, v in obj.items() if v is not None}

    return ExtractionResult(
        title=raw.get("title"),
        authors=raw.get("authors") or [],
        journal=raw.get("journal"),
        year=raw.get("year"),
        doi=raw.get("doi"),
        abstract=raw.get("abstract"),
        impact_factor=raw.get("impact_factor"),
        material_info=parse_section(raw.get("material_info", {})),
        input_variables=parse_section(raw.get("input_variables", {})),
        output_variables=parse_section(raw.get("output_variables", {})),
        raw_summary=raw.get("raw_summary", ""),
    )
