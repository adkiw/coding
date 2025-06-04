# modules/update.py

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
    /* Įkeliame konteinerį atskirai, kad būtų horizontalus skrolas */
    .scroll-container {
      overflow-x: auto;
    }
    </style>
""", unsafe_allow_html=True)

# Funkcija laiko formatavimui "HHMM" → "HH:MM"
def format_time_str(t):
    t = str(t).zfill(4)
    return t[:2] + ":" + t[2:]

def show(conn, c):
    st.title("DISPO – Update")

    # 1) Vilkikų filtravimas pagal ekspedicines grupes
    c.execute("SELECT pavadinimas FROM grupes ORDER BY numeris")
    all_groups = [row[0] for row in c.fetchall()]
    selected_group = st.selectbox("Pasirinkti ekspedicinę grupę", ["Visi"] + all_groups)

    # 2) Surenkame vilkikus, priklausančius pasirinktai grupei (arba visus)
    if selected_group == "Visi":
        c.execute("SELECT numeris FROM vilkikai ORDER BY numeris")
        vilkikai = [row[0] for row in c.fetchall()]
    else:
        # Vilkikai, kurių ekspedicijos grupė sutampa su selected_group
        c.execute("""
            SELECT numeris
            FROM vilkikai
            WHERE eksp_grupe = ?
            ORDER BY numeris
        """, (selected_group,))
        vilkikai = [row[0] for row in c.fetchall()]

    if not vilkikai:
        st.info("Šioje grupėje nėra vilkikų.")
        return

    # 3) Krovių užklausa iš lentelės "kroviniai"
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
        WHERE vilkikas IN ({placeholders})
          AND pakrovimo_data >= ?
        ORDER BY vilkikas ASC, pakrovimo_data ASC
    """
    params = vilkikai + [str(today)]
    kroviniai = c.execute(query, params).fetchall()

    # 4) Parenkame vilkiko grupių ir ekspedicijos grupių žemėlapius rodymui
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

    # 5) Stulpelių antraščių plotis (vienetai proporcingi)
    col_widths = [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3]

    # 6) Pridedame CSS apvyniojimą, kad susidarytų horizontalus skrolas
    st.markdown("<div class='scroll-container'>", unsafe_allow_html=True)

    # 7) Generuojame eilutes – kiekvienam krovinio įrašui atskiros kolonos
    for k in kroviniai:
        # 7.1) Paimame paskutinį darbo įrašą iš vilkiku_darbo_laikai
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

        # 7.2) Jeigu iškrovimo statusas "Iškrauta" ir iškrovimo data praeityje – ignoruojam šį krovinį
        if darbo and darbo[7] == "Iškrauta":
            try:
                iskrov_data = pd.to_datetime(darbo[9]).date()
            except:
                iskrov_data = None
        else:
            iskrov_data = None

        if iskrov_data and iskrov_data < today:
            continue

        # 7.3) Nustatome pakrovimo/iškrovimo duomenis rodyme
        created = darbo[3] if darbo and darbo[3] else None
        sa_in = darbo[0] if darbo and darbo[0] else ""
        bdl_in = darbo[1] if darbo and darbo[1] else ""
        ldl_in = darbo[2] if darbo and darbo[2] else ""
        pk_status = darbo[4] if darbo and darbo[4] else ""
        pk_laikas = darbo[5] if darbo and darbo[5] else (str(k[7])[:5] if k[7] else "")
        pk_data = darbo[6] if darbo and darbo[6] else str(k[3])
        ikr_status = darbo[7] if darbo and darbo[7] else ""
        ikr_laikas = darbo[8] if darbo and darbo[8] else (str(k[9])[:5] if k[9] else "")
        ikr_data = darbo[9] if darbo and darbo[9] else str(k[4])
        komentaras = darbo[10] if darbo and darbo[10] else ""
        trans_gr = darbo[12] if darbo and darbo[12] else vilk_grupes.get(k[5], "")
        eksp_gr = darbo[13] if darbo and darbo[13] else eksp_grupes.get(k[0], "")

        row_cols = st.columns(col_widths)

        # 7.4) Save mygtukas
        save = row_cols[0].button("💾", key=f"save_{k[0]}")

        # 7.5) Atnaujinta data
        if created:
            laikas = pd.to_datetime(created)
            row_cols[1].markdown(
                f"<div style='padding:2px 6px;'>{laikas.strftime('%Y-%m-%d %H:%M')}</div>",
                unsafe_allow_html=True
            )
        else:
            row_cols[1].markdown("<div style='padding:2px 6px;'>&nbsp;</div>", unsafe_allow_html=True)

        # 7.6) Vilkikas
        row_cols[2].write(str(k[5])[:7])
        # 7.7) Priekaba
        row_cols[3].write(str(k[6])[:7])
        # 7.8) Pakrovimo data
        row_cols[4].write(str(k[3]))
        # 7.9) Pakrovimo laikas (rodoma „HH:MM – HH:MM“ formatu, jei yra)
        row_cols[5].write(str(k[7])[:5] + (f" - {str(k[8])[:5]}" if k[8] else ""))
        # 7.10) Pakrovimo vieta
        vieta_pk = f"{k[11] or ''}{k[12] or ''}"
        row_cols[6].write(vieta_pk)
        # 7.11) Iškrovimo data
        row_cols[7].write(str(k[4]))
        # 7.12) Iškrovimo laikas
        row_cols[8].write(str(k[9])[:5] + (f" - {str(k[10])[:5]}" if k[10] else ""))
        # 7.13) Iškrovimo vieta
        vieta_ikr = f"{k[13] or ''}{k[14] or ''}"
        row_cols[9].write(vieta_ikr)
        # 7.14) Km
        row_cols[10].write(str(k[15])[:5])

        # 7.15) Transporto grupė
        row_cols[11].write(trans_gr)
        # 7.16) Transporto vadybininkas
        tv = c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()
        row_cols[12].write(tv[0] if tv else "")
        # 7.17) Ekspedicijos grupė
        row_cols[13].write(str(k[16])[:7] if len(k) > 16 else "")
        # 7.18) Ekspedicijos vadybininkas
        row_cols[14].write(str(k[17])[:7] if len(k) > 17 else "")

        # 7.19) SA (paskutinė reikšmė)
        row_cols[15].write(sa_in)
        # 7.20) BDL (paskutinė reikšmė)
        row_cols[16].write(bdl_in)
        # 7.21) LDL (paskutinė reikšmė)
        row_cols[17].write(ldl_in)

        # 7.22) Pakrovimo data (edit)
        default_pk_date = datetime.now().date() if not pk_data else datetime.fromisoformat(pk_data).date()
        pk_data_key = f"pk_date_{k[0]}"
        pk_data_in = row_cols[18].date_input("", value=default_pk_date, key=pk_data_key, label_visibility="collapsed")

        # 7.23) Pakrovimo laikas (edit)
        default_pk_time = format_time_str(pk_laikas) if pk_laikas else ""
        pk_time_key = f"pk_time_{k[0]}"
        pk_laikas_in = row_cols[19].text_input("", value=default_pk_time, key=pk_time_key, label_visibility="collapsed", placeholder="HHMM")

        # 7.24) Pakrovimo statusas (edit)
        pk_status_options = ["", "Atvyko", "Pakrauta", "Kita"]
        default_pk_status_idx = pk_status_options.index(pk_status) if pk_status in pk_status_options else 0
        pk_status_in = row_cols[20].selectbox("", options=pk_status_options, index=default_pk_status_idx, key=f"pk_status_{k[0]}", label_visibility="collapsed")

        # 7.25) Iškrovimo data (edit)
        default_ikr_date = datetime.now().date() if not ikr_data else datetime.fromisoformat(ikr_data).date()
        ikr_data_key = f"ikr_date_{k[0]}"
        ikr_data_in = row_cols[21].date_input("", value=default_ikr_date, key=ikr_data_key, label_visibility="collapsed")

        # 7.26) Iškrovimo laikas (edit)
        default_ikr_time = format_time_str(ikr_laikas) if ikr_laikas else ""
        ikr_time_key = f"ikr_time_{k[0]}"
        ikr_laikas_in = row_cols[22].text_input("", value=default_ikr_time, key=ikr_time_key, label_visibility="collapsed", placeholder="HHMM")

        # 7.27) Iškrovimo statusas (edit)
        ikr_status_options = ["", "Atvyko", "Iškrauta", "Kita"]
        default_ikr_status_idx = ikr_status_options.index(ikr_status) if ikr_status in ikr_status_options else 0
        ikr_status_in = row_cols[23].selectbox("", options=ikr_status_options, index=default_ikr_status_idx, key=f"ikr_status_{k[0]}", label_visibility="collapsed")

        # 7.28) Komentaras (edit)
        komentaras_in = row_cols[24].text_input("", value=komentaras, key=f"komentaras_{k[0]}", label_visibility="collapsed")

        # 7.29) Išsaugojimo logika
        if save:
            jau_irasas = c.execute("""
                SELECT id FROM vilkiku_darbo_laikai WHERE vilkiko_numeris = ? AND data = ?
            """, (k[5], k[3])).fetchone()
            now_str = datetime.now().isoformat()
            formatted_pk_date = pk_data_in.isoformat()
            formatted_ikr_date = ikr_data_in.isoformat()
            if jau_irasas:
                c.execute("""
                    UPDATE vilkiku_darbo_laikai SET
                      sa = ?, darbo_laikas = ?, likes_laikas = ?, created_at = ?,
                      pakrovimo_statusas = ?, pakrovimo_laikas = ?, pakrovimo_data = ?,
                      iskrovimo_statusas = ?, iskrovimo_laikas = ?, iskrovimo_data = ?,
                      komentaras = ?, ats_transporto_vadybininkas = ?, ats_ekspedicijos_vadybininkas = ?,
                      trans_grupe = ?, eksp_grupe = ?
                    WHERE id = ?
                """, (
                    sa_in, bdl_in, ldl_in, now_str,
                    pk_status_in, pk_laikas_in, formatted_pk_date,
                    ikr_status_in, ikr_laikas_in, formatted_ikr_date,
                    komentaras_in,
                    c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()[0],
                    k[16] if len(k) > 16 else "",
                    trans_gr, eksp_gr,
                    jau_irasas[0]
                ))
            else:
                c.execute("""
                    INSERT INTO vilkiku_darbo_laikai (
                      vilkiko_numeris, data, sa, darbo_laikas, likes_laikas, created_at,
                      pakrovimo_statusas, pakrovimo_laikas, pakrovimo_data,
                      iskrovimo_statusas, iskrovimo_laikas, iskrovimo_data,
                      komentaras, ats_transporto_vadybininkas, ats_ekspedicijos_vadybininkas,
                      trans_grupe, eksp_grupe
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    k[5], k[3], sa_in, bdl_in, ldl_in, now_str,
                    pk_status_in, pk_laikas_in, formatted_pk_date,
                    ikr_status_in, ikr_laikas_in, formatted_ikr_date,
                    komentaras_in,
                    c.execute("SELECT vadybininkas FROM vilkikai WHERE numeris = ?", (k[5],)).fetchone()[0],
                    k[16] if len(k) > 16 else "",
                    trans_gr, eksp_gr
                ))
            conn.commit()
            st.success("✅ Išsaugota!")

    # 8) Uždarome scroll-container div
    st.markdown("</div>", unsafe_allow_html=True)
