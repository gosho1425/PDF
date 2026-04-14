"""
Utilities for transforming database records into BO-ready feature matrices.
[BO-READY] This module is the bridge between the paper extraction database
and the Bayesian optimization pipeline (Phase 2).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


def build_feature_matrix(
    records: List[dict],
    input_role: str = "input",
    output_role: str = "output",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transform a list of extraction records into X (inputs) and y (outputs)
    DataFrames suitable for Bayesian optimization.

    [BO-READY] Call this function in Phase 2 to feed data into the surrogate model.

    Args:
        records: List of extraction records (from export API JSON format)
        input_role: variable_role value for input features
        output_role: variable_role value for output targets

    Returns:
        (X, y) tuple of DataFrames, one row per paper.
        Missing values are represented as NaN.
    """
    X_rows = []
    y_rows = []

    for rec in records:
        paper_id = rec.get("paper_id", "unknown")
        extraction = rec.get("extraction", {})

        # Extract input features from bo_ready.X
        bo = extraction.get("bo_ready", {})
        x_row = {"paper_id": paper_id}
        for name, info in bo.get("X", {}).items():
            x_row[name] = info.get("value")
        X_rows.append(x_row)

        # Extract output targets from bo_ready.y
        y_row = {"paper_id": paper_id}
        for name, info in bo.get("y", {}).items():
            y_row[name] = info.get("value")
        y_rows.append(y_row)

    X = pd.DataFrame(X_rows).set_index("paper_id") if X_rows else pd.DataFrame()
    y = pd.DataFrame(y_rows).set_index("paper_id") if y_rows else pd.DataFrame()

    return X, y


def summarize_coverage(X: pd.DataFrame, y: pd.DataFrame) -> dict:
    """
    Summarize how much data is available for each variable.
    Useful for deciding which properties to target in BO.
    """
    return {
        "n_papers": len(X),
        "input_variables": {
            col: {
                "n_observed": int(X[col].notna().sum()),
                "coverage_pct": round(100 * X[col].notna().mean(), 1),
                "min": float(X[col].min()) if X[col].notna().any() else None,
                "max": float(X[col].max()) if X[col].notna().any() else None,
            }
            for col in X.columns
        },
        "output_variables": {
            col: {
                "n_observed": int(y[col].notna().sum()),
                "coverage_pct": round(100 * y[col].notna().mean(), 1),
                "min": float(y[col].min()) if y[col].notna().any() else None,
                "max": float(y[col].max()) if y[col].notna().any() else None,
            }
            for col in y.columns
        },
    }
