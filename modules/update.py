import streamlit as st
import pandas as pd
from datetime import datetime, date

# CSS iškart po set_page_config (nepamiršk, main.py pradžioje PRIVALO būti st.set_page_config)
st.markdown("""
    <style>
    th, td {font-size: 12px !important;}
    .tiny {font-size:10px;color:#888;}
    .stTextInput>div>div>input {font-size:12px !important; min-height:2em;}
    .block-container { padding-top: 0.5rem !important;}
    .streamlit-expanderHeader { overflow-x: auto; }
    .stDataFrame div[role="columnheader"] { white-space: nowrap; }
    div[role="option"] svg, div[role="combobox"] svg, span[data-baseweb="select"] svg { display: none !important; }
    </style>
""", unsafe_allow_html=True)

def format_time_str(input_str):
    digits = "".join(filter(str.isdigit, str(input_str)))
    if not digits:
        return ""
    if len(digits) == 1:
        h = digits
        return f"0{h}:00"
    if len(digits) == 2:
        h = digits
        return f"{int(h):02d}:00"
    if len(digits) == 3:
        h = digits[:-2]
        m = digits[-2:]
        return f"0{int(h)}:{int(m):02d}"
    if len(digits) == 4:
        h = digits[:-2]
        m = digits[-2:]
        return f"{int(h):02d}:{int(m):02d}"
    return input_str

