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

    # 2) Gather data for dropdowns
    kroviniai = [r[0] for r in c.execute("SELECT numeris FROM kroviniai").fetchall()]
    vairuotoju_list = [f"{r[1]} {r[2]}" for r in c.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()]

    vadybininku_list = [
        r[0]
        for r in c.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?", 
            ("Transporto vadybininkas",)
        ).fetchall()
    ]
    vadybininku_dropdown = [""] + vadybininku_list  # pirmas - tuščias

    priekabu_list = [f"{r[0]}" for r in c.execute("SELECT numeris FROM priekabos").fetchall()]

    # Callbacks for clearing or initializing selection
    def clear_selection():
        st.session_state.selected_vilk = None
        for key in list(st.session_state):
            if key.startswith("f_"):
                st.session_state[key] = ""
    def new_vilk():
        st.session_state.selected_vilk = 0
    def edit_vilk(numeris):
        st.session_state.selected_vilk = numeris

    # 3) Title and Add button
    col_title, col_add = st.columns([9, 1])
    col_title.title("DISPO – Vilkikų valdymas")
    col_add.button("➕ Pridėti naują vilkiką", on_click=new_vilk)

    # 4) Initialize session state
    if 'selected_vilk' not in st.session_state:
        st.session_state.selected_vilk = None

    # 5) Bendras priekabų priskirstymas (above list)
    st.markdown("### 🔄 Bendras priekabų priskirstymas")
    if st.session_state.selected_vilk is None:
        # List all vilkikai
        df = pd.DataFrame(c.execute("SELECT numeris, marke, pagaminimo_metai FROM vilkikai").fetchall(),
                          columns=["Numeris", "Markė", "Pagaminimo metai"])
        st.dataframe(df)

    # 6) Form for adding/editing a vilkikas
    if st.session_state.selected_vilk is not None:
        is_new = (st.session_state.selected_vilk == 0)
        if is_new:
            vilk = {"numeris": "", "marke": "", "pagaminimo_metai": "", "tech_apziura": "", "draudimas": "", "vadybininkas": "", "vairuotojai": "", "priekaba": ""}
        else:
            row = c.execute("SELECT numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba FROM vilkikai WHERE numeris = ?", 
                            (st.session_state.selected_vilk,)).fetchone()
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

        with st.form(key="vilk_form"):
            col1, col2 = st.columns(2)
            numeris = col1.text_input("Numeris", value=vilk["numeris"])
            marke = col1.text_input("Markė", value=vilk["marke"])
            pag_metai = col1.number_input("Pagaminimo metai", min_value=1900, max_value=date.today().year,
                                          value=vilk["pagaminimo_metai"] or date.today().year, step=1)

            tech_date = col2.date_input("Techninė apžiūra", 
                                        value=date.fromisoformat(vilk["tech_apziura"]) if vilk["tech_apziura"] else None)
            draud_date = col2.date_input("Draudimo galiojimas", 
                                         value=date.fromisoformat(vilk["draudimas"]) if vilk["draudimas"] else None)

            # Dropdown for transporto vadybininkas (now only vardas)
            if not is_new and vilk.get("vadybininkas", "") in vadybininku_list:
                vadyb_idx = vadybininku_dropdown.index(vilk["vadybininkas"])
            else:
                vadyb_idx = 0
            vadyb = col2.selectbox(
                "Transporto vadybininkas",
                vadybininku_dropdown,
                index=vadyb_idx
            )

            # Dropdown for vairuotojai (first two slots)
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

            # Dropdown for priekaba
            prk_opts = [""] + priekabu_list
            prk_idx = 0
            if not is_new and vilk["priekaba"] in priekabu_list:
                prk_idx = prk_opts.index(vilk["priekaba"])
            prk = col2.selectbox("Priekaba", prk_opts, index=prk_idx)

            # Submit and Cancel buttons
            submit_btn = st.form_submit_button("💾 Išsaugoti")
            cancel_btn = st.form_submit_button("✖ Atšaukti")

            if cancel_btn:
                clear_selection()
                st.experimental_rerun()

            if submit_btn:
                try:
                    if is_new:
                        c.execute(
                            "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (
                                numeris,
                                marke or None,
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
                            "UPDATE vilkikai SET marke = ?, pagaminimo_metai = ?, tech_apziura = ?, draudimas = ?, vadybininkas = ?, vairuotojai = ?, priekaba = ? WHERE numeris = ?",
                            (
                                marke or None,
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
                    if tech_date:
                        st.info(f"🔧 Dienų iki tech. apžiūros liko: {(tech_date - date.today()).days}")
                    if draud_date:
                        st.info(f"🛡️ Dienų iki draudimo pabaigos liko: {(draud_date - date.today()).days}")
                    clear_selection()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Klaida saugant: {e}")

    # 7) Edit buttons in list
    if st.session_state.selected_vilk is None:
        df_list = pd.DataFrame(c.execute(
            "SELECT numeris, marke, pagaminimo_metai, vadybininkas, priekaba FROM vilkikai"
        ).fetchall(), columns=["Numeris", "Markė", "Pagaminimo metai", "Vadybininkas", "Priekaba"])
        df_list["✏️"] = df_list["Numeris"].apply(lambda x: f"edit_{x}")
        for idx, row in df_list.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 2, 2, 2, 1])
            col1.write(row["Numeris"])
            col2.write(row["Markė"])
            col3.write(row["Pagaminimo metai"])
            col4.write(row["Vadybininkas"])
            col5.write(row["Priekaba"])
            if col6.button("✏️", key=row["✏️"]):
                edit_vilk(row["Numeris"])

    # 8) Delete functionality (optional)
    #    Can add a delete button next to each row if needed

# End of modules/vilkikai.py
