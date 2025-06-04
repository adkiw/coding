# db.py

import sqlite3

def init_db():
    conn = sqlite3.connect("dispo.db", check_same_thread=False)
    c = conn.cursor()

    # 1) lentelė "lookup"
    c.execute("""
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reikšmė TEXT
        )
    """)

    # 2) lentelė "klientai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT,
            kontaktai TEXT,
            salis TEXT,
            miestas TEXT,
            regionas TEXT,
            vat_numeris TEXT
        )
    """)

    # 3) lentelė "vilkikai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            marke TEXT,
            modelis TEXT,
            vin TEXT,
            registracijos_metai INTEGER,
            tipas TEXT,
            keliamoji_galia INTEGER,
            teatras TEXT
        )
    """)

    # 4) lentelė "priekabos"
    c.execute("""
        CREATE TABLE IF NOT EXISTS priekabos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            marke TEXT,
            modelis TEXT,
            tipas TEXT,
            keliamoji_tona INTEGER,
            teatras TEXT
        )
    """)

    # 5) lentelė "kroviniai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkikas TEXT,
            priekaba TEXT,
            klientas TEXT,
            pakrovimo_data TEXT,
            pakrovimo_laikas TEXT,
            iskrovimo_salis TEXT,
            iskrovimo_regionas TEXT,
            iskrovimo_data TEXT,
            iskrovimo_laikas_nuo TEXT,
            vaziuos TEXT,
            rodiklio_tip TEXT
        )
    """)

    # 6) lentelė "dispo"
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkikas TEXT,
            priekaba TEXT,
            klientas TEXT,
            pakrovimo_data TEXT,
            pakrovimo_laikas TEXT,
            iskrovimo_salis TEXT,
            iskrovimo_regionas TEXT,
            iskrovimo_data TEXT,
            iskrovimo_laikas_nuo TEXT,
            vaziuos TEXT,
            rodiklio_tip TEXT
        )
    """)

    # 7) lentelė "grupes"
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            pavadinimas TEXT,
            aprasymas TEXT
        )
    """)

    # 8) lentelė "grupiu_regionai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupiu_regionai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupe_id INTEGER,
            regiono_kodas TEXT,
            FOREIGN KEY (grupe_id) REFERENCES grupes (id)
        )
    """)

    # 9) lentelė "vairuotojai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            teises TEXT,
            teises_exp TEXT,
            telefonas TEXT,
            el_pastas TEXT,
            pastabos TEXT
        )
    """)

    # 10) lentelė "darbuotojai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS darbuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            pareigos TEXT,
            skyrius TEXT,
            telefonas TEXT,
            el_pastas TEXT
        )
    """)

    # 11) lentelė "vilkiku_darbo_laikai"
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkiku_darbo_laikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkiko_numeris TEXT,
            data TEXT,
            darbo_laikas INTEGER,
            likes_laikas INTEGER,
            atvykimo_pakrovimas TEXT,
            atvykimo_iskrovimas TEXT,
            iskrovimo_statusas TEXT,
            iskrovimo_data TEXT,
            iskrovimo_laikas TEXT,
            sa TEXT
        )
    """)

    conn.commit()
    return conn, c
