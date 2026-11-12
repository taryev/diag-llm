from pathlib import Path

import streamlit as st


@st.cache_data()
def read_markdown_file(markdown_file) -> str:
    return Path(markdown_file).read_text()


intro_markdown = read_markdown_file("README.md")
st.markdown(intro_markdown)
