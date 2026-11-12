import json
import os

import streamlit as st
from openai import (
    OpenAI,
)
from sqlalchemy.exc import SQLAlchemyError

from database import get_sqlite_conn, insert_history
from llm.prompts import DEFAULT_SYSTEM_PROMPT
from llm.schemas import DiagnosisResponse
from llm.tools import execute_tool, tools

BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MAX_TOOL_CALLS = 10

st.session_state.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
st.session_state.setdefault("messages", [])


# OpenAI API client
@st.cache_resource
def get_llm_client() -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=300.0, max_retries=1)


client = get_llm_client()


# Installed models
@st.cache_data(ttl=300)
def list_models() -> list:
    models = client.models.list()
    return [model.id for model in models.data]


# LLM Agent Function
def ask_llm(user_prompt: str, model: str | None, system_prompt: str) -> tuple:
    if not model:
        raise RuntimeError("No model selected")

    system = system_prompt.replace(
        "{schema}", json.dumps(DiagnosisResponse.model_json_schema())
    )

    memory = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]

    trace = []

    # ReAct loop
    for _ in range(MAX_TOOL_CALLS):
        # STEP 1 - REASON
        reason = client.chat.completions.create(
            model=model,
            messages=memory,  # type: ignore
            tools=tools,
            tool_choice="auto",
        )

        message = reason.choices[0].message
        memory.append(message)  # type: ignore

        tool_calls = message.tool_calls
        # Exit the loop if no tools were called
        if not tool_calls:
            break

        # STEP 2 - ACT
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            trace.append(
                {
                    "tool": tool_call.function.name,  # type: ignore
                    "arguments": tool_call.function.arguments,  # type: ignore
                    "result": result,
                }
            )
            # STEP 3 - OBSERVE
            memory.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    # Structured output (no tools)
    memory.append(
        {
            "role": "user",
            "content": "Produce the final JSON object now, using only the tool results above. Set icd_11_* to null where no code was obtained.",
        }
    )
    final_reason = client.chat.completions.create(
        model=model,
        messages=memory,  # type: ignore
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "DiagnosisResponse",
                "strict": True,
                "schema": DiagnosisResponse.model_json_schema(),
            },
        },
    )
    final_message = final_reason.choices[0].message
    if not final_message.content:
        raise RuntimeError("Empty final response from the model.")

    result = DiagnosisResponse.model_validate_json(final_message.content)
    return result, trace, memory


# Streamlit app
st.title("LLM playground")


# Helper for rendering results on Streamlit
def render_assistant(msg: dict) -> None:
    if "error" in msg:
        st.error(f"Error : {msg['error']}")
        return

    response, trace, memory = msg["response"], msg["trace"], msg["memory"]

    if response.status == "found":
        st.success(f"{len(response.diagnoses)} diagnoses found")
        st.dataframe(
            [d.model_dump() for d in response.diagnoses],
            width="stretch",
            column_config={
                "llm_diagnosis": "Diagnosis",
                "icd_11_code": "ICD-11 code",
                "icd_11_text": "ICD-11 title",
            },
        )
    else:
        st.warning("Inconclusive")

    with st.expander(f"Tool calls ({len(trace)})"):
        st.json(trace)
    with st.expander("Memory"):
        st.json(memory)


# Sidebar
with st.sidebar:
    try:
        model = st.selectbox("Model", list_models())
    except:
        st.error("Error while reaching the LLM API server")

    with st.expander("System prompt"):
        st.markdown(
            "Use the `{schema}` placeholder to include the structured output JSON schema."
        )
        st.text_area("Prompt", key="system_prompt", height=300)
    if st.button(":material/delete: Clear history", width="stretch"):
        st.session_state.messages = []
        st.rerun()

# Chat
st.info(
    "Do not use real-world data when running models through cloud-based services or third-party APIs. In particular, MIMIC data must not be submitted to external services as stated in the [PhysioNet Data Use Agreement](https://physionet.org/news/post/llm-responsible-use/).",
    title="Important",
)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_assistant(msg)

if note := st.chat_input("Enter clinical note"):
    st.session_state.messages.append({"role": "user", "content": note})
    with st.chat_message("user"):
        st.markdown(note)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Processing.."):
                response, trace, memory = ask_llm(
                    note, model, st.session_state.system_prompt
                )
            try:
                insert_history(
                    get_sqlite_conn(),
                    source="LLM Playground",
                    clinical_note=note,
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
        except Exception as e:
            reply = {"role": "assistant", "error": str(e)}
        render_assistant(reply)

    st.session_state.messages.append(reply)
