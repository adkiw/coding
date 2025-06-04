# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 0) CSS stilius lentelės atvaizdavimui
    # ==============================
    st.markdown("""
    <style>
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 4px; vertical-align: top; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    # ==============================
    # 1) Užkrauname visas ekspedicijos grupes (id, numeris, pavadinimas)
    # ==============================
    c.execute("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris")
    grupes = c.fetchall()  # [(id, numeris, pavadinimas), ...]

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
    date_strs = [d.isoformat() for d in date_list]  # ['YYYY-MM-DD', ...]

    # ==============================
    # 3) Paimame visų vilkikų informaciją: numeris, priekaba, vadybininkas
    # ==============================
    c.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai ORDER BY numeris")
    vilkikai_rows = c.fetchall()  # [(numeris, priekaba, vadybininkas), ...]
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

    if df.empty:
        st.info("Šiame laikotarpyje nėra planuojamų iškrovimų.")
        return

    # ==============================
    # 5) Konvertuojame „salis“ ir „regionas“ į tekstą, sujungiame į „vietos_kodas“
    # ==============================
    df["salis"] = df["salis"].fillna("").astype(str)
    df["regionas"] = df["regionas"].fillna("").astype(str)
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"] + df["regionas"]  # pvz. "IT10"

    # ==============================
    # 6) Filtravimas pagal ekspedicijos grupę (jei pasirinkta ne „Visi“)
    # ==============================
    if selected != "Visi":
        numeris = selected.split(" – ")[0]
        grupe_id = next((gid for gid, gnum, _ in grupes if gnum == numeris), None)
        if grupe_id is not None:
            c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id,)
            )
            regionai = [row[0] for row in c.fetchall()]  # pvz. ["FR10", "IT20", ...]
            df = df[df["vietos_kodas"].apply(lambda x: any(x.startswith(r) for r in regionai))]

    if df.empty:
        st.info("Pasirinktoje ekspedicijos grupėje nėra planuojamų iškrovimų per šį laikotarpį.")
        return

    # ==============================
    # 7) Parenkame tik paskutinį (didžiausią) kiekvieno vilkiko įrašą šiame intervale
    # ==============================
    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()

    # ==============================
    # 8) Iš lentelės "vilkiku_darbo_laikai" paimame papildomus laukus:
    #    – iskrovimo_laikas
    #    – darbo_laikas (BDL)
    #    – likes_laikas (LDL)
    # ==============================
    papildomi_map = {}
    for _, row in df_last.iterrows():
        v = row["vilkikas"]
        d = row["data"]
        rc = c.execute(
            """
            SELECT iskrovimo_laikas, darbo_laikas, likes_laikas
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ? AND iskrovimo_data = ?
            ORDER BY id DESC LIMIT 1
            """,
            (v, d)
        ).fetchone()
        if rc:
            ikr_laikas, bdl, ldl = rc
        else:
            ikr_laikas, bdl, ldl = None, None, None

        # Jeigu None arba NaN, paverčiame tuščius stringus
        if ikr_laikas is None or (isinstance(ikr_laikas, float) and pd.isna(ikr_laikas)):
            ikr_laikas = ""
        else:
            ikr_laikas = str(ikr_laikas)

        if bdl is None or (isinstance(bdl, float) and pd.isna(bdl)):
            bdl = ""
        else:
            bdl = str(bdl)

        if ldl is None or (isinstance(ldl, float) and pd.isna(ldl)):
            ldl = ""
        else:
            ldl = str(ldl)

        papildomi_map[(v, d)] = {
            "ikr_laikas": ikr_laikas,
            "bdl": bdl,
            "ldl": ldl
        }

    # ==============================
    # 9) Paruošiame stulpelį "cell_val":
    #     – vienoje eilutėje: regiono_kodas ikr_laikas_or_-- bdl_or_-- ldl_or_--
    #     – jeigu regiono nėra, langelis tuščias
    # ==============================
    def make_cell(vilkikas, data, vieta):
        if not vieta:
            return ""  # jeigu nėra regiono, langelis tuščias

        info = papildomi_map.get((vilkikas, data), {})
        parts = []

        # Regiono kodas visada pirmas
        parts.append(vieta)

        # Iškr. laikas arba "--"
        ikr = info.get("ikr_laikas", "")
        parts.append(ikr if ikr else "--")

        # BDL arba "--"
        bdl_val = info.get("bdl", "")
        parts.append(bdl_val if bdl_val else "--")

        # LDL arba "--"
        ldl_val = info.get("ldl", "")
        parts.append(ldl_val if ldl_val else "--")

        return " ".join(parts)

    df_last["cell_val"] = df_last.apply(
        lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]),
        axis=1
    )

    # ==============================
    # 10) Sukuriame pivot lentelę:
    #     index = vilkikas, columns = data, values = cell_val
    # ==============================
    pivot_df = df_last.pivot(
        index="vilkikas",
        columns="data",
        values="cell_val"
    )

    # ==============================
    # 11) Užtikriname, kad stulpeliai atitiktų visas datas intervale
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 12) Filtruojame eilutes pagal grupės logiką:
    #     – Jei "Visi": rodomi visi vilkikai (tuščiomis eilutėmis)
    #     – Jei kita grupė: rodomi tik tie vilkikai, kurių yra įrašas df_last
    # ==============================
    if selected == "Visi":
        pivot_df = pivot_df.reindex(index=vilkikai_all, fill_value="")
    else:
        pivot_df = pivot_df.reindex(index=df_last["vilkikas"].unique(), fill_value="")

    # ==============================
    # 13) Paimame SA iš paskutinio "vilkiku_darbo_laikai" įrašo kiekvienam vilkikui
    # ==============================
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
        sa_map[v] = row[0] if row and row[0] is not None else ""

    # ==============================
    # 14) Sukuriame indekso stulpelį:
    #     "Vilkikas/Priekaba Vadybininkas SA"
    # ==============================
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        sa = sa_map.get(v, "")

        label = v
        if priek:
            label += f"/{priek}"
        if vad:
            label += f" {vad}"
        if sa:
            label += f" {sa}"

        combined_index.append(label)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas/Priekaba Vadybininkas SA"

    # ==============================
    # 15) Išvedame HTML lentelę per st.markdown
    # ==============================
    html = "<table>\n"
    # Antraštės
    html += "  <thead>\n    <tr>\n"
    html += "      <th>Vilkikas/Priekaba Vadybininkas SA</th>\n"
    for d in date_strs:
        html += f"      <th>{d}</th>\n"
    html += "    </tr>\n  </thead>\n"
    # Turinio eilutės
    html += "  <tbody>\n"
    for idx in pivot_df.index:
        html += "    <tr>\n"
        html += f"      <td>{idx}</td>\n"
        for d in date_strs:
            val = pivot_df.at[idx, d]
            # Jei langelis lygus NaN arba yra tuščias stringas, rodome blank
            if pd.isna(val) or str(val).strip() == "":
                cell_html = ""
            else:
                cell_html = val
            html += f"      <td>{cell_html}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n</table>"

    st.markdown(html, unsafe_allow_html=True)
