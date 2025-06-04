import streamlit as st
import pandas as pd
from datetime import date

def show(conn, c):
    # 1) Ensure needed columns exist
    existing = [r[1] for r in c.execute("PRAGMA table_info(vilkikai)").fetchall()]
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
        if col not in existing:
            c.execute(f"ALTER TABLE vilkikai ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Dropdown data
    priekabu_list = [r[0] for r in c.execute("SELECT numeris FROM priekabos").fetchall()]
    markiu_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = 'Markė'").fetchall()]
    vairuotoju_list = [f"{r[1]} {r[2]}" for r in c.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()]

    vadybininku_list = [
        f"{r[0]} {r[1]}"
        for r in c.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?", 
            ("Transporto vadybininkas",)
        ).fetchall()
    ]
    vadybininku_dropdown = [""] + vadybininku_list  # pirmas - tuščias

    # Callbacks
    def clear_selection():
        st.session_state.selected_vilk = None
        for key in list(st.session_state):
            if key.startswith("f_"):
                st.session_state[key] = ""
    def new_vilk(): st.session_state.selected_vilk = 0
    def edit_vilk(numeris): st.session_state.selected_vilk = numeris

    # 3) Title and Add button
    col_title, col_add = st.columns([9, 1])
    col_title.title("DISPO – Vilkikų valdymas")
    col_add.button("➕ Pridėti naują vilkiką", on_click=new_vilk)

    # 4) Initialize session state
    if 'selected_vilk' not in st.session_state:
        st.session_state.selected_vilk = None

    # 5) Bendras priekabų priskirstymas (above list)
    st.markdown("### 🔄 Bendras priekabų priskirstymas")
    with st.form("priekabu_priskirt_forma", clear_on_submit=True):
        vilk_list = [""] + [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        pr_opts = [""]
        for num in priekabu_list:
            assigned = [r[0] for r in c.execute("SELECT numeris FROM vilkikai WHERE priekaba = ?", (num,)).fetchall()]
            pr_opts.append(
                f"🔴 {num} ({', '.join(assigned)})" if assigned else f"🟢 {num} (laisva)"
            )
        sel_vilk = st.selectbox("Pasirinkite vilkiką", vilk_list)
        sel_priek = st.selectbox("Pasirinkite priekabą", pr_opts)
        upd = st.form_submit_button("💾 Išsaugoti")
    if upd and sel_vilk:
        # Tikrinimas: ar yra bent du split elementai
        prn = None
        if sel_priek and (sel_priek.startswith("🟢") or sel_priek.startswith("🔴")):
            split = sel_priek.split()
            if len(split) > 1:
                prn = split[1]
        c.execute("UPDATE vilkikai SET priekaba = ? WHERE numeris = ?", (prn, sel_vilk))
        conn.commit()
        st.success(f"✅ Priekaba {prn or '(tuščia)'} priskirta {sel_vilk}.")

    # 6) List view
    if st.session_state.selected_vilk is None:
        df = pd.read_sql_query("SELECT * FROM vilkikai ORDER BY tech_apziura ASC", conn)
        if df.empty:
            st.info("🔍 Kol kas nėra vilkikų.")
            return

        # Prepare display DataFrame
        df_disp = df.copy()
        df_disp.rename(columns={'marke': 'Modelis',
                                 'pagaminimo_metai': 'Pirmos registracijos data'},
                       inplace=True)
        drivers = df_disp.get('vairuotojai', pd.Series(dtype=str)).fillna('')
        drivers_df = drivers.str.split(', ', n=1, expand=True)
        if 1 not in drivers_df:
            drivers_df[1] = None
        df_disp['Vairuotojas 1'] = drivers_df[0]
        df_disp['Vairuotojas 2'] = drivers_df[1]
        df_disp.drop(columns=['vairuotojai'], inplace=True)
        df_disp.rename(columns={'vadybininkas': 'Transporto vadybininkas'}, inplace=True)
        df_disp['Liko iki tech apžiūros'] = df_disp['tech_apziura'].apply(
            lambda x: (date.fromisoformat(x) - date.today()).days if x else None)
        df_disp['Liko iki draudimo'] = df_disp['draudimas'].apply(
            lambda x: (date.fromisoformat(x) - date.today()).days if x else None)

        filter_cols = st.columns(len(df_disp.columns) + 1)
        for i, col in enumerate(df_disp.columns):
            filter_cols[i].text_input(col, key=f"f_{col}")
        filter_cols[-1].write("")
        df_filt = df_disp.copy()
        for col in df_disp.columns:
            val = st.session_state.get(f"f_{col}", "")
            if val:
                df_filt = df_filt[df_filt[col].astype(str).str.contains(val, case=False, na=False)]

        hdr = st.columns(len(df_filt.columns) + 1)
        for i, col in enumerate(df_filt.columns): hdr[i].markdown(f"**{col}**")
        hdr[-1].markdown("**Veiksmai**")
        for _, row in df_filt.iterrows():
            row_cols = st.columns(len(df_filt.columns) + 1)
            for i, col in enumerate(df_filt.columns): row_cols[i].write(row[col])
            row_cols[-1].button("✏️", key=f"edit_{row['numeris']}", on_click=edit_vilk, args=(row['numeris'],))

        csv = df.to_csv(index=False, sep=';').encode('utf-8')
        st.download_button(label="💾 Eksportuoti kaip CSV", data=csv, file_name="vilkikai.csv", mime="text/csv")
        return

    # 7) Detail / New form view
    sel = st.session_state.selected_vilk
    is_new = (sel == 0)
    vilk = {}
    if not is_new:
        df_v = pd.read_sql_query("SELECT * FROM vilkikai WHERE numeris = ?", conn, params=(sel,))
        if df_v.empty:
            st.error("❌ Vilkikas nerastas.")
            clear_selection()
            return
        vilk = df_v.iloc[0]

    with st.form("vilkiku_forma", clear_on_submit=False):
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Vilkiko numeris", value=("" if is_new else vilk['numeris']))
        opts_m = [""] + markiu_list
        idx_m = 0 if is_new or vilk.get('marke') not in markiu_list else opts_m.index(vilk['marke'])
        modelis = col1.selectbox("Modelis", opts_m, index=idx_m)
        pr_initial = (date.fromisoformat(vilk['pagaminimo_metai'])
                      if not is_new and vilk['pagaminimo_metai'] else None)
        pr_data = col1.date_input("Pirmos registracijos data", value=pr_initial, key="pr_data")
        tech_initial = (date.fromisoformat(vilk['tech_apziura'])
                        if not is_new and vilk['tech_apziura'] else None)
        tech_date = col1.date_input("Tech. apžiūros pabaiga", value=tech_initial, key="tech_date")
        draud_initial = (date.fromisoformat(vilk['draudimas'])
                         if not is_new and vilk['draudimas'] else None)
        draud_date = col1.date_input("Draudimo galiojimo pabaiga", value=draud_initial, key="draud_date")

        # Transporto vadybininkas su dropdown
        if not is_new and vilk.get('vadybininkas', "") in vadybininku_list:
            vadyb_idx = vadybininku_dropdown.index(vilk['vadybininkas'])
        else:
            vadyb_idx = 0
        vadyb = col2.selectbox(
            "Transporto vadybininkas",
            vadybininku_dropdown,
            index=vadyb_idx
        )

        v1_opts = [""] + vairuotoju_list
        v1_idx, v2_idx = 0, 0
        if not is_new and vilk['vairuotojai']:
            parts = vilk['vairuotojai'].split(', ')
            if parts and parts[0] in vairuotoju_list: v1_idx = v1_opts.index(parts[0])
            if len(parts)>1 and parts[1] in vairuotoju_list: v2_idx = v1_opts.index(parts[1])
        v1 = col2.selectbox("Vairuotojas 1", v1_opts, index=v1_idx, key="v1")
        v2 = col2.selectbox("Vairuotojas 2", v1_opts, index=v2_idx, key="v2")
        pr_opts = [""]
        for num in priekabu_list:
            assigned = [r[0] for r in c.execute("SELECT numeris FROM vilkikai WHERE priekaba = ?", (num,)).fetchall()]
            pr_opts.append(
                f"🔴 {num} ({', '.join(assigned)})" if assigned else f"🟢 {num} (laisva)"
            )
        pr_idx = 0
        if not is_new and vilk['priekaba']:
            for i, opt in enumerate(pr_opts):
                split = opt.split()
                if len(split) > 1 and split[1] == vilk['priekaba']:
                    pr_idx = i
                    break
        sel_pr = col2.selectbox("Priekaba", pr_opts, index=pr_idx)

        back = st.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_selection)
        submit = st.form_submit_button("📅 Išsaugoti vilkiką")

    if submit:
        if not numeris:
            st.warning("⚠️ Įveskite vilkiko numerį.")
        else:
            draud = ", ".join(filter(None, [v1, v2])) or None
            prn = None
            if sel_pr and (sel_pr.startswith("🟢") or sel_pr.startswith("🔴")):
                split = sel_pr.split()
                if len(split) > 1:
                    prn = split[1]
            try:
                if is_new:
                    c.execute(
                        "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba)"
                        " VALUES (?,?,?,?,?,?,?,?)",
                        (numeris, modelis or None,
                         pr_data.isoformat() if pr_data else None,
                         tech_date.isoformat() if tech_date else None,
                         draud_date.isoformat() if draud_date else None,
                         vadyb or None, draud, prn)
                    )
                else:
                    c.execute(
                        "UPDATE vilkikai SET marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=?, vadybininkas=?, vairuotojai=?, priekaba=? WHERE numeris=?",
                        (modelis or None,
                         pr_data.isoformat() if pr_data else None,
                         tech_date.isoformat() if tech_date else None,
                         draud_date.isoformat() if draud_date else None,
                         vadyb or None, draud, prn, sel)
                    )
                conn.commit()
                st.success("✅ Vilkikas išsaugotas sėkmingai.")
                if tech_date:
                    st.info(f"🔧 Dienų iki tech. apžiūros liko: {(tech_date-date.today()).days}")
                if draud_date:
                    st.info(f"🛡️ Dienų iki draudimo pabaigos liko: {(draud_date-date.today()).days}")
            except Exception as e:
                st.error(f"❌ Klaida saugant: {e}")
