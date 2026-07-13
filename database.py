"""SQLite helpers for the Internal Flow Opportunity Radar data pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "db" / "arya.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the project-local SQLite database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def _read_table(table_name: str) -> pd.DataFrame:
    """Read a pipeline table and raise a clear error when it is unavailable."""
    connection = get_connection()

    try:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)
    except Exception as error:
        raise RuntimeError(
            f"The '{table_name}' table is unavailable. Run the required pipeline step first."
        ) from error
    finally:
        connection.close()


def _save_table(dataframe: pd.DataFrame, table_name: str) -> None:
    """Replace a pipeline table with the supplied DataFrame."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")

    connection = get_connection()

    try:
        dataframe.to_sql(
            name=table_name,
            con=connection,
            if_exists="replace",
            index=False,
        )
    finally:
        connection.close()


def get_all_flows() -> pd.DataFrame:
    """Return imported flow records."""
    return _read_table("flows")


def get_taxonomy() -> pd.DataFrame:
    """Return imported taxonomy records."""
    return _read_table("taxonomy")


def get_classifications() -> pd.DataFrame:
    """Return the latest keyword-based flow classifications."""
    return _read_table("flow_classification")


def get_scores() -> pd.DataFrame:
    """Return the latest calculated flow scores."""
    return _read_table("flow_scores")


def save_scores(dataframe: pd.DataFrame) -> None:
    """Save calculated scores for dashboard and export use."""
    _save_table(dataframe, "flow_scores")


def save_classification(dataframe: pd.DataFrame) -> None:
    """Save keyword-based capability classifications."""
    _save_table(dataframe, "flow_classification")