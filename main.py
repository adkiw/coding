# main.py

import streamlit as st

# TURI BŪTI PIRMAS KVIEČIMAS – prieš bet kokį kitą st.xxx kvietimą:
st.set_page_config(
    page_title="DISPO – Aplikacija",
    layout="wide"
)

# Dabar tęsiame su savo import’ais ir visa kita
import sqlite3
from modules import dispo, kroviniai, vilkikai, priekabos, grupes
from modules import vairuotojai, klientai, darbuotojai, nustatymai
from modules import planavimas, update

conn = sqlite3.connect("db.sqlite")
c = conn.cursor()

menu = st.sidebar.radio(
    "Pasirinkite modulį:",
    ("Dispo", "Kroviniai", "Vilkikai", "Priekabos", "Grupės",
     "Vairuotojai", "Klientai", "Darbuotojai", "Nustatymai",
     "Planavimas", "Update")
)

if menu == "Dispo":
    dispo.show(conn, c)
elif menu == "Kroviniai":
    kroviniai.show(conn, c)
elif menu == "Vilkikai":
    vilkikai.show(conn, c)
elif menu == "Priekabos":
    priekabos.show(conn, c)
elif menu == "Grupės":
    grupes.show(conn, c)
elif menu == "Vairuotojai":
    vairuotojai.show(conn, c)
elif menu == "Klientai":
    klientai.show(conn, c)
elif menu == "Darbuotojai":
    darbuotojai.show(conn, c)
elif menu == "Nustatymai":
    nustatymai.show(conn, c)
elif menu == "Planavimas":
    planavimas.show(conn, c)
elif menu == "Update":
    update.show(conn, c)
