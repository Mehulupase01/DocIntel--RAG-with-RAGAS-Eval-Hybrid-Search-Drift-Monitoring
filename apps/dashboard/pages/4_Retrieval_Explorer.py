from __future__ import annotations

import httpx
import pandas as pd
import streamlit as st
from lib.api_client import SEARCH_STRATEGIES, run_search_matrix

st.title("Retrieval Explorer")
st.caption("Run the live `/search` API across all retrieval strategies and compare ranked chunks side by side.")

query = st.text_input("Query", value="What is a high-risk AI system?")
top_k = st.slider("Top K", min_value=1, max_value=10, value=5)

if st.button("Run Retrieval", type="primary"):
    if not query.strip():
        st.warning("Enter a query before running the explorer.")
    else:
        try:
            with st.spinner("Querying all strategies..."):
                results = run_search_matrix(query=query, top_k=top_k)
            top_row = st.columns(2)
            bottom_row = st.columns(2)
            containers = [top_row[0], top_row[1], bottom_row[0], bottom_row[1]]
            for container, strategy in zip(containers, SEARCH_STRATEGIES, strict=True):
                with container:
                    st.subheader(strategy)
                    payload = results[strategy]
                    ranked = payload.get("results", [])
                    if not ranked:
                        st.info("No chunks returned.")
                        continue
                    table = pd.DataFrame(
                        [
                            {
                                "rank": row["rank"],
                                "document": row["document_title"],
                                "section": row["section_path"],
                                "pages": f"{row['page_start']}-{row['page_end']}",
                                "bm25": row.get("bm25_score"),
                                "vector": row.get("vector_score"),
                                "fused": row.get("fused_score"),
                                "rerank": row.get("rerank_score"),
                            }
                            for row in ranked
                        ]
                    )
                    st.dataframe(table, use_container_width=True, hide_index=True)
                    for row in ranked[: min(3, len(ranked))]:
                        with st.expander(f"#{row['rank']} {row['section_path'] or row['document_title']}"):
                            st.write(row["text"])
        except httpx.HTTPError as exc:
            st.error(f"Search request failed: {exc}")
