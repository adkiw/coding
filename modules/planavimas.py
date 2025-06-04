# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 1) Užkrauname visas ekspedicijos grupes (id, numeris, pavadinimas)
    # ==============================
    c.execute("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris")
    grupes = c.fetchall()  # kiekvienas: (id, numeris, pavadinimas)

    # Paruošiame pasirinkimo laukelį grupių filtravimui
    group_options = ["Visi"] + [f"{numeris} – {pavadinimas}" for _, numeris, pavadinimas in grupes]
    selected = st.selectbox("Pasirinkti ekspedicijos grupę", group_options)

    # ==============================
    # 2) Apskaičiuojame datų intervalą: nuo vakar iki savaitės į priekį
    # ==============================
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=7)

    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    date_strs = [d.isoformat() for d in date_list]

    # ==============================
    # 3) Paimame visų vilkikų numerius su priekaba ir pagrindiniu vadybininku
    # ==============================
    c.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai ORDER BY numeris")
    vilkikai_rows = c.fetchall()  # kiekvienas: (numeris, priekaba, vadybininkas)
    vilkikai_all = [row[0] for row in vilkikai_rows]

    priekaba_map = {row[0]: (row[1] or "") for row in vilkikai_rows}
    vadybininkas_map = {row[0]: (row[2] or "") for row in vilkikai_rows}

    # ==============================
    # 4) Iš lentelės "kroviniai" paimame įrašus su iškrovimo data šiame intervale
    # ==============================
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    query = f"""
        SELECT
            vilkikas AS vilkikas,
            iskrovimo_salis AS salis,
            iskrovimo_regionas AS regionas,
            iskrovimo_data AS data
        FROM kroviniai
        WHERE iskrovimo_data BETWEEN '{start_str}' AND '{end_str}'
          AND iskrovimo_data IS NOT NULL
        ORDER BY vilkikas, iskrovimo_data
    """
    df = pd.read_sql_query(query, conn)

    # Jei nėra jokių įrašų šiame intervale, rodome pranešimą ir išeiname
    if df.empty:
        st.info("Šiame laikotarpyje nėra planuojamų iškrovimų.")
        return

    # ==============================
    # 5) Sukuriame stulpelį "vietos_kodas" = "šalis"+"regionas", pvz. "IT10"
    # ==============================
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"].fillna("") + df["regionas"].fillna("")

    # ==============================
    # 6) Jeigu pasirinkta konkreti ekspedicijos grupė – filtruojame pagal grupės regionus
    # ==============================
    if selected != "Visi":
        numeris = selected.split(" – ")[0]
        grupe_id = None
        for gid, gnum, _ in grupes:
            if gnum == numeris:
                grupe_id = gid
                break

        if grupe_id is not None:
            c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id,)
            )
            regionai = [row[0] for row in c.fetchall()]
            # Filtruojame df – paliekame tik tuos įrašus, kurių vietos_kodas yra grupės regionuose
            df = df[df["vietos_kodas"].isin(regionai)]

    # Jei po grupės filtravimo nebeliko įrašų, rodome info ir išeiname
    if df.empty:
        st.info("Pasirinktoje ekspedicijos grupėje nėra planuojamų iškrovimų per šį laikotarpį.")
        return

    # ==============================
    # 7) Pivot lentelės kūrimas:
    #    index = vilkikas, columns = data, values = vietos_kodas
    # ==============================
    pivot_df = df.pivot(
        index="vilkikas",
        columns="data",
        values="vietos_kodas"
    )

    # ==============================
    # 8) Užtikriname, kad pivot lentelė turi VISAS datas kaip stulpelius
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 9) Filtruojame eilutes pagal tai, ar vilkikas egzistuoja df po filtravimo
    #    Jeigu grupė "Visi" – rodomi visi vilkikai; jeigu kita grupė – tik tie,
    #    kurie turi bent vieną ne-tuščią langelį
    # ==============================
    if selected == "Visi":
        pivot_df = pivot_df.reindex(index=vilkikai_all, fill_value="")
    else:
        pivot_df = pivot_df.dropna(how="all", subset=date_strs)

    # ==============================
    # 10) Paimame SA reikšmes iš paskutinio įrašo vilkiku_darbo_laikai kiekvienam vilkikui
    # ==============================
    # Paruošiame žemėlapį: vilkikas -> SA (naujausias)
    sa_map = {}
    for v in pivot_df.index:
        row = c.execute(
            """
            SELECT sa
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ?
              AND sa IS NOT NULL
            ORDER BY data DESC LIMIT 1
            """, (v,)
        ).fetchone()
        sa_map[v] = row[0] if row and row[0] else ""

    # ==============================
    # 11) Sukuriame naują indekso stulpelį:
    #     "Vilkikas/Priekaba Vadybininkas SA"
    # - Tarp vilkiko ir priekabos nėra tarpų aplink "/"
    # - Tarp vadybininko ir SA įdedamas tarpas
    # ==============================
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        sa = sa_map.get(v, "")

        # Suformuojame "Vilkikas/Priekaba"
        vp_part = v
        if priek:
            vp_part += f"/{priek}"

        # Po to " Vadybininkas" (jei yra)
        if vad:
            vp_part += f" {vad}"

        # Ir galiausiai " SA" (jei yra)
        if sa:
            vp_part += f" {sa}"

        combined_index.append(vp_part)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas/Priekaba Vadybininkas SA"

    # ==============================
    # 12) Išvedame lentelę Streamlit'e
    # ==============================
    st.dataframe(pivot_df, use_container_width=True)
