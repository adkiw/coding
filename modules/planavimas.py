# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")
    
    # ==============================
    # 0) CSS klasė “tiny” norint mažesniu šriftu parašyti “nėra”
    # ==============================
    st.markdown("""
    <style>
    .tiny { font-size:10px; color:#888; }
    </style>
    """, unsafe_allow_html=True)

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

    # Sukuriame stulpelį "vietos_kodas" = "šalis"+"regionas", pvz. "IT10"
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"] + df["regionas"]

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
            # Gauname regionų kodus, pvz. ["FR10", "IT20", ...]
            c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id,)
            )
            regionai = [row[0] for row in c.fetchall()]

            # Filtruojame df: paliekame tik tuos, kurių "vietos_kodas" prasideda bent vienu iš regionai
            mask = df["vietos_kodas"].apply(
                lambda x: any(x.startswith(r) for r in regionai)
            )
            df = df[mask]

    # Jei po grupės filtravimo nebeliko įrašų, rodome info ir išeiname
    if df.empty:
        st.info("Pasirinktoje ekspedicijos grupėje nėra planuojamų iškrovimų per šį laikotarpį.")
        return

    # ==============================
    # 7) Pasirenkame kiekvienam vilkikui tik paskutinį (didžiausią) įvykį šiame intervale
    # ==============================
    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()

    # ==============================
    # 8) Imame papildomus duomenis iš vilkiku_darbo_laikai:
    #    – Iškr. laikas (kolonoje iskrovimo_laikas)
    #    – BDL (darbo_laikas)
    #    – LDL (likes_laikas)
    # ==============================
    # Paruošiame žemėlapį: (vilkikas, data) → (ikr_laikas, bdl, ldl)
    šalia_map = {}
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
        šalia_map[(v, d)] = {
            "ikr_laikas": ikr_laikas if ikr_laikas not in [None, ""] else "",
            "bdl": bdl if bdl not in [None, ""] else "",
            "ldl": ldl if ldl not in [None, ""] else ""
        }

    # ==============================
    # 9) Paruošiame naują stulpelį "cell_val", kombinaciją regiono + Iškr. laikas + BDL + LDL.
    #    – Kiekvieną informaciją žymime atskirom eilute
    #    – Jeigu laikas/BDL/LDL neturi reikšmės, parašome “<span class='tiny'>nėra</span>”
    # ==============================
    def make_cell(vilkikas, data, vieta):
        info = šalia_map.get((vilkikas, data), {})
        # Regiono kodas
        regiono_kodas = vieta or ""
        # Iškr. laikas
        ikr = info.get("ikr_laikas", "")
        ikr_str = ikr if ikr else "<span class='tiny'>nėra</span>"
        # BDL
        bdl_val = info.get("bdl", "")
        bdl_str = str(bdl_val) if bdl_val != "" else "<span class='tiny'>nėra</span>"
        # LDL
        ldl_val = info.get("ldl", "")
        ldl_str = str(ldl_val) if ldl_val != "" else "<span class='tiny'>nėra</span>"

        # Kiekvieną dalį atskiriame <br> (HTML newline)
        # Kadangi st.markdown gali atvaizduoti HTML, vėliau naudosime st.markdown
        # vietoje st.dataframe.  
        return (
            f"{regiono_kodas}<br>"
            f"Iškr. laikas: {ikr_str}<br>"
            f"BDL: {bdl_str}  LDL: {ldl_str}"
        )

    # Įtraukiame “cell_val” į df_last
    df_last["cell_val"] = df_last.apply(
        lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]), axis=1
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
    # 11) Užtikriname, kad pivot lentelė turi VISAS datas kaip stulpelius
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 12) Filtruojame eilutes pagal tai, ar vilkikas egzistuoja df_last:
    #     – Jei grupė "Visi" – rodomi visi vilkikai (tuščiomis eilutėmis tiems be įrašų)
    #     – Jei kita grupė – rodomi tik vilkikai, kurių df_last yra bent vienas įrašas
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
        sa_map[v] = row[0] if row and row[0] else ""

    # ==============================
    # 14) Sukuriame naują indekso stulpelį:
    #     "Vilkikas/Priekaba Vadybininkas SA"
    #     – Tarp vilkiko ir priekabos nėra tarpų aplink "/"
    #     – Po priekabos seka tarpas, tada vadybininkas, tada tarpas ir SA
    # ==============================
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        sa = sa_map.get(v, "")

        # Sudarome dalį "Vilkikas/Priekaba" (be tarpų aplink "/")
        vp_part = v
        if priek:
            vp_part += f"/{priek}"

        # Pridedame vadybininką (jei yra), atskirtą tarpu
        if vad:
            vp_part += f" {vad}"

        # Pridedame SA (jei yra), taip pat tarpu atskirtą
        if sa:
            vp_part += f" {sa}"

        combined_index.append(vp_part)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas/Priekaba Vadybininkas SA"

    # ==============================
    # 15) Išvedame HTML lentelę per st.markdown, nes norime atvaizduoti <br> ir <span>
    # ==============================
    # Surenkame visas stulpelių pavadinimų ir indekso vertes
    html = "<table style='border-collapse: collapse; width: 100%;'>\n"
    # Header row
    html += "  <thead>\n    <tr>\n"
    html += "      <th style='border:1px solid #ddd; padding:4px; text-align:center;'>Vilkikas/Priekaba Vadybininkas SA</th>\n"
    for d in date_strs:
        html += f"      <th style='border:1px solid #ddd; padding:4px; text-align:center;'>{d}</th>\n"
    html += "    </tr>\n  </thead>\n"
    # Body rows
    html += "  <tbody>\n"
    for idx in pivot_df.index:
        html += "    <tr>\n"
        # Eilutės pavadinimas
        html += f"      <td style='border:1px solid #ddd; padding:4px;'>{idx}</td>\n"
        # Kiekvienos datos langelis
        for d in date_strs:
            val = pivot_df.at[idx, d]
            # Jeigu tuščias, paliekame tarpelį
            if not val:
                cell_html = ""
            else:
                cell_html = val
            html += f"      <td style='border:1px solid #ddd; padding:4px; vertical-align: top; text-align:center;'>{cell_html}</td>\n"
        html += "    </tr>\n"
    html += "  </tbody>\n</table>"

    st.markdown(html, unsafe_allow_html=True)
