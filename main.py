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
