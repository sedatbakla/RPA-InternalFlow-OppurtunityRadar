"""Load, validate, enrich, and import the project CSV files into SQLite."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from database import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = PROJECT_ROOT / "data"
FLOW_CATALOG_PATH = DATA_DIRECTORY / "flow_catalog_sample.csv"
TAXONOMY_PATH = DATA_DIRECTORY / "task_capability_taxonomy.csv"

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
TAXONOMY_REQUIRED_COLUMNS = ("Keyword", "Capability")
FLOW_NUMERIC_COLUMNS = (
    "Flow ID",
    "Run Count",
    "Error Rate",
    "Manual Time",
    "Transaction Volume",
)
FLOW_TEXT_COLUMNS = ("Flow Name", "Customer", "Department", "Capability")


def _read_csv(path: Path, required_columns: tuple[str, ...]) -> pd.DataFrame:
    """Read a non-empty CSV and verify its required columns and values."""
    if not path.is_file():
        raise FileNotFoundError(f"Required CSV file was not found: {path}")

    try:
        dataframe = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"CSV file is empty: {path}") from error
    except pd.errors.ParserError as error:
        raise ValueError(f"CSV file could not be parsed: {path}") from error

    if dataframe.empty:
        raise ValueError(f"CSV file contains no data rows: {path}")

    dataframe.columns = dataframe.columns.str.strip()
    if dataframe.columns.duplicated().any():
        raise ValueError(f"CSV file contains duplicate column names: {path}")

    missing_columns = sorted(set(required_columns) - set(dataframe.columns))
    if missing_columns:
        raise ValueError(
            f"CSV file is missing required columns {missing_columns}: {path}"
        )

    empty_columns = [
        column
        for column in required_columns
        if (
            dataframe[column].isna()
            | dataframe[column].astype(str).str.strip().eq("")
        ).any()
    ]
    if empty_columns:
        raise ValueError(
            f"CSV file contains empty required values in columns {empty_columns}: {path}"
        )

    return dataframe


def load_flows(path: Path = FLOW_CATALOG_PATH) -> pd.DataFrame:
    """Load flow records and derive customer counts by capability."""
    flows = _read_csv(path, FLOW_REQUIRED_COLUMNS)

    for column in FLOW_TEXT_COLUMNS:
        flows[column] = flows[column].astype(str).str.strip()

    for column in FLOW_NUMERIC_COLUMNS:
        converted = pd.to_numeric(flows[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"Column '{column}' must contain only numeric values: {path}")
        if (converted < 0).any():
            raise ValueError(f"Column '{column}' cannot contain negative values: {path}")
        flows[column] = converted

    if (flows["Flow ID"] % 1 != 0).any():
        raise ValueError(f"Column 'Flow ID' must contain whole numbers: {path}")
    flows["Flow ID"] = flows["Flow ID"].astype(int)

    if flows["Flow ID"].duplicated().any():
        raise ValueError(f"Column 'Flow ID' must contain unique values: {path}")

    flows["Customer Count"] = (
        flows.groupby("Capability")["Customer"].transform("nunique").astype(int)
    )

    return flows


def load_taxonomy(path: Path = TAXONOMY_PATH) -> pd.DataFrame:
    """Load and validate the keyword-to-capability taxonomy."""
    taxonomy = _read_csv(path, TAXONOMY_REQUIRED_COLUMNS)
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