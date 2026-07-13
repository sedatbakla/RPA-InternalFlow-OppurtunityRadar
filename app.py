"""Streamlit dashboard for scored internal flow opportunities."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from export import (
    build_marketplace_export,
    build_scored_export,
    dataframe_to_csv_bytes,
)
from pipeline import load_or_build_scores
from recommendation import build_customer_recommendations


REQUIRED_SCORE_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Capability",
    "Run Count",
    "Error Rate",
    "Customer Count",
    "Risk Score",
    "Risk Level",
    "Product Score",
    "Opportunity Score",
    "Opportunity Level",
    "Priority Score",
    "Priority Level",
)
DISPLAY_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Capability",
    "Run Count",
    "Customer Count",
    "Opportunity Score",
    "Opportunity Level",
    "Product Score",
    "Risk Score",
    "Risk Level",
    "Priority Score",
    "Priority Level",
)
TOP_OPPORTUNITY_COLUMNS = (
    "Flow Name",
    "Department",
    "Capability",
    "Customer Count",
    "Opportunity Score",
    "Opportunity Level",
    "Product Score",
    "Risk Level",
)
RISK_COLUMNS = (
    "Flow Name",
    "Department",
    "Capability",
    "Error Rate",
    "Risk Score",
    "Risk Level",
    "Priority Score",
    "Priority Level",
)
RISK_LEVELS = ("Low", "Medium", "High", "Critical")


def load_dashboard_data() -> pd.DataFrame:
    """Load scored flows and validate the dashboard data contract."""
    scores = load_or_build_scores(REQUIRED_SCORE_COLUMNS)
    if scores.empty:
        raise ValueError("The flow_scores table contains no records")

    missing_columns = sorted(set(REQUIRED_SCORE_COLUMNS) - set(scores.columns))
    if missing_columns:
        raise ValueError(f"The flow_scores table is missing columns: {missing_columns}")

    numeric_columns = (
        "Error Rate",
        "Customer Count",
        "Opportunity Score",
        "Product Score",
        "Risk Score",
        "Priority Score",
    )
    for column in numeric_columns:
        converted = pd.to_numeric(scores[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"Dashboard column '{column}' contains invalid values")
        scores[column] = converted

    return scores


def apply_filters(
    scores: pd.DataFrame,
    departments: list[str] | None = None,
    capabilities: list[str] | None = None,
    opportunity_range: tuple[float, float] = (0.0, 100.0),
    risk_levels: list[str] | None = None,
) -> pd.DataFrame:
    """Return flows matching the selected dashboard filters."""
    filtered = scores.copy()

    if departments:
        filtered = filtered[filtered["Department"].isin(departments)]
    if capabilities:
        filtered = filtered[filtered["Capability"].isin(capabilities)]
    if risk_levels:
        filtered = filtered[filtered["Risk Level"].isin(risk_levels)]

    minimum_score, maximum_score = opportunity_range
    filtered = filtered[
        filtered["Opportunity Score"].between(minimum_score, maximum_score)
    ]
    return filtered


def render_filters(scores: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar controls and return the filtered portfolio."""
    st.sidebar.header("Filters")
    departments = st.sidebar.multiselect(
        "Department",
        options=sorted(scores["Department"].unique()),
    )
    capabilities = st.sidebar.multiselect(
        "Capability",
        options=sorted(scores["Capability"].unique()),
    )
    opportunity_range = st.sidebar.slider(
        "Opportunity score",
        min_value=0.0,
        max_value=100.0,
        value=(0.0, 100.0),
        step=1.0,
    )
    risk_levels = st.sidebar.multiselect(
        "Risk level",
        options=RISK_LEVELS,
    )

    filtered = apply_filters(
        scores,
        departments=departments,
        capabilities=capabilities,
        opportunity_range=opportunity_range,
        risk_levels=risk_levels,
    )
    st.sidebar.caption(f"{len(filtered)} of {len(scores)} flows")
    return filtered


def render_summary(scores: pd.DataFrame) -> None:
    """Render the primary portfolio metrics."""
    visible_flows = len(scores)
    average_opportunity = (
        scores["Opportunity Score"].mean() if visible_flows else 0.0
    )
    high_opportunities = scores["Opportunity Level"].eq("High").sum()
    critical_risks = scores["Risk Level"].eq("Critical").sum()

    total_column, average_column, opportunity_column, risk_column = st.columns(4)
    total_column.metric("Visible flows", f"{visible_flows}")
    average_column.metric("Average opportunity", f"{average_opportunity:.1f}")
    opportunity_column.metric("High opportunities", f"{high_opportunities}")
    risk_column.metric("Critical risks", f"{critical_risks}")


