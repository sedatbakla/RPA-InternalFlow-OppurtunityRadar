"""Classify flow names with the project capability taxonomy."""

from __future__ import annotations

import pandas as pd

from data_contract import match_department
from database import get_all_flows, get_taxonomy, save_classification


FLOW_REQUIRED_COLUMNS = ("Flow ID", "Flow Name")
TAXONOMY_REQUIRED_COLUMNS = ("Keyword", "Capability")


def _validate_columns(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...],
    source_name: str,
) -> None:
    """Validate that a non-empty DataFrame contains its required columns."""
    if dataframe.empty:
        raise ValueError(f"{source_name} data cannot be empty")

    missing_columns = sorted(set(required_columns) - set(dataframe.columns))
    if missing_columns:
        raise ValueError(f"{source_name} data is missing columns: {missing_columns}")

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
            f"{source_name} data contains empty values in columns: {empty_columns}"
        )


def _prepare_taxonomy(taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Return a validated and normalized taxonomy copy."""
    _validate_columns(taxonomy, TAXONOMY_REQUIRED_COLUMNS, "Taxonomy")
    prepared = taxonomy.loc[:, TAXONOMY_REQUIRED_COLUMNS].copy()
    prepared["Keyword"] = prepared["Keyword"].astype(str).str.strip()
    prepared["Capability"] = prepared["Capability"].astype(str).str.strip()

    if prepared["Keyword"].str.casefold().duplicated().any():
        raise ValueError("Taxonomy keywords must be unique")

    return prepared


def _classify_with_keyword(
    flow_name: str,
    taxonomy: pd.DataFrame,
) -> tuple[str, str | None]:
    """Return the first matching capability and keyword for a flow name."""
    normalized_name = flow_name.casefold()

    for keyword, capability in taxonomy.itertuples(index=False, name=None):
        if keyword.casefold() in normalized_name:
            return capability, keyword

    return "Other", None


def classify_flow(flow_name: str, taxonomy: pd.DataFrame) -> str:
    """Return the capability predicted for one flow name."""
    if not isinstance(flow_name, str) or not flow_name.strip():
        raise ValueError("flow_name must be a non-empty string")

    prepared_taxonomy = _prepare_taxonomy(taxonomy)
    capability, _ = _classify_with_keyword(flow_name.strip(), prepared_taxonomy)
    return capability


def classify_flows(flows: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Classify flows and derive an auditable target department."""
    _validate_columns(flows, FLOW_REQUIRED_COLUMNS, "Flow")
    if flows["Flow ID"].duplicated().any():
        raise ValueError("Flow IDs must be unique")

    prepared_taxonomy = _prepare_taxonomy(taxonomy)
    result = flows.loc[:, FLOW_REQUIRED_COLUMNS].copy()
    result["Flow Name"] = result["Flow Name"].astype(str).str.strip()

    matches = [
        _classify_with_keyword(flow_name, prepared_taxonomy)
        for flow_name in result["Flow Name"]
    ]
    result["Predicted Capability"] = [capability for capability, _ in matches]
    result["Matched Keyword"] = [keyword for _, keyword in matches]

    if "Capability" in flows.columns:
        result["Original Capability"] = flows["Capability"].astype(str).str.strip()
        result["Classification Correct"] = (
            result["Predicted Capability"].str.casefold()
            == result["Original Capability"].str.casefold()
        )

    if "Department" in flows.columns:
        result["Original Department"] = (
            flows["Department"].astype(str).str.strip()
        )
        department_matches = [
            match_department(capability, department)
            for capability, department in zip(
                result["Predicted Capability"],
                result["Original Department"],
                strict=True,
            )
        ]
        result["Predicted Department"] = [
            department for department, _ in department_matches
        ]
        result["Department Match"] = [
            status for _, status in department_matches
        ]

    return result


def run_classification() -> pd.DataFrame:
    """Classify imported flows and save the results to SQLite."""
    flows = get_all_flows()
    taxonomy = get_taxonomy()
    classifications = classify_flows(flows, taxonomy)
    save_classification(classifications)
    return classifications


def main() -> None:
    """Run classification after the CSV import step."""
    classifications = run_classification()
    matched_count = classifications["Matched Keyword"].notna().sum()
    message = (
        f"Classified {len(classifications)} flows; "
        f"{matched_count} matched a taxonomy keyword."
    )

    if "Classification Correct" in classifications.columns:
        accuracy = classifications["Classification Correct"].mean() * 100
        message += f" Ground-truth accuracy: {accuracy:.1f}%."

    print(message)


if __name__ == "__main__":
    main()
