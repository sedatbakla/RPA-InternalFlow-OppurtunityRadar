"""Shared source-data contracts and controlled column normalization."""

from __future__ import annotations

import re

import pandas as pd


FLOW_REQUIRED_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Capability",
    "Run Count",
    "Error Rate",
    "Manual Time",
    "Transaction Volume",
)
FLOW_NUMERIC_COLUMNS = (
    "Flow ID",
    "Run Count",
    "Error Rate",
    "Manual Time",
    "Transaction Volume",
)
FLOW_TEXT_COLUMNS = ("Flow Name", "Customer", "Department", "Capability")
TAXONOMY_REQUIRED_COLUMNS = ("Keyword", "Capability")
CAPABILITY_DEPARTMENT_MAP = {
    "Finance": "Finance",
    "Government Affairs": "Government Affairs",
    "HR": "HR",
    "IT": "IT",
    "Legal": "Legal",
    "Operations": "Operations",
    "Planning": "Planning",
    "Sales": "Sales",
}

_KNOWN_COLUMNS = (
    *FLOW_REQUIRED_COLUMNS,
    *TAXONOMY_REQUIRED_COLUMNS,
    "Customer Count",
)
_DEPARTMENT_LOOKUP = {
    capability.casefold(): department
    for capability, department in CAPABILITY_DEPARTMENT_MAP.items()
}


def _column_key(column: object) -> str:
    """Return a conservative comparison key for a column label."""
    label = str(column).replace("\ufeff", "").strip()
    return re.sub(r"[\s_]+", " ", label).casefold()


_COLUMN_LOOKUP = {_column_key(column): column for column in _KNOWN_COLUMNS}


def normalize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize known column labels without guessing unrelated aliases."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("Dataset must be a pandas DataFrame")

    normalized = dataframe.copy()
    column_names: list[str] = []
    for column in normalized.columns:
        stripped = str(column).replace("\ufeff", "").strip()
        column_names.append(_COLUMN_LOOKUP.get(_column_key(stripped), stripped))

    empty_columns = [index + 1 for index, name in enumerate(column_names) if not name]
    if empty_columns:
        raise ValueError(f"Dataset contains unnamed columns at positions: {empty_columns}")

    duplicates = sorted(
        {name for name in column_names if column_names.count(name) > 1}
    )
    if duplicates:
        raise ValueError(f"Dataset contains duplicate column names: {duplicates}")

    normalized.columns = column_names
    return normalized


def match_department(
    capability: object,
    source_department: object,
) -> tuple[str, str]:
    """Return the target department and an auditable match status."""
    capability_name = str(capability).strip()
    source_name = str(source_department).strip()
    predicted = _DEPARTMENT_LOOKUP.get(capability_name.casefold())
    if predicted is None:
        return source_name, "Source retained"
    if predicted.casefold() == source_name.casefold():
        return predicted, "Matched"
    return predicted, "Review"
