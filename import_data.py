"""Load, validate, enrich, and import the project CSV files into SQLite."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_contract import (
    FLOW_NUMERIC_COLUMNS,
    FLOW_REQUIRED_COLUMNS,
    FLOW_TEXT_COLUMNS,
    TAXONOMY_REQUIRED_COLUMNS,
    normalize_column_names,
)
from database import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = PROJECT_ROOT / "data"
FLOW_CATALOG_PATH = DATA_DIRECTORY / "flow_catalog_sample.csv"
TAXONOMY_PATH = DATA_DIRECTORY / "task_capability_taxonomy.csv"


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a non-empty project CSV from disk."""
    if not path.is_file():
        raise FileNotFoundError(f"Required CSV file was not found: {path}")

    try:
        dataframe = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"CSV file is empty: {path}") from error
    except pd.errors.ParserError as error:
        raise ValueError(f"CSV file could not be parsed: {path}") from error

    dataframe = dataframe.dropna(how="all").reset_index(drop=True)
    if dataframe.empty:
        raise ValueError(f"CSV file contains no data rows: {path}")

    return normalize_column_names(dataframe)


def _validate_required_values(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...],
    source_name: str,
) -> None:
    """Validate required columns and non-empty values for one dataset."""
    if dataframe.empty:
        raise ValueError(f"{source_name} contains no data rows")

    missing_columns = sorted(set(required_columns) - set(dataframe.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"{source_name} is missing required columns: {missing}")

    empty_columns = [
        column
        for column in required_columns
        if (
            dataframe[column].isna()
            | dataframe[column].astype(str).str.strip().eq("")
        ).any()
    ]
    if empty_columns:
        empty = ", ".join(empty_columns)
        raise ValueError(
            f"{source_name} contains empty required values in columns: {empty}"
        )


def prepare_flows(
    dataframe: pd.DataFrame,
    source_name: str = "Flow dataset",
) -> pd.DataFrame:
    """Normalize and validate flow records, then derive customer counts."""
    flows = normalize_column_names(
        dataframe.dropna(how="all").reset_index(drop=True)
    )
    _validate_required_values(flows, FLOW_REQUIRED_COLUMNS, source_name)

    for column in FLOW_TEXT_COLUMNS:
        flows[column] = flows[column].astype(str).str.strip()

    for column in FLOW_NUMERIC_COLUMNS:
        converted = pd.to_numeric(flows[column], errors="coerce")
        invalid_numeric = converted.isna() | converted.isin(
            [float("inf"), float("-inf")]
        )
        if invalid_numeric.any():
            invalid_rows = (invalid_numeric[invalid_numeric].index + 2).tolist()
            raise ValueError(
                f"Column '{column}' must contain only numeric values "
                f"at CSV/worksheet rows {invalid_rows}: {source_name}"
            )
        if (converted < 0).any():
            raise ValueError(
                f"Column '{column}' cannot contain negative values: {source_name}"
            )
        flows[column] = converted

    if (flows["Flow ID"] % 1 != 0).any():
        raise ValueError(
            f"Column 'Flow ID' must contain whole numbers: {source_name}"
        )
    flows["Flow ID"] = flows["Flow ID"].astype(int)

    if flows["Flow ID"].duplicated().any():
        raise ValueError(
            f"Column 'Flow ID' must contain unique values: {source_name}"
        )

    flows["Customer Count"] = (
        flows.groupby("Capability")["Customer"].transform("nunique").astype(int)
    )
    return flows


def load_flows(path: Path = FLOW_CATALOG_PATH) -> pd.DataFrame:
    """Load flow records and derive customer counts by capability."""
    return prepare_flows(_read_csv(path), source_name=str(path))


def load_taxonomy(path: Path = TAXONOMY_PATH) -> pd.DataFrame:
    """Load and validate the keyword-to-capability taxonomy."""
    taxonomy = _read_csv(path)
    _validate_required_values(taxonomy, TAXONOMY_REQUIRED_COLUMNS, str(path))
    taxonomy["Keyword"] = taxonomy["Keyword"].astype(str).str.strip()
    taxonomy["Capability"] = taxonomy["Capability"].astype(str).str.strip()

    if taxonomy["Keyword"].str.casefold().duplicated().any():
        raise ValueError(f"Taxonomy keywords must be unique: {path}")

    return taxonomy


def _replace_table(dataframe: pd.DataFrame, table_name: str) -> None:
    """Replace a SQLite table and always close the database connection."""
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


def import_flows(path: Path = FLOW_CATALOG_PATH) -> pd.DataFrame:
    """Validate, enrich, and import flow records into SQLite."""
    flows = load_flows(path)
    _replace_table(flows, "flows")
    return flows


def import_taxonomy(path: Path = TAXONOMY_PATH) -> pd.DataFrame:
    """Validate and import taxonomy records into SQLite."""
    taxonomy = load_taxonomy(path)
    _replace_table(taxonomy, "taxonomy")
    return taxonomy


def main() -> None:
    """Import both project CSV files in the required pipeline order."""
    flows = import_flows()
    taxonomy = import_taxonomy()
    print(f"Imported {len(flows)} flow records and {len(taxonomy)} taxonomy records.")


if __name__ == "__main__":
    main()
