# main.py

import streamlit as st
import sqlite3

# 1) Privalo būti pirmoji Streamlit komanda
st.set_page_config(layout="wide")

# 2) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 3) Importuojame modulius
from modules import (
    dispo,
    kroviniai,
    vilkikai,
    priekabos,
    grupes,
    vairuotojai,
    klientai,
    darbuotojai,
    nustatymai,
    update,
    planavimas
)

# 4) Viršuje – tab’ai („klavišo formos“) be papildomo teksto
moduli = [
    "Dispo",
    "Kroviniai",
    "Vilkikai",
    "Priekabos",
    "Grupės",
    "Vairuotojai",
    "Klientai",
    "Darbuotojai",
    "Nustatymai",
    "Planavimas",
    "Update"
]
tabai = st.tabs(moduli)

# 5) Kiekviename tabe patalpinsime atitinkamo modulio show(...)
for pavadinimas, tab in zip(moduli, tabai):
    with tab:
        if pavadinimas == "Dispo":
            dispo.show(conn, c)
        elif pavadinimas == "Kroviniai":
            kroviniai.show(conn, c)
        elif pavadinimas == "Vilkikai":
            vilkikai.show(conn, c)
        elif pavadinimas == "Priekabos":
            priekabos.show(conn, c)
        elif pavadinimas == "Grupės":
            grupes.show(conn, c)
        elif pavadinimas == "Vairuotojai":
            vairuotojai.show(conn, c)
        elif pavadinimas == "Klientai":
            klientai.show(conn, c)
        elif pavadinimas == "Darbuotojai":
            darbuotojai.show(conn, c)
        elif pavadinimas == "Nustatymai":
            nustatymai.show(conn, c)
        elif pavadinimas == "Planavimas":
            planavimas.show(conn, c)
        elif pavadinimas == "Update":
            update.show(conn, c)
