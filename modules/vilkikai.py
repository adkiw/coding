# modules/vilkikai.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Vilkikai")

    st.subheader("Įkelti Vilkikų duomenis")
    failas = st.file_uploader("Pasirinkite Excel failą", type=["xlsx"])
    if failas:
        df = pd.read_excel(failas)
        st.dataframe(df.head())
        if st.button("Įkelti į DB"):
            for _, row in df.iterrows():
                try:
                    c.execute("""
                        INSERT OR IGNORE INTO vilkikai (
                            numeris, marke, modelis, vin, registracijos_metai,
                            tipas, keliamoji_galia, teatras
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["Numeris"], row["Markė"], row["Modelis"], row["VIN"],
                        row["Registracijos metai"], row["Tipas"],
                        row["Keliamoji galia"], row["Teatras"]
                    ))
                    conn.commit()
                except Exception as e:
                    st.error(f"❌ Klaida vykdant: {e}")
            st.success("✅ Vilkikai įvesti.")

    st.markdown("---")
    st.subheader("Esami Vilkikai")
    vilk_df = pd.DataFrame(c.execute("SELECT * FROM vilkikai").fetchall(),
                          columns=[
                              "id", "Numeris", "Markė", "Modelis", "VIN",
                              "Registracijos metai", "Tipas",
                              "Keliamoji galia", "Teatras"
                          ])
    st.dataframe(vilk_df)