def show(conn, c):
    st.title("DISPO – Vilkikų ir krovinių atnaujinimas (Update)")

    # Papildome DB laukus, jei trūksta
    existing = [r[1] for r in c.execute("PRAGMA table_info(vilkiku_darbo_laikai)").fetchall()]
    extra_cols = [
        ("pakrovimo_statusas", "TEXT"),
        ("pakrovimo_laikas", "TEXT"),
        ("pakrovimo_data", "TEXT"),
        ("iskrovimo_statusas", "TEXT"),
        ("iskrovimo_laikas", "TEXT"),
        ("iskrovimo_data", "TEXT"),
        ("komentaras", "TEXT"),
        ("sa", "TEXT"),
        ("created_at", "TEXT"),
        ("ats_transporto_vadybininkas", "TEXT"),
        ("ats_ekspedicijos_vadybininkas", "TEXT"),
        ("trans_grupe", "TEXT"),
        ("eksp_grupe", "TEXT"),
    ]
    for col, coltype in extra_cols:
        if col not in existing:
            c.execute(f"ALTER TABLE vilkiku_darbo_laikai ADD COLUMN {col} {coltype}")
    conn.commit()

    # 1. Filtrai
    vadybininkai = [r[0] for r in c.execute(
        "SELECT DISTINCT vadybininkas FROM vilkikai WHERE vadybininkas IS NOT NULL AND vadybininkas != ''"
    ).fetchall()]
    grupe_list = [r[0] for r in c.execute("SELECT pavadinimas FROM grupes").fetchall()]
    vadyb = st.selectbox("Pasirink transporto vadybininką", [""] + vadybininkai, index=0)
    grupe_filtras = st.selectbox("Filtruok pagal transporto grupę", [""] + grupe_list, index=0)

    # 2. Vilkikai pagal pasirinktus filtrus
    vilkikai_info = c.execute("""
        SELECT v.numeris, g.pavadinimas
        FROM vilkikai v
        LEFT JOIN darbuotojai d ON v.vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall()
    # Filtruojam pagal vadybininką ir grupę
    vilkikai = []
    for v, g in vilkikai_info:
        if vadyb and c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (v,)).fetchone()[0] != vadyb:
            continue
        if grupe_filtras and (g or "") != grupe_filtras:
            continue
        vilkikai.append(v)

    if not vilkikai:
        st.info("Nėra vilkikų pagal pasirinktus filtrus.")
        return

    # 3. Paimam kroviniai, sortinam pagal vilkiko numerį ir datą
    today = date.today()
    placeholders = ", ".join("?" for _ in vilkikai)
    query = f"""
        SELECT id, klientas, uzsakymo_numeris, pakrovimo_data, iskrovimo_data, 
               vilkikas, priekaba, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
               iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
               pakrovimo_salis, pakrovimo_regionas,
               iskrovimo_salis, iskrovimo_regionas, kilometrai,
               ekspedicijos_vadybininkas
        FROM kroviniai
        WHERE vilkikas IN ({placeholders}) AND pakrovimo_data >= ?
        ORDER BY vilkikas ASC, pakrovimo_data ASC
    """
    params = list(vilkikai) + [str(today)]
    kroviniai = c.execute(query, params).fetchall()

    # 4. Transporto ir ekspedicinė grupė paėmimas
    vilk_grupes = dict(c.execute("""
        SELECT v.numeris, g.pavadinimas FROM vilkikai v
        LEFT JOIN darbuotojai d ON v.vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall())
    eksp_grupes = dict(c.execute("""
        SELECT k.id, g.pavadinimas FROM kroviniai k
        LEFT JOIN darbuotojai d ON k.ekspedicijos_vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall())

    # 5. Stulpeliai
    col_widths = [
        0.5,  # Save
        0.85,  # Atnaujinta:
        0.4,  # Vilkikas
        0.4,  # Priekaba
        0.7,  # Pakr. data (originali)
        0.7,  # Pakr. laikas (originalus)
        1.0,  # Pakrovimo vieta
        0.7,  # Iškr. data (originali)
        0.7,  # Iškr. laikas (originalus)
        1.0,  # Iškr. vieta
        0.6,  # Km
        0.45, # Transporto grupė (nauja)
        0.8,  # Transporto vadybininkas
        0.45, # Ekspedicinė grupė (nauja)
        0.8,  # Ekspedicijos vadybininkas
        0.45, # SA
        0.45, # BDL
        0.45, # LDL
        0.8,  # Pakr. data (edit)
        0.5,  # Pakr. laikas (edit)
        0.75, # Pakr. statusas
        0.8,  # Iškr. data (edit)
        0.5,  # Iškr. laikas (edit)
        0.75, # Iškr. statusas
        1.0,  # Komentaras
    ]
    headers = [
        "Save", "Atnaujinta:", "Vilkikas", "Priekaba", "Pakr. data", "Pakr. laikas", "Pakrovimo vieta",
        "Iškr. data", "Iškr. laikas", "Iškr. vieta", "Km",
        "Transporto grupė", "Transporto vadybininkas",
        "Ekspedicinė grupė", "Ekspedicijos vadybininkas",
        "SA", "BDL", "LDL",
        "Pakr. data (edit)", "Pakr. laikas (edit)", "Pakr. statusas",
        "Iškr. data (edit)", "Iškr. laikas (edit)", "Iškr. statusas",
        "Komentaras"
    ]
    cols = st.columns(col_widths)
    for i, label in enumerate(headers):
        cols[i].markdown(f"<b>{label}</b>", unsafe_allow_html=True)

    # 6. Pagrindinė lentelė
    for k in kroviniai:
        # Patikrinam, ar kroviniui reikia išnykti (Iškrauta + iskrovimo_data < šiandien)
        darbo = c.execute("""
            SELECT sa, darbo_laikas, likes_laikas, created_at,
                   pakrovimo_statusas, pakrovimo_laikas, pakrovimo_data,
                   iskrovimo_statusas, iskrovimo_laikas, iskrovimo_data,
                   komentaras, ats_transporto_vadybininkas, ats_ekspedicijos_vadybininkas,
                   trans_grupe, eksp_grupe
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris = ? AND data = ?
            ORDER BY id DESC LIMIT 1
        """, (k[5], k[3])).fetchone()
        iskrovimo_statusas = darbo[7] if darbo and darbo[7] else ""
        iskrovimo_data = darbo[9] if darbo and darbo[9] else str(k[4])
        if (
            iskrovimo_statusas == "Iškrauta" and
            pd.to_datetime(iskrovimo_data).date() < today
        ):
            continue  # NErodom šio krovinio

        sa = darbo[0] if darbo and darbo[0] else ""
        bdl = darbo[1] if darbo and darbo[1] not in [None, ""] else ""
        ldl = darbo[2] if darbo and darbo[2] not in [None, ""] else ""
        created = darbo[3] if darbo and darbo[3] else None
        pk_status = darbo[4] if darbo and darbo[4] else ""
        pk_laikas = darbo[5] if darbo and darbo[5] else (str(k[7])[:5] if k[7] else "")
        pk_data = darbo[6] if darbo and darbo[6] else str(k[3])
        komentaras = darbo[10] if darbo and darbo[10] else ""
        trans_gr = darbo[12] if darbo and darbo[12] else vilk_grupes.get(k[5], "")
        eksp_gr = darbo[13] if darbo and darbo[13] else eksp_grupes.get(k[0], "")

        row_cols = st.columns(col_widths)

        # 0) Save mygtukas
        save = row_cols[0].button("💾", key=f"save_{k[0]}")

        # 1) Atnaujinta data
        if created:
            laikas = pd.to_datetime(created)
            row_cols[1].markdown(
                f"<div style='padding:2px 6px;'>{laikas.strftime('%Y-%m-%d %H:%M')}</div>",
                unsafe_allow_html=True
            )
        else:
            row_cols[1].markdown("<div style='padding:2px 6px;'>&nbsp;</div>", unsafe_allow_html=True)

        # 2) Vilkikas
        row_cols[2].write(str(k[5])[:7])
        # 3) Priekaba
        row_cols[3].write(str(k[6])[:7])
        # 4) Pakrovimo data
        row_cols[4].write(str(k[3]))
        # 5) Pakrovimo laikas
        row_cols[5].write(str(k[7])[:5] + (f" - {str(k[8])[:5]}" if k[8] else ""))
        # 6) Pakrovimo vieta
        vieta_pk = f"{k[11] or ''}{k[12] or ''}"
        row_cols[6].write(vieta_pk[:18])
        # 7) Iškr. data
        row_cols[7].write(str(k[4]))
        # 8) Iškr. laikas
        row_cols[8].write(str(k[9])[:5] + (f" - {str(k[10])[:5]}" if k[10] else ""))
        # 9) Iškr. vieta
        vieta_is = f"{k[13] or ''}{k[14] or ''}"
        row_cols[9].write(vieta_is[:18])
        # 10) Km
        row_cols[10].write(str(k[15]))
        # 11) Transporto grupė
        row_cols[11].write(trans_gr or "")
        # 12) Transporto vadybininkas
        row_cols[12].write(c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()[0])
        # 13) Ekspedicinė grupė
        row_cols[13].write(eksp_gr or "")
        # 14) Ekspedicijos vadybininkas
        row_cols[14].write(k[16] if len(k) > 16 else "")

        # 15-17) SA, BDL, LDL – input
        sa_in = row_cols[15].text_input("", value=str(sa), key=f"sa_{k[0]}", label_visibility="collapsed")
        bdl_in = row_cols[16].text_input("", value=str(bdl), key=f"bdl_{k[0]}", label_visibility="collapsed")
        ldl_in = row_cols[17].text_input("", value=str(ldl), key=f"ldl_{k[0]}", label_visibility="collapsed")

        # 18) Pakrovimo data (edit)
        try:
            default_pk_date = datetime.fromisoformat(pk_data).date()
        except:
            default_pk_date = datetime.now().date()
        pk_data_key = f"pk_date_{k[0]}"
        pk_data_in = row_cols[18].date_input("", value=default_pk_date, key=pk_data_key, label_visibility="collapsed")

        # 19) Pakrovimo laikas (edit)
        pk_time_key = f"pk_time_{k[0]}"
        formatted_pk = format_time_str(pk_laikas) if pk_laikas else ""
        pk_laikas_in = row_cols[19].text_input("", value=formatted_pk, key=pk_time_key, label_visibility="collapsed", placeholder="HHMM")
        # Automatinis formatavimas (nebūtina, bet jei nori - gali naudot input_on_change)

        # 20) Pakrovimo statusas
        pk_status_options = [""] + ["Atvyko", "Pakrauta", "Kita"]
        default_pk_status_idx = pk_status_options.index(pk_status) if pk_status in pk_status_options else 0
        pk_status_in = row_cols[20].selectbox("", options=pk_status_options, index=default_pk_status_idx, key=f"pk_status_{k[0]}", label_visibility="collapsed")

        # 21) Iškr. data (edit)
        ikr_data = darbo[9] if darbo and darbo[9] else str(k[4])
        try:
            default_ikr_date = datetime.fromisoformat(ikr_data).date()
        except:
            default_ikr_date = datetime.now().date()
        ikr_data_key = f"ikr_date_{k[0]}"
        ikr_data_in = row_cols[21].date_input("", value=default_ikr_date, key=ikr_data_key, label_visibility="collapsed")

        # 22) Iškr. laikas (edit)
        ikr_laikas = darbo[8] if darbo and darbo[8] else (str(k[9])[:5] if k[9] else "")
        ikr_time_key = f"ikr_time_{k[0]}"
        formatted_ikr = format_time_str(ikr_laikas) if ikr_laikas else ""
        ikr_laikas_in = row_cols[22].text_input("", value=formatted_ikr, key=ikr_time_key, label_visibility="collapsed", placeholder="HHMM")

        # 23) Iškr. statusas
        ikr_status = darbo[7] if darbo and darbo[7] else ""
        ikr_status_options = [""] + ["Atvyko", "Iškrauta", "Kita"]
        default_ikr_status_idx = ikr_status_options.index(ikr_status) if ikr_status in ikr_status_options else 0
        ikr_status_in = row_cols[23].selectbox("", options=ikr_status_options, index=default_ikr_status_idx, key=f"ikr_status_{k[0]}", label_visibility="collapsed")

        # 24) Komentaras
        komentaras_in = row_cols[24].text_input("", value=komentaras, key=f"komentaras_{k[0]}", label_visibility="collapsed")

        # Išsaugojimo logika
        if save:
            jau_irasas = c.execute("""
                SELECT id FROM vilkiku_darbo_laikai WHERE vilkiko_numeris = ? AND data = ?
            """, (k[5], k[3])).fetchone()
            now_str = datetime.now().isoformat()
            formatted_pk_date = pk_data_in.isoformat()
            formatted_ikr_date = ikr_data_in.isoformat()
            if jau_irasas:
                c.execute("""
                    UPDATE vilkiku_darbo_laikai
                    SET sa=?, darbo_laikas=?, likes_laikas=?, created_at=?,
                        pakrovimo_statusas=?, pakrovimo_laikas=?, pakrovimo_data=?,
                        iskrovimo_statusas=?, iskrovimo_laikas=?, iskrovimo_data=?,
                        komentaras=?, ats_transporto_vadybininkas=?, ats_ekspedicijos_vadybininkas=?,
                        trans_grupe=?, eksp_grupe=?
                    WHERE id=?
                """, (
                    sa_in, bdl_in, ldl_in, now_str,
                    pk_status_in, pk_laikas_in, formatted_pk_date,
                    ikr_status_in, ikr_laikas_in, formatted_ikr_date,
                    komentaras_in,
                    c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()[0],
                    k[16] if len(k)>16 else "",
                    trans_gr, eksp_gr, jau_irasas[0]
                ))
            else:
                c.execute("""
                    INSERT INTO vilkiku_darbo_laikai
                    (vilkiko_numeris, data, sa, darbo_laikas, likes_laikas, created_at,
                     pakrovimo_statusas, pakrovimo_laikas, pakrovimo_data,
                     iskrovimo_statusas, iskrovimo_laikas, iskrovimo_data, komentaras,
                     ats_transporto_vadybininkas, ats_ekspedicijos_vadybininkas,
                     trans_grupe, eksp_grupe)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    k[5], k[3], sa_in, bdl_in, ldl_in, now_str,
                    pk_status_in, pk_laikas_in, formatted_pk_date,
                    ikr_status_in, ikr_laikas_in, formatted_ikr_date,
                    komentaras_in,
                    c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()[0],
                    k[16] if len(k)>16 else "",
                    trans_gr, eksp_gr
                ))
            conn.commit()
            st.success("✅ Išsaugota!")
