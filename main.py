# main.py

import streamlit as st
import sqlite3

# 1) Privalo būti pirmasis: tinkamas page config
st.set_page_config(layout="wide")

# 2) “Hot‐zone” CSS + nematomas swipe‐down sidebar
st.markdown("""
    <style>
      [data-testid="stSidebar"] {
        position: fixed;
        top: -100%;
        left: 0;
        width: 250px;
        height: 100vh;
        background-color: var(--primary-background-color);
        transition: top 0.3s ease-in-out;
        z-index: 1000;
      }
      .hover-zone {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 20px;
        z-index: 999;
      }
      .hover-zone:hover + [data-testid="stSidebar"] {
        top: 0;
      }
      [data-testid="stSidebar"]:hover {
        top: 0;
      }
      th, td, .stTextInput>div>div>input, .stDateInput>div>div>input {
        font-size: 12px !important;
      }
      .tiny {
        font-size: 10px;
        color: #888;
      }
      .block-container {
        padding-top: 0.5rem !important;
      }
      div[role="option"] svg,
      div[role="combobox"] svg,
      span[data-baseweb="select"] svg {
        display: none !important;
      }
    </style>
    <div class="hover-zone"></div>
""", unsafe_allow_html=True)

# 3) Prisijungimas prie SQLite DB
conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
c = conn.cursor()

# 4) Importai
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

# 5) Sidebar meniu (paslėptas, kol neatsidurs viršuje hover)
with st.sidebar:
    st.header("📂 Pasirink modulį")
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
    pasirinktas = st.radio("", moduliai)

# 6) Pagal pasirinktą modulį kviečiame atitinkamą show(...)
#    Jeigu „dispo“ modulyje SQL vēl klaida, pasitikrinkite 1. ir 2. punktus
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
