"""Coordinate the complete data preparation pipeline for the application."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from classifier import run_classification
from database import get_scores
from import_data import import_flows, import_taxonomy
from scoring import run_scoring


def run_pipeline() -> pd.DataFrame:
    """Import source data, classify flows, calculate scores, and persist results."""
    import_flows()
    import_taxonomy()
    run_classification()
    return run_scoring()


def load_or_build_scores(
    required_columns: Iterable[str] = (),
) -> pd.DataFrame:
    """Return ready scores or rebuild them when the stored result is unavailable."""
    required = set(required_columns)

    try:
        scores = get_scores()
    except RuntimeError:
        return run_pipeline()

    missing_columns = required - set(scores.columns)
    if scores.empty or missing_columns:
        return run_pipeline()

    return scores


def main() -> None:
    """Build all pipeline tables from the project CSV files."""
    scores = run_pipeline()
    print(f"Prepared {len(scores)} scored flow records.")


if __name__ == "__main__":
    main()
