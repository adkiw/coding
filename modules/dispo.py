# modules/dispo.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Dispo")

    st.subheader("Įkelti Dispo duomenis")
    failas = st.file_uploader("Pasirinkite Excel failą", type=["xlsx"])
    if failas:
        df = pd.read_excel(failas)
        st.dataframe(df.head())
        if st.button("Įkelti į DB"):
            for _, row in df.iterrows():
                try:
                    c.execute("""
                        INSERT OR IGNORE INTO dispo (
                            vilkikas, priekaba, klientas, pakrovimo_data,
                            pakrovimo_laikas, iskrovimo_salis,
                            iskrovimo_regionas, iskrovimo_data,
                            iskrovimo_laikas_nuo, vaziuos, rodiklio_tip
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["Vilkikas"], row["Priekaba"], row["Klientas"],
                        row["Pakrovimo data"], row["Pakrovimo laikas"],
                        row["Iškr. šalis"], row["Iškr. regionas"],
                        row["Iškr. data"], row["Iškr. laikas nuo"],
                        row["Vaziuos"], row["Rodiklio tipas"]
                    ))
                    conn.commit()
                except Exception as e:
                    st.error(f"❌ Klaida vykdant: {e}")
            st.success("✅ Dispo duomenys įvesti.")

    st.markdown("---")
    st.subheader("Esami Dispo įrašai")
    dispo_df = pd.DataFrame(c.execute("SELECT * FROM dispo").fetchall(),
                           columns=[
                               "id", "Vilkikas", "Priekaba", "Klientas",
                               "Pakrovimo data", "Pakrovimo laikas",
                               "Iškr. šalis", "Iškr. regionas",
                               "Iškr. data", "Iškr. laikas nuo",
                               "Vaziuos", "Rodiklio tipas"
                           ])
    st.dataframe(dispo_df)
