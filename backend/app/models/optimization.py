"""
Optimization models — Phase 2.

Tables:
  optimization_projects    — a named research goal (e.g. "Maximise Tc for YBCO thin films")
  project_variables        — which input/output variables belong to the project
  user_experiments         — manually entered lab runs
  experiment_measurements  — individual measured values for a run
  recommendation_runs      — a single call to the BO engine
  recommended_candidates   — individual candidate experiments produced by a run

Design principles:
  - literature-derived data lives in the existing Paper / extraction JSON.
    We read it at query time; we never duplicate it here.
  - user_experiments live here with source_type='user_experiment'.
  - Both sources are combined by the BO service at recommendation time.
  - Every column uses plain SQLite-compatible types (no JSONB etc.).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, Boolean,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class VariableRole(str, enum.Enum):
    input    = "input"
    output   = "output"
    material = "material"


class VariableType(str, enum.Enum):
    continuous   = "continuous"    # float, with optional [min, max]
    categorical  = "categorical"   # string from a fixed set
    integer      = "integer"       # integer, with optional [min, max]
    boolean      = "boolean"       # True/False


class ExperimentStatus(str, enum.Enum):
    planned   = "planned"
    running   = "running"
    completed = "completed"
    failed    = "failed"


class SourceType(str, enum.Enum):
    literature       = "literature"
    user_experiment  = "user_experiment"


class RecommendationStatus(str, enum.Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"


# ── Tables ────────────────────────────────────────────────────────────────────

class OptimizationProject(Base):
    """
    A named optimization campaign.
    Examples: 'Maximise Tc for YBCO PLD', 'Minimise resistivity — NbN sputtering'
    """
    __tablename__ = "optimization_projects"

    id          = Column(String(36), primary_key=True,
                         default=lambda: str(uuid.uuid4()))
    name        = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # Material system used to filter relevant literature
    material_system = Column(String(256), nullable=True,
                             doc="e.g. 'YBCO', 'NbN', 'MgB2'")

    # The single scalar objective: which variable name and direction
    objective_variable  = Column(String(128), nullable=True,
                                 doc="Name of the output variable to optimise")
    objective_direction = Column(String(16), nullable=True,
                                 doc="'maximize' or 'minimize'")

    # Optional notes on constraints (stored as free text; structured later)
    constraints_note = Column(Text, nullable=True)

    # Counts (denormalised for quick display)
    n_literature_points = Column(Integer, default=0)
    n_user_experiments  = Column(Integer, default=0)
    n_recommendations   = Column(Integer, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    variables        = relationship("ProjectVariable",
                                    back_populates="project",
                                    cascade="all, delete-orphan")
    user_experiments = relationship("UserExperiment",
                                    back_populates="project",
                                    cascade="all, delete-orphan")
    recommendation_runs = relationship("RecommendationRun",
                                       back_populates="project",
                                       cascade="all, delete-orphan")


class ProjectVariable(Base):
    """
    A variable (input or output) that belongs to a project.
    Maps to the names used in the extraction schema (e.g. 'Tc', 'sputtering_power').
    Custom variables can be added without schema changes.
    """
    __tablename__ = "project_variables"

    id         = Column(String(36), primary_key=True,
                        default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("optimization_projects.id",
                                               ondelete="CASCADE"),
                        nullable=False, index=True)

    name        = Column(String(128), nullable=False,
                         doc="machine key, e.g. 'Tc' or 'sputtering_power'")
    label       = Column(String(256), nullable=True,
                         doc="human label, e.g. 'Critical Temperature (Tc)'")
    role        = Column(Enum(VariableRole), nullable=False)
    var_type    = Column(Enum(VariableType), nullable=False,
                         default=VariableType.continuous)
    unit        = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    # For continuous/integer variables: allowed range
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)

    # For categorical variables: allowed choices stored as JSON list
    choices = Column(JSON, nullable=True,
                     doc="e.g. ['PLD', 'sputtering', 'MBE']")

    # Is this the objective variable?
    is_objective   = Column(Boolean, default=False)
    # Is this a constraint (must stay within min_value..max_value)?
    is_constraint  = Column(Boolean, default=False)

    # Normalisation info (filled by the BO service)
    norm_min = Column(Float, nullable=True)
    norm_max = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    project = relationship("OptimizationProject", back_populates="variables")


class UserExperiment(Base):
    """
    A single lab experiment entered manually by the scientist.
    This is the highest-trust data source for posterior updating.
    """
    __tablename__ = "user_experiments"

    id         = Column(String(36), primary_key=True,
                        default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("optimization_projects.id",
                                               ondelete="CASCADE"),
                        nullable=False, index=True)

    # Human-readable label for the run
    name  = Column(String(256), nullable=True,
                   doc="e.g. 'Run 003 — high power attempt'")
    notes = Column(Text, nullable=True)

    source_type = Column(Enum(SourceType), nullable=False,
                         default=SourceType.user_experiment)
    status      = Column(Enum(ExperimentStatus), nullable=False,
                         default=ExperimentStatus.completed)

    # All input and output values stored as flexible JSON
    # { "sputtering_power": {"value": 150, "unit": "W"}, ... }
    input_values  = Column(JSON, nullable=True)
    output_values = Column(JSON, nullable=True)

    # Objective value extracted from output_values for quick access
    objective_value = Column(Float, nullable=True)

    # Was this experiment recommended by the BO system?
    from_recommendation_id = Column(String(36), nullable=True,
                                    doc="ID of the recommendation that suggested this run")

    run_date   = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    project      = relationship("OptimizationProject",
                                back_populates="user_experiments")
    measurements = relationship("ExperimentMeasurement",
                                back_populates="experiment",
                                cascade="all, delete-orphan")


class ExperimentMeasurement(Base):
    """
    Individual measured scalar value for one variable in one experiment.
    Allows storing repeated measurements, uncertainty, and raw notes.
    """
    __tablename__ = "experiment_measurements"

    id            = Column(String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("user_experiments.id",
                                                  ondelete="CASCADE"),
                           nullable=False, index=True)

    variable_name = Column(String(128), nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_text    = Column(String(512), nullable=True,
                           doc="for categorical values")
    unit          = Column(String(64), nullable=True)
    uncertainty   = Column(Float, nullable=True,
                           doc="standard deviation or half-width")
    notes         = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    experiment = relationship("UserExperiment", back_populates="measurements")


class RecommendationRun(Base):
    """
    One invocation of the Bayesian optimisation engine.
    Records the full snapshot so recommendations are reproducible.
    """
    __tablename__ = "recommendation_runs"

    id         = Column(String(36), primary_key=True,
                        default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("optimization_projects.id",
                                               ondelete="CASCADE"),
                        nullable=False, index=True)

    status  = Column(Enum(RecommendationStatus), nullable=False,
                     default=RecommendationStatus.pending)
    message = Column(Text, nullable=True,
                     doc="Error message or summary note")

    # Snapshot of data used
    n_literature_points = Column(Integer, default=0)
    n_user_points       = Column(Integer, default=0)
    n_candidates        = Column(Integer, default=0)

    # Model info
    model_type      = Column(String(64), nullable=True,
                             doc="e.g. 'GaussianProcessRegressor'")
    acquisition_fn  = Column(String(64), nullable=True,
                             doc="e.g. 'EI', 'UCB', 'literature_heuristic'")

    # Full result JSON for debugging / transparency
    result_json = Column(JSON, nullable=True)

    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project    = relationship("OptimizationProject",
                              back_populates="recommendation_runs")
    candidates = relationship("RecommendedCandidate",
                              back_populates="run",
                              cascade="all, delete-orphan",
                              order_by="RecommendedCandidate.rank")


class RecommendedCandidate(Base):
    """
    One candidate experiment proposed by the BO engine in a recommendation run.
    """
    __tablename__ = "recommended_candidates"

    id     = Column(String(36), primary_key=True,
                    default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("recommendation_runs.id",
                                          ondelete="CASCADE"),
                    nullable=False, index=True)

    rank = Column(Integer, nullable=False, default=1,
                  doc="1 = best candidate")

    # Proposed input conditions { variable_name: value, ... }
    proposed_inputs = Column(JSON, nullable=True)

    # Model predictions
    predicted_mean        = Column(Float, nullable=True)
    predicted_std         = Column(Float, nullable=True)
    acquisition_score     = Column(Float, nullable=True)

    # Human-readable explanation
    explanation = Column(Text, nullable=True)

    # Nearest literature references (list of paper IDs)
    supporting_paper_ids = Column(JSON, nullable=True)

    # Did the user actually run this experiment?
    was_executed          = Column(Boolean, default=False)
    executed_experiment_id = Column(String(36), nullable=True,
                                    doc="FK to user_experiments.id if executed")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    run = relationship("RecommendationRun", back_populates="candidates")
