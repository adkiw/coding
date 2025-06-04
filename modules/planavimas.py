# modules/planavimas.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Planavimas")

    # 1) Užkrauname visas ekspedicijos grupes (id, numeris, pavadinimas)
    c.execute("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris")
    grupes = c.fetchall()  # sąrašas tuplų: (id, numeris, pavadinimas)

    # Pasirinkimo langelis (streamlit selectbox)
    group_options = ["Visi"] + [f"{numeris} – {pavadinimas}" for _, numeris, pavadinimas in grupes]
    selected = st.selectbox("Pasirinkti ekspedicijos grupę", group_options)

    # 2) SQL: kiekvienam vilkikui paimti jo paskutinį 'iškrovimo' įrašą iš lentelės kroviniai
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
        ) sub
          ON k.vilkikas = sub.v
         AND k.iskrovimo_data = sub.max_data
        WHERE k.vilkikas IS NOT NULL
        ORDER BY k.vilkikas
    """
    df = pd.read_sql_query(query, conn)

    # 3) Jei pasirinkta tam tikra ekspedicijos grupė, filtruojame pagal regionus
    if selected != "Visi":
        # Išskiriame grupės numerį iki " – " (pvz. EKSP1)
        numeris = selected.split(" – ")[0]

        # Randame iš 'grupes' lentelės tą id, kur numeris == pasirinktas numeris
        grupe_id = None
        for gid, gnum, _ in grupes:
            if gnum == numeris:
                grupe_id = gid
                break

        if grupe_id is not None:
            # Iš 'grupiu_regionai' lentelės surenkame regionų kodus
            c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id,)
            )
            regionai = [row[0] for row in c.fetchall()]

            # Filtruojame DataFrame pagal tai, kas matoma stulpelyje 'paskutinis_regionas'
            df = df[df["paskutinis_regionas"].isin(regionai)]

    # 4) Gautą DataFrame atvaizduojame streamlit'e
    if df.empty:
        st.info("Nėra duomenų pagal pasirinktą grupę.")
    else:
        # Pervadiname stulpelius, kad būtų aiškiau
        df = df.rename(columns={
            "vilkikas": "Vilkiko numeris",
            "paskutinis_regionas": "Paskutinis iškrovimo regionas",
            "paskutine_data": "Paskutinė iškrovimo data"
        })
        st.dataframe(df, use_container_width=True)
