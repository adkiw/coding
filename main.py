# main.py

import streamlit as st
import sqlite3

# 1) Standartinis set_page_config (privalo būti pirmasis Streamlit komanda)
st.set_page_config(layout="wide")

# 2) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 3) Importuojame visus modulius
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

# 4) Viršuje – sukuriame „expander“, kuriame yra modulio pasirinkimo radio.
#    Iš pradžių jis suskleistas, paspaudus išsiskleidžia.
with st.expander("☰ Modulių meniu", expanded=False):
    moduliai = [
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
    pasirinktas = st.radio("", moduliai, horizontal=True)

# Jeigu vartotojas dar nepaspaudė, "pasirinktas" kintamasis nebus apibrėžtas.
# Todėl apsaugome:
if 'pasirinktas' not in locals():
    st.info("Pasirinkite modulį viršuje spustelėdami „☰ Modulių meniu“.")
    st.stop()

st.divider()

# 5) Pagal pasirinktą modulį kviečiame atitinkamą show(...)
if pasirinktas == "Dispo":
    dispo.show(conn, c)
elif pasirinktas == "Kroviniai":
    kroviniai.show(conn, c)
elif pasirinktas == "Vilkikai":
    vilkikai.show(conn, c)
elif pasirinktas == "Priekabos":
    priekabos.show(conn, c)
elif pasirinktas == "Grupės":
    grupes.show(conn, c)
elif pasirinktas == "Vairuotojai":
    vairuotojai.show(conn, c)
elif pasirinktas == "Klientai":
    klientai.show(conn, c)
elif pasirinktas == "Darbuotojai":
    darbuotojai.show(conn, c)
elif pasirinktas == "Nustatymai":
    nustatymai.show(conn, c)
elif pasirinktas == "Planavimas":
    planavimas.show(conn, c)
elif pasirinktas == "Update":
    update.show(conn, c)
