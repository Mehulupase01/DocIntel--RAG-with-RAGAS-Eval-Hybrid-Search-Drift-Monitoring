from __future__ import annotations

import plotly.express as px
import streamlit as st
from lib.db import fetch_daily_costs, fetch_latency_summary, fetch_model_cost_breakdown

st.title("Cost and Latency")
st.caption("Cost per day, endpoint latency percentiles, and answer-model cost contribution.")

costs = fetch_daily_costs(days=30)
latency = fetch_latency_summary(days=30)
models = fetch_model_cost_breakdown(days=30)

top_left, top_right = st.columns(2)
with top_left:
    st.subheader("Cost Per Day")
    if costs.empty:
        st.info("No answer cost data is available yet.")
    else:
        chart = px.bar(costs, x="date", y="cost_usd", title="Answer spend by day")
        chart.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(chart, use_container_width=True)

with top_right:
    st.subheader("Latency By Endpoint")
    if latency.empty:
        st.info("No latency samples are available yet.")
    else:
        melted = latency.melt(
            id_vars=["endpoint", "request_count"],
            value_vars=["p50_latency_ms", "p95_latency_ms"],
            var_name="percentile",
            value_name="latency_ms",
        )
        chart = px.bar(
            melted,
            x="endpoint",
            y="latency_ms",
            color="percentile",
            barmode="group",
            title="P50 and P95 latency",
        )
        chart.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(latency, use_container_width=True, hide_index=True)

st.subheader("Model Cost Breakdown")
if models.empty:
    st.info("No answer-model cost data is available yet.")
else:
    chart = px.bar(
        models,
        x="cost_usd",
        y="model",
        orientation="h",
        text="answer_count",
        title="Cost and volume by answer model",
    )
    chart.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20), yaxis_title="")
    st.plotly_chart(chart, use_container_width=True)
    st.dataframe(models, use_container_width=True, hide_index=True)
