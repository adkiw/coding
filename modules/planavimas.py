# modules/planavimas.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("DISPO – Planavimas")

    # 1. Pasirinkti ekspedicinę grupę
    grupes = c.execute("SELECT pavadinimas FROM grupes").fetchall()
    grupiu_sarasas = ["Visos"] + [g[0] for g in grupes]
    pasirinkta_grupe = st.selectbox("Pasirink ekspedicinę grupę", grupiu_sarasas)

    # 2. Jei pasirinkta konkreti grupė, paimti jos regionų kodus
    regionu_filtras = []
    if pasirinkta_grupe != "Visos":
        grupe_id = c.execute(
            "SELECT id FROM grupes WHERE pavadinimas = ?",
            (pasirinkta_grupe,)
        ).fetchone()
        if grupe_id:
            regionai = c.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ?",
                (grupe_id[0],)
            ).fetchall()
            regionu_filtras = [r[0] for r in regionai]

    # 3. Paimti visų vilkikų numerius
    vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]

    rezultatai = []
    for v in vilkikai:
        # 3.1. Paimti visus krovinio įrašus tam vilkikui
        kroviniai = c.execute("""
            SELECT pakrovimo_data,
                   iskrovimo_salis,
                   iskrovimo_regionas,
                   iskrovimo_data,
                   iskrovimo_laikas_nuo
            FROM kroviniai
            WHERE vilkikas = ?
        """, (v,)).fetchall()

        paskutinis = None
        for kro in kroviniai:
            pak_data, orig_salis, orig_region, orig_data, orig_laikas = kro

            # 3.2. Patikrinti, ar yra atnaujinta informacija iš vilkiku_darbo_laikai
            atn = c.execute("""
                SELECT iskrovimo_statusas,
                       iskrovimo_data,
                       iskrovimo_laikas,
                       sa
                FROM vilkiku_darbo_laikai
                WHERE vilkiko_numeris = ? AND data = ?
                ORDER BY id DESC
                LIMIT 1
            """, (v, pak_data)).fetchone()

            if atn and atn[1]:
                eff_data = atn[1]
                eff_laikas = atn[2] or ""
                eff_statusas = atn[0] or ""
                eff_sa = atn[3] or ""
            else:
                eff_data = orig_data or ""
                eff_laikas = orig_laikas or ""
                eff_statusas = ""
                eff_sa = ""

            if not eff_data:
                continue

            # 3.3. Išsaugoti, jei tai paskutinė data
            kandidatas = (eff_data, orig_salis or "", orig_region or "", eff_laikas, eff_statusas, eff_sa)
            if not paskutinis or kandidatas[0] > paskutinis[0]:
                paskutinis = kandidatas

        if paskutinis:
            rezultatai.append({
                "Vilkikas": v,
                "Iškrovimo vieta": f"{paskutinis[1]}{paskutinis[2]}",
                "Iškrovimo data": paskutinis[0],
                "Iškrovimo laikas": paskutinis[3],
                "Iškrovimo statusas": paskutinis[4],
                "SA": paskutinis[5],
                "Regionas": paskutinis[2]
            })
        else:
            rezultatai.append({
                "Vilkikas": v,
                "Iškrovimo vieta": "",
                "Iškrovimo data": "",
                "Iškrovimo laikas": "",
                "Iškrovimo statusas": "",
                "SA": "",
                "Regionas": ""
            })

    df = pd.DataFrame(rezultatai)

    # 4. Filtruoti pagal regionus, jei pasirinkta ekspedicinė grupė
    if pasirinkta_grupe != "Visos" and regionu_filtras:
        df = df[df["Regionas"].isin(regionu_filtras)].reset_index(drop=True)

    # 5. Rodyti lentelę be kolonos "Regionas"
    if not df.empty:
        df = df.drop(columns=["Regionas"])
    st.dataframe(df)
