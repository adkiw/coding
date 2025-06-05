# modules/update.py

import streamlit as st
import pandas as pd
from datetime import datetime, date

# ==============================
# 0) CSS tam, kad visi headeriai ir reikšmės nebūtų lūžinami,
#    o visa eilutė būtų viena horizontali linija su skrolu
# ==============================
st.markdown("""
    <style>
      /* Apgaubti visą atvaizduojamą turinį scroll-container div'u,
         kurio viduje galima slinkti horizontaliai */
      .scroll-container {
        overflow-x: auto;
      }
      /* Pritaikyti visiems vidiniams elementams, kad tekstas nekeltų jokių lūžių */
      .scroll-container * {
        white-space: nowrap !important;
      }
      /* Sutrumpinamas fontas, kad tilptų daugiau informacijos vienoje eilutėje */
      th, td, .stTextInput>div>div>input, .stDateInput>div>div>input {
        font-size: 12px !important;
      }
      .tiny {
        font-size: 10px;
        color: #888;
      }
      .block-container {
        padding-top: 0.5rem !important;
      }
      /* Paslėpti selectbox rodykles */
      div[role="option"] svg,
      div[role="combobox"] svg,
      span[data-baseweb="select"] svg {
        display: none !important;
      }
      /* Praplečiame vilkiko numerio langelį ir paryškiname */
      .vilk-cell {
        background-color: #f0f8ff;
        font-weight: bold;
      }
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

def relative_time(created_str):
    try:
        created = pd.to_datetime(created_str)
    except:
        return ""
    now = pd.Timestamp.now()
    delta = now - created
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def show(conn, c):
    st.title("Padėties atnaujinimai")

    # ==============================
    # 1) Užtikriname, kad lentelėje "vilkiku_darbo_laikai" būtų visi stulpeliai
    # ==============================
    existing = [r[1] for r in c.execute("PRAGMA table_info(vilkiku_darbo_laikai)").fetchall()]
    extra_cols = [
        ("pakrovimo_statusas", "TEXT"),
        ("pakrovimo_laikas",       "TEXT"),
        ("pakrovimo_data",         "TEXT"),
        ("iskrovimo_statusas",     "TEXT"),
        ("iskrovimo_laikas",       "TEXT"),
        ("iskrovimo_data",         "TEXT"),
        ("komentaras",             "TEXT"),
        ("sa",                     "TEXT"),
        ("created_at",             "TEXT"),
        ("ats_transporto_vadybininkas", "TEXT"),
        ("ats_ekspedicijos_vadybininkas","TEXT"),
        ("trans_grupe",            "TEXT"),
        ("eksp_grupe",             "TEXT"),
    ]
    for col, coltype in extra_cols:
        if col not in existing:
            c.execute(f"ALTER TABLE vilkiku_darbo_laikai ADD COLUMN {col} {coltype}")
    conn.commit()

    # ==============================
    # 2) Filtrai: Transporto vadybininkas ir Transporto grup4 (vienoje eilutėje)
    # ==============================
    vadybininkai = [
        r[0] for r in c.execute(
            "SELECT DISTINCT vadybininkas FROM vilkikai WHERE vadybininkas IS NOT NULL AND vadybininkas != ''"
        ).fetchall()
    ]
    grupe_list = [r[0] for r in c.execute("SELECT pavadinimas FROM grupes").fetchall()]

    col1, col2 = st.columns(2)
    vadyb         = col1.selectbox("Transporto vadybininkas", [""] + vadybininkai, index=0)
    grupe_filtras = col2.selectbox("Transporto grup4", [""] + grupe_list, index=0)

    # ==============================
    # 3) Pasirenkame vilkikus pagal filtrus
    # ==============================
    vilkikai_info = c.execute("""
        SELECT v.numeris, g.pavadinimas
        FROM vilkikai v
        LEFT JOIN darbuotojai d ON v.vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall()

    vilkikai = []
    for v, g in vilkikai_info:
        if vadyb and c.execute(
            "SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (v,)
        ).fetchone()[0] != vadyb:
            continue
        if grupe_filtras and (g or "") != grupe_filtras:
            continue
        vilkikai.append(v)

    if not vilkikai:
        st.info("Nėra vilkikų pagal pasirinktus filtrus.")
        return

    # ==============================
    # 4) Paimame kroviniai iš lentelės "kroviniai"
    # ==============================
    today = date.today()
    placeholders = ", ".join("?" for _ in vilkikai)
    query = f"""
        SELECT
            id, klientas, uzsakymo_numeris,
            pakrovimo_data, iskrovimo_data,
            vilkikas, priekaba,
            pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
            iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
            pakrovimo_salis, pakrovimo_regionas,
            iskrovimo_salis, iskrovimo_regionas,
            kilometrai, ekspedicijos_vadybininkas
        FROM kroviniai
        WHERE vilkikas IN ({placeholders}) AND pakrovimo_data >= ?
        ORDER BY vilkikas ASC, pakrovimo_data ASC
    """
    params = list(vilkikai) + [str(today)]
    kroviniai = c.execute(query, params).fetchall()

    # ==============================
    # 5) Žemėlapiai transporto ir ekspedicijos grupėms
    # ==============================
    vilk_grupes = dict(c.execute("""
        SELECT v.numeris, g.pavadinimas
        FROM vilkikai v
        LEFT JOIN darbuotojai d ON v.vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall())
    eksp_grupes = dict(c.execute("""
        SELECT k.id, g.pavadinimas
        FROM kroviniai k
        LEFT JOIN darbuotojai d ON k.ekspedicijos_vadybininkas = d.vardas
        LEFT JOIN grupes g ON d.grupe = g.pavadinimas
    """).fetchall())

    # ==============================
    # 6) Stulpelių proporcijos (vienetai proporcingi)
    # ==============================
    col_widths = [
        0.5,   # Save
        0.85,  # Atnaujinta prieš
        0.6,   # Vilkikas
        0.7,   # P.D.
        0.7,   # P.L.
        1.0,   # P.V.
        0.7,   # I.D.
        0.7,   # I.L.
        1.0,   # I.V.
        0.6,   # Km
        0.8,   # E.Vad.
        0.45,  # SA
        0.45,  # BDL
        0.45,  # LDL
        0.8,   # P.D.* 
        0.5,   # P.L.* 
        0.75,  # P.St.* 
        0.8,   # I.D.* 
        0.5,   # I.L.* 
        0.75,  # I.St.* 
        1.0    # Kom.
    ]

    headers = [
        ("💾",      "Save"),                    # Save
        ("Atnaujinta prieš", "Laikas"),         # Atnaujinta prieš
        ("Vilk.",   "Vilkikas"),                # Vilkikas
        ("P.D.",    "Pakrovimo data"),          # P.D.
        ("P.L.",    "Pakrovimo laikas"),        # P.L.
        ("P.V.",    "Pakrovimo vieta"),         # P.V.
        ("I.D.",    "Iškrovimo data"),          # I.D.
        ("I.L.",    "Iškrovimo laikas"),        # I.L.
        ("I.V.",    "Iškrovimo vieta"),         # I.V.
        ("Km",      "Kilometražas"),            # Km
        ("E.Vad.",  "Ekspedicijos vadybininkas"),# E.Vad.
        ("SA",      "Savaitinė atstova"),       # SA
        ("BDL",     "Darbo laiko pabaiga"),      # BDL
        ("LDL",     "Likusios darbo valandos"),  # LDL
        ("P.D.*",   "Planuojamas P.D."),         # P.D.* 
        ("P.L.*",   "Planuojamas P.L."),         # P.L.* 
        ("P.St.*",  "Pakrovimo statusas"),       # P.St.* 
        ("I.D.*",   "Planuojamas I.D."),         # I.D.* 
        ("I.L.*",   "Planuojamas I.L."),         # I.L.* 
        ("I.St.*",  "Iškrovimo statusas"),       # I.St.* 
        ("Kom.",    "Komentaras")                # Kom.
    ]

    # ==============================
    # 7) Rodyti antraštę su tooltips ir scroll
    # ==============================
    st.markdown("<div class='scroll-container'>", unsafe_allow_html=True)
    cols = st.columns(col_widths)
    for i, (abbr, full) in enumerate(headers):
        cols[i].markdown(f"<b title='{full}'>{abbr}</b>", unsafe_allow_html=True)

    # ==============================
    # 8) Rodyti kiekvieną krovinį – viskas vienoje eilutėje
    # ==============================
    for k in kroviniai:
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

        if darbo and darbo[7] == "Iškrauta":
            try:
                iskrov_data = pd.to_datetime(darbo[9]).date()
            except:
                iskrov_data = None
        else:
            iskrov_data = None

        if iskrov_data and iskrov_data < today:
            continue

        # 8.3) Paruošiame rodomus laukus
        created = darbo[3] if darbo and darbo[3] else None
        rel_atn = relative_time(created) if created else ""

        sa          = darbo[0] if darbo and darbo[0] else ""
        bdl         = darbo[1] if darbo and darbo[1] not in [None, ""] else ""
        ldl         = darbo[2] if darbo and darbo[2] not in [None, ""] else ""
        pk_status   = darbo[4] if darbo and darbo[4] else ""
        pk_laikas   = darbo[5] if darbo and darbo[5] else (str(k[7])[:5] if k[7] else "")
        pk_data     = darbo[6] if darbo and darbo[6] else str(k[3])
        komentaras  = darbo[10] if darbo and darbo[10] else ""
        eksp_vad    = darbo[12] if darbo and darbo[12] else k[16] if len(k) > 16 else ""
        # trans_gr, eksp_gr išimti
        trans_gr    = ""
        eksp_gr     = ""

        row_cols = st.columns(col_widths)

        # 8.4) Save mygtukas
        save = row_cols[0].button("💾", key=f"save_{k[0]}")

        # 8.5) Atnaujinta prieš (HH:MM)
        row_cols[1].write(rel_atn)

        # 8.6) Vilkikas (išplėstas, paryškintas)
        vilk_text = f"<span class='vilk-cell'>{str(k[5])}</span>"
        row_cols[2].markdown(vilk_text, unsafe_allow_html=True)

        # 8.7) Pakrovimo data (originali)
        row_cols[3].write(str(k[3]))
        # 8.8) Pakrovimo laikas (originalus)
        row_cols[4].write(
            str(k[7])[:5] + (f" - {str(k[8])[:5]}" if k[8] else "")
        )
        # 8.9) Pakrovimo vieta
        vieta_pk = f"{k[11] or ''}{k[12] or ''}"
        row_cols[5].write(vieta_pk[:18])
        # 8.10) Iškr. data (originali)
        row_cols[6].write(str(k[4]))
        # 8.11) Iškr. laikas (originalus)
        row_cols[7].write(
            str(k[9])[:5] + (f" - {str(k[10])[:5]}" if k[10] else "")
        )
        # 8.12) Iškr. vieta
        vieta_is = f"{k[13] or ''}{k[14] or ''}"
        row_cols[8].write(vieta_is[:18])
        # 8.13) Km
        row_cols[9].write(str(k[15]))

        # 8.14) Ekspedicijos vadybininkas
        row_cols[10].write(eksp_vad or "")

        # 8.15) SA – tekstinis įvesties langelis
        sa_in = row_cols[11].text_input("", value=str(sa), key=f"sa_{k[0]}", label_visibility="collapsed")
        # 8.16) BDL – tekstinis įvesties langelis
        bdl_in = row_cols[12].text_input("", value=str(bdl), key=f"bdl_{k[0]}", label_visibility="collapsed")
        # 8.17) LDL – tekstinis įvesties langelis
        ldl_in = row_cols[13].text_input("", value=str(ldl), key=f"ldl_{k[0]}", label_visibility="collapsed")

        # 8.18) Pakrovimo data (edit)
        try:
            default_pk_date = datetime.fromisoformat(pk_data).date()
        except:
            default_pk_date = datetime.now().date()
        pk_data_key = f"pk_date_{k[0]}"
        pk_data_in = row_cols[14].date_input(
            "", value=default_pk_date, key=pk_data_key, label_visibility="collapsed"
        )

        # 8.19) Pakrovimo laikas (edit)
        pk_time_key = f"pk_time_{k[0]}"
        formatted_pk = format_time_str(pk_laikas) if pk_laikas else ""
        pk_laikas_in = row_cols[15].text_input(
            "", value=formatted_pk, key=pk_time_key, label_visibility="collapsed", placeholder="HHMM"
        )

        # 8.20) Pakrovimo statusas – drop list
        pk_status_options = ["", "Atvyko", "Pakrauta", "Kita"]
        default_pk_status_idx = pk_status_options.index(pk_status) if pk_status in pk_status_options else 0
        pk_status_in = row_cols[16].selectbox(
            "", options=pk_status_options, index=default_pk_status_idx,
            key=f"pk_status_{k[0]}", label_visibility="collapsed"
        )

        # 8.21) Iškr. data (edit)
        try:
            ikr_data = darbo[9] if darbo and darbo[9] else str(k[4])
            default_ikr_date = datetime.fromisoformat(ikr_data).date()
        except:
            default_ikr_date = datetime.now().date()
        ikr_data_key = f"ikr_date_{k[0]}"
        ikr_data_in = row_cols[17].date_input(
            "", value=default_ikr_date, key=ikr_data_key, label_visibility="collapsed"
        )

        # 8.22) Iškr. laikas (edit)
        ikr_laikas = darbo[8] if darbo and darbo[8] else (str(k[9])[:5] if k[9] else "")
        ikr_time_key = f"ikr_time_{k[0]}"
        formatted_ikr = format_time_str(ikr_laikas) if ikr_laikas else ""
        ikr_laikas_in = row_cols[18].text_input(
            "", value=formatted_ikr, key=ikr_time_key, label_visibility="collapsed", placeholder="HHMM"
        )

        # 8.23) Iškr. statusas – drop list
        ikr_status = darbo[7] if darbo and darbo[7] else ""
        ikr_status_options = ["", "Atvyko", "Iškrauta", "Kita"]
        default_ikr_status_idx = ikr_status_options.index(ikr_status) if ikr_status in ikr_status_options else 0
        ikr_status_in = row_cols[19].selectbox(
            "", options=ikr_status_options, index=default_ikr_status_idx,
            key=f"ikr_status_{k[0]}", label_visibility="collapsed"
        )

        # 8.24) Komentaras (edit)
        komentaras_in = row_cols[20].text_input(
            "", value=komentaras, key=f"komentaras_{k[0]}", label_visibility="collapsed"
        )

        # 8.25) Išsaugojimo (Save) logika
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
                    eksp_vad,
                    "", "",
                    jau_irasas[0]
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
                    eksp_vad,
                    "", ""
                ))
            conn.commit()
            st.success("✅ Išsaugota!")

    # ==============================
    # 9) Uždarome scroll-container div
    # ==============================
    st.markdown("</div>", unsafe_allow_html=True)
