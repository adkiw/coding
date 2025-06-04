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
    # 5) Užtikriname, kad "salis" ir "regionas" yra tekstinio tipo ir tuščias vietoje NULL
    # ==============================
    df["salis"] = df["salis"].fillna("").astype(str)
    df["regionas"] = df["regionas"].fillna("").astype(str)

    # Sukuriame stulpelį "vietos_kodas" = "salis"+"regionas", pvz. "IT10"
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"] + df["regionas"]

    # ==============================
    # 6) Jeigu pasirinkta ekspedicijos grupė – filtruojame pagal grupės regionus
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

            # Filtruojame: vietos_kodas turi prasidėti nuo bent vieno regiono kodo
            df = df[df["vietos_kodas"].apply(lambda x: any(x.startswith(r) for r in regionai))]

    # Jei po grupės filtravimo nebeliko įrašų, rodome pranešimą ir išeiname
    if df.empty:
        st.info("Pasirinktoje ekspedicijos grupėje nėra planuojamų iškrovimų per šį laikotarpį.")
        return

    # ==============================
    # 7) Atrenkame tik paskutinį įrašą per vilkiką šiame intervale
    # ==============================
    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()

    # ==============================
    # 8) Papildomų duomenų paėmimas iš vilkiku_darbo_laikai:
    #     – iskrovimo_laikas
    #     – darbo_laikas (BDL)
    #     – likes_laikas (LDL)
    # ==============================
    # Paruošiame žemėlapį: (vilkikas, data) → (ikr_laikas, bdl, ldl)
    papildomi_map = {}
    for idx, row in df_last.iterrows():
        v = row["vilkikas"]
        d = row["data"]
        rc = c.execute(
            """
            SELECT iskrovimo_laikas, darbo_laikas, likes_laikas
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ? AND data = ?
            ORDER BY id DESC LIMIT 1
            """,
            (v, d)
        ).fetchone()
        if rc:
            ikr_laikas, bdl, ldl = rc
        else:
            ikr_laikas, bdl, ldl = None, None, None

        # Pašaliname galimas NaN, None (paverčiame į tuščią eilutę)
        if ikr_laikas is None or (isinstance(ikr_laikas, float) and pd.isna(ikr_laikas)):
            ikr_laikas = ""
        if bdl is None or (isinstance(bdl, float) and pd.isna(bdl)):
            bdl = ""
        if ldl is None or (isinstance(ldl, float) and pd.isna(ldl)):
            ldl = ""

        papildomi_map[(v, d)] = {
            "ikr_laikas": str(ikr_laikas),
            "bdl": str(bdl),
            "ldl": str(ldl)
        }

    # ==============================
    # 9) Paruošiame stulpelį "cell_val": vienoje eilutėje:
    #     {vietos_kodas} {ikr_laikas} {bdl} {ldl}
    #     – jeigu kuri nors reikšmė tuščia, ją tiesiog praleidžiame
    # ==============================
    def make_cell(vilkikas, data, vieta):
        info = papildomi_map.get((vilkikas, data), {})
        parts = []
        # Pridedame vietos kodą (jeigu yra)
        if vieta:
            parts.append(vieta)
        # Pridedame iskrovimo laiką (jeigu yra)
        ikr = info.get("ikr_laikas", "")
        if ikr:
            parts.append(ikr)
        # Pridedame BDL (jeigu yra)
        bdl_val = info.get("bdl", "")
        if bdl_val:
            parts.append(bdl_val)
        # Pridedame LDL (jeigu yra)
        ldl_val = info.get("ldl", "")
        if ldl_val:
            parts.append(ldl_val)

        # Jeigu visos dalys tuščios, grąžiname tuščią
        if not parts:
            return ""
        # Sujungiame tarpu
        return " ".join(parts)

    df_last["cell_val"] = df_last.apply(
        lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]), axis=1
    )

    # ==============================
    # 10) Pivot lentelė:
    #     index = vilkikas, columns = data, values = cell_val
    # ==============================
    pivot_df = df_last.pivot(
        index="vilkikas",
        columns="data",
        values="cell_val"
    )

    # ==============================
    # 11) Užtikriname, kad stulpeliai būtų pilnai pagal datas
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 12) Filtruojame eilutes pagal grupės logiką:
    #     – Jei "Visi": rodomi visi vilkikai (tuščios eilutės tiems be įrašų)
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
    # 14) Sukuriame naują indekso stulpelį:
    #     "Vilkikas/Priekaba Vadybininkas SA"
    #     – be tarpų aplink "/", po priekabos tarpas, po vadybininko tarpas
    # ==============================
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        sa = sa_map.get(v, "")

        # Vilkikas/Priekaba
        label = v
        if priek:
            label += f"/{priek}"
        # Po priekabos – tarpas + vadybininkas
        if vad:
            label += f" {vad}"
        # Po vadybininko – tarpas + SA
        if sa:
            label += f" {sa}"

        combined_index.append(label)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas/Priekaba Vadybininkas SA"

    # ==============================
    # 15) Išvedame lentelę Streamlit'e
    # ==============================
    st.dataframe(pivot_df, use_container_width=True)
