# main.py

import streamlit as st
st.set_page_config(layout="wide")

# Tiesiogiai importuojame kiekvieną modulį iš modules katalogo
import modules.dispo as dispo
import modules.kroviniai as kroviniai
import modules.vilkikai as vilkikai
import modules.priekabos as priekabos
import modules.grupes as grupes
import modules.vairuotojai as vairuotojai
import modules.klientai as klientai
import modules.darbuotojai as darbuotojai
import modules.nustatymai as nustatymai
import modules.planavimas as planavimas
import modules.update as update

from db import init_db

# Prisijungimas prie DB
conn, c = init_db()

# Moduliai rodomi meniu
moduliai = [
    "Dispo", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai", "Planavimas", "Update"
]

# Streamlit šoninis meniu
st.sidebar.title("MENIU")
modulis = st.sidebar.radio("Pasirinkite modulį:", moduliai)

# Pagrindinis logikos blokas: kviečiame atitinkamo modulio show() funkciją
if modulis == "Dispo":
    dispo.show(conn, c)
elif modulis == "Kroviniai":
    kroviniai.show(conn, c)
elif modulis == "Vilkikai":
    vilkikai.show(conn, c)
elif modulis == "Priekabos":
    priekabos.show(conn, c)
elif modulis == "Grupės":
    grupes.show(conn, c)
elif modulis == "Vairuotojai":
    vairuotojai.show(conn, c)
elif modulis == "Klientai":
    klientai.show(conn, c)
elif modulis == "Darbuotojai":
    darbuotojai.show(conn, c)
elif modulis == "Nustatymai":
    nustatymai.show(conn, c)
elif modulis == "Planavimas":
    planavimas.show(conn, c)
elif modulis == "Update":
    update.show(conn, c)
