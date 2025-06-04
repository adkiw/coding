# modules/darbuotojai.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Darbuotojai")

    st.subheader("Įkelti Darbuotojų duomenis")
    failas = st.file_uploader("Pasirinkite Excel failą", type=["xlsx"])
    if failas:
        df = pd.read_excel(failas)
        st.dataframe(df.head())
        if st.button("Įkelti į DB"):
            for _, row in df.iterrows():
                try:
                    c.execute("""
                        INSERT OR IGNORE INTO darbuotojai (
                            vardas, pavarde, pareigos, skyrius,
                            telefonas, el_pastas
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        row["Vardas"], row["Pavardė"], row["Pareigos"],
                        row["Skyrius"], row["Telefonas"], row["El. paštas"]
                    ))
                    conn.commit()
                except Exception as e:
                    st.error(f"❌ Klaida vykdant: {e}")
            st.success("✅ Darbuotojai įvesti.")

    st.markdown("---")
    st.subheader("Esami Darbuotojai")
    darbuotojai_df = pd.DataFrame(c.execute("SELECT * FROM darbuotojai").fetchall(),
                                  columns=[
                                      "id", "Vardas", "Pavardė", "Pareigos",
                                      "Skyrius", "Telefonas", "El. paštas"
                                  ])
    st.dataframe(darbuotojai_df)
