"""
Extraction prompt and schema builder.
Generates the JSON schema and system/user prompts used by all LLM providers.
Keeping prompts here means changing extraction logic never requires touching
the provider files.
"""
from __future__ import annotations

import json
from typing import Any


# ── Default parameters ─────────────────────────────────────────────────────────
# These are extracted for every paper regardless of user config.
# Role: "input" = controllable variable, "output" = measured result,
#       "material" = material/structure descriptor

DEFAULT_PARAMETERS: list[dict] = [
    # Material information
    {"name": "material",          "label": "Material / Compound",        "unit": "",     "role": "material",  "description": "Chemical formula or name of the main material studied"},
    {"name": "substrate",         "label": "Substrate",                  "unit": "",     "role": "material",  "description": "Substrate material (e.g. SrTiO3, MgO, Si, LAO)"},
    {"name": "crystal_structure", "label": "Crystal Structure / Phase",  "unit": "",     "role": "material",  "description": "Crystal structure or phase (e.g. perovskite, REBCO, infinite-layer)"},
    {"name": "film_geometry",     "label": "Film Geometry",              "unit": "",     "role": "material",  "description": "Thin film, bulk, wire, multilayer, etc."},

    # Input / controllable variables
    {"name": "deposition_method",      "label": "Deposition Method",           "unit": "",     "role": "input",   "description": "PLD, sputtering, MBE, CVD, ALD, etc."},
    {"name": "deposition_temperature", "label": "Deposition Temperature",      "unit": "°C",   "role": "input",   "description": "Substrate temperature during deposition"},
    {"name": "sputtering_power",       "label": "Sputtering Power",            "unit": "W",    "role": "input",   "description": "RF or DC sputtering power"},
    {"name": "working_pressure",       "label": "Working Pressure",            "unit": "Pa",   "role": "input",   "description": "Chamber pressure during deposition"},
    {"name": "gas_composition",        "label": "Gas Composition / Ratio",     "unit": "",     "role": "input",   "description": "Gas mixture and ratios used (e.g. Ar:O2 = 4:1)"},
    {"name": "film_thickness",         "label": "Film Thickness",              "unit": "nm",   "role": "input",   "description": "Thickness of the deposited film"},
    {"name": "annealing_temperature",  "label": "Annealing Temperature",       "unit": "°C",   "role": "input",   "description": "Post-deposition annealing temperature"},
    {"name": "annealing_atmosphere",   "label": "Annealing Atmosphere",        "unit": "",     "role": "input",   "description": "Atmosphere used during annealing (e.g. O2, N2, vacuum)"},
    {"name": "annealing_duration",     "label": "Annealing Duration",          "unit": "min",  "role": "input",   "description": "Duration of annealing"},
    {"name": "oxygen_pressure",        "label": "Oxygen Partial Pressure",     "unit": "Pa",   "role": "input",   "description": "Oxygen partial pressure during growth or annealing"},
    {"name": "laser_fluence",          "label": "Laser Fluence (PLD)",         "unit": "J/cm²","role": "input",   "description": "Laser energy density for PLD"},
    {"name": "target_composition",     "label": "Target Composition",          "unit": "",     "role": "input",   "description": "Composition of sputtering or PLD target"},

    # Output / measured variables
    {"name": "Tc",                "label": "Critical Temperature (Tc)",   "unit": "K",       "role": "output",  "description": "Superconducting critical temperature"},
    {"name": "Tc_onset",          "label": "Tc onset",                    "unit": "K",       "role": "output",  "description": "Onset of superconducting transition"},
    {"name": "delta_Tc",          "label": "Transition Width (ΔTc)",      "unit": "K",       "role": "output",  "description": "Width of the superconducting transition"},
    {"name": "Jc",                "label": "Critical Current Density (Jc)","unit": "A/cm²",  "role": "output",  "description": "Critical current density at specified temperature/field"},
    {"name": "resistivity",       "label": "Normal-state Resistivity",    "unit": "μΩ·cm",   "role": "output",  "description": "Electrical resistivity just above Tc"},
    {"name": "RRR",               "label": "Residual Resistivity Ratio",  "unit": "",        "role": "output",  "description": "RRR = R(300K)/R(Tc+)"},
    {"name": "surface_roughness", "label": "Surface Roughness (RMS)",     "unit": "nm",      "role": "output",  "description": "RMS surface roughness from AFM"},
    {"name": "crystallinity",     "label": "Crystallinity / FWHM",        "unit": "°",       "role": "output",  "description": "XRD rocking curve FWHM as measure of crystallinity"},
    {"name": "lattice_parameter", "label": "Lattice Parameter",           "unit": "Å",       "role": "output",  "description": "Out-of-plane or in-plane lattice constant"},
    {"name": "upper_critical_field","label":"Upper Critical Field (Hc2)",  "unit": "T",       "role": "output",  "description": "Upper critical magnetic field"},
    {"name": "coherence_length",  "label": "Coherence Length (ξ)",        "unit": "nm",      "role": "output",  "description": "Superconducting coherence length"},
    {"name": "penetration_depth", "label": "London Penetration Depth (λ)","unit": "nm",      "role": "output",  "description": "London penetration depth"},
    {"name": "band_gap",          "label": "Band Gap",                    "unit": "eV",      "role": "output",  "description": "Electronic band gap"},
]


