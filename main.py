# main.py

import streamlit as st
import sqlite3

# 1) Standartinis set_page_config (privalo būti pirmasis Streamlit komanda)
st.set_page_config(layout="wide")

# 2) CSS: paslėptas viršutinis juostos radionavigacijos blokas, kuris išsiplečia hover‘ui
st.markdown("""
    <style>
      /* Nematomos 5px aukščio „hot zone“ lango viršuje */
      .hover-zone {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        z-index: 999;
      }
      /* Streamlit radio blokas – fiksuojamas virš ekrano, pasislepia už -40px */
      .stRadio {
        position: fixed;
        top: -40px;
        left: 0;
        right: 0;
        background-color: var(--primary-background-color);
        z-index: 1000;
        height: 40px;
        overflow: hidden;
        transition: top 0.3s ease-in-out;
        display: flex;
        align-items: center;
        justify-content: center;
        padding-left: 10px;
      }
      /* Hover virš nematomos zonos – radionavigacija nusileidžia */
      .hover-zone:hover + .stRadio {
        top: 0;
      }
      /* Jei užvedame pelę tiesiai virš radio bloko – laikome jį atvertą */
      .stRadio:hover {
        top: 0;
      }
      /* Sutrumpintas fontas, kad tilptų tekstas */
      .stRadio label, .stRadio div {
        font-size: 14px !important;
      }
    </style>
    <!-- Nematomos „hot zone“ div -->
    <div class="hover-zone"></div>
""", unsafe_allow_html=True)

# 3) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 4) Importuojame visus modulius
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

# 5) Radionavigacija viršuje (paslėpta, kol hover‘uojama virš „hot zone“)
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

# 6) Pagal pasirinktą modulį kviečiame atitinkamą show(...)
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
