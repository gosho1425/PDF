"""
bo_engine.py — Bayesian Optimisation engine.

Architecture decision: scikit-optimize (skopt)
  - Reason: pure Python, no C++ build required, works on Windows without conda,
    supports continuous + categorical + integer variables, mature and stable,
    integrates cleanly with NumPy / sklearn.
  - Alternative considered: BoTorch — requires PyTorch which is ~800 MB and
    has Windows build issues with pip.  Rejected for local-first MVP.
  - Future: the Optimizer interface is abstract; swapping to BoTorch or Ax
    later requires only changing this file.

Workflow:
  Phase A (warm start from literature only):
    - Use literature data points as observations.
    - Fit a Gaussian Process surrogate.
    - Sample candidate points via Expected Improvement (EI).
    - Return top-K candidates with predicted mean, std, and EI score.

  Phase B (posterior update with user experiments):
    - Combine literature + user_experiment points.
    - User points get higher weight (trust_weight=2.0 default).
    - Re-fit GP and recommend next experiments.

  Categorical variables:
    - Label-encoded as integers for GP (skopt handles this natively
      with CategoricalDimension).
    - Decoded back to strings before returning to the UI.

  Transparency:
    - Each candidate includes: proposed inputs, predicted mean ± std,
      EI acquisition score, plain-English explanation, nearest supporting
      literature IDs (by Euclidean distance in normalised space).
"""
from __future__ import annotations

import logging
import math
import random
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.optimization import (
    OptimizationProject, ProjectVariable,
    RecommendationRun, RecommendedCandidate,
    RecommendationStatus, VariableRole, VariableType, SourceType,
)
from app.services.optimization.data_collector import build_dataset

log = logging.getLogger(__name__)

# How many candidate experiments to return per run
N_CANDIDATES = 5
# How many random points to evaluate per candidate search (EI sampling)
N_RANDOM_EVAL = 1000
# How many supporting literature examples to show per candidate
N_SUPPORTING = 3
# Trust multiplier for user-experiment observations (vs literature)
USER_TRUST_WEIGHT = 2.0


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _normalise(value: float, vmin: float, vmax: float) -> float:
    """Min-max scale to [0, 1]. Returns 0.5 if range is zero."""
    if vmax == vmin:
        return 0.5
    return (value - vmin) / (vmax - vmin)


def _denormalise(norm: float, vmin: float, vmax: float) -> float:
    return vmin + norm * (vmax - vmin)


# ── Kernel / GP surrogate ──────────────────────────────────────────────────────

def _build_gp():
    """Build a Gaussian Process regressor."""
    try:
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
        kernel = (
            ConstantKernel(1.0, (1e-3, 1e3))
            * Matern(length_scale=0.5, length_scale_bounds=(1e-2, 10.0), nu=2.5)
            + WhiteKernel(noise_level=0.01, noise_level_bounds=(1e-5, 0.5))
        )
        return GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=5,
            normalize_y=True,
            random_state=42,
        )
    except ImportError:
        raise RuntimeError(
            "scikit-learn is required for Bayesian optimisation. "
            "Run: pip install scikit-learn"
        )


# ── Expected Improvement ───────────────────────────────────────────────────────

def _expected_improvement(
    mean: float,
    std: float,
    best_so_far: float,
    direction: str = "maximize",
    xi: float = 0.01,
) -> float:
    """
    Compute Expected Improvement acquisition value.

    EI(x) = (μ - f* - ξ) * Φ(Z) + σ * φ(Z)
    where Z = (μ - f* - ξ) / σ
    """
    if std < 1e-9:
        return 0.0
    if direction == "maximize":
        improvement = mean - best_so_far - xi
    else:
        improvement = best_so_far - mean - xi

    Z = improvement / std
    # Standard normal CDF and PDF
    phi_Z  = math.exp(-0.5 * Z * Z) / math.sqrt(2 * math.pi)
    Phi_Z  = 0.5 * (1.0 + math.erf(Z / math.sqrt(2)))
    ei     = improvement * Phi_Z + std * phi_Z
    return max(0.0, ei)


