# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 1) Apskaičiuojame datų intervalą:
    #    nuo vakar (today - 1) iki savaitės į priekį (today + 7)
    # ==============================
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=7)

    # Generuojame kiekvieną dieną šiame intervale ir paverčiame į 'YYYY-MM-DD'
    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    date_strs = [d.isoformat() for d in date_list]

    # ==============================
    # 2) Paimame visų vilkikų numerius, kad turėtume pilną eilučių sąrašą
    # ==============================
    c.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai ORDER BY numeris")
    vilkikai_rows = c.fetchall()  # kiekvienas: (numeris, priekaba, vadybininkas)
    vilkikai_all = [row[0] for row in vilkikai_rows]

    # Sukuriame žemėlapį: vilkikas → (priekaba, vadybininkas)
    priekaba_map = {row[0]: row[1] or "" for row in vilkikai_rows}
    vadybininkas_map = {row[0]: row[2] or "" for row in vilkikai_rows}

    # ==============================
    # 3) Ištraukiame iš kroviniai lentelės visus įrašus su iškrovimo data šiame intervale
    #    bei judame regiono ir šalies kodus:
    #
    #    - iskrovimo_salis: saugo šalies prefiksą (pvz., "IT", "FR") :contentReference[oaicite:0]{index=0}
    #    - iskrovimo_regionas: saugo regiono skaičių ar kodą (pvz., "10", "05") :contentReference[oaicite:1]{index=1}
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

    # ==============================
    # 4) Jei nėra jokių įrašų šiame intervale, rodome pranešimą ir išeiname
    # ==============================
    if df.empty:
        st.info("Šiame laikotarpyje nėra planuojamų iškrovimų.")
        return

    # ==============================
    # 5) Paruošiame stulpelį, kuriame sujungiame šalies kodą + regioną:
    #    pvz. salis="IT", regionas="10" → "IT10"
    # ==============================
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"].fillna("") + df["regionas"].fillna("")

    # ==============================
    # 6) Pivot lentelė:
    #    - eilutės: vilkikas
    #    - stulpeliai: data (YYYY-MM-DD)
    #    - reikšmės: vietos_kodas (pvz., "IT10" arba tuščias, jei įrašo nėra)
    # ==============================
    pivot_df = df.pivot(
        index="vilkikas",
        columns="data",
        values="vietos_kodas"
    )

    # ==============================
    # 7) Užtikriname, kad stulpeliai atitiktų visas datas intervale,
    #    net jei tam tikrai datai įrašų nėra
    # ==============================
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 8) Užtikriname, kad visų vilkikų numeriai būtų tarp eilučių:
    #    pivot_df index pildome pagal pilną vilkikai_all sąrašą
    # ==============================
    pivot_df = pivot_df.reindex(index=vilkikai_all, fill_value="")

    # ==============================
    # 9) Sukuriame naują indekso stulpelį, derindami:
    #    Vilkiko numerį, Priekabos numerį ir Vadybininko vardą
    #    Formatą: "Vilkikas / Priekaba / Vadybininkas"
    # ==============================
    # Pirmiausia paimame dabartinį indekso sąrašą (vilkikai_all)
    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        combined_label = f"{v}"
        if priek:
            combined_label += f" / {priek}"
        if vad:
            combined_label += f" / {vad}"
        combined_index.append(combined_label)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas / Priekaba / Vadybininkas"

    # ==============================
    # 10) Išvedame galutinę lentelę Streamlit'e
    # ==============================
    st.dataframe(pivot_df, use_container_width=True)
