"""
data_collector.py — gather and normalise data for the BO engine.

Two sources of truth:
  1. Literature data  — extracted from PDFs, stored in Paper.extraction JSON
  2. User experiments — stored in UserExperiment rows

Both are merged into a unified DataFrame with clearly labelled source_type.
The normalisation layer handles:
  - unit aliasing
  - string-to-float coercion
  - confidence filtering (skip low-confidence literature values)
  - categorical encoding (label encoding for now, one-hot later)
  - outlier capping at [mean ± 4σ] per variable
  - [0, 1] min-max scaling per variable
"""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.optimization import (
    OptimizationProject, ProjectVariable, UserExperiment,
    VariableRole, VariableType, SourceType,
)
from app.models.paper import Paper, PaperStatus

log = logging.getLogger(__name__)

# Minimum confidence to include a literature data point
MIN_CONFIDENCE = 0.5


# ── Unit aliases ──────────────────────────────────────────────────────────────
# Map common alternative spellings to a canonical unit string.
# Values are already stored with the extraction unit, but papers are inconsistent.
UNIT_ALIASES: dict[str, str] = {
    # Temperature
    "k": "K", "kelvin": "K",
    "c": "C", "celsius": "C", "deg c": "C", "°c": "C",
    # Pressure
    "pa": "Pa", "mpa": "MPa", "torr": "Torr", "mbar": "mbar",
    "mtorr": "mTorr",
    # Current density
    "a/cm2": "A/cm2", "a/cm²": "A/cm2", "ma/cm2": "mA/cm2",
    "ga/m2": "GA/m2",
    # Resistivity
    "uohm cm": "uOhm cm", "μohm cm": "uOhm cm", "mohm cm": "mOhm cm",
    "ohm cm": "Ohm cm",
    # Length
    "nm": "nm", "um": "um", "μm": "um", "angstrom": "A", "å": "A",
    # Power
    "w": "W",
    # Other
    "deg": "deg", "°": "deg", "j/cm2": "J/cm2",
}


def _canonical_unit(u: Optional[str]) -> Optional[str]:
    if not u:
        return u
    return UNIT_ALIASES.get(u.strip().lower(), u.strip())


