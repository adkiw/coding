import streamlit as st
st.set_page_config(layout="wide")

from modules import (
    dispo_show,
    kroviniai_show,
    vilkikai_show,
    priekabos_show,
    grupes_show,
    vairuotojai_show,
    klientai_show,
    darbuotojai_show,
    nustatymai_show,
    planavimas_show,   # <-- čia turi būti būtent taip
    update_show
)
from db import init_db

conn, c = init_db()

moduliai = [
    "Dispo", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai", "Planavimas", "Update"
]

st.sidebar.title("MENIU")
modulis = st.sidebar.radio("Pasirinkite modulį:", moduliai)

if modulis == "Dispo":
    dispo_show(conn, c)
elif modulis == "Kroviniai":
    kroviniai_show(conn, c)
elif modulis == "Vilkikai":
    vilkikai_show(conn, c)
elif modulis == "Priekabos":
    priekabos_show(conn, c)
elif modulis == "Grupės":
    grupes_show(conn, c)
elif modulis == "Vairuotojai":
    vairuotojai_show(conn, c)
elif modulis == "Klientai":
    klientai_show(conn, c)
elif modulis == "Darbuotojai":
    darbuotojai_show(conn, c)
elif modulis == "Nustatymai":
    nustatymai_show(conn, c)
elif modulis == "Planavimas":
    planavimas_show(conn, c)
elif modulis == "Update":
    update_show(conn, c)
