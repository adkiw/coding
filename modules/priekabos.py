"""
modulis: priekabos.py

Pagrindinė funkcija `show` suteikia Streamlit aplinkoje:
- Priekabų lentelės struktūros užtikrinimą (ALTER TABLE prireikus).
- Priekabų peržiūrą, filtravimą, naujų įrašų kūrimą ir esamų redagavimą.
- Ryšį su vilkikai moduliu (priskirtų vilkikų atvaizdavimas).
- CSV eksporto galimybę.
"""

import streamlit as st
import pandas as pd
from datetime import date

def show(conn, c):
    """
    Rodo priekabų valdymo modulį Streamlit lange.

    Funkcijos eiga:
    1) Užtikrinami visi reikalingi stulpeliai lentelėje `priekabos`.
    2) Ruošiami duomenys dropdown formoms (vilkikų sąrašas).
    3) Nustatoma Streamlit sesijos būsena.
    4) Pagal būseną rodomas:
       a) Redagavimo forma (kai pasirenkama egzistuojanti priekaba),
       b) Įvedimo forma (kai paspaustas "Pridėti naują"),
       c) Lentelės rodinys su filtravimo ir CSV eksporto galimybėmis.
    5) Duomenų įrašai arba atnaujinimai saugomi DB per `conn` ir `c`.

    Args:
        conn (sqlite3.Connection): Atidarytas SQLite prisijungimas.
        c (sqlite3.Cursor): Duomenų bazės kursorius.
    """
    st.title("Trailer management")

    # 1) Užtikriname, kad lentelėje 'priekabos' egzistuotų visi reikiami stulpeliai
    existing = [r[1] for r in c.execute("PRAGMA table_info(priekabos)").fetchall()]
    extras = {
        'priekabu_tipas': 'TEXT',
        'numeris': 'TEXT',
        'marke': 'TEXT',
        'pagaminimo_metai': 'TEXT',
        'tech_apziura': 'TEXT',
        'draudimas': 'TEXT'
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE priekabos ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Paruošiame duomenis dropdown meniu: vilkikų sąrašą
    vilkikai_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]

    # 3) Inicializuojame sesijos būseną redagavimui/pridėjimui
    if 'selected_priek' not in st.session_state:
        st.session_state.selected_priek = None

    # Callback'ai
    def clear_sel():
        """Išvalo pasirinkimą ir filtrus iš session_state."""
        st.session_state.selected_priek = None
        for key in list(st.session_state):
            if key.startswith("f_"):
                st.session_state[key] = ""

    def new():
        """Pradeda naujos priekabos kūrimo režimą."""
        st.session_state.selected_priek = 0

    def edit(id):
        """Pasirenkama esama priekaba redagavimui pagal ID."""
        st.session_state.selected_priek = id

    # 4) "Add trailer" button
    st.button("➕ Add trailer", on_click=new, use_container_width=True)

    sel = st.session_state.selected_priek

    # 5) Redagavimo rodinys (kai pasirenkama egzistuojanti priekaba)
    if sel not in (None, 0):
        df_sel = pd.read_sql_query(
            "SELECT * FROM priekabos WHERE id = ?", conn, params=(sel,)
        )
        if df_sel.empty:
            st.error("❌ Priekaba nerasta.")
            clear_sel()
            return

        row = df_sel.iloc[0]
        with st.form("edit_form", clear_on_submit=False):
            # 5.1) Trailer type
            priekabu_tipas_opts = ["", "Curtain", "Box trailer", "Reefer", "Cistern"]
            tip_idx = priekabu_tipas_opts.index(row['priekabu_tipas']) if row['priekabu_tipas'] in priekabu_tipas_opts else 0
            tip = st.selectbox("Trailer type", priekabu_tipas_opts, index=tip_idx)

            # 5.2) Kiti laukai: numeris, markė, datos
            num = st.text_input("Number", value=row['numeris'])
            model = st.text_input("Brand", value=row['marke'])
            pr_data = st.date_input(
                "First registration date",
                value=(date.fromisoformat(row['pagaminimo_metai']) if row['pagaminimo_metai'] else date(2000,1,1)),
                key="pr_data"
            )
            tech = st.date_input(
                "Technical inspection",
                value=(date.fromisoformat(row['tech_apziura']) if row['tech_apziura'] else date.today()),
                key="tech_date"
            )
            draud_date = st.date_input(
                "Insurance expiry date",
                value=(date.fromisoformat(row['draudimas']) if row['draudimas'] else date.today()),
                key="draud_date"
            )

            # 5.3) Priskirtas vilkikas (tik skaitomas, negalima keisti čia)
            assigned_vilk = c.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba = ?", (row['numeris'],)
            ).fetchone()
            pv = assigned_vilk[0] if assigned_vilk else ""
            st.text_input("Assigned truck", value=pv, disabled=True)

            # Veiksmai mygtukais
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Save")
            back = col2.form_submit_button("🔙 Back to list", on_click=clear_sel)

        if save:
            try:
                c.execute(
                    "UPDATE priekabos SET priekabu_tipas=?, numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=? WHERE id=?",
                    (
                        tip or None,
                        num,
                        model or None,
                        pr_data.isoformat() if pr_data else None,
                        tech.isoformat() if tech else None,
                        draud_date.isoformat() if draud_date else None,
                        sel
                    )
                )
                conn.commit()
                st.success("✅ Changes saved.")
                clear_sel()
            except Exception as e:
                st.error(f"❌ Error: {e}")
        return

    # 6) Naujos priekabos įvedimo forma
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            priekabu_tipas_opts = ["", "Curtain", "Box trailer", "Reefer", "Cistern"]
            tip = st.selectbox("Trailer type", priekabu_tipas_opts)

            num = st.text_input("Number")
            model = st.text_input("Brand")
            pr_data = st.date_input("First registration date", value=date(2000,1,1), key="new_pr_data")
            tech = st.date_input("Technical inspection", value=date.today(), key="new_tech_date")
            draud_date = st.date_input("Insurance expiry date", value=date.today(), key="new_draud_date")

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Save trailer")
            back = col2.form_submit_button("🔙 Back to list", on_click=clear_sel)

        if save:
            if not num:
                st.warning("⚠️ Enter number.")
            else:
                try:
                    c.execute(
                        "INSERT INTO priekabos(priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas) VALUES(?,?,?,?,?,?)",
                        (
                            tip or None,
                            num,
                            model or None,
                            pr_data.isoformat(),
                            tech.isoformat(),
                            draud_date.isoformat()
                        )
                    )
                    conn.commit()
                    st.success("✅ Trailer saved.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        return

    # 7) Priekabų sąrašas lentelės pavidalu su filtravimo ir CSV eksporto galimybe
    df = pd.read_sql_query("SELECT * FROM priekabos", conn)
    if df.empty:
        st.info("ℹ️ No trailers.")
        return

    # 7.1) None → tuščias string
    df = df.fillna('')
    df_disp = df.copy()
    df_disp.rename(
        columns={
            'marke': 'Brand',
            'pagaminimo_metai': 'First registration date',
            'draudimas': 'Insurance expiry date'
        },
        inplace=True
    )

    # 7.2) Pridedame stulpelį "Priskirtas vilkikas"
    assigned_list = []
    for _, row in df.iterrows():
        prn = row['numeris']
        assigned_vilk = c.execute(
            "SELECT numeris FROM vilkikai WHERE priekaba = ?", (prn,)
        ).fetchone()
        assigned_list.append(assigned_vilk[0] if assigned_vilk else "")
    df_disp['Assigned truck'] = assigned_list

    # 7.3) Filtravimo placeholder'ai (be headerių)
    filter_cols = st.columns(len(df_disp.columns) + 1)
    for i, col in enumerate(df_disp.columns):
        filter_cols[i].text_input(label="", placeholder=col, key=f"f_{col}")
    filter_cols[-1].write("")

    df_filt = df_disp.copy()
    for col in df_disp.columns:
        val = st.session_state.get(f"f_{col}", "")
        if val:
            df_filt = df_filt[df_filt[col].astype(str).str.lower().str.startswith(val.lower())]

    # 7.4) Display rows with edit buttons
    for _, row in df_filt.iterrows():
        row_cols = st.columns(len(df_filt.columns) + 1)
        for i, col in enumerate(df_filt.columns):
            row_cols[i].write(row[col])
        row_cols[-1].button(
            "✏️",
            key=f"edit_{row['id']}",
            on_click=edit,
            args=(row['id'],)
        )

    # 7.5) CSV export
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label="💾 Download CSV",
        data=csv,
        file_name="priekabos.csv",
        mime="text/csv"
    )