def _to_float(val: Any) -> Optional[float]:
    """Try to convert an arbitrary value to float. Return None on failure."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if math.isfinite(float(val)) else None
    if isinstance(val, str):
        val = val.strip()
        # remove trailing units like "92 K" → try "92"
        parts = val.split()
        for candidate in [parts[0]] if parts else []:
            try:
                f = float(candidate.replace(",", "."))
                return f if math.isfinite(f) else None
            except ValueError:
                pass
    return None


def _extract_field_value(field_dict: Any) -> tuple[Optional[float], Optional[str], float]:
    """
    Pull (numeric_value, unit, confidence) from a FieldValue dict.
    Works with both the full dict format and bare scalars.
    """
    if not isinstance(field_dict, dict):
        return _to_float(field_dict), None, 1.0
    value    = _to_float(field_dict.get("value"))
    unit     = _canonical_unit(field_dict.get("unit"))
    conf     = float(field_dict.get("confidence", 1.0))
    return value, unit, conf


# ── Literature data collector ─────────────────────────────────────────────────

def collect_literature_points(
    db: Session,
    project: OptimizationProject,
    variables: list[ProjectVariable],
) -> list[dict]:
    """
    Return a list of data-point dicts extracted from processed Papers.

    Each dict has keys:
      source_type, paper_id, paper_title, <var_name>, <var_name>_unit, ...

    Only papers whose extraction JSON contains at least one relevant variable
    are included. Low-confidence values (< MIN_CONFIDENCE) are set to None.
    """
    var_names = {v.name for v in variables}
    papers = (
        db.query(Paper)
        .filter(
            Paper.status == PaperStatus.done,
            Paper.extraction.isnot(None),
        )
        .all()
    )

    rows: list[dict] = []
    for paper in papers:
        ext = paper.extraction or {}
        if not isinstance(ext, dict):
            continue

        # Filter by material system if configured
        if project.material_system:
            mat_info = ext.get("material_info", {}) or {}
            mat_field = mat_info.get("material", {})
            mat_val = ""
            if isinstance(mat_field, dict):
                mat_val = str(mat_field.get("value") or "").lower()
            elif mat_field:
                mat_val = str(mat_field).lower()
            system = project.material_system.lower()
            # Simple substring match — could be improved with synonym list
            if system and system not in mat_val and mat_val not in system:
                # Also check title and abstract
                title_text = (paper.title or "").lower()
                abstract_text = (paper.abstract or "").lower()
                if system not in title_text and system not in abstract_text:
                    continue

        row: dict = {
            "source_type":  SourceType.literature.value,
            "paper_id":     paper.id,
            "paper_title":  paper.title or paper.file_name,
            "paper_year":   paper.year,
        }

        # Merge all sections: material_info, input_variables, output_variables, custom_fields
        all_sections = [
            ext.get("material_info", {}),
            ext.get("input_variables", {}),
            ext.get("output_variables", {}),
            ext.get("custom_fields", {}),
        ]

        found_any = False
        for section in all_sections:
            if not isinstance(section, dict):
                continue
            for field_name, field_data in section.items():
                if field_name not in var_names:
                    continue
                val, unit, conf = _extract_field_value(field_data)
                if val is not None and conf >= MIN_CONFIDENCE:
                    row[field_name]            = val
                    row[f"{field_name}_unit"]  = unit
                    row[f"{field_name}_conf"]  = conf
                    found_any = True

        if found_any:
            rows.append(row)

    log.info(
        f"[data_collector] literature: {len(rows)} points from {len(papers)} papers"
        f" (material_system={project.material_system!r})"
    )
    return rows


def collect_user_points(
    db: Session,
    project: OptimizationProject,
) -> list[dict]:
    """
    Return user experiment rows for this project as data-point dicts.
    User experiments are the highest-trust data source.
    """
    experiments = (
        db.query(UserExperiment)
        .filter(
            UserExperiment.project_id == project.id,
            UserExperiment.status == "completed",
        )
        .all()
    )

    rows: list[dict] = []
    for exp in experiments:
        row: dict = {
            "source_type":     SourceType.user_experiment.value,
            "experiment_id":   exp.id,
            "experiment_name": exp.name or f"Run {exp.id[:8]}",
            "run_date":        exp.run_date.isoformat() if exp.run_date else None,
            "notes":           exp.notes,
        }

        for section in [exp.input_values or {}, exp.output_values or {}]:
            if not isinstance(section, dict):
                continue
            for field_name, field_data in section.items():
                if isinstance(field_data, dict):
                    val  = _to_float(field_data.get("value"))
                    unit = field_data.get("unit")
                else:
                    val  = _to_float(field_data)
                    unit = None
                if val is not None:
                    row[field_name]           = val
                    row[f"{field_name}_unit"] = unit
                    row[f"{field_name}_conf"] = 1.0  # user experiments = full trust

        rows.append(row)

    log.info(
        f"[data_collector] user experiments: {len(rows)} completed runs"
    )
    return rows


def build_dataset(
    db: Session,
    project: OptimizationProject,
    variables: list[ProjectVariable],
) -> tuple[list[dict], dict]:
    """
    Merge literature and user data into a unified list of point dicts.

    Returns:
      (points, stats) where stats contains per-variable min/max/mean/std
      computed from the merged dataset (for normalisation reference).
    """
    lit_points  = collect_literature_points(db, project, variables)
    user_points = collect_user_points(db, project)
    all_points  = lit_points + user_points

    # Compute per-variable stats
    stats: dict[str, dict] = {}
    for var in variables:
        vals = [
            p[var.name]
            for p in all_points
            if isinstance(p.get(var.name), (int, float))
               and math.isfinite(p[var.name])
        ]
        if not vals:
            stats[var.name] = {"n": 0, "min": None, "max": None,
                               "mean": None, "std": None}
            continue
        n    = len(vals)
        mean = sum(vals) / n
        std  = math.sqrt(sum((v - mean) ** 2 for v in vals) / n) if n > 1 else 0.0
        vmin = min(vals)
        vmax = max(vals)
        # Cap outliers at mean ± 4σ
        cap_lo = mean - 4 * std
        cap_hi = mean + 4 * std
        vals_capped = [max(cap_lo, min(cap_hi, v)) for v in vals]
        stats[var.name] = {
            "n":    n,
            "min":  min(vals_capped),
            "max":  max(vals_capped),
            "mean": mean,
            "std":  std,
        }

    log.info(
        f"[data_collector] dataset: {len(lit_points)} literature + "
        f"{len(user_points)} user = {len(all_points)} total points"
    )
    return all_points, stats
