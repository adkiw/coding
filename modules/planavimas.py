# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 0) CSS stilius lentelės atvaizdavimui su horizontaliniu skrolu
    # ==============================
    st.markdown("""
    <style>
      .scroll-container {
        overflow-x: auto;
      }
      table {
        border-collapse: collapse;
        width: 100%;
        white-space: nowrap;
      }
      th, td {
        border: 1px solid #ddd;
        padding: 4px;
        vertical-align: top;
        text-align: center;
      }
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
    # 2) Apskaičiuojame datų intervalą: nuo vakar iki dviejų savaičių į priekį
    # ==============================
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=14)  # dvi savaitės į priekį

    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    date_strs = [d.isoformat() for d in date_list]  # pvz. ['2025-06-03', ..., '2025-06-17']

    # ==============================
    # 3) Paimame visų vilkikų informaciją: numeris, priekaba, vadybininkas
    # ==============================
    c.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai ORDER BY numeris")
    vilkikai_rows = c.fetchall()  # [(numeris, priekaba, vadybininkas), ...]
    vilkikai_all = [row[0] for row in vilkikai_rows]

    priekaba_map = { row[0]: (row[1] or "") for row in vilkikai_rows }
    vadybininkas_map = { row[0]: (row[2] or "") for row in vilkikai_rows }

    # ==============================
    # 4) Iš lentelės "kroviniai" paimame:
    #    – vilkikas
    #    – iskrovimo_salis, iskrovimo_regionas → „vietos_kodas“
    #    – date(iskrovimo_data) AS data (vien tik data)
    #    – date(pakrovimo_data)   AS pak_data
    #    Filtruojame pagal date(iskrovimo_data) intervalą.
    # ==============================
    start_str = start_date.isoformat()
    end_str   = end_date.isoformat()
    query = f"""
        SELECT
            vilkikas AS vilkikas,
            iskrovimo_salis AS salis,
            iskrovimo_regionas AS regionas,
            date(iskrovimo_data) AS data,
            date(pakrovimo_data)   AS pak_data
        FROM kroviniai
        WHERE date(iskrovimo_data) BETWEEN '{start_str}' AND '{end_str}'
          AND iskrovimo_data IS NOT NULL
        ORDER BY vilkikas, date(iskrovimo_data)
    """
    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.info("Šiame laikotarpyje nėra planuojamų iškrovimų.")
        return

    # ==============================
    # 5) Konvertuojame „salis“ ir „regionas“ į tekstą, sujungiame į „vietos_kodas“
    # ==============================
    df["salis"]    = df["salis"].fillna("").astype(str)
    df["regionas"] = df["regionas"].fillna("").astype(str)
    df["data"]     = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pak_data"] = pd.to_datetime(df["pak_data"]).dt.date.astype(str)
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
    # 7) Kiekvienam vilkikui parenkame tik paskutinį įrašą („data“ stulpelyje didžiausia reikšmė)
    # ==============================
    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()
    # df_last turi stulpelius: vilkikas, salis, regionas, data (iškrovimo), pak_data (pakrovimo)

    # ==============================
    # 8) Iš lentelės "vilkiku_darbo_laikai" paimame:
    #    – iškrovimo_laikas („iskrovimo_laikas“)
    #    – darbo_laikas    („darbo_laikas“)
    #    – likes_laikas    („likes_laikas“)
    #
    #    Filtruojame pagal `data = pak_data`
    # ==============================
    papildomi_map = {}
    for _, row in df_last.iterrows():
        v     = row["vilkikas"]
        pak_d = row["pak_data"]  # pvz. "2025-06-07"
        rc = c.execute(
            """
            SELECT iskrovimo_laikas, darbo_laikas, likes_laikas
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ? AND data = ?
            ORDER BY id DESC LIMIT 1
            """,
            (v, pak_d)
        ).fetchone()

        if rc:
            ikr_laikas, bdl, ldl = rc
        else:
            ikr_laikas, bdl, ldl = None, None, None

        # Jei None arba NaN → paverčiame į tuščią stringą
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

        # Saugojame pagal raktą (vilkiko numeris, iškrovimo data)
        papildomi_map[(v, row["data"])] = {
            "ikr_laikas": ikr_laikas,
            "bdl":         bdl,
            "ldl":         ldl
        }

    # ==============================
    # 9) Paruošiame stulpelį "cell_val":
    #    – vienoje eilutėje: [vietos_kodas] [ikr_laikas or "--"] [bdl or "--"] [ldl or "--"]
    #    – jeigu „vietos_kodas“ tuščias → grąžinam tuščią stringą
    # ==============================
    def make_cell(vilkikas, iskr_data, vieta):
        if not vieta:
            return ""  # jei regiono nėra, tuščias langelis

        info = papildomi_map.get((vilkikas, iskr_data), {})
        parts = []

        # regiono kodas (pvz. “IT10”)
        parts.append(vieta)

        # iškrovimo laikas arba "--"
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
    #       – index   = vilkikas
    #       – columns = data (iškrovimo data, pvz. '2025-06-05', ..., '2025-06-17')
    #       – values  = cell_val
    # ==============================
    pivot_df = df_last.pivot(
        index="vilkikas",
        columns="data",
        values="cell_val"
    )

    # ==============================
    # 11) Užtikriname, kad stulpeliai atitiktų visas „date_strs“ datas
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 12) Rodyti tik vilkikus, turinčius „df_last“ įrašą (t.y. tie, kurie iškrauna per du savaites)
    # ==============================
    pivot_df = pivot_df.reindex(index=df_last["vilkikas"].unique(), fill_value="")

    # ==============================
    # 13) Paimame SA (paskutinę reikšmę) iš vilkiku_darbo_laikai kiekvienam vilkikui:
    #     – filtruojame pagal `data = pak_data`
    # ==============================
    sa_map = {}
    for v in pivot_df.index:
        pak_d = df_last.loc[df_last["vilkikas"] == v, "pak_data"].values[0]
        row = c.execute(
            """
            SELECT sa
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ? AND data = ?
            ORDER BY id DESC LIMIT 1
            """,
            (v, pak_d)
        ).fetchone()
        sa_map[v] = row[0] if row and row[0] is not None else ""

    # ==============================
    # 14) Sukuriame indekso (eilutės) pavadinimą:
    #       “Vilkikas/Priekaba Vadybininkas SA”
    #     – be tarpų aplink “/”
    #     – jei priekaba yra, pridedame “/<priekaba>”
    #     – jei vadybininkas yra, pridedame “ <vadybininkas>”
    #     – jei SA yra, pridedame “ <SA>”
    # ==============================
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad  = vadybininkas_map.get(v, "")
        sa   = sa_map.get(v, "")

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
    # 15) Generuojame HTML lentelę su horizontaliu skrolu
    # ==============================
    html = "<div class='scroll-container'><table>\n"
    # 15.1) Antraštės eilutė
    html += "  <thead>\n    <tr>\n"
    html += "      <th>Vilkikas/Priekaba Vadybininkas SA</th>\n"
    for d in date_strs:
        html += f"      <th>{d}</th>\n"
    html += "    </tr>\n  </thead>\n"

    # 15.2) Turinio eilutės
    html += "  <tbody>\n"
    for idx in pivot_df.index:
        html += "    <tr>\n"
        html += f"      <td>{idx}</td>\n"
        for d in date_strs:
            val = pivot_df.at[idx, d]
            # jei val = NaN arba blank, paliekame tuščią
            if pd.isna(val) or str(val).strip() == "":
                cell_html = ""
            else:
                cell_html = val
            html += f"      <td>{cell_html}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n</table></div>"

    st.markdown(html, unsafe_allow_html=True)
