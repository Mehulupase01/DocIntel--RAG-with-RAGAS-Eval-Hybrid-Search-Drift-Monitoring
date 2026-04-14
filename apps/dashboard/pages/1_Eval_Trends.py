from __future__ import annotations

import plotly.express as px
import streamlit as st
from lib.db import fetch_eval_trends

st.title("Eval Trends")
st.caption("Faithfulness, precision, recall, and relevancy over recent evaluation runs.")

eval_trends = fetch_eval_trends(limit=100)
if eval_trends.empty:
    st.info("No evaluation runs are available yet.")
else:
    melted = eval_trends.melt(
        id_vars=["started_at", "status", "retrieval_strategy"],
        value_vars=[
            "faithfulness_mean",
            "context_precision_mean",
            "context_recall_mean",
            "answer_relevancy_mean",
        ],
        var_name="metric",
        value_name="value",
    ).dropna(subset=["value"])
    chart = px.line(
        melted,
        x="started_at",
        y="value",
        color="metric",
        markers=True,
        hover_data=["status", "retrieval_strategy"],
        title="Evaluation metrics by run",
    )
    chart.update_layout(height=480, margin=dict(l=20, r=20, t=60, b=20), legend_title_text="")
    st.plotly_chart(chart, use_container_width=True)

    st.dataframe(
        eval_trends[
            [
                "started_at",
                "status",
                "retrieval_strategy",
                "faithfulness_mean",
                "context_precision_mean",
                "context_recall_mean",
                "answer_relevancy_mean",
                "cases_passed",
                "total_cases",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