# ── Categorical encoding ───────────────────────────────────────────────────────

def _encode_categorical(value: str, choices: list[str]) -> float:
    """Encode a categorical choice as a float index."""
    try:
        return float(choices.index(value))
    except ValueError:
        return 0.0


def _decode_categorical(value: float, choices: list[str]) -> str:
    idx = min(max(0, round(value)), len(choices) - 1)
    return choices[idx]


# ── Main BO function ───────────────────────────────────────────────────────────

def run_bayesian_optimisation(
    db: Session,
    project: OptimizationProject,
    variables: list[ProjectVariable],
    n_candidates: int = N_CANDIDATES,
) -> dict:
    """
    Run a full BO cycle for the given project.

    Returns a dict with:
      status, message, n_literature, n_user, n_total,
      model_type, acquisition_fn,
      candidates: [ { rank, proposed_inputs, predicted_mean, predicted_std,
                       acquisition_score, explanation, supporting_paper_ids } ]
    """
    log.info(f"[BO] Starting BO for project '{project.name}' (id={project.id})")

    # 1. Collect data
    all_points, stats = build_dataset(db, project, variables)

    # Identify input/output variables with data
    input_vars  = [v for v in variables if v.role == VariableRole.input]
    output_vars = [v for v in variables if v.role == VariableRole.output]
    obj_var     = next((v for v in output_vars if v.is_objective), None)

    if not obj_var:
        # Fall back to first output variable
        obj_var = output_vars[0] if output_vars else None

    if not obj_var:
        return {
            "status": "failed",
            "message": "No objective variable defined. "
                       "Mark one output variable as the objective.",
            "candidates": [],
        }

    direction = project.objective_direction or "maximize"

    # 2. Build training set: only points that have the objective value
    X_raw: list[list[float]] = []
    y_raw: list[float]       = []
    point_meta: list[dict]   = []    # for finding neighbours later
    weights: list[float]     = []

    # Per-variable min/max for normalisation
    var_ranges: dict[str, tuple[float, float]] = {}
    for v in input_vars:
        s = stats.get(v.name, {})
        vmin = v.min_value if v.min_value is not None else (s.get("min") or 0.0)
        vmax = v.max_value if v.max_value is not None else (s.get("max") or 1.0)
        if vmax == vmin:
            vmax = vmin + 1.0
        var_ranges[v.name] = (vmin, vmax)

    obj_stat = stats.get(obj_var.name, {})
    obj_min  = obj_var.min_value if obj_var.min_value is not None else (obj_stat.get("min") or 0.0)
    obj_max  = obj_var.max_value if obj_var.max_value is not None else (obj_stat.get("max") or 1.0)
    if obj_max == obj_min:
        obj_max = obj_min + 1.0

    for pt in all_points:
        obj_val = pt.get(obj_var.name)
        if obj_val is None or not isinstance(obj_val, (int, float)):
            continue

        row: list[float] = []
        valid = True
        for v in input_vars:
            val = pt.get(v.name)
            if val is None or not isinstance(val, (int, float)):
                # Impute with midpoint for literature; skip for user experiments
                if pt.get("source_type") == SourceType.user_experiment.value:
                    valid = False
                    break
                vmin, vmax = var_ranges[v.name]
                val = (vmin + vmax) / 2.0
            vmin, vmax = var_ranges[v.name]
            row.append(_normalise(float(val), vmin, vmax))

        if not valid or not row:
            continue

        X_raw.append(row)
        y_raw.append(float(obj_val))
        point_meta.append(pt)
        trust = (USER_TRUST_WEIGHT
                 if pt.get("source_type") == SourceType.user_experiment.value
                 else 1.0)
        weights.append(trust)

    n_lit  = sum(1 for p in point_meta
                 if p.get("source_type") == SourceType.literature.value)
    n_user = sum(1 for p in point_meta
                 if p.get("source_type") == SourceType.user_experiment.value)
    n_total = len(X_raw)

    log.info(
        f"[BO] Training set: {n_total} points "
        f"({n_lit} literature, {n_user} user)"
    )

    # 3. Choose strategy based on data volume
    if n_total < 2:
        return _literature_heuristic(
            all_points, input_vars, output_vars, obj_var,
            var_ranges, direction, n_candidates, stats,
        )

    # 4. Fit GP surrogate
    try:
        import numpy as np
        X = np.array(X_raw)
        y = np.array(y_raw)

        # Weight user experiments by duplicating them
        if n_user > 0:
            X_extra = np.array([
                X_raw[i] for i, p in enumerate(point_meta)
                if p.get("source_type") == SourceType.user_experiment.value
            ])
            y_extra = np.array([
                y_raw[i] for i, p in enumerate(point_meta)
                if p.get("source_type") == SourceType.user_experiment.value
            ])
            # Duplicate user rows to give them ~2x weight
            X = np.vstack([X, X_extra])
            y = np.concatenate([y, y_extra])

        gp = _build_gp()
        gp.fit(X, y)

        # 5. Find best observed value
        best_y = float(np.max(y) if direction == "maximize" else np.min(y))

        # 6. Random search for candidates with highest EI
        rng = random.Random(42)
        candidates_scored: list[dict] = []

        for _ in range(N_RANDOM_EVAL):
            # Sample a random point in [0,1]^d
            x_cand = [rng.random() for _ in input_vars]
            x_arr  = np.array(x_cand).reshape(1, -1)
            mean, std = gp.predict(x_arr, return_std=True)
            mean_f = float(mean[0])
            std_f  = float(std[0])
            ei = _expected_improvement(mean_f, std_f, best_y, direction)
            candidates_scored.append({
                "x_norm": x_cand,
                "mean":   mean_f,
                "std":    std_f,
                "ei":     ei,
            })

        # Sort by EI descending, take top n_candidates (deduplicated)
        candidates_scored.sort(key=lambda c: c["ei"], reverse=True)

        # Deduplicate: remove points too close to each other (threshold 0.05)
        deduped: list[dict] = []
        for cand in candidates_scored:
            too_close = False
            for kept in deduped:
                dist = math.sqrt(sum(
                    (a - b) ** 2
                    for a, b in zip(cand["x_norm"], kept["x_norm"])
                ))
                if dist < 0.05:
                    too_close = True
                    break
            if not too_close:
                deduped.append(cand)
            if len(deduped) >= n_candidates:
                break

        # 7. Build candidate output
        candidates: list[dict] = []
        for rank, cand in enumerate(deduped, 1):
            # Denormalise inputs
            proposed = {}
            for v, norm_val in zip(input_vars, cand["x_norm"]):
                vmin, vmax = var_ranges[v.name]
                real_val = _denormalise(norm_val, vmin, vmax)
                if v.var_type == VariableType.categorical and v.choices:
                    proposed[v.name] = _decode_categorical(real_val, v.choices)
                elif v.var_type == VariableType.integer:
                    proposed[v.name] = round(real_val)
                else:
                    proposed[v.name] = round(real_val, 4)

            # Find nearest literature neighbours
            x_arr_cand = np.array(cand["x_norm"])
            neighbours = []
            for i, pt in enumerate(point_meta):
                if pt.get("source_type") != SourceType.literature.value:
                    continue
                if i >= len(X_raw):
                    continue
                dist = float(np.linalg.norm(x_arr_cand - np.array(X_raw[i])))
                neighbours.append((dist, pt.get("paper_id"), pt.get("paper_title")))
            neighbours.sort(key=lambda t: t[0])
            supporting_ids   = [t[1] for t in neighbours[:N_SUPPORTING] if t[1]]
            supporting_titles = [t[2] for t in neighbours[:N_SUPPORTING] if t[2]]

            # Human-readable explanation
            pred_val   = round(cand["mean"], 4)
            pred_std   = round(cand["std"],  4)
            explanation = (
                f"Predicted {obj_var.label or obj_var.name} = "
                f"{pred_val} ± {pred_std} {obj_var.unit or ''}. "
                f"EI score = {cand['ei']:.4f} "
                f"({'higher is better' if direction=='maximize' else 'lower is better'}). "
            )
            if supporting_titles:
                explanation += (
                    f"Nearest supporting literature: "
                    + "; ".join(f'"{t}"' for t in supporting_titles[:2])
                    + "."
                )

            candidates.append({
                "rank":                rank,
                "proposed_inputs":     proposed,
                "predicted_mean":      round(cand["mean"], 4),
                "predicted_std":       round(cand["std"],  4),
                "acquisition_score":   round(cand["ei"],   6),
                "explanation":         explanation,
                "supporting_paper_ids": supporting_ids,
            })

        return {
            "status":       "completed",
            "message":      f"GP+EI on {n_total} points ({n_lit} lit, {n_user} user)",
            "n_literature": n_lit,
            "n_user":       n_user,
            "n_total":      n_total,
            "model_type":   "GaussianProcessRegressor",
            "acquisition_fn": "ExpectedImprovement",
            "candidates":   candidates,
        }

    except Exception as exc:
        log.exception(f"[BO] GP failed: {exc}")
        # Graceful fallback to heuristic
        log.warning("[BO] Falling back to literature heuristic")
        return _literature_heuristic(
            all_points, input_vars, output_vars, obj_var,
            var_ranges, direction, n_candidates, stats,
        )


