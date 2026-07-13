"""Generate customer growth recommendations from scored flow usage."""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd


RECOMMENDATION_REQUIRED_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Capability",
    "Opportunity Score",
    "Product Score",
    "Risk Score",
    "Risk Level",
)
RECOMMENDATION_COLUMNS = (
    "Target Customer",
    "Recommended Capability",
    "Reference Flow",
    "Reference Customer",
    "Reference Department",
    "Customer Reach",
    "Opportunity Score",
    "Product Score",
    "Risk Score",
    "Risk Level",
    "Recommendation Reason",
)


def _validate_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Return a validated copy of scored flow data."""
    if not isinstance(scores, pd.DataFrame):
        raise TypeError("Recommendation data must be a pandas DataFrame")
    if scores.empty:
        return scores.copy()

    missing_columns = sorted(
        set(RECOMMENDATION_REQUIRED_COLUMNS) - set(scores.columns)
    )
    if missing_columns:
        raise ValueError(
            f"Recommendation data is missing columns: {missing_columns}"
        )

    prepared = scores.copy()
    text_columns = (
        "Flow Name",
        "Customer",
        "Department",
        "Capability",
        "Risk Level",
    )
    for column in text_columns:
        invalid_values = (
            prepared[column].isna()
            | prepared[column].astype(str).str.strip().eq("")
        )
        if invalid_values.any():
            raise ValueError(
                f"Recommendation column '{column}' contains empty values"
            )
        prepared[column] = prepared[column].astype(str).str.strip()

    numeric_columns = (
        "Opportunity Score",
        "Product Score",
        "Risk Score",
    )
    for column in numeric_columns:
        converted = pd.to_numeric(prepared[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(
                f"Recommendation column '{column}' contains invalid values"
            )
        if ((converted < 0) | (converted > 100)).any():
            raise ValueError(
                f"Recommendation column '{column}' must be between 0 and 100"
            )
        prepared[column] = converted

    return prepared


def build_customer_recommendations(
    scores: pd.DataFrame,
    excluded_risk_levels: Collection[str] = ("Critical",),
) -> pd.DataFrame:
    """Recommend capabilities that each customer does not currently use."""
    prepared = _validate_scores(scores)
    if prepared.empty or prepared["Customer"].nunique() < 2:
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    excluded_levels = {
        str(level).strip().casefold() for level in excluded_risk_levels
    }
    candidates = prepared[
        ~prepared["Risk Level"].str.casefold().isin(excluded_levels)
    ].copy()
    if candidates.empty:
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    customers = sorted(prepared["Customer"].unique())
    existing_usage = set(
        prepared.loc[:, ["Customer", "Capability"]].itertuples(
            index=False,
            name=None,
        )
    )
    customer_reach = prepared.groupby("Capability")["Customer"].nunique()
    representatives = (
        candidates.sort_values(
            ["Capability", "Opportunity Score", "Product Score", "Risk Score"],
            ascending=[True, False, False, True],
        )
        .groupby("Capability", as_index=False)
        .first()
    )

    recommendations: list[dict[str, object]] = []
    for _, representative in representatives.iterrows():
        capability = representative["Capability"]
        reach = int(customer_reach.loc[capability])

        for customer in customers:
            if (customer, capability) in existing_usage:
                continue

            recommendations.append(
                {
                    "Target Customer": customer,
                    "Recommended Capability": capability,
                    "Reference Flow": representative["Flow Name"],
                    "Reference Customer": representative["Customer"],
                    "Reference Department": representative["Department"],
                    "Customer Reach": reach,
                    "Opportunity Score": representative["Opportunity Score"],
                    "Product Score": representative["Product Score"],
                    "Risk Score": representative["Risk Score"],
                    "Risk Level": representative["Risk Level"],
                    "Recommendation Reason": (
                        f"Used by {reach} existing customers; "
                        f"benchmark flow: {representative['Flow Name']}."
                    ),
                }
            )

    if not recommendations:
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    result = pd.DataFrame(recommendations)
    result = result.sort_values(
        [
            "Opportunity Score",
            "Product Score",
            "Customer Reach",
            "Target Customer",
        ],
        ascending=[False, False, False, True],
    )
    return result.loc[:, RECOMMENDATION_COLUMNS].reset_index(drop=True)
