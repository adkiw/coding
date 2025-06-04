import streamlit as st

def show(conn, c):
    st.title("DISPO – Nustatymai (Dropdown reikšmių valdymas)")

    kategorijos = [row[0] for row in c.execute(
        "SELECT DISTINCT kategorija FROM lookup"
    ).fetchall()]

    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kategorija = col2.text_input("Arba įveskite naują kategoriją")

    pasirinkta_kategorija = nauja_kategorija.strip() if nauja_kategorija else esama

    st.markdown("---")

    if pasirinkta_kategorija:
        st.subheader(f"Kategorija: **{pasirinkta_kategorija}**")

        reiksmes = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (pasirinkta_kategorija,)
        ).fetchall()]

        st.write(reiksmes or "_(Nėra reikšmių šioje kategorijoje)_")

        nauja_reiksme = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti"):
            if nauja_reiksme:
                try:
                    c.execute(
                        "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
                        (pasirinkta_kategorija, nauja_reiksme)
                    )
                    conn.commit()
                    st.success(f"✅ Reikšmė „{nauja_reiksme}“ pridėta.")
                except Exception:
                    st.warning("⚠️ Toks įrašas jau egzistuoja.")

        istr_reiksme = st.selectbox("Pasirink reikšmę ištrynimui", [""] + reiksmes)
        if st.button("🗑 Ištrinti"):
            if istr_reiksme:
                c.execute(
                    "DELETE FROM lookup WHERE kategorija = ? AND reiksme = ?",
                    (pasirinkta_kategorija, istr_reiksme)
                )
                conn.commit()
                st.success(f"✅ Reikšmė „{istr_reiksme}“ ištrinta.")
    else:
        st.info("👉 Pasirink esamą arba sukurk naują kategoriją.")
