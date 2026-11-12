import streamlit as st
from dotenv import load_dotenv

from database import get_sqlite_conn, init_db

load_dotenv()

st.set_page_config(page_title="diag-llm", page_icon="📝", layout="wide")

conn = get_sqlite_conn()
init_db(conn)

homepage = st.Page("home.py", title="Home", icon=":material/home:")
mimic = st.Page("mimic.py", title="MIMIC Dataset", icon=":material/dataset:")
icd = st.Page(
    "icd.py", title="ICD Playground", icon=":material/book_5:", visibility="hidden"
)
llm_playground = st.Page(
    "llm/app.py",
    title="LLM Playground",
    icon=":material/robot_2:",
    url_path="playground",
)
history = st.Page("history.py", title="LLM calls history", icon=":material/history:")

pg = st.navigation([homepage, mimic, llm_playground, icd, history])


pg.run()
