"""
Optimization API — Phase 2.

Endpoints:
  Projects
    GET    /api/optimization/projects
    POST   /api/optimization/projects
    GET    /api/optimization/projects/{id}
    PUT    /api/optimization/projects/{id}
    DELETE /api/optimization/projects/{id}
    GET    /api/optimization/projects/{id}/dataset      → merged lit+user data preview
    GET    /api/optimization/projects/{id}/variables

  Variables
    POST   /api/optimization/projects/{id}/variables
    PUT    /api/optimization/variables/{id}
    DELETE /api/optimization/variables/{id}

  User experiments
    GET    /api/optimization/projects/{id}/experiments
    POST   /api/optimization/projects/{id}/experiments
    GET    /api/optimization/experiments/{id}
    PUT    /api/optimization/experiments/{id}
    DELETE /api/optimization/experiments/{id}

  Recommendations
    POST   /api/optimization/projects/{id}/recommend   → trigger BO run
    GET    /api/optimization/projects/{id}/runs        → list past runs
    GET    /api/optimization/runs/{id}                 → full run detail
    POST   /api/optimization/candidates/{id}/execute   → mark candidate as executed
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.optimization import (
    OptimizationProject, ProjectVariable, UserExperiment,
    RecommendationRun, RecommendedCandidate,
    VariableRole, VariableType, ExperimentStatus, SourceType,
    RecommendationStatus,
)

router = APIRouter()
log = logging.getLogger(__name__)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name:                str
    description:         Optional[str] = None
    material_system:     Optional[str] = None
    objective_variable:  Optional[str] = None
    objective_direction: Optional[str] = "maximize"
    constraints_note:    Optional[str] = None


class ProjectUpdate(BaseModel):
    name:                Optional[str] = None
    description:         Optional[str] = None
    material_system:     Optional[str] = None
    objective_variable:  Optional[str] = None
    objective_direction: Optional[str] = None
    constraints_note:    Optional[str] = None


class VariableCreate(BaseModel):
    name:         str
    label:        Optional[str] = None
    role:         str   # "input" | "output" | "material"
    var_type:     str = "continuous"
    unit:         Optional[str] = None
    description:  Optional[str] = None
    min_value:    Optional[float] = None
    max_value:    Optional[float] = None
    choices:      Optional[list[str]] = None
    is_objective: bool = False
    is_constraint: bool = False


class VariableUpdate(BaseModel):
    label:        Optional[str] = None
    role:         Optional[str] = None
    var_type:     Optional[str] = None
    unit:         Optional[str] = None
    description:  Optional[str] = None
    # Use a sentinel so we can distinguish "not provided" from "explicitly null"
    min_value:    Optional[float] = None
    max_value:    Optional[float] = None
    choices:      Optional[list[str]] = None
    is_objective: Optional[bool] = None
    is_constraint: Optional[bool] = None

    model_config = {"populate_by_name": True}


class ExperimentCreate(BaseModel):
    name:          Optional[str] = None
    notes:         Optional[str] = None
    status:        str = "completed"
    input_values:  Optional[dict] = None
    output_values: Optional[dict] = None
    run_date:      Optional[str] = None   # ISO date string


class ExperimentUpdate(BaseModel):
    name:          Optional[str] = None
    notes:         Optional[str] = None
    status:        Optional[str] = None
    input_values:  Optional[dict] = None
    output_values: Optional[dict] = None
    run_date:      Optional[str] = None


class RecommendRequest(BaseModel):
    n_candidates: int = 5


class ExecuteCandidateRequest(BaseModel):
    experiment_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_project_or_404(db: Session, project_id: str) -> OptimizationProject:
    p = db.get(OptimizationProject, project_id)
    if not p:
        raise HTTPException(404, f"Project {project_id} not found")
    return p


def _serialize_project(p: OptimizationProject) -> dict:
    return {
        "id":                   p.id,
        "name":                 p.name,
        "description":          p.description,
        "material_system":      p.material_system,
        "objective_variable":   p.objective_variable,
        "objective_direction":  p.objective_direction,
        "constraints_note":     p.constraints_note,
        "n_literature_points":  p.n_literature_points,
        "n_user_experiments":   p.n_user_experiments,
        "n_recommendations":    p.n_recommendations,
        "created_at":           p.created_at.isoformat(),
        "updated_at":           p.updated_at.isoformat(),
    }


def _serialize_variable(v: ProjectVariable) -> dict:
    return {
        "id":           v.id,
        "project_id":   v.project_id,
        "name":         v.name,
        "label":        v.label,
        "role":         v.role.value,
        "var_type":     v.var_type.value,
        "unit":         v.unit,
        "description":  v.description,
        "min_value":    v.min_value,
        "max_value":    v.max_value,
        "choices":      v.choices,
        "is_objective": v.is_objective,
        "is_constraint": v.is_constraint,
        "created_at":   v.created_at.isoformat(),
    }


def _serialize_experiment(e: UserExperiment) -> dict:
    return {
        "id":            e.id,
        "project_id":    e.project_id,
        "name":          e.name,
        "notes":         e.notes,
        "source_type":   e.source_type.value,
        "status":        e.status.value,
        "input_values":  e.input_values,
        "output_values": e.output_values,
        "objective_value": e.objective_value,
        "from_recommendation_id": e.from_recommendation_id,
        "run_date":      e.run_date.isoformat() if e.run_date else None,
        "created_at":    e.created_at.isoformat(),
        "updated_at":    e.updated_at.isoformat(),
    }


def _serialize_candidate(c: RecommendedCandidate) -> dict:
    return {
        "id":                   c.id,
        "run_id":               c.run_id,
        "rank":                 c.rank,
        "proposed_inputs":      c.proposed_inputs,
        "predicted_mean":       c.predicted_mean,
        "predicted_std":        c.predicted_std,
        "acquisition_score":    c.acquisition_score,
        "explanation":          c.explanation,
        "supporting_paper_ids": c.supporting_paper_ids,
        "was_executed":         c.was_executed,
        "executed_experiment_id": c.executed_experiment_id,
        "created_at":           c.created_at.isoformat(),
    }


def _serialize_run(r: RecommendationRun, include_candidates: bool = True) -> dict:
    d = {
        "id":                   r.id,
        "project_id":           r.project_id,
        "status":               r.status.value,
        "message":              r.message,
        "n_literature_points":  r.n_literature_points,
        "n_user_points":        r.n_user_points,
        "n_candidates":         r.n_candidates,
        "model_type":           r.model_type,
        "acquisition_fn":       r.acquisition_fn,
        "created_at":           r.created_at.isoformat(),
        "completed_at":         r.completed_at.isoformat() if r.completed_at else None,
    }
    if include_candidates:
        d["candidates"] = [_serialize_candidate(c) for c in r.candidates]
    return d


def _update_objective_value(exp: UserExperiment, project: OptimizationProject) -> None:
    """Extract the objective variable value from output_values and cache it."""
    if not project.objective_variable:
        return
    output = exp.output_values or {}
    field  = output.get(project.objective_variable)
    if field is None:
        return
    if isinstance(field, dict):
        val = field.get("value")
    else:
        val = field
    try:
        exp.objective_value = float(val)
    except (TypeError, ValueError):
        pass


# ── Project endpoints ─────────────────────────────────────────────────────────

@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(OptimizationProject).order_by(
        OptimizationProject.updated_at.desc()
    ).all()
    return [_serialize_project(p) for p in projects]


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = OptimizationProject(
        name=body.name,
        description=body.description,
        material_system=body.material_system,
        objective_variable=body.objective_variable,
        objective_direction=body.objective_direction or "maximize",
        constraints_note=body.constraints_note,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serialize_project(p)


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _serialize_project(_get_project_or_404(db, project_id))


@router.put("/projects/{project_id}")
def update_project(project_id: str, body: ProjectUpdate,
                   db: Session = Depends(get_db)):
    p = _get_project_or_404(db, project_id)
    if body.name is not None:                p.name = body.name
    if body.description is not None:         p.description = body.description
    if body.material_system is not None:     p.material_system = body.material_system
    if body.objective_variable is not None:  p.objective_variable = body.objective_variable
    if body.objective_direction is not None: p.objective_direction = body.objective_direction
    if body.constraints_note is not None:    p.constraints_note = body.constraints_note
    db.commit()
    return _serialize_project(p)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = _get_project_or_404(db, project_id)
    db.delete(p)
    db.commit()


@router.get("/projects/{project_id}/dataset")
def project_dataset(project_id: str, db: Session = Depends(get_db)):
    """
    Return a preview of the merged literature + user dataset for this project.
    Useful for inspecting what data the BO sees.
    """
    from app.services.optimization.data_collector import build_dataset
    p = _get_project_or_404(db, project_id)
    points, stats = build_dataset(db, p, p.variables)
    return {
        "n_total":    len(points),
        "n_literature": sum(1 for pt in points
                           if pt.get("source_type") == SourceType.literature.value),
        "n_user":     sum(1 for pt in points
                         if pt.get("source_type") == SourceType.user_experiment.value),
        "stats":      stats,
        "points":     points,
    }


# ── Variable endpoints ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/variables")
def list_variables(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    variables = (
        db.query(ProjectVariable)
        .filter(ProjectVariable.project_id == project_id)
        .all()
    )
    return [_serialize_variable(v) for v in variables]


@router.post("/projects/{project_id}/variables", status_code=201)
def create_variable(project_id: str, body: VariableCreate,
                    db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    try:
        role     = VariableRole(body.role)
        var_type = VariableType(body.var_type)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # If this is marked as objective, clear the flag from others
    if body.is_objective:
        db.query(ProjectVariable).filter(
            ProjectVariable.project_id == project_id,
            ProjectVariable.is_objective == True,
        ).update({"is_objective": False})

    v = ProjectVariable(
        project_id=project_id,
        name=body.name,
        label=body.label or body.name,
        role=role,
        var_type=var_type,
        unit=body.unit,
        description=body.description,
        min_value=body.min_value,
        max_value=body.max_value,
        choices=body.choices,
        is_objective=body.is_objective,
        is_constraint=body.is_constraint,
    )
    db.add(v)

    # Sync project.objective_variable if needed
    if body.is_objective:
        p = _get_project_or_404(db, project_id)
        p.objective_variable = body.name

    db.commit()
    db.refresh(v)
    return _serialize_variable(v)


@router.put("/variables/{variable_id}")
def update_variable(variable_id: str, body: VariableUpdate,
                    db: Session = Depends(get_db)):
    v = db.get(ProjectVariable, variable_id)
    if not v:
        raise HTTPException(404, "Variable not found")

    # model_fields_set contains all fields that were explicitly provided in the
    # request body — this lets us distinguish "not sent" (skip) from "sent as
    # null" (clear the value).
    provided = body.model_fields_set

    if body.label is not None:        v.label = body.label
    if body.unit is not None:         v.unit = body.unit
    if body.description is not None:  v.description = body.description

    # min_value / max_value: update if the field was sent (even if null → clear)
    if "min_value" in provided:
        v.min_value = body.min_value   # may be None → clears the value
    if "max_value" in provided:
        v.max_value = body.max_value   # may be None → clears the value

    if body.choices is not None:      v.choices = body.choices
    if body.is_constraint is not None: v.is_constraint = body.is_constraint
    if body.role is not None:
        try:
            v.role = VariableRole(body.role)
        except ValueError:
            raise HTTPException(400, f"Invalid role: {body.role}")
    if body.var_type is not None:
        try:
            v.var_type = VariableType(body.var_type)
        except ValueError:
            raise HTTPException(400, f"Invalid var_type: {body.var_type}")
    if body.is_objective is not None:
        if body.is_objective:
            db.query(ProjectVariable).filter(
                ProjectVariable.project_id == v.project_id,
                ProjectVariable.is_objective == True,
            ).update({"is_objective": False})
            p = db.get(OptimizationProject, v.project_id)
            if p:
                p.objective_variable = v.name
        v.is_objective = body.is_objective

    db.commit()
    return _serialize_variable(v)


@router.delete("/variables/{variable_id}", status_code=204)
def delete_variable(variable_id: str, db: Session = Depends(get_db)):
    v = db.get(ProjectVariable, variable_id)
    if not v:
        raise HTTPException(404, "Variable not found")
    db.delete(v)
    db.commit()


# ── User experiment endpoints ─────────────────────────────────────────────────

@router.get("/projects/{project_id}/experiments")
def list_experiments(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    exps = (
        db.query(UserExperiment)
        .filter(UserExperiment.project_id == project_id)
        .order_by(UserExperiment.created_at.desc())
        .all()
    )
    return [_serialize_experiment(e) for e in exps]


@router.post("/projects/{project_id}/experiments", status_code=201)
def create_experiment(project_id: str, body: ExperimentCreate,
                      db: Session = Depends(get_db)):
    p = _get_project_or_404(db, project_id)
    try:
        status = ExperimentStatus(body.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {body.status}")

    run_date = None
    if body.run_date:
        try:
            run_date = datetime.fromisoformat(body.run_date)
        except ValueError:
            pass

    exp = UserExperiment(
        project_id=project_id,
        name=body.name,
        notes=body.notes,
        status=status,
        source_type=SourceType.user_experiment,
        input_values=body.input_values or {},
        output_values=body.output_values or {},
        run_date=run_date,
    )
    _update_objective_value(exp, p)

    db.add(exp)
    p.n_user_experiments = (p.n_user_experiments or 0) + 1
    db.commit()
    db.refresh(exp)
    return _serialize_experiment(exp)


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    e = db.get(UserExperiment, experiment_id)
    if not e:
        raise HTTPException(404, "Experiment not found")
    return _serialize_experiment(e)


@router.put("/experiments/{experiment_id}")
def update_experiment(experiment_id: str, body: ExperimentUpdate,
                      db: Session = Depends(get_db)):
    e = db.get(UserExperiment, experiment_id)
    if not e:
        raise HTTPException(404, "Experiment not found")

    if body.name is not None:         e.name = body.name
    if body.notes is not None:        e.notes = body.notes
    if body.input_values is not None: e.input_values = body.input_values
    if body.output_values is not None: e.output_values = body.output_values
    if body.status is not None:
        try:
            e.status = ExperimentStatus(body.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {body.status}")
    if body.run_date:
        try:
            e.run_date = datetime.fromisoformat(body.run_date)
        except ValueError:
            pass

    p = db.get(OptimizationProject, e.project_id)
    if p:
        _update_objective_value(e, p)

    db.commit()
    return _serialize_experiment(e)


@router.delete("/experiments/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    e = db.get(UserExperiment, experiment_id)
    if not e:
        raise HTTPException(404, "Experiment not found")
    p = db.get(OptimizationProject, e.project_id)
    if p and p.n_user_experiments:
        p.n_user_experiments = max(0, p.n_user_experiments - 1)
    db.delete(e)
    db.commit()


# ── Recommendation endpoints ──────────────────────────────────────────────────

@router.post("/projects/{project_id}/recommend")
def trigger_recommendation(
    project_id: str,
    body: RecommendRequest,
    db: Session = Depends(get_db),
):
    """
    Trigger a Bayesian Optimisation run for this project.
    Blocks until complete (may take 5-30s for large datasets).
    """
    from app.services.optimization.bo_engine import create_recommendation_run

    p = _get_project_or_404(db, project_id)

    if not p.variables:
        raise HTTPException(
            400,
            "No variables defined for this project. "
            "Add at least one input and one output variable first."
        )
    output_vars = [v for v in p.variables
                   if v.role in (VariableRole.output,)]
    if not output_vars:
        raise HTTPException(
            400,
            "No output (objective) variables defined. "
            "Add at least one output variable and mark it as the objective."
        )

    n_cand = max(1, min(body.n_candidates, 10))
    run = create_recommendation_run(db, p, n_candidates=n_cand)
    db.refresh(run)
    return _serialize_run(run, include_candidates=True)


@router.get("/projects/{project_id}/runs")
def list_runs(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    runs = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.project_id == project_id)
        .order_by(RecommendationRun.created_at.desc())
        .all()
    )
    return [_serialize_run(r, include_candidates=False) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    r = db.get(RecommendationRun, run_id)
    if not r:
        raise HTTPException(404, "Recommendation run not found")
    return _serialize_run(r, include_candidates=True)


@router.post("/candidates/{candidate_id}/execute")
def mark_candidate_executed(
    candidate_id: str,
    body: ExecuteCandidateRequest,
    db: Session = Depends(get_db),
):
    """Mark a recommended candidate as 'I ran this experiment'."""
    c = db.get(RecommendedCandidate, candidate_id)
    if not c:
        raise HTTPException(404, "Candidate not found")
    c.was_executed = True
    if body.experiment_id:
        c.executed_experiment_id = body.experiment_id
    db.commit()
    return {"status": "marked_executed", "candidate_id": candidate_id}


# ── Seeding endpoint (import from DEFAULT_PARAMETERS) ────────────────────────

@router.post("/projects/{project_id}/seed-variables")
def seed_variables_from_defaults(project_id: str,
                                 db: Session = Depends(get_db)):
    """
    Import the default extraction parameters as project variables.
    This gives a quick start without manual variable entry.
    Only adds variables that don't already exist (by name).
    """
    from app.llm.schema import DEFAULT_PARAMETERS

    p = _get_project_or_404(db, project_id)
    existing_names = {v.name for v in p.variables}

    added = []
    for param in DEFAULT_PARAMETERS:
        if param["name"] in existing_names:
            continue
        role_map = {
            "input":    VariableRole.input,
            "output":   VariableRole.output,
            "material": VariableRole.material,
        }
        role = role_map.get(param["role"], VariableRole.input)

        v = ProjectVariable(
            project_id=project_id,
            name=param["name"],
            label=param.get("label", param["name"]),
            role=role,
            var_type=VariableType.continuous,
            unit=param.get("unit"),
            description=param.get("description"),
        )
        # Mark known output as objective if project has none yet
        if (role == VariableRole.output
                and param["name"] == (p.objective_variable or "Tc")):
            v.is_objective = True

        db.add(v)
        added.append(param["name"])

    db.commit()
    return {"added": added, "count": len(added)}


# ── Literature preview for a project ─────────────────────────────────────────

@router.get("/projects/{project_id}/literature-preview")
def literature_preview(project_id: str, db: Session = Depends(get_db)):
    """
    Return papers that mention the project's material system,
    along with which tracked variables they have data for.
    """
    from app.services.optimization.data_collector import collect_literature_points

    p     = _get_project_or_404(db, project_id)
    pts   = collect_literature_points(db, p, p.variables)
    var_names = {v.name for v in p.variables}

    preview = []
    for pt in pts:
        present = [n for n in var_names if pt.get(n) is not None]
        preview.append({
            "paper_id":    pt.get("paper_id"),
            "paper_title": pt.get("paper_title"),
            "paper_year":  pt.get("paper_year"),
            "source_type": pt.get("source_type"),
            "variables_present": present,
            "n_variables": len(present),
        })

    # Sort by number of variables found (most useful first)
    preview.sort(key=lambda x: x["n_variables"], reverse=True)
    return {
        "n_papers": len(preview),
        "papers":   preview,
    }
