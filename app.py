"""Streamlit dashboard for scored internal flow opportunities."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from dataset_upload import (
    MAX_UPLOAD_MEGABYTES,
    dataset_fingerprint,
    load_uploaded_dataset,
    safe_file_name,
)
from export import (
    build_marketplace_export,
    build_scored_export,
    dataframe_to_csv_bytes,
)
from pipeline import load_or_build_scores, process_flow_dataset
from recommendation import build_customer_recommendations


REQUIRED_SCORE_COLUMNS = (
    "Flow ID",
    "Flow Name",
    "Customer",
    "Department",
    "Predicted Department",
    "Department Match",
    "Capability",
    "Run Count",
    "Error Rate",
    "Customer Count",
    "Usage Score",
    "Resell Score",
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
    "Predicted Department",
    "Department Match",
    "Capability",
    "Run Count",
    "Customer Count",
    "Usage Score",
    "Resell Score",
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
    "Predicted Department",
    "Department Match",
    "Capability",
    "Customer Count",
    "Usage Score",
    "Resell Score",
    "Opportunity Score",
    "Opportunity Level",
    "Product Score",
    "Risk Level",
)
RISK_COLUMNS = (
    "Flow Name",
    "Department",
    "Predicted Department",
    "Department Match",
    "Capability",
    "Error Rate",
    "Risk Score",
    "Risk Level",
    "Priority Score",
    "Priority Level",
)
RISK_LEVELS = ("Low", "Medium", "High", "Critical")
DATA_SOURCE_OPTIONS = ("Sample dataset", "Upload dataset")
DATA_SOURCE_KEY = "data_source"
UPLOAD_STATE_KEY = "uploaded_dataset_state"
UPLOAD_VERSION_KEY = "upload_widget_version"
FILTER_STATE_KEYS = (
    "department_filter",
    "capability_filter",
    "department_match_filter",
    "opportunity_filter",
    "risk_filter",
    "target_customer_filter",
)


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
        "Usage Score",
        "Resell Score",
        "Opportunity Score",
        "Product Score",
        "Risk Score",
        "Priority Score",
    )
    for column in numeric_columns:
        converted = pd.to_numeric(scores[column], errors="coerce")
        invalid_numeric = converted.isna() | converted.isin(
            [float("inf"), float("-inf")]
        )
        if invalid_numeric.any():
            raise ValueError(f"Dashboard column '{column}' contains invalid values")
        scores[column] = converted

    return scores


@st.cache_data(show_spinner=False, max_entries=4)
def prepare_uploaded_scores(file_name: str, content: bytes) -> dict[str, object]:
    """Validate, classify, and score an uploaded dataset in memory."""
    uploaded = load_uploaded_dataset(file_name, content)
    scores = process_flow_dataset(uploaded.flows)
    return {
        "fingerprint": uploaded.fingerprint,
        "status": "Successful",
        "file_name": uploaded.file_name,
        "file_format": uploaded.file_format,
        "row_count": uploaded.row_count,
        "column_count": uploaded.column_count,
        "export_stem": uploaded.export_stem,
        "scores": scores,
    }


def clear_filter_state() -> None:
    """Remove filters that may not exist in the next active dataset."""
    for key in FILTER_STATE_KEYS:
        st.session_state.pop(key, None)


def handle_data_source_change() -> None:
    """Clear stale dataset and filter state when the source changes."""
    clear_filter_state()
    if st.session_state.get(DATA_SOURCE_KEY) == "Sample dataset":
        st.session_state.pop(UPLOAD_STATE_KEY, None)
        st.session_state[UPLOAD_VERSION_KEY] = (
            st.session_state.get(UPLOAD_VERSION_KEY, 0) + 1
        )


def reset_uploaded_dataset() -> None:
    """Return the application to the bundled sample dataset."""
    st.session_state[DATA_SOURCE_KEY] = "Sample dataset"
    st.session_state.pop(UPLOAD_STATE_KEY, None)
    st.session_state[UPLOAD_VERSION_KEY] = (
        st.session_state.get(UPLOAD_VERSION_KEY, 0) + 1
    )
    clear_filter_state()


def _render_upload_metadata(upload_state: dict[str, object]) -> None:
    """Show validation and shape details for the current upload."""
    st.sidebar.caption(f"File: {upload_state['file_name']}")
    if upload_state.get("row_count") is not None:
        st.sidebar.caption(f"Rows: {upload_state['row_count']}")
    if upload_state.get("column_count") is not None:
        st.sidebar.caption(f"Columns: {upload_state['column_count']}")
    st.sidebar.caption(f"Format: {upload_state['file_format']}")

    if upload_state["status"] == "Successful":
        st.sidebar.success("Validation: Successful")
    else:
        st.sidebar.error("Validation: Failed")
        st.sidebar.caption(str(upload_state["error"]))


def render_data_source() -> tuple[pd.DataFrame | None, str, str | None]:
    """Render source controls and return active scores, export stem, and error."""
    st.sidebar.header("Data Source")
    st.session_state.setdefault(UPLOAD_VERSION_KEY, 0)
    selected_source = st.sidebar.radio(
        "Data source",
        options=DATA_SOURCE_OPTIONS,
        key=DATA_SOURCE_KEY,
        on_change=handle_data_source_change,
    )

    if selected_source == "Sample dataset":
        st.sidebar.button(
            "Reset to sample dataset",
            icon=":material/restart_alt:",
            width="stretch",
            disabled=True,
        )
        return load_dashboard_data(), "internalflow", None

    upload_key = f"flow_dataset_upload_{st.session_state[UPLOAD_VERSION_KEY]}"
    uploaded_file = st.sidebar.file_uploader(
        "Upload flow dataset",
        type=["csv", "xlsx"],
        key=upload_key,
        max_upload_size=MAX_UPLOAD_MEGABYTES,
        help=f"CSV or XLSX, up to {MAX_UPLOAD_MEGABYTES} MB.",
    )
    st.sidebar.button(
        "Reset to sample dataset",
        on_click=reset_uploaded_dataset,
        icon=":material/restart_alt:",
        width="stretch",
    )

    if uploaded_file is None:
        st.session_state.pop(UPLOAD_STATE_KEY, None)
        st.sidebar.info("Upload a CSV or XLSX flow dataset to continue.")
        return None, "uploaded_flows", None

    content = uploaded_file.getvalue()
    fingerprint = dataset_fingerprint(uploaded_file.name, content)
    upload_state = st.session_state.get(UPLOAD_STATE_KEY)
    if not upload_state or upload_state.get("fingerprint") != fingerprint:
        clear_filter_state()
        try:
            upload_state = prepare_uploaded_scores(uploaded_file.name, content)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            upload_state = {
                "fingerprint": fingerprint,
                "status": "Failed",
                "file_name": safe_file_name(uploaded_file.name),
                "file_format": (
                    "XLSX"
                    if safe_file_name(uploaded_file.name).casefold().endswith(".xlsx")
                    else "CSV"
                ),
                "row_count": None,
                "column_count": None,
                "export_stem": "uploaded_flows",
                "error": str(error),
            }
        st.session_state[UPLOAD_STATE_KEY] = upload_state

    _render_upload_metadata(upload_state)
    if upload_state["status"] != "Successful":
        return None, str(upload_state["export_stem"]), str(upload_state["error"])

    return (
        upload_state["scores"],
        str(upload_state["export_stem"]),
        None,
    )


def apply_filters(
    scores: pd.DataFrame,
    departments: list[str] | None = None,
    capabilities: list[str] | None = None,
    department_matches: list[str] | None = None,
    opportunity_range: tuple[float, float] = (0.0, 100.0),
    risk_levels: list[str] | None = None,
) -> pd.DataFrame:
    """Return flows matching the selected dashboard filters."""
    filtered = scores.copy()

    if departments:
        filtered = filtered[filtered["Department"].isin(departments)]
    if capabilities:
        filtered = filtered[filtered["Capability"].isin(capabilities)]
    if department_matches:
        filtered = filtered[
            filtered["Department Match"].isin(department_matches)
        ]
    if risk_levels:
        filtered = filtered[filtered["Risk Level"].isin(risk_levels)]

    minimum_score, maximum_score = opportunity_range
    filtered = filtered[
        filtered["Opportunity Score"].between(minimum_score, maximum_score)
    ]
    return filtered


def _sanitize_multiselect_state(key: str, options: list[str]) -> None:
    """Keep only still-valid values in a dynamic multiselect."""
    if key not in st.session_state:
        return
    st.session_state[key] = [
        value for value in st.session_state[key] if value in options
    ]


def render_filters(scores: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar controls and return the filtered portfolio."""
    st.sidebar.header("Filters")
    department_options = sorted(scores["Department"].astype(str).unique())
    capability_options = sorted(scores["Capability"].astype(str).unique())
    department_match_options = sorted(
        scores["Department Match"].astype(str).unique()
    )
    available_risks = set(scores["Risk Level"].astype(str).unique())
    risk_options = [level for level in RISK_LEVELS if level in available_risks]

    _sanitize_multiselect_state("department_filter", department_options)
    _sanitize_multiselect_state("capability_filter", capability_options)
    _sanitize_multiselect_state(
        "department_match_filter", department_match_options
    )
    _sanitize_multiselect_state("risk_filter", risk_options)

    departments = st.sidebar.multiselect(
        "Department",
        options=department_options,
        key="department_filter",
    )
    capabilities = st.sidebar.multiselect(
        "Capability",
        options=capability_options,
        key="capability_filter",
    )
    department_matches = st.sidebar.multiselect(
        "Department match",
        options=department_match_options,
        key="department_match_filter",
    )

    minimum_score = float(math.floor(scores["Opportunity Score"].min()))
    maximum_score = float(math.ceil(scores["Opportunity Score"].max()))
    if maximum_score <= minimum_score:
        maximum_score = minimum_score + 1.0

    current_range = st.session_state.get("opportunity_filter")
    if current_range is not None and (
        len(current_range) != 2
        or current_range[0] < minimum_score
        or current_range[1] > maximum_score
        or current_range[0] > current_range[1]
    ):
        st.session_state.pop("opportunity_filter", None)

    opportunity_range = st.sidebar.slider(
        "Opportunity score",
        min_value=minimum_score,
        max_value=maximum_score,
        value=(minimum_score, maximum_score),
        step=1.0,
        key="opportunity_filter",
    )
    risk_levels = st.sidebar.multiselect(
        "Risk level",
        options=risk_options,
        key="risk_filter",
    )

    filtered = apply_filters(
        scores,
        departments=departments,
        capabilities=capabilities,
        department_matches=department_matches,
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
    mapped_departments = scores["Department Match"].isin(["Matched", "Review"])
    department_match_rate = (
        scores.loc[mapped_departments, "Department Match"].eq("Matched").mean() * 100
        if mapped_departments.any()
        else 0.0
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric("Visible flows", f"{visible_flows}")
    metric_columns[1].metric(
        "Average opportunity", f"{average_opportunity:.1f}"
    )
    metric_columns[2].metric("High opportunities", f"{high_opportunities}")
    metric_columns[3].metric("Critical risks", f"{critical_risks}")
    metric_columns[4].metric("Department match", f"{department_match_rate:.1f}%")


def render_scoring_methodology() -> None:
    """Explain productization and opportunity scoring inside the dashboard."""
    with st.expander(
        "Scoring methodology",
        icon=":material/calculate:",
    ):
        product_column, opportunity_column = st.columns(2)
        with product_column:
            st.markdown("**Productization score**")
            st.code(
                "Product Score =\n"
                "  Usage Score x 0.60\n"
                "+ Resell Score x 0.40",
                language=None,
            )
            st.markdown(
                "Usage Score measures relative run frequency. Resell Score "
                "measures unique customer reach for the predicted capability."
            )
        with opportunity_column:
            st.markdown("**Opportunity score**")
            st.code(
                "Opportunity Score =\n"
                "  Usage x 0.30\n"
                "+ Transaction x 0.25\n"
                "+ Product x 0.30\n"
                "+ Time Saving x 0.15\n"
                "- Risk x 0.20",
                language=None,
            )
            st.markdown(
                "High opportunity starts at 60. Risk reduces the score, while "
                "usage, volume, reuse, and time saving increase it."
            )


def render_portfolio_charts(scores: pd.DataFrame) -> None:
    """Render graphical opportunity and risk summaries for the active scope."""
    st.subheader("Portfolio signals")
    if scores.empty:
        st.info("No portfolio signals match the active filters.")
        return

    department_chart = (
        scores.groupby("Predicted Department", as_index=False)["Opportunity Score"]
        .mean()
        .rename(columns={"Opportunity Score": "Average Opportunity"})
        .sort_values("Average Opportunity", ascending=True)
    )
    risk_chart = (
        scores["Risk Level"]
        .value_counts()
        .reindex(RISK_LEVELS, fill_value=0)
        .rename_axis("Risk Level")
        .reset_index(name="Flow Count")
    )

    opportunity_column, risk_column = st.columns(2)
    with opportunity_column:
        st.caption("Average opportunity by matched department")
        st.bar_chart(
            department_chart,
            x="Predicted Department",
            y="Average Opportunity",
            color="#ff4b55",
            horizontal=True,
            height=320,
        )
    with risk_column:
        st.caption("Flow count by risk level")
        st.bar_chart(
            risk_chart,
            x="Risk Level",
            y="Flow Count",
            color="#168c82",
            height=320,
        )

def build_export_file_names(export_stem: str) -> tuple[str, str]:
    """Return source-aware names for both dashboard downloads."""
    if export_stem == "internalflow":
        return (
            "internalflow_scored_results.csv",
            "internalflow_marketplace_tasks.csv",
        )
    return (
        f"{export_stem}_scored.csv",
        f"{export_stem}_marketplace_tasks.csv",
    )

def render_exports(scores: pd.DataFrame, export_stem: str) -> None:
    """Render downloads for the currently filtered portfolio."""
    scored_export = build_scored_export(scores)
    marketplace_export = build_marketplace_export(scores)
    downloads_disabled = scores.empty
    scored_name, marketplace_name = build_export_file_names(export_stem)


    st.sidebar.divider()
    st.sidebar.subheader("Export")
    st.sidebar.download_button(
        "Scored results",
        data=dataframe_to_csv_bytes(scored_export),
        file_name=scored_name,
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
        disabled=downloads_disabled,
    )
    st.sidebar.download_button(
        "Marketplace tasks",
        data=dataframe_to_csv_bytes(marketplace_export),
        file_name=marketplace_name,
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
            "Predicted Department": st.column_config.TextColumn(
                "Matched Department"
            ),
            "Department Match": st.column_config.TextColumn(
                "Department Match"
            ),
            "Usage Score": st.column_config.ProgressColumn(
                "Usage",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Resell Score": st.column_config.ProgressColumn(
                "Resell",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
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
    """Render opportunity, risk, growth, and full portfolio views."""
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
        if scores.empty:
            st.caption("0 customer growth opportunities")
            st.info("No customer growth opportunities match this view.")
        else:
            recommendations = build_customer_recommendations(recommendation_scores)
            customer_options = [
                "All customers",
                *sorted(recommendations["Target Customer"].unique()),
            ]
            if (
                st.session_state.get("target_customer_filter")
                not in customer_options
            ):
                st.session_state.pop("target_customer_filter", None)
            selected_customer = st.selectbox(
                "Target customer",
                options=customer_options,
                key="target_customer_filter",
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
                        "Usage Score": st.column_config.ProgressColumn(
                "Usage",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Resell Score": st.column_config.ProgressColumn(
                "Resell",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
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
        scores, export_stem, upload_error = render_data_source()
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        st.error("Scored flow data is not available.")
        st.caption(str(error))
        st.code("python pipeline.py", language="bash")
        st.stop()

    if scores is None:
        if upload_error:
            st.error("Uploaded dataset could not be processed.")
            st.caption(upload_error)
        else:
            st.info("Choose a CSV or XLSX flow dataset from the sidebar.")
        st.stop()

    filtered_scores = render_filters(scores)
    render_exports(filtered_scores, export_stem)
    render_summary(filtered_scores)
    render_scoring_methodology()
    render_portfolio_charts(filtered_scores)
    st.divider()
    render_dashboard_views(filtered_scores, scores)


if __name__ == "__main__":
    main()
