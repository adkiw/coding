# modules/planavimas.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Planavimas")

    # 1) Gauti visas ekspedicijos grupes
    c.execute("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris")
    grupes = c.fetchall()  # kiekvienas įrašas: (id, numeris, pavadinimas)

    # Paruošiame pasirinkimo laukelį
    group_options = ["Visi"] + [f"{numeris} – {pavadinimas}" for _, numeris, pavadinimas in grupes]
    selected = st.selectbox("Pasirinkti ekspedicijos grupę", group_options)

    # 2) SQL užklausa: kiekvienam vilkikui rasti paskutinį (didžiausią) iškrovimo įrašą
    query = """
        SELECT k.vilkikas AS vilkikas,
               k.iskrovimo_regionas AS paskutinis_regionas,
               k.iskrovimo_data AS paskutine_data
        FROM kroviniai k
        JOIN (
            SELECT vilkikas AS v, MAX(iskrovimo_data) AS max_data
            FROM kroviniai
            WHERE iskrovimo_data IS NOT NULL
            GROUP BY vilkikas
        ) sub ON k.vilkikas = sub.v AND k.iskrovimo_data = sub.max_data
        WHERE k.vilkikas IS NOT NULL
        ORDER BY k.vilkikas
    """
    df = pd.read_sql_query(query, conn)

    # 3) Jeigu pasirinkta konkreti grupė, filtruojame pagal regionus
    if selected != "Visi":
        # Išskiriame grupės numerį (prieš „ – “)
        numeris = selected.split(" – ")[0]
        # Randame atitinkamą grupe_id
        grupe_id = None
        for gid, gnum, _ in grupes:
            if gnum == numeris:
                grupe_id = gid
                break

        # Jeigu radome grupę, gauname jos regionų kodus
        if grupe_id is not None:
            c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id,)
            )
            regionai = [row[0] for row in c.fetchall()]
            # Filtruojame DataFrame pagal paskutinį iškrovimo regioną
            df = df[df["paskutinis_regionas"].isin(regionai)]

    # 4) Rodome rezultatus
    if df.empty:
        st.info("Nėra duomenų pagal pasirinktą grupę.")
    else:
        df = df.rename(columns={
            "vilkikas": "Vilkiko numeris",
            "paskutinis_regionas": "Paskutinis iškrovimo regionas",
            "paskutine_data": "Paskutinė iškrovimo data"
        })
        st.dataframe(df, use_container_width=True)
