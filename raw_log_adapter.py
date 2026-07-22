"""Convert raw RPA task log data (test_veri.xlsx) into the flow_catalog
format expected by the Internal Flow Opportunity Radar system.

Usage:
    python raw_log_adapter.py <path-to-source-xlsx> <path-to-output-csv>

If no arguments are given, it looks for "test_veri.xlsx" in the same
folder as this script, and writes "flow_catalog_from_real_data.csv"
next to it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


MANUAL_TIME_CAP = 480  # ~99th percentile of Human Time; caps extreme outliers


def load_source(path: Path) -> pd.DataFrame:
    """Read the raw task log Excel file."""
    return pd.read_excel(path)


def filter_active(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only flows currently marked as Active."""
    return df[df["Task_Statu"] == "Aktif"].copy()


def normalize_task_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase Task_Code so casing differences don't split one flow into several."""
    df = df.copy()
    df["Task_Code"] = df["Task_Code"].str.upper()
    return df


def prepare_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add helper columns used by the grouping step."""
    df = df.copy()
    df["Human Time (capped)"] = df["Human Time"].clip(upper=MANUAL_TIME_CAP)
    df["is_resolved"] = df["Statu"].isin(["Success", "Failed"])
    df["is_failed"] = df["Statu"] == "Failed"
    return df


def group_by_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse many log rows per Task_Code into one summary row per flow."""
    grouped = df.groupby("Task_Code").agg(
        Customer=("Customer", "first"),
        Run_Count=("Task_Code", "size"),
        Resolved_Count=("is_resolved", "sum"),
        Failed_Count=("is_failed", "sum"),
        Manual_Time=("Human Time (capped)", "median"),
        Transaction_Volume=("DataCounter_2", lambda s: s.fillna(0).sum()),
    ).reset_index()

    # Error Rate = Failed / (Success + Failed); flows with zero resolved
    # runs get 0 rather than an undefined division.
    grouped["Error_Rate"] = (
        grouped["Failed_Count"] / grouped["Resolved_Count"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    return grouped


def finalize_schema(grouped: pd.DataFrame) -> pd.DataFrame:
    """Rename/reorder columns to match the flow_catalog schema and add
    placeholder values for fields the raw data does not provide."""
    grouped = grouped.sort_values("Task_Code").reset_index(drop=True)
    grouped["Flow ID"] = range(1, len(grouped) + 1)

    # The raw data has no real Department or Capability. Both are
    # currently "required" (non-empty) by the system, so a placeholder
    # is used until Department is made optional in data_contract.py.
    # "Unknown" is NOT a real ground-truth label.
    grouped["Department"] = "Unknown"
    grouped["Capability"] = "Unknown"

    final = grouped.rename(columns={
        "Task_Code": "Flow Name",
        "Run_Count": "Run Count",
        "Error_Rate": "Error Rate",
        "Manual_Time": "Manual Time",
        "Transaction_Volume": "Transaction Volume",
    })

    return final[[
        "Flow ID", "Flow Name", "Customer", "Department", "Capability",
        "Run Count", "Error Rate", "Manual Time", "Transaction Volume",
    ]]


def convert(source_path: Path) -> pd.DataFrame:
    """Run the full conversion pipeline on one raw log file."""
    df = load_source(source_path)
    df = filter_active(df)
    df = normalize_task_codes(df)
    df = prepare_columns(df)
    grouped = group_by_flow(df)
    return finalize_schema(grouped)


def main() -> None:
    script_dir = Path(__file__).resolve().parent

    if len(sys.argv) >= 3:
        source_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    else:
        source_path = script_dir / "test_veri.xlsx"
        output_path = script_dir / "flow_catalog_from_real_data.csv"

    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    result = convert(source_path)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Converted {len(result)} unique flows.")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
