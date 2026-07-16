"""Build scored and marketplace-ready CSV exports."""

from __future__ import annotations

import pandas as pd


MARKETPLACE_REQUIRED_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Capability",
    "Run Count",
    "Transaction Volume",
    "Customer Count",
    "Resell Score",
    "Product Score",
    "Opportunity Score",
    "Opportunity Level",
    "Risk Level",
    "Priority Level",
)
MARKETPLACE_EXPORT_COLUMNS = (
    "Task ID",
    "Task Name",
    "Task Type",
    "Department",
    "Reference Customer",
    "Task Description",
    "Monthly Run Count",
    "Transaction Volume",
    "Customer Reach",
    "Resellability Score",
    "Productization Score",
    "Opportunity Score",
    "Risk Level",
    "Priority Level",
    "Marketplace Status",
)


def _validate_export_data(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...],
) -> None:
    """Validate a dataframe against an export contract."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("Export data must be a pandas DataFrame")

    missing_columns = sorted(set(required_columns) - set(dataframe.columns))
    if missing_columns:
        raise ValueError(f"Export data is missing columns: {missing_columns}")


def build_scored_export(scores: pd.DataFrame) -> pd.DataFrame:
    """Return scored flows ordered from highest to lowest opportunity."""
    if not isinstance(scores, pd.DataFrame):
        raise TypeError("Export data must be a pandas DataFrame")
    if "Opportunity Score" not in scores.columns:
        raise ValueError("Export data is missing columns: ['Opportunity Score']")

    return scores.sort_values("Opportunity Score", ascending=False).copy()


def build_marketplace_export(scores: pd.DataFrame) -> pd.DataFrame:
    """Convert scored flows into the marketplace task import format."""
    _validate_export_data(scores, MARKETPLACE_REQUIRED_COLUMNS)
    ordered_scores = scores.sort_values(
        "Opportunity Score",
        ascending=False,
    ).copy()

    marketplace_status = pd.Series(
        "Backlog",
        index=ordered_scores.index,
        dtype="string",
    )
    marketplace_status.loc[
        ordered_scores["Opportunity Level"].eq("Medium")
    ] = "Candidate"
    marketplace_status.loc[
        ordered_scores["Opportunity Level"].eq("High")
    ] = "Ready"
    marketplace_status.loc[
        ordered_scores["Risk Level"].eq("Critical")
    ] = "Risk Review"

    target_departments = (
        ordered_scores["Predicted Department"]
        if "Predicted Department" in ordered_scores.columns
        else ordered_scores["Department"]
    )
    task_description = (
        ordered_scores["Flow Name"].astype(str)
        + " is a "
        + ordered_scores["Capability"].astype(str)
        + " flow matched to "
        + target_departments.astype(str)
        + "."
    )

    marketplace = pd.DataFrame(
        {
            "Task ID": ordered_scores["Flow ID"],
            "Task Name": ordered_scores["Flow Name"],
            "Task Type": ordered_scores["Capability"],
            "Department": target_departments,
            "Reference Customer": ordered_scores["Customer"],
            "Task Description": task_description,
            "Monthly Run Count": ordered_scores["Run Count"],
            "Transaction Volume": ordered_scores["Transaction Volume"],
            "Customer Reach": ordered_scores["Customer Count"],
            "Resellability Score": ordered_scores["Resell Score"],
            "Productization Score": ordered_scores["Product Score"],
            "Opportunity Score": ordered_scores["Opportunity Score"],
            "Risk Level": ordered_scores["Risk Level"],
            "Priority Level": ordered_scores["Priority Level"],
            "Marketplace Status": marketplace_status,
        }
    )
    return marketplace.loc[:, MARKETPLACE_EXPORT_COLUMNS].reset_index(drop=True)


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """Serialize a dataframe as an Excel-compatible UTF-8 CSV file."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("Export data must be a pandas DataFrame")
    return dataframe.to_csv(index=False).encode("utf-8-sig")
