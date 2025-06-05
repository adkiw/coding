# main.py

import streamlit as st
import sqlite3

# 1) Privalo būti pirmasis – nustatome platų išdėstymą
st.set_page_config(layout="wide")

# 2) CSS stilius, kad viršuje esantis radio bar būtų apie 1 cm aukščio
st.markdown("""
    <style>
      /* Tiesiogiai taikome CSS radio-grupei, kad visi pasirinkimai būtų viena eilute ir baras būtų ~ 1 cm */
      .stRadio > div {
        height: 1cm !important;
        overflow: hidden; 
      }
      /* Kaip papildoma – sumažiname kiekvieno radion mygtuko vertikalinius padding’us */
      .stRadio > div > label > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
    </style>
""", unsafe_allow_html=True)

# 3) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 4) Importuojame modulius
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

# 5) Viršuje – horizontalus mygtukų baras (radio be jokių užrašų)
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

# 6) Pagal pasirinktą modulį kviečiame atitinkamą funkciją
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
