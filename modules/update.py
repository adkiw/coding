# modules/update.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Update")

    st.subheader("Įkelti atnaujintą iškrovimo informaciją")
    failas = st.file_uploader("Pasirinkite Excel failą", type=["xlsx"])
    if failas:
        df = pd.read_excel(failas)
        st.dataframe(df.head())
        if st.button("Įkelti atnaujintus duomenis į DB"):
            for _, row in df.iterrows():
                try:
                    c.execute("""
                        INSERT INTO vilkiku_darbo_laikai (
                            vilkiko_numeris, data, iskrovimo_statusas,
                            iskrovimo_data, iskrovimo_laikas, sa
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        row["Vilkiko numeris"], row["Data"],
                        row["Iškr. statusas"], row["Iškr. data (edit)"],
                        row["Iškr. laikas (edit)"], row["SA"]
                    ))
                    conn.commit()
                except Exception as e:
                    st.error(f"❌ Klaida vykdant: {e}")
            st.success("✅ Atkurtas vilkikų darbo laikas įvestas.")

    st.markdown("---")
    st.subheader("Esama atnaujinta informacija")
    darbo_laikai_df = pd.DataFrame(
        c.execute("SELECT * FROM vilkiku_darbo_laikai").fetchall(),
        columns=[
            "id", "Vilkiko numeris", "Data", "Iškr. statusas",
            "Iškr. data", "Iškr. laikas", "SA"
        ]
    )
    st.dataframe(darbo_laikai_df)
