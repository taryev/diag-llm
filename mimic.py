import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from database import get_sqlite_conn, insert_history
from llm.app import ask_llm, list_models, render_assistant
from llm.prompts import DEFAULT_SYSTEM_PROMPT

st.session_state.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)


def extract_context(
    text: str, keyword: str = "discharge diagnosis", before: int = 50, after: int = 200
) -> list[str]:
    results = []
    lower_text = text.lower()
    start = 0

    while (pos := lower_text.find(keyword, start)) != -1:
        context_start = max(0, pos - before)
        context_end = pos + len(keyword) + after

        results.append((text[context_start:context_end]).replace("\\n", "\n"))
        start = pos + len(keyword)

    return results


def get_random_note(conn):
    result = conn.query(
        "SELECT text, note_id FROM mimiciv_note.discharge ORDER BY RANDOM() LIMIT 1",
        show_spinner=False,
        ttl=0,
    )
    return result


def count_mimic_notes(conn):
    result = conn.query(
        "SELECT count(note_id) FROM mimiciv_note.discharge", show_spinner=False
    )
    return result.iloc[0, 0]


# Streamlit app
st.title("MIMIC Dataset")

with st.sidebar:
    try:
        model = st.selectbox("Model", list_models())
    except:
        st.error("Error while reaching the LLM API server")
    enable_mimic = st.toggle("Enable MIMIC support")
    if enable_mimic:
        st.warning(
            "According to MIMIC's DUA, no MIMIC data must be sent to third-party LLM services. Make sure that you are using a local server before continuing. Failure to comply may result in breaching the [PhysioNet Credentialed Health Data License](https://physionet.org/about/licenses/physionet-credentialed-health-data-license-150/).",
            title="Important",
        )
        dua_mimic = st.toggle("I understand")

if enable_mimic and dua_mimic:
    try:
        conn = st.connection("postgresql", type="sql")
        conn.connect()
    except:
        st.error("Unable to connect to MIMIC database. Check secrets.", title="Error")

    # count = count_mimic_notes(conn)
    # st.metric(label="Notes count", value=str(count))

    col1, col2 = st.columns(2)
    with col1:
        if "random_note_df" not in st.session_state:
            st.session_state.random_note_df = get_random_note(conn)

        random_note_df = st.session_state.random_note_df

        random_note = st.expander(
            label=f"Random note from dataset (ID `{random_note_df.iloc[0, 1]}`)",
            expanded=True,
            width="stretch",
        )
        with random_note:
            note_text = str(random_note_df.iloc[0, 0])
            context = extract_context(note_text, before=15, after=200)
            quick_look = (
                context[0]
                if context
                else "Not found, try to look up manually using the full note."
            )
            st.code(quick_look, language=None)
            full_note = st.expander(label="Full note", type="compact")
            with full_note:
                st.code(note_text, language=None)

    with col2:
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            if st.button("Refresh note", icon=":material/refresh:", width="stretch"):
                st.session_state.random_note_df = get_random_note(conn)
                st.rerun()
        with col2_2:
            extract_btn = st.button(
                "Extract diagnoses from this note",
                icon=":material/export_notes:",
                width="stretch",
            )

        if extract_btn:
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Processing.."):
                        response, trace, memory = ask_llm(
                            note_text, model, st.session_state.system_prompt
                        )
                    try:
                        insert_history(
                            get_sqlite_conn(),
                            source="MIMIC",
                            mimic_id=str(random_note_df.iloc[0, 1]),
                            clinical_note=note_text,
                            llm_response=response.model_dump_json(),
                        )
                    except SQLAlchemyError as e:
                        st.error(f"Unable to save call history: {e}")
                    reply = {
                        "role": "assistant",
                        "response": response,
                        "trace": trace,
                        "memory": memory,
                    }
                except Exception as e:  # noqa: BLE001
                    reply = {"role": "assistant", "error": str(e)}
                render_assistant(reply)