def _literature_heuristic(
    all_points: list[dict],
    input_vars: list[ProjectVariable],
    output_vars: list[ProjectVariable],
    obj_var: ProjectVariable,
    var_ranges: dict,
    direction: str,
    n_candidates: int,
    stats: dict,
) -> dict:
    """
    When there's too little data for GP, use a transparent heuristic:
    1. Find literature points that have the objective value.
    2. Rank them by objective value.
    3. Return top-K as initial candidates (with their actual input conditions).

    This gives the scientist a literature-informed warm start.
    """
    log.info("[BO] Using literature heuristic (insufficient data for GP)")

    scored: list[dict] = []
    for pt in all_points:
        obj_val = pt.get(obj_var.name)
        if obj_val is None or not isinstance(obj_val, (int, float)):
            continue
        scored.append((float(obj_val), pt))

    if not scored:
        return {
            "status":       "completed",
            "message":      "No data points with objective value found. "
                            "Add more papers or enter a user experiment.",
            "n_literature": 0,
            "n_user":       0,
            "n_total":      0,
            "model_type":   "literature_heuristic",
            "acquisition_fn": "literature_heuristic",
            "candidates":   _random_candidates(input_vars, var_ranges, n_candidates),
        }

    scored.sort(key=lambda t: t[0], reverse=(direction == "maximize"))
    top = scored[:n_candidates]

    candidates: list[dict] = []
    for rank, (obj_val, pt) in enumerate(top, 1):
        proposed = {}
        for v in input_vars:
            val = pt.get(v.name)
            if val is not None:
                proposed[v.name] = val

        src = pt.get("source_type", "literature")
        paper_id    = pt.get("paper_id")
        paper_title = pt.get("paper_title", "")
        explanation = (
            f"Literature-informed warm start. "
            f"This paper reported {obj_var.label or obj_var.name} = {obj_val} "
            f"{obj_var.unit or ''}. "
            f"Source: {src}. "
            + (f'Paper: "{paper_title}"' if paper_title else "")
        )

        candidates.append({
            "rank":                rank,
            "proposed_inputs":     proposed,
            "predicted_mean":      float(obj_val),
            "predicted_std":       None,
            "acquisition_score":   float(rank),
            "explanation":         explanation,
            "supporting_paper_ids": [paper_id] if paper_id else [],
        })

    return {
        "status":       "completed",
        "message":      f"Literature heuristic: top {len(candidates)} conditions by {direction} {obj_var.name}",
        "n_literature": sum(1 for _, p in top
                           if p.get("source_type") == SourceType.literature.value),
        "n_user":       sum(1 for _, p in top
                           if p.get("source_type") == SourceType.user_experiment.value),
        "n_total":      len(top),
        "model_type":   "literature_heuristic",
        "acquisition_fn": "literature_heuristic",
        "candidates":   candidates,
    }


