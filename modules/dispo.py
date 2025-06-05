# modules/dispo.py

import streamlit as st
from datetime import date, timedelta

def show(conn, c):
    st.title("DISPO – Planavimo lentelė su grupėmis")

    # ==============================
    # 0) Įsitikiname, kad lentelėje "vilkiku_darbo_laikai" egzistuoja
    #    skirti stulpeliai. Jei ne – pridedame juos automatiškai.
    # ==============================
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(vilkiku_darbo_laikai)").fetchall()}
    extra_cols = [
        ("ats_ekspedicijos_vadybininkas", "TEXT"),
        ("eksp_grupe",                "TEXT")
    ]
    for col, coltype in extra_cols:
        if col not in existing_cols:
            c.execute(f"ALTER TABLE vilkiku_darbo_laikai ADD COLUMN {col} {coltype}")
    conn.commit()

    # ==============================
    # 1) Kalendoriaus intervalas: vartotojas pasirenka
    # ==============================
    lt_weekdays = {
        0: "Pirmadienis", 1: "Antradienis", 2: "Trečiadienis",
        3: "Ketvirtadienis", 4: "Penktadienis", 5: "Šeštadienis", 6: "Sekmadienis"
    }

    def col_letter(n: int) -> str:
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    def iso_monday(d: date) -> date:
        return d - timedelta(days=(d.isoweekday() - 1))

    today = date.today()
    this_monday = iso_monday(today)
    start_default = this_monday - timedelta(weeks=2)
    end_default   = this_monday + timedelta(weeks=2, days=6)

    c1, c2 = st.columns(2)
    with c1:
        start_sel = st.date_input("Pradžios data:", value=start_default)
    with c2:
        end_sel = st.date_input("Pabaigos data:", value=end_default)

    if end_sel < start_sel:
        start_date, end_date = end_sel, start_sel
    else:
        start_date, end_date = start_sel, end_sel

    num_days = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    st.write(f"Rodyti {num_days} dienų nuo {start_date} iki {end_date}.")

    # ==============================
    # 2) Antraštės: bendri laukai + dienų blokų pavadinimai
    # ==============================
    common_headers = [
        "Transporto grupė", "Ekspedicijos grupės nr.",
        "Vilkiko nr.",       "Ekspeditorius",
        "Trans. vadybininkas","Priekabos nr.",
        "Vair. sk.",         "Savaitinė atstova",
        "Pastabos"
    ]
    day_headers = [
        "B. d. laikas",   "L. d. laikas",    "Atvykimo laikas",
        "Laikas nuo",     "Laikas iki",      "Vieta",
        "Atsakingas",     "Tušti km",        "Krauti km",
        "Kelių išlaidos","Frachtas"
    ]

    # ==============================
    # 3) Pagrindinė užklausa – surenkame duomenis kiekvienam vilkikui
    # ==============================
    # Čia klaidingą e.grupe pataisome į e.eksp_grupe
    trucks_info = c.execute("""
        SELECT
            v.numeris AS vilkikas,
            v.priekaba AS priekaba,
            d.vardas || ' ' || d.pavarde AS vadybininkas,
            g.pavadinimas AS trans_grupė,
            e.ats_ekspedicijos_vadybininkas AS eksp_vad,
            eg.pavadinimas AS eksp_grupė
        FROM vilkikai v
        LEFT JOIN darbuotojai d
            ON v.vadybininkas = d.vardas
        LEFT JOIN grupes g
            ON d.grupe = g.pavadinimas
        LEFT JOIN (
            SELECT vilkiko_numeris,
                   ats_ekspedicijos_vadybininkas,
                   eksp_grupe
            FROM vilkiku_darbo_laikai
            ORDER BY id DESC
            LIMIT 1
        ) e
            ON v.numeris = e.vilkiko_numeris
        LEFT JOIN grupes eg
            ON e.eksp_grupe = eg.pavadinimas
    """).fetchall()

    # ==============================
    # 4) Jeigu nėra duomenų, pranešame
    # ==============================
    if not trucks_info:
        st.info("Šiuo laikotarpiu nėra duomenų susijusių su vilkikais.")
        return

    # ==============================
    # 5) Atvaizduojame lentelę vartotojui (pavyzdžiui, paprasta st.write())
    #    Čia galite patys suformatuoti pagal poreikį (DataFrame, HTML ir pan.)
    # ==============================
    import pandas as pd

    df = pd.DataFrame(trucks_info, columns=[
        "Vilkikas", "Priekaba", "Vadybininkas", "Transporto grupė",
        "Eksp. vadovas", "Eksp. grupė"
    ])

    st.dataframe(df, use_container_width=True)
