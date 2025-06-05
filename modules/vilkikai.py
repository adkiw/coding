# modules/vilkikai.py

import streamlit as st
import pandas as pd
from datetime import date

def show(conn, c):
    """
    DISPO – Vilkikų valdymas

    Ši funkcija atvaizduoja vilkikų valdymo sąsają:
    - Leidžia matyti jau įvestus vilkikus sąraše;
    - Pridėti naują vilkiką arba redaguoti esamą;
    - Užtikrina, kad lentelėje "vilkikai" būtų visi reikiami stulpeliai;
    - Leidžia priskirti priekabą, transporto vadybininką ir vairuotojus.
    """

    # 1) Įsitikiname, kad lentelėje "vilkikai" egzistuoja visi reikalingi stulpeliai
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(vilkikai)").fetchall()]
    extras = {
        "draudimas": "TEXT",
        "pagaminimo_metai": "INTEGER",
        "marke": "TEXT",
        "tech_apziura": "TEXT",
        "vadybininkas": "TEXT",
        "vairuotojai": "TEXT",
        "priekaba": "TEXT"
    }
    for col, typ in extras.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE vilkikai ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Surenkame duomenis dropdown sąrašams
    # Vairuotojų sąrašas (vardas + pavardė)
    vairuotoju_list = [
        f"{r[1]} {r[2]}"
        for r in c.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()
    ]

    # Transporto vadybininkų sąrašas (tik vardas, kad sutaptų su darbuotojų lentele)
    vadybininku_list = [
        r[0]
        for r in c.execute(
            "SELECT vardas FROM darbuotojai WHERE pareigybe = ?", 
            ("Transporto vadybininkas",)
        ).fetchall()
    ]
    vadybininku_dropdown = [""] + vadybininku_list  # tuščias pasirinkimas pirmoje vietoje

    # Priekabų sąrašas: iš lentelės "priekabos"
    priekabu_list = [r[0] for r in c.execute("SELECT numeris FROM priekabos").fetchall()]

    # 3) Funkcijos, skirtos tik sesijos būsenai valdyti
    def clear_selection():
        """Išvalo pasirinkto vilkiko būseną ir visų filtrų įvestį"""
        st.session_state.selected_vilk = None
        for key in list(st.session_state):
            if key.startswith("f_"):
                st.session_state[key] = ""

    def new_vilk():
        """Nustato sesijos būseną, kad būtų kuriamas naujas vilkikas"""
        st.session_state.selected_vilk = 0

    def edit_vilk(numeris):
        """Nustato sesijos būseną, kad būtų redaguojamas esamas vilkikas"""
        st.session_state.selected_vilk = numeris

    # 4) Puslapio antraštė ir mygtukas "Pridėti naują vilkiką"
    col_title, col_add = st.columns([9, 1])
    col_title.title("DISPO – Vilkikų valdymas")
    col_add.button("➕ Pridėti naują vilkiką", on_click=new_vilk)

    # 5) Inicializuojame sesijos būseną, jei jos dar nėra
    if 'selected_vilk' not in st.session_state:
        st.session_state.selected_vilk = None

    # 6) Jei niekas nėra pažymėta (selected_vilk is None) – rodomas sąrašas
    if st.session_state.selected_vilk is None:
        df = pd.read_sql_query("SELECT numeris, marke, pagaminimo_metai FROM vilkikai ORDER BY numeris", conn)
        if df.empty:
            st.info("🔍 Kol kas nėra vilkikų.")
        else:
            df_disp = df.copy()
            df_disp.rename(
                columns={
                    'marke': 'Modelis',
                    'pagaminimo_metai': 'Pirmos registracijos metai'
                },
                inplace=True
            )
            st.dataframe(df_disp)

        # 7) Sukuriame mygtukus redagavimui
        if not df.empty:
            for _, row in df.iterrows():
                cols = st.columns([2, 2, 2, 1])
                cols[0].write(row["numeris"])
                cols[1].write(row["marke"])
                cols[2].write(row["pagaminimo_metai"])
                if cols[3].button("✏️", key=f"edit_{row['numeris']}"):
                    edit_vilk(row["numeris"])
        return  # išeiname – sąrašas jau atvaizduotas

    # 8) Jei selected_vilk != None, atidarome formą (naujam arba esamam vilkikui)
    is_new = (st.session_state.selected_vilk == 0)
    if is_new:
        vilk = {
            "numeris": "",
            "marke": "",
            "pagaminimo_metai": "",
            "tech_apziura": "",
            "draudimas": "",
            "vadybininkas": "",
            "vairuotojai": "",
            "priekaba": ""
        }
    else:
        # Krauname esamo vilkiko duomenis iš DB
        row = c.execute(
            "SELECT numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba "
            "FROM vilkikai WHERE numeris = ?",
            (st.session_state.selected_vilk,)
        ).fetchone()
        if not row:
            st.error("❌ Vilkikas nerastas.")
            clear_selection()
            st.experimental_rerun()
            return
        vilk = {
            "numeris": row[0],
            "marke": row[1],
            "pagaminimo_metai": row[2],
            "tech_apziura": row[3],
            "draudimas": row[4],
            "vadybininkas": row[5],
            "vairuotojai": row[6],
            "priekaba": row[7]
        }

    # 9) Formos atvaizdavimas (įvedimui / redagavimui)
    with st.form(key="vilk_form"):
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Numeris", value=vilk["numeris"], max_chars=20)
        marke = col1.text_input("Markė", value=vilk["marke"])
        pag_metai = col1.number_input(
            "Pagaminimo metai",
            min_value=1900,
            max_value=date.today().year,
            value=vilk["pagaminimo_metai"] or date.today().year,
            step=1
        )

        tech_date = col2.date_input(
            "Techninė apžiūra",
            value=date.fromisoformat(vilk["tech_apziura"]) if vilk["tech_apziura"] else date.today()
        )
        draud_date = col2.date_input(
            "Draudimo galiojimas",
            value=date.fromisoformat(vilk["draudimas"]) if vilk["draudimas"] else date.today()
        )

        # Dropdown transporto vadybininkui (tik vardas)
        if not is_new and vilk.get("vadybininkas") in vadybininku_list:
            vadyb_idx = vadybininku_dropdown.index(vilk["vadybininkas"])
        else:
            vadyb_idx = 0
        vadyb = col2.selectbox(
            "Transporto vadybininkas",
            vadybininku_dropdown,
            index=vadyb_idx
        )

        # Dropdown vairuotojams (maksimaliai du)
        v1_opts = [""] + vairuotoju_list
        v1_idx = v2_idx = 0
        if not is_new and vilk["vairuotojai"]:
            parts = vilk["vairuotojai"].split(", ")
            if parts and parts[0] in vairuotoju_list:
                v1_idx = v1_opts.index(parts[0])
            if len(parts) > 1 and parts[1] in vairuotoju_list:
                v2_idx = v1_opts.index(parts[1])
        v1 = col1.selectbox("Vairuotojas 1", v1_opts, index=v1_idx)
        v2 = col1.selectbox("Vairuotojas 2", v1_opts, index=v2_idx)

        # Dropdown priekabai
        prk_opts = [""] + priekabu_list
        prk_idx = 0
        if not is_new and vilk["priekaba"] in priekabu_list:
            prk_idx = prk_opts.index(vilk["priekaba"])
        prk = col2.selectbox("Priekaba", prk_opts, index=prk_idx)

        # Išsaugojimo / atšaukimo mygtukai
        submit_btn = st.form_submit_button("💾 Išsaugoti")
        cancel_btn = st.form_submit_button("✖ Atšaukti")

        if cancel_btn:
            clear_selection()
            st.experimental_rerun()
            return

        if submit_btn:
            # Įrašome naujai arba atnaujiname esamą
            try:
                if is_new:
                    c.execute(
                        "INSERT INTO vilkikai "
                        "(numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            numeris.strip() or None,
                            marke.strip() or None,
                            pag_metai,
                            tech_date.isoformat() if tech_date else None,
                            draud_date.isoformat() if draud_date else None,
                            vadyb or None,
                            (", ".join([v for v in [v1, v2] if v])) or None,
                            prk or None
                        )
                    )
                else:
                    c.execute(
                        "UPDATE vilkikai SET "
                        "marke = ?, "
                        "pagaminimo_metai = ?, "
                        "tech_apziura = ?, "
                        "draudimas = ?, "
                        "vadybininkas = ?, "
                        "vairuotojai = ?, "
                        "priekaba = ? "
                        "WHERE numeris = ?",
                        (
                            marke.strip() or None,
                            pag_metai,
                            tech_date.isoformat() if tech_date else None,
                            draud_date.isoformat() if draud_date else None,
                            vadyb or None,
                            (", ".join([v for v in [v1, v2] if v])) or None,
                            prk or None,
                            numeris
                        )
                    )
                conn.commit()
                st.success("✅ Vilkikas išsaugotas sėkmingai.")
                # Informacija apie likusias dienas iki tech. apžiūros / draudimo
                if tech_date:
                    st.info(f"🔧 Dienų iki tech. apžiūros liko: {(tech_date - date.today()).days}")
                if draud_date:
                    st.info(f"🛡️ Dienų iki draudimo pabaigos liko: {(draud_date - date.today()).days}")
                clear_selection()
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Klaida saugant vilkiką: {e}")
                return