def _random_candidates(
    input_vars: list[ProjectVariable],
    var_ranges: dict,
    n: int,
) -> list[dict]:
    """Last-resort: propose random conditions within defined ranges."""
    rng = random.Random(42)
    candidates = []
    for rank in range(1, n + 1):
        proposed = {}
        for v in input_vars:
            vmin, vmax = var_ranges.get(v.name, (0.0, 1.0))
            proposed[v.name] = round(vmin + rng.random() * (vmax - vmin), 3)
        candidates.append({
            "rank":               rank,
            "proposed_inputs":    proposed,
            "predicted_mean":     None,
            "predicted_std":      None,
            "acquisition_score":  None,
            "explanation":        "Random initialisation — no data available yet. "
                                  "Define variable ranges in the project for better results.",
            "supporting_paper_ids": [],
        })
    return candidates


# ── Entry point called by the router ─────────────────────────────────────────

def create_recommendation_run(
    db: Session,
    project: OptimizationProject,
    n_candidates: int = N_CANDIDATES,
) -> RecommendationRun:
    """
    Create a RecommendationRun, execute the BO, persist candidates, return the run.
    """
    from datetime import datetime

    variables = project.variables

    # Create the run record
    run = RecommendationRun(
        project_id=project.id,
        status=RecommendationStatus.running,
    )
    db.add(run)
    db.flush()  # get run.id

    try:
        result = run_bayesian_optimisation(db, project, variables, n_candidates)

        run.status              = RecommendationStatus.completed \
                                  if result["status"] == "completed" \
                                  else RecommendationStatus.failed
        run.message             = result.get("message")
        run.n_literature_points = result.get("n_literature", 0)
        run.n_user_points       = result.get("n_user", 0)
        run.n_candidates        = len(result.get("candidates", []))
        run.model_type          = result.get("model_type")
        run.acquisition_fn      = result.get("acquisition_fn")
        run.completed_at        = datetime.utcnow()
        run.result_json         = result

        # Persist candidates
        for c in result.get("candidates", []):
            cand = RecommendedCandidate(
                run_id                = run.id,
                rank                  = c["rank"],
                proposed_inputs       = c["proposed_inputs"],
                predicted_mean        = c.get("predicted_mean"),
                predicted_std         = c.get("predicted_std"),
                acquisition_score     = c.get("acquisition_score"),
                explanation           = c.get("explanation"),
                supporting_paper_ids  = c.get("supporting_paper_ids"),
            )
            db.add(cand)

        # Update project counts
        project.n_recommendations += 1
        lit_pts, _ = build_dataset(db, project, variables)
        # build_dataset calls both collectors; we just refresh counts
        project.n_user_experiments = len([
            p for p in lit_pts
            if p.get("source_type") == SourceType.user_experiment.value
        ])
        project.n_literature_points = len([
            p for p in lit_pts
            if p.get("source_type") == SourceType.literature.value
        ])

        db.commit()

    except Exception as exc:
        db.rollback()
        log.exception(f"[BO] run failed: {exc}")
        run.status  = RecommendationStatus.failed
        run.message = str(exc)
        run.completed_at = datetime.utcnow()
        db.add(run)
        db.commit()

    return run
