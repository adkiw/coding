# main.py
import streamlit as st

# 1) Page settings – use wide layout
st.set_page_config(layout="wide")

# 2) Minimal CSS to reduce spacing at the top of the page
st.markdown("""
<style>
  .css-18e3th9 { padding-top: 0 !important; }
  .stRadio > div          { height: 1cm !important; margin-top: 0 !important; }
  .stRadio > div > label > div { padding-top: 0 !important; padding-bottom: 0 !important; }
</style>
""", unsafe_allow_html=True)

# 3) Initialise the DB – tables are created inside connect()
from db import connect

# Maintain DB connection across Streamlit reruns
if "db_conn" not in st.session_state or "db_cursor" not in st.session_state:
    st.session_state.db_conn, st.session_state.db_cursor = connect()

conn = st.session_state.db_conn
c = st.session_state.db_cursor

# 4) Import all modules (modular structure: all module files in one folder)
from modules import (
    kroviniai,
    vilkikai,
    priekabos,
    grupes,
    vairuotojai,
    klientai,
    darbuotojai,
    planavimas,
    update
)

# 5) Horizontal menu (module titles)
modules_list = [
    "Cargo",
    "Trucks",
    "Trailers",
    "Groups",
    "Drivers",
    "Clients",
    "Employees",
    "Planning",
    "Update"
]

if "selected_module" not in st.session_state:
    st.session_state.selected_module = modules_list[0]

selected = st.radio(
    "Select module",
    modules_list,
    horizontal=True,
    key="selected_module",
    label_visibility="collapsed",
)

# 6) Maršrutizacija – pagal pasirinkimą atidaromas atitinkamas modulis
if selected == "Cargo":
    kroviniai.show(conn, c)
elif selected == "Trucks":
    vilkikai.show(conn, c)
elif selected == "Trailers":
    priekabos.show(conn, c)
elif selected == "Groups":
    grupes.show(conn, c)
elif selected == "Drivers":
    vairuotojai.show(conn, c)
elif selected == "Clients":
    klientai.show(conn, c)
elif selected == "Employees":
    darbuotojai.show(conn, c)
elif selected == "Planning":
    planavimas.show(conn, c)
elif selected == "Update":
    update.show(conn, c)
