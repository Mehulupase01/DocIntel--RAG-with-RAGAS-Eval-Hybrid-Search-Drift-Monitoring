from __future__ import annotations

from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html

from lib.db import fetch_drift_reports


def _format_decimal(value) -> str:
    return f"{value:.3f}" if value is not None else "--"


st.title("Drift Reports")
st.caption("Weekly drift snapshots with persisted scores and HTML Evidently artifacts.")

reports = fetch_drift_reports(limit=50)
if reports.empty:
    st.info("No drift reports are available yet.")
else:
    st.dataframe(
        reports[
            [
                "id",
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

    selected_report_id = st.selectbox("Select a report", reports["id"].tolist())
    selected = reports.loc[reports["id"] == selected_report_id].iloc[0]

    metric_columns = st.columns(3)
    metric_columns[0].metric("Embedding Drift", _format_decimal(selected["embedding_drift_score"]))
    metric_columns[1].metric("Query Drift", _format_decimal(selected["query_drift_score"]))
    metric_columns[2].metric("Rerank Delta", _format_decimal(selected["retrieval_quality_delta"]))
    st.caption(f"Status: {selected['status']} | Created at: {selected['created_at']}")

    html_path = selected.get("html_path")
    if html_path and Path(html_path).exists():
        html(Path(html_path).read_text(encoding="utf-8"), height=900, scrolling=True)
    else:
        st.warning("The HTML artifact is missing from local disk.")

    with st.expander("Payload JSON"):
        st.json(selected.get("payload_json") or {})
