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

    # 2) SQL užklausa: kiekvienam vilkikui rasti paskutinį „Iškrauta“ įrašą vilkiku_darbo_laikai
    query = """
        SELECT v.vilkiko_numeris AS vilkikas,
               v.atvykimo_iskrovimas AS paskutinis_regionas,
               v.data AS paskutine_data
        FROM vilkiku_darbo_laikai v
        WHERE v.iskrovimo_statusas = 'Iškrauta'
          AND v.data = (
              SELECT MAX(v2.data)
              FROM vilkiku_darbo_laikai v2
              WHERE v2.vilkiko_numeris = v.vilkiko_numeris
                AND v2.iskrovimo_statusas = 'Iškrauta'
          )
        ORDER BY v.vilkiko_numeris
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
