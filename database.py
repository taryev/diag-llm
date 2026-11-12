import streamlit as st
from sqlalchemy import text
from streamlit.connections import SQLConnection


@st.cache_resource
def get_sqlite_conn() -> SQLConnection:
    conn = st.connection("sqlite", type="sql")
    return conn


def init_db(conn) -> None:
    with conn.session as s:
        s.execute(
            text(
                "CREATE TABLE IF NOT EXISTS runs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
                "source TEXT,"
                "mimic_id TEXT,"
                "clinical_note TEXT,"
                "llm_response TEXT)"
            )
        )
        s.commit()


def insert_history(
    conn: SQLConnection,
    source: str,
    clinical_note: str,
    llm_response: str,
    mimic_id: str | None = None,
) -> None:
    with conn.session as s:
        s.execute(
            text(
                "INSERT INTO runs (source, mimic_id, clinical_note, llm_response) "
                "VALUES (:source, :mimic_id, :clinical_note, :llm_response)"
            ),
            {
                "source": source,
                "mimic_id": mimic_id,
                "clinical_note": clinical_note,
                "llm_response": llm_response,
            },
        )
        s.commit()
