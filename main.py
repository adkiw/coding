# main.py

import streamlit as st
st.set_page_config(layout="wide")

from modules import (
    dispo, kroviniai, vilkikai, priekabos,
    grupes, vairuotojai, klientai,
    darbuotojai, nustatymai, update, planavimas
)
from db import init_db

# Prisijungimas prie DB
conn, c = init_db()

# Moduliai rodomi meniu
moduliai = [
    "Dispo", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai", "Update", "Planavimas"
]

st.sidebar.title("Navigacija")
pasirinktas_puslapis = st.sidebar.radio("Pasirinkite modulį", moduliai)

if pasirinktas_puslapis == "Dispo":
    dispo.show(conn, c)
elif pasirinktas_puslapis == "Kroviniai":
    kroviniai.show(conn, c)
elif pasirinktas_puslapis == "Vilkikai":
    vilkikai.show(conn, c)
elif pasirinktas_puslapis == "Priekabos":
    priekabos.show(conn, c)
elif pasirinktas_puslapis == "Grupės":
    grupes.show(conn, c)
elif pasirinktas_puslapis == "Vairuotojai":
    vairuotojai.show(conn, c)
elif pasirinktas_puslapis == "Klientai":
    klientai.show(conn, c)
elif pasirinktas_puslapis == "Darbuotojai":
    darbuotojai.show(conn, c)
elif pasirinktas_puslapis == "Nustatymai":
    nustatymai.show(conn, c)
elif pasirinktas_puslapis == "Update":
    update.show(conn, c)
elif pasirinktas_puslapis == "Planavimas":
    planavimas.show(conn, c)
