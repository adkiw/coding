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
    # 1) Užtikrinkime, kad lentelėje 'vairuotojai' egzistuotų visi reikalingi stulpeliai
    existing = [r[1] for r in c.execute("PRAGMA table_info(vairuotojai)").fetchall()]
    extras = {
        "vardas": "TEXT",
        "pavarde": "TEXT",
        "gimimo_metai": "TEXT",
        "tautybe": "TEXT",
        "kadencijos_pabaiga": "TEXT",
        "atostogu_pabaiga": "TEXT",
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE vairuotojai ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Surenkame priskyrimus iš 'vilkikai' modulio:
    #    sudarome žodyną driver_to_vilk, kad vardas+pavardė → vilkiko numeris
    driver_to_vilk = {}
    for numeris, drv_str in c.execute("SELECT numeris, vairuotojai FROM vilkikai").fetchall():
        if drv_str:
            for name in drv_str.split(", "):
                driver_to_vilk[name] = numeris

    # 3) Inicijuojame sesijos būseną
    if "selected_vair" not in st.session_state:
        st.session_state.selected_vair = None

    def clear_sel():
        st.session_state.selected_vair = None

    def new_vair():
        st.session_state.selected_vair = 0

    def edit_vair(id):
        st.session_state.selected_vair = id

    sel = st.session_state.selected_vair

    # 4) Redagavimo forma (kai pasirinktas esamas vairuotojas)
    if sel not in (None, 0):
        df_sel = pd.read_sql_query(
            "SELECT * FROM vairuotojai WHERE id = ?", conn, params=(sel,)
        )
        if df_sel.empty:
            st.error("❌ Vairuotojas nerastas.")
            clear_sel()
            return

        row = df_sel.iloc[0]
        full_name = f"{row['vardas']} {row['pavarde']}"
        is_assigned = full_name in driver_to_vilk

        with st.form("edit_form", clear_on_submit=False):
            # --- Pagrindiniai laukai ---
            vardas = st.text_input(
                "Vardas",
                value=row.get("vardas", ""),
                key="vardas"
            )
            pavarde = st.text_input(
                "Pavardė",
                value=row.get("pavarde", ""),
                key="pavarde"
            )
            gim_data = st.date_input(
                "Gimimo data",
                value=(
                    date.fromisoformat(row["gimimo_metai"])
                    if row.get("gimimo_metai") else date(1980, 1, 1)
                ),
                min_value=date(1950, 1, 1),
                key="gim_data"
            )
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe_index = 0
            if row.get("tautybe"):
                for idx, v in enumerate(tautybes_opts):
                    if row["tautybe"] in v:
                        tautybe_index = idx
                        break
            tautybe = st.selectbox(
                "Tautybė",
                tautybes_opts,
                index=tautybe_index,
                key="tautybe"
            )

            # --- Kadencijos pabaigos laukas: tik jei vairuotojas priskirtas ---
            if is_assigned:
                kad_initial = (
                    date.fromisoformat(row["kadencijos_pabaiga"])
                    if row.get("kadencijos_pabaiga") else date.today()
                )
                kad_pab = st.date_input(
                    "Kadencijos pabaiga",
                    value=kad_initial,
                    key="kad_pab"
                )
            else:
                kad_pab = None

            # --- Atostogų pabaigos laukas: tik jei vairuotojas nepriskirtas ---
            if not is_assigned:
                atost_initial = (
                    date.fromisoformat(row["atostogu_pabaiga"])
                    if row.get("atostogu_pabaiga") else date.today()
                )
                atost_pab = st.date_input(
                    "Atostogų pabaiga",
                    value=atost_initial,
                    key="atost_pab"
                )
            else:
                atost_pab = None

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            error = False
            if not st.session_state.vardas or not st.session_state.pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
                error = True

            # Jei dabar priskirtas, neturi būti pildoma atostogų pabaiga
            if is_assigned and st.session_state.get("atost_pab"):
                st.error("❌ Negalite nurodyti atostogų pabaigos, kai vairuotojas priskirtas vilkikui.")
                error = True

            # Jei dabar nepriskirtas, neturi būti pildoma kadencijos pabaiga
            if not is_assigned and st.session_state.get("kad_pab"):
                st.error("❌ Negalite nurodyti kadencijos pabaigos, kai vairuotojas nepriskirtas vilkikui.")
                error = True

            if not error:
                try:
                    # Jeigu priskirtas: įrašome tik kadencijos_pabaiga, atostogu_pabaiga išvalome
                    if is_assigned:
                        kad_str = st.session_state.kad_pab.isoformat() if st.session_state.kad_pab else ""
                        atost_str = ""
                    else:
                        # Jeigu nepriskirtas: įrašome tik atostogu_pabaiga, kadencijos_pabaiga išvalome
                        atost_str = st.session_state.atost_pab.isoformat() if st.session_state.atost_pab else ""
                        kad_str = ""

                    c.execute(
                        """
                        UPDATE vairuotojai
                        SET vardas = ?, pavarde = ?, gimimo_metai = ?, tautybe = ?, 
                            kadencijos_pabaiga = ?, atostogu_pabaiga = ?
                        WHERE id = ?
                        """,
                        (
                            st.session_state.vardas,
                            st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else "",
                            st.session_state.tautybe.split("(")[-1][:-1]
                                if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            kad_str,
                            atost_str,
                            sel
                        )
                    )
                    conn.commit()
                    st.success("✅ Pakeitimai išsaugoti.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # 5) Naujo vairuotojo forma (visada nepriskirtas → rodom tik atostogų pabaiga)
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            vardas = st.text_input("Vardas", key="vardas")
            pavarde = st.text_input("Pavardė", key="pavarde")
            gim_data = st.date_input(
                "Gimimo data",
                value=date(1980, 1, 1),
                min_value=date(1950, 1, 1),
                key="gim_data"
            )
            tautybes_opts = [f"{name} ({code})" for name, code in TAUTYBES]
            tautybe = st.selectbox("Tautybė", tautybes_opts, key="tautybe")

            # Naujam vairuotojui rodome tik "Atostogų pabaiga"
            atost_pab = st.date_input(
                "Atostogų pabaiga",
                value=date.today(),
                key="atost_pab"
            )

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti vairuotoją")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            error = False
            if not st.session_state.vardas or not st.session_state.pavarde:
                st.warning("⚠️ Privalomi laukai: vardas ir pavardė.")
                error = True

            if not error:
                try:
                    # Įrašome: atostogu_pabaiga = įvesta data, kadencijos_pabaiga = tuščia
                    c.execute(
                        """
                        INSERT INTO vairuotojai(
                            vardas, pavarde, gimimo_metai, tautybe,
                            kadencijos_pabaiga, atostogu_pabaiga
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            st.session_state.vardas,
                            st.session_state.pavarde,
                            st.session_state.gim_data.isoformat() if st.session_state.gim_data else "",
                            st.session_state.tautybe.split("(")[-1][:-1]
                                if "(" in st.session_state.tautybe else st.session_state.tautybe,
                            "",
                            st.session_state.atost_pab.isoformat() if st.session_state.atost_pab else ""
                        )
                    )
                    conn.commit()
                    st.success("✅ Vairuotojas įrašytas.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # 6) Vairuotojų sąrašas
    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    if df.empty:
        st.info("ℹ️ Nėra vairuotojų.")
        return

    # 6.1) Mygtukas „➕ Pridėti vairuotoją“ per visą plotį, prieš filtrus
    st.button("➕ Pridėti vairuotoją", on_click=new_vair, use_container_width=True)

    # 6.2) Paruošiame duomenis rodymui: lieka 'id', pildome None → ''
    df = df.fillna("")
    df_disp = df[[
        "id", "vardas", "pavarde", "gimimo_metai", "tautybe",
        "kadencijos_pabaiga", "atostogu_pabaiga"
    ]].copy()
    df_disp.rename(
        columns={
            "vardas": "Vardas",
            "pavarde": "Pavardė",
            "gimimo_metai": "Gimimo data",
            "tautybe": "Tautybė",
            "kadencijos_pabaiga": "Kadencijos pabaiga",
            "atostogu_pabaiga": "Atostogų pabaiga"
        },
        inplace=True,
    )

    # 6.3) Atnaujiname „Kadencijos pabaiga“ ir „Atostogų pabaiga“ rodinius pagal priskyrimą
    kad_vals = []
    atost_vals = []
    for _, row in df.iterrows():
        name = f"{row['vardas']} {row['pavarde']}"
        assigned_vilk = driver_to_vilk.get(name)
        if assigned_vilk:
            # Priskirtas → rodyti kadencijos pabaigą arba „trūksta datos“
            kad_date = row.get("kadencijos_pabaiga", "")
            kad_vals.append(kad_date if kad_date else "trūksta datos")
            atost_vals.append("")  # atostogų pabaiga visada tuščia, kai priskirtas
        else:
            # Nepriskirtas → rodyti atostogų pabaigą arba „trūksta datos“
            atost_date = row.get("atostogu_pabaiga", "")
            atost_vals.append(atost_date if atost_date else "trūksta datos")
            kad_vals.append("")  # kadencijos pabaiga visada tuščia, kai nepriskirtas

    df_disp["Kadencijos pabaiga"] = kad_vals
    df_disp["Atostogų pabaiga"] = atost_vals

    # 6.4) Pridedame stulpelį „Priskirtas vilkikas“
    assigned = []
    for _, row in df.iterrows():
        name = f"{row['vardas']} {row['pavarde']}"
        assigned.append(driver_to_vilk.get(name, ""))
    df_disp["Priskirtas vilkikas"] = assigned

    # 6.5) FILTRAVIMO LAUKAI be antraščių virš jų (tik placeholder)
    filter_cols = st.columns(len(df_disp.columns) + 1)
    for i, col in enumerate(df_disp.columns):
        filter_cols[i].text_input(label="", placeholder=col, key=f"f_{col}")
    filter_cols[-1].write("")  # papildomas tuščias stulpelis filtrui

    df_filt = df_disp.copy()
    for col in df_disp.columns:
        val = st.session_state.get(f"f_{col}", "")
        if val:
            # Naudojame prefix matching (startswith) vietoje substring:
            df_filt = df_filt[
                df_filt[col].astype(str).str.lower().str.startswith(val.lower())
            ]

    # 6.6) **PAŠALINTA: header blokas po filtrų**, kad nebūtų dubliuojama.

    # 6.7) Lentelės eilutės su redagavimo mygtuku
    for _, row in df_filt.iterrows():
        row_cols = st.columns(len(df_filt.columns) + 1)
        for i, col in enumerate(df_filt.columns):
            row_cols[i].write(row[col])
        row_cols[-1].button(
            "✏️",
            key=f"edit_{row['id']}",
            on_click=edit_vair,
            args=(row["id"],),
        )

    # 6.8) Eksportas į CSV
    csv = df.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="💾 Eksportuoti kaip CSV",
        data=csv,
        file_name="vairuotojai.csv",
        mime="text/csv",
    )
