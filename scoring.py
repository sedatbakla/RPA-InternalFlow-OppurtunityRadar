"""Calculate opportunity, risk, product, and priority scores for flows."""

from __future__ import annotations

import pandas as pd

from database import get_all_flows, get_classifications, save_scores


FLOW_REQUIRED_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Run Count",
    "Error Rate",
    "Manual Time",
    "Transaction Volume",
)
CLASSIFICATION_REQUIRED_COLUMNS = ("Flow ID", "Predicted Capability")
NUMERIC_COLUMNS = (
    "Run Count",
    "Error Rate",
    "Manual Time",
    "Transaction Volume",
)
SCORE_COLUMNS = (
    "Usage Score",
    "Risk Score",
    "Time Saving Score",
    "Resell Score",
    "Transaction Score",
    "Product Score",
    "Business Impact",
    "Criticality Score",
    "Opportunity Score",
    "Priority Score",
)


def _validate_dataframe(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...],
    source_name: str,
) -> None:
    """Validate required columns and values for a scoring input."""
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


def _max_normalize(series: pd.Series) -> pd.Series:
    """Normalize numeric values to a 0-100 scale without dividing by zero."""
    maximum = series.max()
    if maximum <= 0:
        return pd.Series(0.0, index=series.index)
    return (series / maximum) * 100


def _categorize_scores(
    scores: pd.Series,
    boundaries: list[float],
    labels: list[str],
) -> pd.Series:
    """Convert numeric scores into ordered business labels."""
    return pd.cut(
        scores,
        bins=[float("-inf"), *boundaries, float("inf")],
        labels=labels,
        right=False,
    ).astype("string")


def _merge_classifications(
    flows: pd.DataFrame,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    """Join one classification to each flow by its stable identifier."""
    _validate_dataframe(flows, FLOW_REQUIRED_COLUMNS, "Flow")
    _validate_dataframe(
        classifications,
        CLASSIFICATION_REQUIRED_COLUMNS,
        "Classification",
    )

    if flows["Flow ID"].duplicated().any():
        raise ValueError("Flow IDs must be unique")
    if classifications["Flow ID"].duplicated().any():
        raise ValueError("Classification Flow IDs must be unique")

    flow_ids = set(flows["Flow ID"])
    classification_ids = set(classifications["Flow ID"])
    missing_ids = sorted(flow_ids - classification_ids)
    unexpected_ids = sorted(classification_ids - flow_ids)
    if missing_ids or unexpected_ids:
        raise ValueError(
            "Flow and classification IDs do not match. "
            f"Missing classifications: {missing_ids}; "
            f"unexpected classifications: {unexpected_ids}"
        )

    classification_columns = ["Flow ID", "Predicted Capability"]
    if "Matched Keyword" in classifications.columns:
        classification_columns.append("Matched Keyword")

    merged = flows.merge(
        classifications[classification_columns],
        on="Flow ID",
        how="left",
        validate="one_to_one",
    )

    if "Capability" in merged.columns:
        merged = merged.rename(columns={"Capability": "Original Capability"})
    else:
        merged["Original Capability"] = pd.NA

    if "Matched Keyword" not in merged.columns:
        merged["Matched Keyword"] = pd.NA

    merged = merged.rename(columns={"Predicted Capability": "Capability"})
    merged["Capability"] = merged["Capability"].astype(str).str.strip()
    merged["Customer Count"] = (
        merged.groupby("Capability")["Customer"].transform("nunique").astype(int)
    )
    return merged


def score_flows(
    flows: pd.DataFrame,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    """Return dashboard-ready flow records with calculated scores and levels."""
    scored = _merge_classifications(flows.copy(), classifications.copy())

    for column in NUMERIC_COLUMNS:
        converted = pd.to_numeric(scored[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"Column '{column}' must contain only numeric values")
        if (converted < 0).any():
            raise ValueError(f"Column '{column}' cannot contain negative values")
        scored[column] = converted

    scored["Usage Score"] = _max_normalize(scored["Run Count"])
    scored["Risk Score"] = (scored["Error Rate"] * 10).clip(upper=100)
    scored["Time Saving Score"] = _max_normalize(scored["Manual Time"])
    scored["Resell Score"] = _max_normalize(scored["Customer Count"])
    scored["Transaction Score"] = _max_normalize(scored["Transaction Volume"])

    scored["Product Score"] = (
        scored["Usage Score"] * 0.60 + scored["Resell Score"] * 0.40
    )
    scored["Business Impact"] = (
        scored["Transaction Score"] * 0.60
        + scored["Time Saving Score"] * 0.40
    )
    scored["Criticality Score"] = (
        scored["Transaction Score"] * 0.50 + scored["Usage Score"] * 0.50
    )
    scored["Opportunity Score"] = (
        scored["Usage Score"] * 0.30
        + scored["Transaction Score"] * 0.25
        + scored["Product Score"] * 0.30
        + scored["Time Saving Score"] * 0.15
        - scored["Risk Score"] * 0.20
    ).clip(lower=0, upper=100)
    scored["Priority Score"] = (
        scored["Risk Score"] * 0.60 + scored["Criticality Score"] * 0.40
    ).clip(lower=0, upper=100)

    scored["Risk Level"] = _categorize_scores(
        scored["Risk Score"],
        boundaries=[30, 60, 80],
        labels=["Low", "Medium", "High", "Critical"],
    )
    scored["Opportunity Level"] = _categorize_scores(
        scored["Opportunity Score"],
        boundaries=[30, 60],
        labels=["Low", "Medium", "High"],
    )
    scored["Priority Level"] = _categorize_scores(
        scored["Priority Score"],
        boundaries=[30, 50, 70],
        labels=["Low", "Medium", "High", "Critical"],
    )

    scored.loc[:, SCORE_COLUMNS] = scored.loc[:, SCORE_COLUMNS].round(3)

    output_columns = [
        "Flow ID",
        "Flow Name",
        "Customer",
        "Department",
        "Capability",
        "Original Capability",
        "Matched Keyword",
        "Run Count",
        "Error Rate",
        "Manual Time",
        "Transaction Volume",
        "Customer Count",
        "Usage Score",
        "Risk Score",
        "Risk Level",
        "Time Saving Score",
        "Resell Score",
        "Transaction Score",
        "Product Score",
        "Business Impact",
        "Criticality Score",
        "Opportunity Score",
        "Opportunity Level",
        "Priority Score",
        "Priority Level",
    ]
    return scored.loc[:, output_columns]


def run_scoring() -> pd.DataFrame:
    """Calculate scores from imported and classified data, then save them."""
    scores = score_flows(get_all_flows(), get_classifications())
    save_scores(scores)
    return scores


def main() -> None:
    """Run scoring after import and classification are complete."""
    scores = run_scoring()
    top_opportunity = scores.nlargest(1, "Opportunity Score").iloc[0]
    print(
        f"Scored {len(scores)} flows. Top opportunity: "
        f"{top_opportunity['Flow Name']} "
        f"({top_opportunity['Opportunity Score']:.3f})."
    )


if __name__ == "__main__":
    main()