# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 0) Patikriname, ar lentelėje "kroviniai" yra reikiami stulpeliai.
    #    Jei jų nėra, pridedame per ALTER TABLE.
    # ==============================
    existing_cols = {r[1] for r in c.execute("PRAGMA table_info(kroviniai)").fetchall()}
    needed_cols = {
        'pakrovimo_salis':    'TEXT',
        'pakrovimo_regionas': 'TEXT',
        'iskrovimo_salis':    'TEXT',
        'iskrovimo_regionas': 'TEXT'
    }
    for col, coltype in needed_cols.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE kroviniai ADD COLUMN {col} {coltype}")
    conn.commit()

    # ==============================
    # 1) CSS stilius lentelės atvaizdavimui su horizontaliniu skrolu
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
    # 2) Užkrauname visas ekspedicijos grupes (id, numeris, pavadinimas)
    # ==============================
    c.execute("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris")
    grupes = c.fetchall()  # [(id, numeris, pavadinimas), ...]

    group_options = ["Visi"] + [f"{numeris} – {pavadinimas}" for _, numeris, pavadinimas in grupes]
    selected = st.selectbox("Pasirinkti ekspedicijos grupę", group_options)

    # ==============================
    # 3) Apskaičiuojame datų intervalą: nuo vakar iki dviejų savaičių į priekį
    # ==============================
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=14)

    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    date_strs = [d.isoformat() for d in date_list]  # pvz. ['2025-06-03', ..., '2025-06-17']

    # ==============================
    # 4) Paimame visų vilkikų informaciją: numeris, priekaba, vadybininkas
    # ==============================
    c.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai ORDER BY numeris")
    vilkikai_rows = c.fetchall()  # [(numeris, priekaba, vadybininkas), ...]
    vilkikai_all = [row[0] for row in vilkikai_rows]

    priekaba_map = {row[0]: (row[1] or "") for row in vilkikai_rows}
    vadybininkas_map = {row[0]: (row[2] or "") for row in vilkikai_rows}

    # ==============================
    # 5) Iš lentelės "kroviniai" paimame įrašus su iškrovimo data šiame intervale
    #    – ištraukiame vilkikas, iskrovimo_salis, iskrovimo_regionas, date(iskrovimo_data), date(pakrovimo_data)
    # ==============================
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
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
    # 6) Konvertuojame „salis“ ir „regionas“ į tekstą, sujungiame į „vietos_kodas“
    # ==============================
    df["salis"] = df["salis"].fillna("").astype(str)
    df["regionas"] = df["regionas"].fillna("").astype(str)
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pak_data"] = pd.to_datetime(df["pak_data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"] + df["regionas"]  # pvz. "IT10"

    # ==============================
    # 7) Filtravimas pagal ekspedicijos grupę (jei pasirinkta ne „Visi“)
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
    # 8) Parenkame tik paskutinį (didžiausią) kiekvieno vilkiko įrašą šiame intervale
    # ==============================
    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()
    # df_last turi stulpelius: vilkikas, salis, regionas, data, pak_data, vietos_kodas

    # ==============================
    # 9) Iš lentelės "vilkiku_darbo_laikai" paimame papildomus laukus pagal pakrovimo datą:
    #    – iškrovimo_laikas (ikr_laikas)
    #    – darbo_laikas    (bdl)
    #    – likes_laikas    (ldl)
    # ==============================
    papildomi_map = {}
    for _, row in df_last.iterrows():
        v = row["vilkikas"]
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

        papildomi_map[(v, row["data"])] = {
            "ikr_laikas": ikr_laikas,
            "bdl":         bdl,
            "ldl":         ldl
        }

    # ==============================
    # 10) Paruošiame funkciją formuoti langelio reikšmę:
    #     – vietos_kodas ikr_laikas_or_-- bdl_or_-- ldl_or_--
    #     – jeigu vietos_kodas tuščias: tuščias langelis
    # ==============================
    def make_cell(vilkikas, iskr_data, vieta):
        if not vieta:
            return ""
        info = papildomi_map.get((vilkikas, iskr_data), {})
        parts = []
        parts.append(vieta)
        ikr = info.get("ikr_laikas", "")
        parts.append(ikr if ikr else "--")
        bdl_val = info.get("bdl", "")
        parts.append(bdl_val if bdl_val else "--")
        ldl_val = info.get("ldl", "")
        parts.append(ldl_val if ldl_val else "--")
        return " ".join(parts)

    df_last["cell_val"] = df_last.apply(
        lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]),
        axis=1
    )

    # ==============================
    # 11) Sukuriame pivot lentelę:
    #       – index   = vilkikas
    #       – columns = data (iškrovimo data)
    #       – values  = cell_val
    # ==============================
    pivot_df = df_last.pivot(
        index="vilkikas",
        columns="data",
        values="cell_val"
    )

    # ==============================
    # 12) Užtikriname, kad stulpeliai atitiktų visas datas intervale
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 13) Filtruojame eilutes: rodome tik tuos vilkikus, kurie turi df_last įrašą
    # ==============================
    pivot_df = pivot_df.reindex(index=df_last["vilkikas"].unique(), fill_value="")

    # ==============================
    # 14) Paimame SA (paskutinę) iš vilkiku_darbo_laikai kiekvienam vilkikui
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
    # 15) Sukuriame indekso pavadinimą:
    #       – vilkikas
    #       – jei yra priekaba: "/priekaba"
    #       – jei yra vadybininkas: " vadybininkas"
    #       – jei yra SA: " SA"
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
    # 16) Atvaizduojame HTML lentelę su horizontaliu skrolu
    # ==============================
    html = "<div class='scroll-container'><table>\n"
    html += "  <thead>\n    <tr>\n"
    html += "      <th title='Vilkikas/Priekaba Vadybininkas SA'>Vilkikas/Priekaba Vadybininkas SA</th>\n"
    for d in date_strs:
        html += f"      <th>{d}</th>\n"
    html += "    </tr>\n  </thead>\n"
    html += "  <tbody>\n"
    for idx in pivot_df.index:
        html += "    <tr>\n"
        html += f"      <td>{idx}</td>\n"
        for d in date_strs:
            val = pivot_df.at[idx, d]
            if pd.isna(val) or str(val).strip() == "":
                cell_html = ""
            else:
                cell_html = val
            html += f"      <td>{cell_html}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n</table></div>"

    st.markdown(html, unsafe_allow_html=True)
