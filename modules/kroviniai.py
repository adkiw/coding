# modules/kroviniai.py

import streamlit as st
import pandas as pd
from datetime import date

def get_vieta(salis, regionas):
    if not salis:
        return ""
    return f"{salis}{regionas or ''}"

# Pagrindinė show funkcija
def show(conn, c):
    st.title("Užsakymų valdymas")

    add_clicked = st.button("➕ Pridėti naują krovinį", use_container_width=True)

    # 1) Užtikriname, kad lentelė „kroviniai“ turi visus būtinus stulpelius
    expected = {
        'klientas': 'TEXT',
        'uzsakymo_numeris': 'TEXT',
        'pakrovimo_salis': 'TEXT',
        'pakrovimo_regionas': 'TEXT',
        'pakrovimo_miestas': 'TEXT',
        'pakrovimo_adresas': 'TEXT',
        'pakrovimo_data': 'TEXT',
        'pakrovimo_laikas_nuo': 'TEXT',
        'pakrovimo_laikas_iki': 'TEXT',
        'iskrovimo_salis': 'TEXT',
        'iskrovimo_regionas': 'TEXT',
        'iskrovimo_miestas': 'TEXT',
        'iskrovimo_adresas': 'TEXT',
        'iskrovimo_data': 'TEXT',
        'iskrovimo_laikas_nuo': 'TEXT',
        'iskrovimo_laikas_iki': 'TEXT',
        'vilkikas': 'TEXT',
        'priekaba': 'TEXT',
        'atsakingas_vadybininkas': 'TEXT',
        'ekspedicijos_vadybininkas': 'TEXT',
        'transporto_vadybininkas': 'TEXT',
        'kilometrai': 'INTEGER',
        'frachtas': 'REAL',
        'svoris': 'INTEGER',
        'paleciu_skaicius': 'INTEGER',
        'saskaitos_busena': 'TEXT',
        'busena': 'TEXT'
    }
    c.execute("PRAGMA table_info(kroviniai)")
    existing = {r[1] for r in c.fetchall()}
    for col, typ in expected.items():
        if col not in existing:
            c.execute(f"ALTER TABLE kroviniai ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Paruošiame duomenis dropdown’ams ir žemėlapius
    klientai = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
    if not klientai:
        st.warning("❗ Nėra nė vieno kliento! Pridėkite klientą modulyje **Klientai** ir grįžkite čia.")
        return

    vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
    vilkikai_df = pd.read_sql_query("SELECT numeris, vadybininkas FROM vilkikai", conn)
    vilk_vad_map = {r['numeris']: r['vadybininkas'] for _, r in vilkikai_df.iterrows()}

    eksped_vadybininkai = [
        f"{r[0]} {r[1]}"
        for r in c.execute("SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?", ("Ekspedicijos vadybininkas",)).fetchall()
    ]
    eksped_dropdown = [""] + eksped_vadybininkai

    # 3) Sukuriame map: klientas → likutinis limitas
    df_klientai = pd.read_sql_query("SELECT pavadinimas, likes_limitas FROM klientai", conn)
    klientu_limitai = {row['pavadinimas']: row['likes_limitas'] for _, row in df_klientai.iterrows()}

    # 4) Session state valdymas (kuris krovinys redaguojamas arba naujas)
    if 'selected_cargo' not in st.session_state:
        st.session_state['selected_cargo'] = None
    if add_clicked:
        st.session_state['selected_cargo'] = 0

    def clear_sel():
        st.session_state['selected_cargo'] = None
        for k in list(st.session_state):
            if k.startswith("f_") or k.startswith("kl_") or k.startswith("pk_") or k.startswith("is_") or k.startswith("vilk_"):
                st.session_state[k] = ""

    def edit_cargo(cid):
        st.session_state['selected_cargo'] = cid

    sel = st.session_state['selected_cargo']

    # 5. Sąrašas esamų krovinių (tik tuomet, kai ne redaguojame neiš naujo)
    if sel is None:
        df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
        if df.empty:
            st.info("Kol kas nėra krovinių.")
        else:
            # Sukuriame kelias papildomas stulpelių reikšmes
            df["pakrovimo_vieta"] = df.apply(
                lambda r: get_vieta(r.get('pakrovimo_salis', ''), r.get('pakrovimo_regionas', '')), axis=1
            )
            df["iskrovimo_vieta"] = df.apply(
                lambda r: get_vieta(r.get('iskrovimo_salis', ''), r.get('iskrovimo_regionas', '')), axis=1
            )
            df["transporto_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")
            df["atsakingas_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")

            # Nustatome krovinio būseną pagal paskutinį įrašą iš vilkiku_darbo_laikai
            def get_busena(c, krovinys):
                if not krovinys.get("vilkikas"):
                    return "Nesuplanuotas"
                busena = "Suplanuotas"
                r = c.execute("""
                    SELECT pakrovimo_statusas, iskrovimo_statusas
                    FROM vilkiku_darbo_laikai
                    WHERE vilkiko_numeris = ? AND data = ?
                    ORDER BY id DESC LIMIT 1
                """, (krovinys['vilkikas'], krovinys['pakrovimo_data'])).fetchone()
                if not r:
                    return busena
                pk_status, ik_status = r
                if ik_status == "Iškrauta":
                    return "Iškrauta"
                if ik_status == "Atvyko":
                    return "Atvyko į iškrovimą"
                if ik_status == "Kita" and pk_status != "Pakrauta":
                    return "Kita (iškrovimas)"
                if pk_status == "Pakrauta":
                    return "Pakrauta"
                if pk_status == "Atvyko":
                    return "Atvyko į pakrovimą"
                if pk_status == "Kita":
                    return "Kita (pakrovimas)"
                return busena

            busenos = [get_busena(c, row) for _, row in df.iterrows()]
            df["busena"] = busenos

            # Rodome lentelę filtruojamą pagal input langelius
            FIELD_ORDER = [
                "id", "busena", "pakrovimo_data", "iskrovimo_data",
                "pakrovimo_vieta", "iskrovimo_vieta",
                "klientas", "vilkikas", "priekaba", "ekspedicijos_vadybininkas",
                "transporto_vadybininkas", "atsakingas_vadybininkas",
                "uzsakymo_numeris", "kilometrai", "frachtas",
                "saskaitos_busena"
            ]
            df_disp = df[FIELD_ORDER].fillna("")

            # Filtravimo input langeliai viršuje
            filter_cols = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                filter_cols[i].text_input(
                    " ",
                    key=f"f_{col}",
                    label_visibility="collapsed"
                )
            filter_cols[-1].write("")

            df_f = df_disp.copy()
            for col in df_disp.columns:
                v = st.session_state.get(f"f_{col}", "")
                if v:
                    df_f = df_f[df_f[col].astype(str).str.contains(v, case=False, na=False)]

            # Header/antros eilutės atvaizdavimas
            HEADER_LABELS = {
                "id": "ID", "busena": "Būsena", "pakrovimo_data": "Pakr. data",
                "iskrovimo_data": "Iškr. data", "pakrovimo_vieta": "Pakr. vieta",
                "iskrovimo_vieta": "Iškr. vieta", "klientas": "Klientas",
                "vilkikas": "Vilkikas", "priekaba": "Priekaba",
                "ekspedicijos_vadybininkas": "Eksp. vadyb.",
                "transporto_vadybininkas": "Transp. vadyb.",
                "atsakingas_vadybininkas": "Atsak. vadyb.",
                "uzsakymo_numeris": "Užsak. nr.", "kilometrai": "Km",
                "frachtas": "Frachtas", "saskaitos_busena": "Sąsk. būsena"
            }

            hdr = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                label = HEADER_LABELS.get(col, col.replace("_", " ").title())
                hdr[i].markdown(f"<b>{label}</b>", unsafe_allow_html=True)
            hdr[-1].markdown("<b>Veiksmai</b>", unsafe_allow_html=True)

            # Kiekvienas krovinys – atskira eilutė su mygtuku redaguoti
            for _, row in df_f.iterrows():
                row_cols = st.columns(len(df_disp.columns) + 1)
                for i, col in enumerate(df_disp.columns):
                    row_cols[i].write(row[col])
                row_cols[-1].button(
                    "✏️",
                    key=f"edit_{row['id']}",
                    on_click=edit_cargo,
                    args=(row['id'],)
                )

            # Eksporto mygtukas CSV formatu
            st.download_button(
                "💾 Eksportuoti kaip CSV",
                data=df_disp.to_csv(index=False, sep=';').encode('utf-8'),
                file_name="kroviniai.csv",
                mime="text/csv"
            )
        return

    # 6) Dabar – arba redagavimas, arba naujas įrašas
    is_new = (sel == 0)
    data = {} if is_new else pd.read_sql_query(
        "SELECT * FROM kroviniai WHERE id=?", conn, params=(sel,)
    ).iloc[0]
    if not is_new and data.empty:
        st.error("Įrašas nerastas.")
        clear_sel()
        return

    # 7) Pateikiame formą (form_submit)
    st.markdown("### Krovinių įvedimas")
    colA, colB, colC, colD = st.columns(4)

    with st.form("cargo_form", clear_on_submit=False):
        # --- Stulpelis A: Pagrindiniai laukai ---
        opts_k = [""] + klientai
        idx_k = 0 if is_new else opts_k.index(data.get('klientas', ''))
        klientas = colA.selectbox("Klientas", opts_k, index=idx_k, key="kl_klientas")

        limito_likutis = klientu_limitai.get(klientas, "")
        if klientas:
            colA.info(f"Limito likutis: {limito_likutis}")

        uzsak = colA.text_input(
            "Užsakymo nr.",
            value=("" if is_new else data.get('uzsakymo_numeris', '')),
            key="kl_uzsak"
        )

        sask_busenos = ["Neapmokėta", "Apmokėta"]
        default_sb = sask_busenos[0] if is_new else data.get("saskaitos_busena", sask_busenos[0])
        sask_busena = colA.selectbox(
            "Sąskaitos būsena", sask_busenos,
            index=sask_busenos.index(default_sb), key="sask_busena"
        )

        # --- Stulpelis B: Pakrovimo duomenys ---
        vilk = colB.selectbox(
            "Vilkikas", [""] + vilkikai,
            index=(0 if is_new else [""] + vilkikai).index(data.get('vilkikas', "")),
            key="vilk_vilkikas"
        )
        priekaba_value = colB.text_input(
            "Priekaba", value=("" if is_new else data.get('priekaba', '')),
            key="vilk_priekaba"
        )
        colB.write("Pakrovimo vieta:")
        pk_salis = colB.text_input(
            "  Šalis (pvz. LT)", value=("" if is_new else data.get('pakrovimo_salis', '')),
            key="pk_salis"
        )
        pk_regionas = colB.text_input(
            "  Regionas (pvz. LT01)", value=("" if is_new else data.get('pakrovimo_regionas', '')),
            key="pk_regionas"
        )
        pk_mie = colB.text_input(
            "  Miestas", value=("" if is_new else data.get('pakrovimo_miestas', '')),
            key="pk_miestas"
        )
        pk_adr = colB.text_input(
            "  Adresas", value=("" if is_new else data.get('pakrovimo_adresas', '')),
            key="pk_adresas"
        )

        # Pakrovimo data/laikas
        if is_new:
            default_pk_data = date.today()
        else:
            default_pk_data = date.fromisoformat(data.get('pakrovimo_data', date.today().isoformat()))
        pk_data = colB.date_input("Pakr. data", value=default_pk_data, key="pk_data")

        default_pk_nuo = (
            date.fromisoformat(data.get('pakrovimo_laikas_nuo'))
            if (not is_new and data.get('pakrovimo_laikas_nuo')) else date.today()
        )
        pk_nuo = colB.time_input("  Laikas nuo", value=default_pk_nuo, key="pk_laikas_nuo")

        default_pk_iki = (
            date.fromisoformat(data.get('pakrovimo_laikas_iki'))
            if (not is_new and data.get('pakrovimo_laikas_iki')) else date.today()
        )
        pk_iki = colB.time_input("  Laikas iki", value=default_pk_iki, key="pk_laikas_iki")

        # --- Stulpelis C: Iškrovimo duomenys ---
        colC.write("Iškr. vieta:")
        is_salis = colC.text_input(
            "  Šalis (pvz. LT)", value=("" if is_new else data.get('iskrovimo_salis', '')),
            key="is_salis"
        )
        is_regionas = colC.text_input(
            "  Regionas (pvz. LT01)", value=("" if is_new else data.get('iskrovimo_regionas', '')),
            key="is_regionas"
        )
        is_mie = colC.text_input(
            "  Miestas", value=("" if is_new else data.get('iskrovimo_miestas', '')),
            key="is_miestas"
        )
        is_adr = colC.text_input(
            "  Adresas", value=("" if is_new else data.get('iskrovimo_adresas', '')),
            key="is_adresas"
        )

        if is_new:
            default_isk_data = date.today()
        else:
            default_isk_data = date.fromisoformat(data.get('iskrovimo_data', date.today().isoformat()))
        isk_data = colC.date_input("Iškr. data", value=default_isk_data, key="is_data")

        default_is_nuo = (
            date.fromisoformat(data.get('iskrovimo_laikas_nuo'))
            if (not is_new and data.get('iskrovimo_laikas_nuo')) else date.today()
        )
        is_nuo = colC.time_input("  Laikas nuo", value=default_is_nuo, key="is_laikas_nuo")

        default_is_iki = (
            date.fromisoformat(data.get('iskrovimo_laikas_iki'))
            if (not is_new and data.get('iskrovimo_laikas_iki')) else date.today()
        )
        is_iki = colC.time_input("  Laikas iki", value=default_is_iki, key="is_laikas_iki")

        # --- Stulpelis D: Kiti laukai (komentarai, vadybininkai, km, frachtas) ---
        eksped_vad = colD.selectbox(
            "Ekspedicijos vadyb.", eksped_dropdown,
            index=(0 if is_new else eksped_dropdown.index(data.get('ekspedicijos_vadybininkas', ""))),
            key="eksped_vad"
        )
        transp_vad = colD.text_input(
            "Transporto vadyb.", value=("" if is_new else data.get('transporto_vadybininkas', '')),
            key="transp_vad"
        )
        km_int = colD.number_input(
            "Km", min_value=0, step=1,
            value=(0 if is_new else data.get('kilometrai', 0)), key="kilometrai"
        )
        frachtas_float = colD.number_input(
            "Frachtas", min_value=0.0, format="%.2f",
            value=(0.0 if is_new else data.get('frachtas', 0.0)), key="frachtas"
        )
        sv_int = colD.number_input(
            "Svoris", min_value=0, step=1,
            value=(0 if is_new else data.get('svoris', 0)), key="svoris"
        )
        pal_int = colD.number_input(
            "Pal. sk.", min_value=0, step=1,
            value=(0 if is_new else data.get('paleciu_skaicius', 0)), key="paleciu_skaicius"
        )

        # Pagrindų validacija (būtini laukai)
        error = False
        if not klientas or not uzsak:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo nr.")
            error = True

        # 8) ČIA PRIDĖJAME INTERVALŲ PERSIDENGIMO PATIKRINIMĄ:
        #    Mūsų tikslas – neleisti įvesti, jeigu:
        #      - Naujasis krovinys (arba redaguojamas) turi vilkiką ⋯
        #      - ... ir jo pakrovimo/iškrovimo datos intervalas persidengia
        #        su bet kuriuo kitu to paties vilkiko įrašu.
        if not error and vilk:
            # Formuojame datas tekstu formatu, kad galėtume palyginti:
            new_pk = pk_data.isoformat()
            new_ik = isk_data.isoformat()

            # Jei redaguojame (is_new = False), turime praleisti savo patį įrašą.
            exclude_clause = ""
            params = [vilk, new_pk, new_pk, new_ik, new_ik, new_pk, new_ik, new_pk, new_ik]
            if not is_new:
                # exclude: AND id != <sel>
                exclude_clause = " AND id != ?"
                params.append(sel)

            # Užklausa: susirandame bent vieną PMS: esamą įrašą to paties vilkiko,
            # kurio intervalas persidengia su new_pk–new_ik.
            overlap_q = f"""
                SELECT id FROM kroviniai
                WHERE vilkikas = ?
                  AND (
                      -- egzampl.1: esamo pak_data ≤ new_pk ≤ esamo isk_data
                      (date(pakrovimo_data) <= date(?) AND date(iskrovimo_data) >= date(?))
                   OR -- egzampl.2: esamo pak_data ≤ new_ik ≤ esamo isk_data
                      (date(pakrovimo_data) <= date(?) AND date(iskrovimo_data) >= date(?))
                   OR -- egzampl.3: new_pk ≤ esamo isk_data AND new_ik ≥ esamo pak_data
                      (date(?) <= date(iskrovimo_data) AND date(?) >= date(pakrovimo_data))
                  )
                  {exclude_clause}
            """
            ov = c.execute(overlap_q, tuple(params)).fetchone()
            if ov:
                st.error("❌ Negalima įvesti: to paties vilkiko krovinių intervalai persidengia.")
                error = True

        # 9) Papildomi limitų patikrinimai (kliento COFACE / frachtas)
        if not error and klientas:
            vat_row = c.execute(
                "SELECT vat_numeris, coface_limitas FROM klientai WHERE pavadinimas = ?",
                (klientas,)
            ).fetchone()
            if not vat_row or not vat_row[0]:
                st.error("❌ Kliento VAT numeris nerastas arba tuščias.")
                error = True
            else:
                vat_of_client, coface_of_client = vat_row
                musu_limitas = coface_of_client / 3.0
                unpaid_sum = 0.0
                try:
                    r = c.execute("""
                        SELECT SUM(k.frachtas)
                        FROM kroviniai AS k
                        JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                        WHERE cl.vat_numeris = ?
                          AND k.saskaitos_busena != 'Apmokėta'
                    """, (vat_of_client,)).fetchone()
                    if r and r[0] is not None:
                        unpaid_sum = r[0]
                except:
                    unpaid_sum = 0.0

                current_limit = musu_limitas - unpaid_sum
                if current_limit < 0:
                    current_limit = 0.0

                if frachtas_float > current_limit:
                    st.error(
                        f"❌ Kliento limito likutis ({round(current_limit,2)}) "
                        f"yra mažesnis nei frachtas ({frachtas_float})."
                    )
                    error = True

        # 10) Jeigu nebuvo klaidų – išsaugome (INSERT arba UPDATE)
        if not error:
            vals = {
                'klientas': klientas,
                'uzsakymo_numeris': uzsak,
                'pakrovimo_salis': pk_salis.strip(),
                'pakrovimo_regionas': pk_regionas.strip(),
                'pakrovimo_miestas': pk_mie.strip(),
                'pakrovimo_adresas': pk_adr.strip(),
                'pakrovimo_data': pk_data.isoformat(),
                'pakrovimo_laikas_nuo': pk_nuo.isoformat(),
                'pakrovimo_laikas_iki': pk_iki.isoformat(),
                'iskrovimo_salis': is_salis.strip(),
                'iskrovimo_regionas': is_regionas.strip(),
                'iskrovimo_miestas': is_mie.strip(),
                'iskrovimo_adresas': is_adr.strip(),
                'iskrovimo_data': isk_data.isoformat(),
                'iskrovimo_laikas_nuo': is_nuo.isoformat(),
                'iskrovimo_laikas_iki': is_iki.isoformat(),
                'vilkikas': vilk.strip(),
                'priekaba': priekaba_value.strip(),
                'atsakingas_vadybininkas': transp_vad.strip(),
                'ekspedicijos_vadybininkas': eksped_vad.strip(),
                'kilometrai': km_int,
                'frachtas': frachtas_float,
                'svoris': sv_int,
                'paleciu_skaicius': pal_int,
                'saskaitos_busena': sask_busena
            }

            try:
                if is_new:
                    cols = ",".join(vals.keys())
                    placeholders = ",".join(["?"] * len(vals))
                    q = f"INSERT INTO kroviniai ({cols}) VALUES ({placeholders})"
                    c.execute(q, tuple(vals.values()))
                else:
                    set_str = ",".join(f"{k}=?" for k in vals)
                    q = f"UPDATE kroviniai SET {set_str} WHERE id=?"
                    c.execute(q, tuple(vals.values()) + (sel,))

                conn.commit()

                # Jei įrašyta, perskaičiuojame kliento likutį
                unpaid_total = 0.0
                try:
                    r2 = c.execute("""
                        SELECT SUM(k.frachtas)
                        FROM kroviniai AS k
                        JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                        WHERE cl.vat_numeris = ?
                          AND k.saskaitos_busena != 'Apmokėta'
                    """, (vat_of_client,)).fetchone()
                    if r2 and r2[0] is not None:
                        unpaid_total = r2[0]
                except:
                    unpaid_total = 0.0

                new_musu = coface_of_client / 3.0
                new_liks = new_musu - unpaid_total
                if new_liks < 0:
                    new_liks = 0.0

                c.execute("""
                    UPDATE klientai
                    SET musu_limitas = ?, likes_limitas = ?
                    WHERE vat_numeris = ?
                """, (new_musu, new_liks, vat_of_client))
                conn.commit()

                st.success("✅ Krovinys išsaugotas ir limitai atnaujinti.")
                clear_sel()

            except Exception as e:
                st.error(f"❌ Klaida: {e}")

        # Jeigu buvo klaidų, vartotojas mato st.error(...) ir formos laukai lieka, kad taisytų.
        # Formos pabaiga:
        st.form_submit_button(" ")  # slaptas „dummy“ mygtukas dėl privalomumo

