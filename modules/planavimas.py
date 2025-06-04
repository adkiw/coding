# modules/planavimas.py

import streamlit as st
import pandas as pd
import datetime

def show(conn, c):
    st.title("DISPO – Planavimas")

    # ==============================
    # 1) Suskaičiuojame norimą datų intervalą:
    #    nuo vakar (today - 1) iki savaitės į priekį (today + 7)
    # ==============================
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=7)

    # Generuojame sąrašą visų datų šiame intervale
    # Pvz. [2025-06-04, 2025-06-05, ..., 2025-06-12]
    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    # Pavertžiame datas į eilutes "YYYY-MM-DD" formatu, kad vėliau galėtume
    # jas naudoti kaip stulpelių pavadinimus
    date_strs = [d.isoformat() for d in date_list]

    # ==============================
    # 2) Ištraukiame visus vilkikų numerius,
    #    kad turėtume visų galimų vilkikų aibę (net jei tam tikromis dienomis
    #    planavimo lentelėje jiems nėra nei vieno įrašo)
    # ==============================
    c.execute("SELECT numeris FROM vilkikai ORDER BY numeris")
    vilkikai_all = [row[0] for row in c.fetchall()]

    # ==============================
    # 3) Iš lentelės "kroviniai" surenkame įrašus tarp start_date ir end_date
    #    (kur yra laukeliai iskrovimo_data, iskrovimo_regionas ir vilkikas)
    # ==============================
    # Pastaba: jeigu iskrovimo_data lauke saugomi ir laiko fragmentai,
    # verta palikti palyginimą tik pagal datą. Bet jeigu tai grynai 'YYYY-MM-DD'
    # formos tekstas, pakanka taip palyginti.
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    query = f"""
        SELECT
            vilkikas AS vilkikas,
            iskrovimo_regionas AS regionas,
            iskrovimo_data AS data
        FROM kroviniai
        WHERE iskrovimo_data BETWEEN '{start_str}' AND '{end_str}'
          AND iskrovimo_data IS NOT NULL
        ORDER BY vilkikas, iskrovimo_data
    """
    df = pd.read_sql_query(query, conn)

    # ==============================
    # 4) Jeigu lentelė tuščia (nėra jokių planuotų iškrovimų šiame intervale),
    #    rodome info pranešimą ir nutraukiame.
    # ==============================
    if df.empty:
        st.info("Šiame laikotarpyje nėra planuojamų iškrovimų.")
        return

    # ==============================
    # 5) Paruošiame DataFrame 'pivot' tipo:
    #    - eilutės: vilkikai
    #    - stulpeliai: kiekviena data intervale
    #    - reikšmės: paskirtas iškrovimo regionas tos dienos vilkikui
    # ==============================
    # Konvertuojame stulpelį "data" į datetime.date tipą, tada į tekstą YYYY-MM-DD
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)

    # Pivot lentelės kūrimas: index=vilkikas, columns=data, values=regionas
    pivot_df = df.pivot(
        index="vilkikas",
        columns="data",
        values="regionas"
    )

    # ==============================
    # 6) Užpildome tuščias vietas (jei tam tikra diena vilkikui neturima įrašo)
    #    paliekame tuščią string'ą
    # ==============================
    # Uždėkime pilną intervalą kaip stulpelius, net jei juose (kol kas) nėra duomenų
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")

    # ==============================
    # 7) Užtikriname, kad visų vilkikų numeriai būtų tarp eilučių (net jei kai kurie
    #    neturėjo nė vieno įrašo šiame intervale)
    # ==============================
    pivot_df = pivot_df.reindex(index=vilkikai_all, fill_value="")

    # ==============================
    # 8) Pervadiname indekso pavadinimą į "Vilkiko numeris"
    # ==============================
    pivot_df.index.name = "Vilkiko numeris"

    # ==============================
    # 9) Išvedame rezultatus Streamlit lange
    # ==============================
    st.dataframe(pivot_df, use_container_width=True)
