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
    st.title("DISPO – Vairuotojai")

    existing = [r[1] for r in c.execute("PRAGMA table_info(vairuotojai)").fetchall()]
    extras = {
        'vardas': 'TEXT',
        'pavarde': 'TEXT',
        'gimimo_metai': 'TEXT',
        'tautybe': 'TEXT',
        'priskirtas_vilkikas': 'TEXT',
        'kadencijos_pabaiga': 'TEXT',
        'atostogu_pabaiga': 'TEXT',
        'kaip_mokinys': 'TEXT'
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE vairuotojai ADD COLUMN {col} {typ}")
    conn.commit()

    vilkikai_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]

    if 'selected_vair' not in st.session_state:
        st.session_state.selected_vair = None

    def clear_sel():
        st.session_state.selected_vair = None
        # Formos laukelių nevalyti – Streamlit jau išlaiko values pagal key

    def new(): st.session_state.selected_vair = 0
    def edit(id): st.session_state.selected_vair = id

    col_title, col_add = st.columns([9,1])
    col_title.write("### ")
    col_add.button("➕ Pridėti vairuotoją", on_click=new)

    sel = st.session_state.selected_vair

    def vilkikas_jau_priskirtas(vilkikas, exclude_id=None, kaip_laukas='priskirtas_vilkikas'):
        if not vilkikas:
            return False
        query = f"SELECT id FROM vairuotojai WHERE {kaip_laukas} = ?"
        params = (vilkikas,)
        if exclude_id is not None:
            query += " AND id != ?"
            params += (exclude_id,)
        return c.execute(query, params).fetchone() is not None

    # Edit existing
    if sel not in (None, 0):
        df_sel = pd.read_sql_query("SELECT * FROM vairuotojai WHERE id = ?", conn, params=(sel,))
        if df_sel.empty:
            st.error("❌ Vairuotojas nerastas.")
            clear_sel()
            return
        row = df_sel.iloc[0]
        with st.form("edit_form", clear_on_submit=False):
            vardas = st.text_input("Vardas", value=row['vardas'], key="vardas")
            pavarde = st.text_input("Pavardė", value=row['pavarde'], key="pavarde")
            gim_data = st.date_input(
                "Gimimo data",
                value=date.fromisoformat(row['gimimo_metai']) if row['gimimo_metai'] else date(1980,1,1),
                min_value=date(1950, 1, 1),
                key="gim_data"
            )
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe_index = 0
            if row['tautybe']:
                for idx, v in enumerate(tautybes_opts):
                    if row['tautybe'] in v: tautybe_index = idx; break
            tautybe = st.selectbox("Tautybė", tautybes_opts, index=tautybe_index, key="tautybe")
            pr_vilk = st.selectbox(
                "Priskirti vilkiką", [""] + vilkikai_list,
                index=(vilkikai_list.index(row['priskirtas_vilkikas'])+1 if row['priskirtas_vilkikas'] in vilkikai_list else 0),
                key="pr_vilk"
            )
            kaip_mokinys = st.selectbox(
                "Kaip mokinys", [""] + vilkikai_list,
                index=(vilkikai_list.index(row['kaip_mokinys'])+1 if row['kaip_mokinys'] in vilkikai_list else 0),
                key="kaip_mokinys"
            )
            kadencijos_pabaiga, atostogu_pabaiga = None, None
            if st.session_state.pr_vilk:
                kadencijos_pabaiga = st.date_input(
                    "Kadencijos pabaigos planas",
                    value=(date.fromisoformat(row['kadencijos_pabaiga']) if row['kadencijos_pabaiga'] else date.today()),
                    key="kad_pab"
                )
            else:
                atostogu_pabaiga = st.date_input(
                    "Atostogų pabaigos planas",
                    value=(date.fromisoformat(row['atostogu_pabaiga']) if row['atostogu_pabaiga'] else date.today()),
                    key="atost_pab"
                )
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)
        if save:
            error = False
            pr_vilk = st.session_state.pr_vilk
            kaip_mokinys = st.session_state.kaip_mokinys
            if pr_vilk:
                if vilkikas_jau_priskirtas(pr_vilk, exclude_id=sel, kaip_laukas='priskirtas_vilkikas'):
                    st.error("❌ Šis vilkikas jau priskirtas kitam pagrindiniam vairuotojui!")
                    error = True
            if kaip_mokinys:
                if vilkikas_jau_priskirtas(kaip_mokinys, exclude_id=sel, kaip_laukas='kaip_mokinys'):
                    st.error("❌ Šis vilkikas jau pasirinktas kitam vairuotojui kaip mokinio vilkikas!")
                    error = True
            if pr_vilk and kaip_mokinys and pr_vilk == kaip_mokinys:
                st.error("❌ Negalima pasirinkti to paties vilkiko abiem laukams!")
                error = True
            if not error:
                try:
                    c.execute(
                        "UPDATE vairuotojai SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?, priskirtas_vilkikas=?, kaip_mokinys=?, kadencijos_pabaiga=?, atostogu_pabaiga=? WHERE id=?",
                        (
                            st.session_state.vardas, st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else None,
                            st.session_state.tautybe.split("(")[-1][:-1] if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            pr_vilk, kaip_mokinys,
                            st.session_state.kad_pab.isoformat() if pr_vilk else None,
                            st.session_state.atost_pab.isoformat() if not pr_vilk else None,
                            sel
                        )
                    )
                    conn.commit()
                    st.success("✅ Pakeitimai išsaugoti.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # New form
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            vardas = st.text_input("Vardas", key="vardas")
            pavarde = st.text_input("Pavardė", key="pavarde")
            gim_data = st.date_input("Gimimo data", value=date(1980,1,1), min_value=date(1950,1,1), key="gim_data")
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe = st.selectbox("Tautybė", tautybes_opts, key="tautybe")
            pr_vilk = st.selectbox("Priskirti vilkiką", [""] + vilkikai_list, key="pr_vilk")
            kaip_mokinys = st.selectbox("Kaip mokinys", [""] + vilkikai_list, key="kaip_mokinys")
            kadencijos_pabaiga, atostogu_pabaiga = None, None
            if pr_vilk:
                kadencijos_pabaiga = st.date_input("Kadencijos pabaigos planas", value=date.today(), key="kad_pab")
            else:
                atostogu_pabaiga = st.date_input("Atostogų pabaigos planas", value=date.today(), key="atost_pab")
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti vairuotoją")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            error = False
            if pr_vilk:
                if vilkikas_jau_priskirtas(pr_vilk, kaip_laukas='priskirtas_vilkikas'):
                    st.error("❌ Šis vilkikas jau priskirtas kitam pagrindiniam vairuotojui!")
                    error = True
            if kaip_mokinys:
                if vilkikas_jau_priskirtas(kaip_mokinys, kaip_laukas='kaip_mokinys'):
                    st.error("❌ Šis vilkikas jau pasirinktas kitam vairuotojui kaip mokinio vilkikas!")
                    error = True
            if pr_vilk and kaip_mokinys and pr_vilk == kaip_mokinys:
                st.error("❌ Negalima pasirinkti to paties vilkiko abiem laukams!")
                error = True
            if not st.session_state.vardas or not st.session_state.pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
                error = True
            if not error:
                try:
                    c.execute(
                        "INSERT INTO vairuotojai(vardas, pavarde, gimimo_metai, tautybe, priskirtas_vilkikas, kaip_mokinys, kadencijos_pabaiga, atostogu_pabaiga) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            st.session_state.vardas, st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else None,
                            st.session_state.tautybe.split("(")[-1][:-1] if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            pr_vilk, kaip_mokinys,
                            st.session_state.kad_pab.isoformat() if pr_vilk else None,
                            st.session_state.atost_pab.isoformat() if not pr_vilk else None
                        )
                    )
                    conn.commit()
                    st.success("✅ Vairuotojas įrašytas.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    st.subheader("📋 Vairuotojų sąrašas")
    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    if df.empty:
        st.info("ℹ️ Nėra vairuotojų.")
        return
    df_disp = df.copy()
    df_disp.rename(
        columns={
            'gimimo_metai': 'Gimimo data',
            'priskirtas_vilkikas': 'Priskirti vilkiką',
            'kadencijos_pabaiga': 'Kadencijos pabaiga',
            'atostogu_pabaiga': 'Atostogų pabaiga',
            'kaip_mokinys': 'Kaip mokinys',
            'tautybe': 'Tautybė'
        },
        inplace=True
    )
    statusas = []
    for _, row in df.iterrows():
        mok_vilk = row.get('kaip_mokinys', "")
        if mok_vilk:
            res = c.execute("SELECT COUNT(*) FROM vairuotojai WHERE priskirtas_vilkikas = ?", (mok_vilk,)).fetchone()
            if res and res[0] == 0:
                statusas.append("⚠️ Nėra pagrindinio vairuotojo")
            else:
                statusas.append("")
        else:
            statusas.append("")
    df_disp["Įspėjimas"] = statusas

    filter_cols = st.columns(len(df_disp.columns)+1)
    for i, col in enumerate(df_disp.columns):
        filter_cols[i].text_input(col, key=f"f_{col}")
    filter_cols[-1].write("")
    df_filt = df_disp.copy()
    for col in df_disp.columns:
        val = st.session_state.get(f"f_{col}", "")
        if val:
            df_filt = df_filt[df_filt[col].astype(str).str.contains(val, case=False, na=False)]
    hdr = st.columns(len(df_filt.columns)+1)
    for i, col in enumerate(df_filt.columns): hdr[i].markdown(f"**{col}**")
    hdr[-1].markdown("**Veiksmai**")
    for _, row in df_filt.iterrows():
        row_cols = st.columns(len(df_filt.columns)+1)
        for i, col in enumerate(df_filt.columns): row_cols[i].write(row[col])
        row_cols[-1].button("✏️", key=f"edit_{row['id']}", on_click=edit, args=(row['id'],))
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(label="💾 Eksportuoti kaip CSV", data=csv, file_name="vairuotojai.csv", mime="text/csv")