def build_extraction_prompt(
    paper_text: str,
    custom_parameters: list[dict],
) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the extraction task.
    Merges DEFAULT_PARAMETERS with user-supplied custom_parameters.
    """
    all_params = DEFAULT_PARAMETERS + [
        p for p in custom_parameters
        if p["name"] not in {d["name"] for d in DEFAULT_PARAMETERS}
    ]

    # Build parameter descriptions grouped by role
    input_params  = [p for p in all_params if p["role"] == "input"]
    output_params = [p for p in all_params if p["role"] == "output"]
    material_params = [p for p in all_params if p["role"] == "material"]

    def param_lines(params: list[dict]) -> str:
        lines = []
        for p in params:
            unit_str = f" [{p['unit']}]" if p.get("unit") else ""
            lines.append(f"  - {p['name']}{unit_str}: {p['description']}")
        return "\n".join(lines)

    # JSON schema for the response
    def field_schema(params: list[dict]) -> dict:
        props = {}
        for p in params:
            props[p["name"]] = {
                "type": "object",
                "properties": {
                    "value":      {"type": ["string", "number", "null"]},
                    "unit":       {"type": ["string", "null"]},
                    "evidence":   {"type": ["string", "null"], "description": "Verbatim quote from the paper"},
                    "page":       {"type": ["integer", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["value", "unit", "evidence", "page", "confidence"],
            }
        return props

    schema = {
        "type": "object",
        "required": ["title", "authors", "journal", "year", "doi", "abstract",
                     "impact_factor", "material_info", "input_variables",
                     "output_variables", "raw_summary"],
        "properties": {
            "title":         {"type": ["string", "null"]},
            "authors":       {"type": "array", "items": {"type": "string"}},
            "journal":       {"type": ["string", "null"]},
            "year":          {"type": ["integer", "null"]},
            "doi":           {"type": ["string", "null"]},
            "abstract":      {"type": ["string", "null"]},
            "impact_factor": {"type": ["number", "null"], "description": "If stated or well-known"},
            "material_info": {
                "type": "object",
                "properties": field_schema(material_params),
            },
            "input_variables": {
                "type": "object",
                "description": "Controllable experimental parameters (inputs for Bayesian optimization)",
                "properties": field_schema(input_params),
            },
            "output_variables": {
                "type": "object",
                "description": "Measured results / outcomes (targets for Bayesian optimization)",
                "properties": field_schema(output_params),
            },
            "raw_summary": {
                "type": "string",
                "description": "3–5 paragraph plain-English summary of the paper",
            },
        },
    }

    system_prompt = (
        "You are an expert research assistant specializing in materials science, "
        "condensed matter physics, and thin-film superconductors. "
        "You extract structured scientific data from research papers with high accuracy. "
        "Return ONLY valid JSON matching the schema exactly. "
        "Use null for fields not mentioned. "
        "Always include verbatim evidence quotes when available. "
        "Confidence is 1.0 for explicit values, 0.7–0.9 for clearly implied, "
        "0.3–0.6 for inferred/estimated."
    )

    user_prompt = f"""Extract structured information from this research paper.

MATERIAL PARAMETERS to extract:
{param_lines(material_params)}

INPUT VARIABLES (controllable experimental parameters):
{param_lines(input_params)}

OUTPUT VARIABLES (measured results — targets for Bayesian optimization):
{param_lines(output_params)}

Return a JSON object matching this schema:
{json.dumps(schema, indent=2)}

PAPER TEXT:
{paper_text[:60000]}"""

    return system_prompt, user_prompt


def parse_llm_response(raw: dict) -> "ExtractionResult":
    """Convert raw LLM JSON dict → ExtractionResult dataclass."""
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
