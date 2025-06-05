# modules/update.py

import streamlit as st
import pandas as pd
from datetime import datetime, date

# ==============================
# 0) CSS tam, kad visi headeriai ir reikšmės nebūtų lūžinami,
#    o visa eilutė būtų viena horizontali linija su skrolu,
#    vilkiko numeriams +2 font-size padidinimas
# ==============================
st.markdown("""
    <style>
      /* Apgaubti visą atvaizduojamą turinį scroll-container div'u,
         kurio viduje galima slinkti horizontaliai */
      .scroll-container {
        overflow-x: auto;
      }
      /* Lentelės stiliai */
      table {
        border-collapse: collapse;
        width: 100%;
        white-space: nowrap !important;
      }
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
      /* Praplečiame ir paryškiname vilkiko numerio langelį, padidiname fontą +2 */
      .vilk-cell {
        background-color: #f0f8ff;
        font-weight: bold;
        font-size: 14px !important;
      }
    </style>
""", unsafe_allow_html=True)


def format_time_str(input_str):
    """
    Paverčia vartotojo įvestą laiką tekstu formatu HH:MM:
    - jei tik viena arba dvi skaitmenys => tiesiog HH:00
    - jei trys skaitmenys => HMM => 0H:MM
    - jei keturi skaitmenys => HHMM => HH:MM
    """
    digits = "".join(filter(str.isdigit, str(input_str)))
    if not digits:
        return ""
    if len(digits) <= 2:
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
    """
    Skaičiuoja laiką (HH:MM), kiek praėjo nuo sukurimo (created_str) iki dabar.
    Jei neįmanoma paversti, gražina tuščią stringą.
    """
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
        ("pakrovimo_statusas",     "TEXT"),
        ("pakrovimo_laikas",       "TEXT"),
        ("pakrovimo_data",         "TEXT"),
        ("iskrovimo_statusas",     "TEXT"),
        ("iskrovimo_laikas",       "TEXT"),
        ("iskrovimo_data",         "TEXT"),
        ("komentaras",             "TEXT"),
        ("sa",                     "TEXT"),
        ("created_at",             "TEXT"),
        ("ats_transporto_vadybininkas", "TEXT"),
        ("ats_ekspedicijos_vadybininkas", "TEXT"),
        ("trans_grupe",            "TEXT"),
        ("eksp_grupe",             "TEXT"),
    ]
    for col, coltype in extra_cols:
        if col not in existing:
            c.execute(f"ALTER TABLE vilkiku_darbo_laikai ADD COLUMN {col} {coltype}")
    conn.commit()

    # ==============================
    # 2) Filtras: Transporto vadybininkas ir Transporto grupė (vienoje eilutėje)
    # ==============================
    vadybininkai = [
        r[0] for r in c.execute(
            "SELECT DISTINCT vadybininkas FROM vilkikai WHERE vadybininkas IS NOT NULL AND vadybininkas != ''"
        ).fetchall()
    ]
    # Rodysime tik grupes, kurių pavadinimas prasideda "TR"
    grupe_list = [
        r[0] for r in c.execute(
            "SELECT pavadinimas FROM grupes WHERE pavadinimas LIKE 'TR%'"
        ).fetchall()
    ]

    col1, col2 = st.columns(2)
    vadyb         = col1.selectbox("Transporto vadybininkas", [""] + vadybininkai, index=0)
    grupe_filtras = col2.selectbox("Transporto grupė", [""] + grupe_list, index=0)

    # ==============================
    # 3) Pasirenkame vilkikus pagal filtrus
    # ==============================
    # Pasiimame kiekvieno vilkiko numerį ir jo transporto grupę (per darbuotojų lentelę)
    vilkikai_info = c.execute("""
        SELECT v.numeris, d.grupe
        FROM vilkikai v
        LEFT JOIN darbuotojai d ON v.vadybininkas = d.vardas || ' ' || d.pavarde
    """).fetchall()

    vilkikai = []
    for v, g in vilkikai_info:
        # Filtruojame pagal vadybininką, jeigu pasirinktas
        if vadyb:
            vb = c.execute(
                "SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (v,)
            ).fetchone()[0]
            if vb != vadyb:
                continue
        # Filtruojame pagal transporto grupę, jeigu pasirinkta
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
    placeholder = st.empty()

    with placeholder.container():
        # Susirenkame visus krovinių įrašus
        df_kroviniai = pd.read_sql_query("SELECT * FROM kroviniai", conn)

    # ==============================
    # 5) Filtruojame kroviniai pagal vilkikus
    # ==============================
    df_kroviniai = df_kroviniai[df_kroviniai["vilkikas"].isin(vilkikai)]
    if df_kroviniai.empty:
        st.info("Nėra krovinio duomenų pasirinktų vilkikų.")
        return

    # ==============================
    # 6) DataFrame transformacijos
    # ==============================
    df_kroviniai["pak_date"] = pd.to_datetime(df_kroviniai["pakrovimo_data"]).dt.date
    df_kroviniai["ikr_date"] = pd.to_datetime(df_kroviniai["iskrovimo_data"]).dt.date

    df_kroviniai["pak_date_str"] = df_kroviniai["pak_date"].astype(str)
    df_kroviniai["ikr_date_str"] = df_kroviniai["ikr_date"].astype(str)

    # ==============================
    # 7) Paruošiame duomenis atnaujinimui: einamą laiką ir statusus
    # ==============================
    df_kroviniai["rel_time"] = df_kroviniai["created_at"].apply(relative_time)
    df_kroviniai["pak_time"] = df_kroviniai["pakrovimo_laikas"].astype(str).apply(format_time_str)
    df_kroviniai["ikr_time"] = df_kroviniai["iskrovimo_laikas"].astype(str).apply(format_time_str)

    # ==============================
    # 8) Atvaizduojame lentelę su horizontaliu skrolu
    # ==============================
    st.markdown("<div class='scroll-container'>", unsafe_allow_html=True)
    # Lentelės antraštės
    headers = [
        "💾", "Rel. laikas", "Vilk.", "P.D.", "P.L.", "P.V.", "I.D.", "I.L.", "I.V.", "K.", "Koment.", 
        "Vadyb.", "E.Vad.", "T.Gr.", "E.Gr."
    ]
    # Parašome HTML rankiniu būdu, kad kontroluotume stilius
    html = "<table>\n<thead><tr>"
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr></thead>\n<tbody>\n"

    for idx, row in df_kroviniai.iterrows():
        k = row  # trumpinys
        # Atnaujinimo mygtukas
        html += "<tr>\n"
        html += "<td class='tiny'>" \
                f"<button style='border:none; background:none; cursor:pointer;' " \
                f"onclick=\"fetch('/_stcore/streamlit_rerun?script=%2Fmnt%2Fapp.py', " \
                f"{'{ method: \\\"POST\\\" }')\">\n" \
                "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='#000' viewBox='0 0 16 16'>\n" \
                "<path d='M8 3a5 5 0 1 1-4.546 2.914.5.5 0 1 0-.908-.418A6 6 0 1 0 8 2v1z'/>\n" \
                "<path d='M8 0a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3A.5.5 0 0 1 8 0z'/>\n" \
                "</svg></button></td>\n"

        # Rel. laikas
        html += f"<td class='tiny'>{k['rel_time']}</td>\n"
        # Vilkiko numeris
        html += f"<td class='vilk-cell'>{k['vilkikas']}</td>\n"
        # Pakrovimo data (P.D.)
        html += f"<td>{k['pak_date_str']}</td>\n"
        # Pakrovimo laikas (P.L.)
        html += f"<td>{k['pak_time']}</td>\n"
        # Pakrovimo vieta (P.V.)
        vieta_pak = k["pakrovimo_kodas"] if k["pakrovimo_kodas"] else ""
        html += f"<td>{vieta_pak}</td>\n"
        # Iškrovimo data (I.D.)
        html += f"<td>{k['ikr_date_str']}</td>\n"
        # Iškrovimo laikas (I.L.)
        html += f"<td>{k['ikr_time']}</td>\n"
        # Iškrovimo vieta (I.V.)
        vieta_ikr = k["iskrovimo_kodas"] if k["iskrovimo_kodas"] else ""
        html += f"<td>{vieta_ikr}</td>\n"
        # Komentaras (K.)
        comment = k["komentaras"] if k["komentaras"] else ""
        html += f"<td class='tiny'>{comment}</td>\n"
        # Vadybininkas (Vadyb.)
        vdb = k["vadybininkas"] if k["vadybininkas"] else ""
        html += f"<td class='tiny'>{vdb}</td>\n"
        # Eksped. vadybininkas (E.Vad.)
        ev = k["ats_ekspedicijos_vadybininkas"] if k["ats_ekspedicijos_vadybininkas"] else ""
        html += f"<td class='tiny'>{ev}</td>\n"
        # Transporto grupė (T.Gr.)
        tg = k["trans_grupe"] if k["trans_grupe"] else ""
        html += f"<td class='tiny'>{tg}</td>\n"
        # Eksped. grupė (E.Gr.)
        eg = k["eksp_grupe"] if k["eksp_grupe"] else ""
        html += f"<td class='tiny'>{eg}</td>\n"

        html += "</tr>\n"

    html += "</tbody>\n</table>\n"
    st.markdown(html, unsafe_allow_html=True)

    # ==============================
    # 9) Uždarome scroll-container div
    # ==============================
    st.markdown("</div>", unsafe_allow_html=True)
