from __future__ import annotations

import plotly.express as px
import streamlit as st

from lib.db import fetch_drift_reports, fetch_eval_trends, fetch_home_kpis


def _format_currency(value) -> str:
    return f"${value:,.4f}" if value is not None else "--"


def _format_decimal(value) -> str:
    return f"{value:.3f}" if value is not None else "--"


def _format_ms(value) -> str:
    return f"{value:.0f} ms" if value is not None else "--"


def _format_text(value) -> str:
    return str(value) if value not in (None, "") else "--"

st.set_page_config(page_title="DocIntel Ops", layout="wide")

st.markdown(
    """
    <style>
      .docintel-hero {
        padding: 1.25rem 1.5rem;
        border: 1px solid rgba(15, 23, 42, 0.10);
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(255, 248, 240, 0.95), rgba(237, 247, 255, 0.92));
        margin-bottom: 1rem;
      }
      .docintel-hero h1 {
        margin: 0;
        font-size: 2rem;
      }
      .docintel-hero p {
        margin: 0.5rem 0 0;
        color: #334155;
      }
    </style>
    <div class="docintel-hero">
      <h1>DocIntel Ops</h1>
      <p>Read-only visibility into eval quality, drift, latency, and retrieval behavior for the EU AI Act RAG system.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

kpis = fetch_home_kpis()
metric_columns = st.columns(4)
metric_columns[0].metric("Latest Faithfulness", _format_decimal(kpis["latest_faithfulness"]))
metric_columns[1].metric("P95 /answer Latency", _format_ms(kpis["p95_answer_latency_ms_7d"]))
metric_columns[2].metric("Latest Drift Status", _format_text(kpis["latest_drift_status"]))
metric_columns[3].metric("Total Cost Last 7d", _format_currency(kpis["total_cost_usd_7d"]))

eval_trends = fetch_eval_trends(limit=20)
drift_reports = fetch_drift_reports(limit=10)

left_column, right_column = st.columns((1.4, 1))
with left_column:
    st.subheader("Recent Eval Trend")
    if eval_trends.empty:
        st.info("No evaluation runs are available yet.")
    else:
        melted = eval_trends.melt(
            id_vars=["started_at"],
            value_vars=[
                "faithfulness_mean",
                "context_precision_mean",
                "context_recall_mean",
                "answer_relevancy_mean",
            ],
            var_name="metric",
            value_name="value",
        ).dropna(subset=["value"])
        fig = px.line(
            melted,
            x="started_at",
            y="value",
            color="metric",
            markers=True,
            title="Quality metrics across recent runs",
        )
        fig.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

with right_column:
    st.subheader("Latest Drift Reports")
    if drift_reports.empty:
        st.info("No drift reports are available yet.")
    else:
        st.dataframe(
            drift_reports[
                [
                    "created_at",
                    "status",
                    "embedding_drift_score",
                    "query_drift_score",
                    "retrieval_quality_delta",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
