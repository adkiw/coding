import streamlit as st
import sqlite3

# 1) Privalo būti pirmasis – nustatome platų išdėstymą
st.set_page_config(layout="wide")

# 2) CSS, kad radio-bar būtų tiesiai lango viršuje ir apie 1 cm aukščio
st.markdown("""
    <style>
      /* Pašaliname visus viršutinius margin’us aplikacijoje */
      .css-18e3th9 {
        padding-top: 0 !important;
      }
      /* Tiesiogiai taikome CSS radio-grupei: 1 cm aukštis, be papildomų tarpelio */
      .stRadio > div {
        height: 1cm !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
        overflow: hidden;
      }
      /* Naikiname radio mygtukų vertikalius padding’us */
      .stRadio > div > label > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
    </style>
""", unsafe_allow_html=True)

# 3) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 4) Importuojame modulius (Dispo ir Nustatymai moduliai pašalinti)
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

# 5) Tiesiai viršuje – horizontalus mygtukų baras (radio be užrašų)
moduliai = [
    "Kroviniai",
    "Vilkikai",
    "Priekabos",
    "Grupės",
    "Vairuotojai",
    "Klientai",
    "Darbuotojai",
    "Planavimas",
    "Update"
]
pasirinktas = st.radio("", moduliai, horizontal=True)

# 6) Pagal pasirinktą modulį kviečiame atitinkamą funkciją
if pasirinktas == "Kroviniai":
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
elif pasirinktas == "Planavimas":
    planavimas.show(conn, c)
elif pasirinktas == "Update":
    update.show(conn, c)