def render_exports(scores: pd.DataFrame) -> None:
    """Render downloads for the currently filtered portfolio."""
    scored_export = build_scored_export(scores)
    marketplace_export = build_marketplace_export(scores)
    downloads_disabled = scores.empty

    st.sidebar.divider()
    st.sidebar.subheader("Export")
    st.sidebar.download_button(
        "Scored results",
        data=dataframe_to_csv_bytes(scored_export),
        file_name="internalflow_scored_results.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
        disabled=downloads_disabled,
    )
    st.sidebar.download_button(
        "Marketplace tasks",
        data=dataframe_to_csv_bytes(marketplace_export),
        file_name="internalflow_marketplace_tasks.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
        disabled=downloads_disabled,
    )


def render_flow_table(
    scores: pd.DataFrame,
    columns: tuple[str, ...],
    height: int,
) -> None:
    """Render a consistently formatted flow table."""
    if scores.empty:
        st.info("No flows match this view.")
        return

    st.dataframe(
        scores.loc[:, columns],
        hide_index=True,
        width="stretch",
        height=height,
        column_config={
            "Flow ID": st.column_config.NumberColumn("Flow ID", format="%d"),
            "Opportunity Score": st.column_config.ProgressColumn(
                "Opportunity",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Product Score": st.column_config.ProgressColumn(
                "Product",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Risk Score": st.column_config.ProgressColumn(
                "Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Priority Score": st.column_config.ProgressColumn(
                "Priority",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
        },
    )


def render_dashboard_views(
    scores: pd.DataFrame,
    recommendation_scores: pd.DataFrame,
) -> None:
    """Render opportunity, risk, and full portfolio views."""
    opportunity_tab, risk_tab, growth_tab, all_flows_tab = st.tabs(
        ["Top opportunities", "Risk monitoring", "Customer growth", "All flows"]
    )

    with opportunity_tab:
        top_opportunities = scores.nlargest(10, "Opportunity Score")
        st.caption(f"Top {len(top_opportunities)} matching flows")
        render_flow_table(
            top_opportunities,
            TOP_OPPORTUNITY_COLUMNS,
            height=390,
        )

    with risk_tab:
        risky_flows = scores[
            scores["Risk Level"].isin(["High", "Critical"])
        ].sort_values(
            ["Risk Score", "Priority Score"],
            ascending=False,
        )
        st.caption(f"{len(risky_flows)} high-risk flows")
        render_flow_table(risky_flows, RISK_COLUMNS, height=480)

    with growth_tab:
        recommendations = build_customer_recommendations(recommendation_scores)
        customer_options = [
            "All customers",
            *sorted(recommendations["Target Customer"].unique()),
        ]
        selected_customer = st.selectbox(
            "Target customer",
            options=customer_options,
            width=320,
        )
        if selected_customer != "All customers":
            recommendations = recommendations[
                recommendations["Target Customer"].eq(selected_customer)
            ]

        st.caption(f"{len(recommendations)} customer growth opportunities")
        if recommendations.empty:
            st.info("No customer growth opportunities match this view.")
        else:
            st.dataframe(
                recommendations,
                hide_index=True,
                width="stretch",
                height=480,
                column_config={
                    "Opportunity Score": st.column_config.ProgressColumn(
                        "Opportunity",
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                    "Product Score": st.column_config.ProgressColumn(
                        "Product",
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                    "Risk Score": st.column_config.ProgressColumn(
                        "Risk",
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                },
            )

    with all_flows_tab:
        ordered_scores = scores.sort_values(
            "Opportunity Score",
            ascending=False,
        )
        st.caption(f"{len(ordered_scores)} matching flows")
        render_flow_table(ordered_scores, DISPLAY_COLUMNS, height=520)


def main() -> None:
    """Render the InternalFlow Opportunity Radar dashboard."""
    st.set_page_config(
        page_title="InternalFlow Opportunity Radar",
        layout="wide",
    )

    st.title("InternalFlow Opportunity Radar")
    st.caption(
        "Scored internal flows ranked for product opportunity and operational risk."
    )

    try:
        scores = load_dashboard_data()
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        st.error("Scored flow data is not available.")
        st.caption(str(error))
        st.code(
            "python pipeline.py",
            language="bash",
        )
        st.stop()

    filtered_scores = render_filters(scores)
    render_exports(filtered_scores)
    render_summary(filtered_scores)
    st.divider()
    render_dashboard_views(filtered_scores, scores)


if __name__ == "__main__":
    main()
