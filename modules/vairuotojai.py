import streamlit as st
import pandas as pd
from datetime import date

TAUTYBES = [
    ("", ""),
    ("Lietuva", "LT"),
    ("Baltarusija", "BY"),
    ("Ukraina", "UA"),
    ("Uzbekistanas", "UZ"),
    ("Indija", "IN"),
    ("Nigerija", "NG"),
    ("Lenkija", "PL"),
]

def show(conn, c):
    # 1) Pakeičiame antraštę
    st.title("Vairuotojų valdymas")

    # 2) Užtikriname, kad lentelėje 'vairuotojai' būtų reikiami stulpeliai
    existing = [r[1] for r in c.execute("PRAGMA table_info(vairuotojai)").fetchall()]
    extras = {
        'vardas': 'TEXT',
        'pavarde': 'TEXT',
        'gimimo_metai': 'TEXT',
        'tautybe': 'TEXT',
        'priskirtas_vilkikas': 'TEXT',
        # 'kaip_mokinys', 'kadencijos_pabaiga' ir 'atostogu_pabaiga' stulpeliai paliekami duombazėje,
        # bet į formą nebededame
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE vairuotojai ADD COLUMN {col} {typ}")
    conn.commit()

    # 3) Gauname vilkikų sąrašą iš vilkikai lentelės
    vilkikai_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]

    # 4) Inicijuojame session_state
    if 'selected_vair' not in st.session_state:
        st.session_state.selected_vair = None

    def clear_sel():
        st.session_state.selected_vair = None

    def new(): 
        st.session_state.selected_vair = 0

    def edit(id): 
        st.session_state.selected_vair = id

    # 5) Pagalbinė funkcija: ar vilkikas jau priskirtas kitam
    def vilkikas_jau_priskirtas(vilkikas, exclude_id=None):
        if not vilkikas:
            return False
        query = "SELECT id FROM vairuotojai WHERE priskirtas_vilkikas = ?"
        params = (vilkikas,)
        if exclude_id is not None:
            query += " AND id != ?"
            params += (exclude_id,)
        return c.execute(query, params).fetchone() is not None

    sel = st.session_state.selected_vair

    # 6) Redagavimo forma, jei pasirinktame esamas vairuotojas
    if sel not in (None, 0):
        df_sel = pd.read_sql_query("SELECT * FROM vairuotojai WHERE id = ?", conn, params=(sel,))
        if df_sel.empty:
            st.error("❌ Vairuotojas nerastas.")
            clear_sel()
            return
        row = df_sel.iloc[0]
        with st.form("edit_form", clear_on_submit=False):
            vardas = st.text_input("Vardas", value=row.get('vardas', ''), key="vardas")
            pavarde = st.text_input("Pavardė", value=row.get('pavarde', ''), key="pavarde")
            gim_data = st.date_input(
                "Gimimo data",
                value=date.fromisoformat(row['gimimo_metai']) if row.get('gimimo_metai') else date(1980,1,1),
                min_value=date(1950, 1, 1),
                key="gim_data"
            )
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe_index = 0
            if row.get('tautybe'):
                for idx, v in enumerate(tautybes_opts):
                    if row['tautybe'] in v:
                        tautybe_index = idx
                        break
            tautybe = st.selectbox("Tautybė", tautybes_opts, index=tautybe_index, key="tautybe")

            # 6.1) Pakeičiame etiketę „Priskirti vilkiką“ į „Priskirtas vilkikas“
            pr_vilk = st.selectbox(
                "Priskirtas vilkikas", 
                [""] + vilkikai_list,
                index=(vilkikai_list.index(row['priskirtas_vilkikas']) + 1 
                       if row.get('priskirtas_vilkikas') in vilkikai_list else 0),
                key="pr_vilk"
            )

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            error = False
            pr_vilk = st.session_state.pr_vilk

            # 6.2) Neleidžiame išsaugoti, jei vilkikas jau priskirtas kitam
            if pr_vilk:
                if vilkikas_jau_priskirtas(pr_vilk, exclude_id=sel):
                    st.error("❌ Šis vilkikas jau priskirtas kitam vairuotojui!")
                    error = True
            if not st.session_state.vardas or not st.session_state.pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
                error = True

            if not error:
                try:
                    c.execute(
                        "UPDATE vairuotojai SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?, priskirtas_vilkikas=? WHERE id=?",
                        (
                            st.session_state.vardas,
                            st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else '',
                            st.session_state.tautybe.split("(")[-1][:-1] 
                                if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            pr_vilk or '',
                            sel
                        )
                    )
                    conn.commit()
                    st.success("✅ Pakeitimai išsaugoti.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # 7) Naujo vairuotojo forma
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            vardas = st.text_input("Vardas", key="vardas")
            pavarde = st.text_input("Pavardė", key="pavarde")
            gim_data = st.date_input("Gimimo data", value=date(1980,1,1), min_value=date(1950,1,1), key="gim_data")
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe = st.selectbox("Tautybė", tautybes_opts, key="tautybe")

            pr_vilk = st.selectbox("Priskirtas vilkikas", [""] + vilkikai_list, key="pr_vilk")

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti vairuotoją")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            error = False
            pr_vilk = st.session_state.pr_vilk

            # 7.1) Neleidžiame priskirti vilkiko, jei jis jau priskirtas kitam
            if pr_vilk:
                if vilkikas_jau_priskirtas(pr_vilk):
                    st.error("❌ Šis vilkikas jau priskirtas kitam vairuotojui!")
                    error = True
            if not st.session_state.vardas or not st.session_state.pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
                error = True

            if not error:
                try:
                    c.execute(
                        "INSERT INTO vairuotojai(vardas, pavarde, gimimo_metai, tautybe, priskirtas_vilkikas) VALUES(?,?,?,?,?)",
                        (
                            st.session_state.vardas,
                            st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else '',
                            st.session_state.tautybe.split("(")[-1][:-1] 
                                if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            pr_vilk or ''
                        )
                    )
                    conn.commit()
                    st.success("✅ Vairuotojas įrašytas.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # 8) Vairuotojų sąrašas
    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    if df.empty:
        st.info("ℹ️ Nėra vairuotojų.")
        return

    # 8.1) Virš sąrašo perkeliame mygtuką „Pridėti vairuotoją“
    st.button("➕ Pridėti vairuotoją", on_click=new, use_container_width=False)

    # 8.2) Paruošiame duomenų rėmelį rodymui, visi None/NaN → ''
    df = df.fillna('')
    df_disp = df.copy()
    df_disp.rename(
        columns={
            'gimimo_metai': 'Gimimo data',
            'priskirtas_vilkikas': 'Priskirtas vilkikas',
            'tautybe': 'Tautybė'
        },
        inplace=True
    )

    # 8.3) Filtravimo laukai paliekami
    filter_cols = st.columns(len(df_disp.columns) + 1)
    for i, col in enumerate(df_disp.columns):
        filter_cols[i].text_input(col, key=f"f_{col}")
    filter_cols[-1].write("")

    df_filt = df_disp.copy()
    for col in df_disp.columns:
        val = st.session_state.get(f"f_{col}", "")
        if val:
            df_filt = df_filt[df_filt[col].astype(str).str.contains(val, case=False, na=False)]

    # 8.4) Lentelės antraštė
    hdr = st.columns(len(df_filt.columns) + 1)
    for i, col in enumerate(df_filt.columns):
        hdr[i].markdown(f"**{col}**")
    hdr[-1].markdown("**Veiksmai**")

    # 8.5) Lentelės eilutės su mygtuku redagavimui
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

    # 8.6) Eksportas į CSV
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label="💾 Eksportuoti kaip CSV",
        data=csv,
        file_name="vairuotojai.csv",
        mime="text/csv"
    )
