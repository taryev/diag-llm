import json

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

st.title("Calls history")

if st.button("Refresh data", icon=":material/refresh:"):
    st.rerun()

from database import get_sqlite_conn

conn = get_sqlite_conn()

try:
    df = conn.query(
        "SELECT id, created_at, source, mimic_id, clinical_note, llm_response "
        "FROM runs ORDER BY created_at DESC, id DESC",
        ttl=0,
    )
except SQLAlchemyError as e:
    st.error(f"Unable to load call history: {e}")
else:
    if df.empty:
        st.info("No LLM calls have been saved yet.")
    else:
        st.dataframe(
            df[["id", "created_at", "source", "mimic_id"]],
            hide_index=True,
            width="stretch",
        )

        selected_id = st.selectbox(
            "Call details",
            df["id"].tolist(),
            format_func=lambda call_id: (
                f"#{call_id} · "
                f"{df.loc[df['id'] == call_id, 'source'].iloc[0]} · "
                f"{df.loc[df['id'] == call_id, 'created_at'].iloc[0]}"
            ),
        )
        selected = df.loc[df["id"] == selected_id].iloc[0]

        with st.expander("Clinical note"):
            st.text(selected["clinical_note"])

        st.subheader("LLM response")
        try:
            st.json(json.loads(selected["llm_response"]))
        except json.JSONDecodeError, TypeError:
            st.code(selected["llm_response"], language=None)
