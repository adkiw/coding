import streamlit as st
st.set_page_config(layout="wide")

from modules import dispo, kroviniai, vilkikai, priekabos, grupes, vairuotojai, klientai, darbuotojai, nustatymai, update
from db import init_db

# Prisijungimas prie DB
conn, c = init_db()

# Moduliai rodomi meniu
moduliai = [
    "Dispo", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai", "Update"
]

# Modulio pasirinkimas
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# Modulių vykdymas
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
elif modulis == "Update":
    update.show(conn, c)
