import sqlite3

def init_db():
    conn = sqlite3.connect("dispo_new.db", check_same_thread=False)
    c = conn.cursor()

    # Universali lookup lentelė
    c.execute("""
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme TEXT UNIQUE
        )
    """)

    # Klientai
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

    # Kroviniai
    c.execute("""
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            klientas TEXT,
            uzsakymo_numeris TEXT,
            pakrovimo_data TEXT,
            iskrovimo_data TEXT,
            kilometrai INTEGER,
            frachtas REAL,
            busena TEXT
        )
    """)

    # Vilkikai
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            marke TEXT,
            pagaminimo_metai INTEGER,
            tech_apziura DATE,
            vadybininkas TEXT,
            vairuotojai TEXT,
            priekaba TEXT
        )
    """)

    # Priekabos
    c.execute("""
        CREATE TABLE IF NOT EXISTS priekabos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priekabu_tipas TEXT,
            numeris TEXT UNIQUE,
            marke TEXT,
            pagaminimo_metai INTEGER,
            tech_apziura DATE,
            priskirtas_vilkikas TEXT
        )
    """)

    # Grupės
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            pavadinimas TEXT,
            aprasymas TEXT
        )
    """)

    # Vairuotojai
    c.execute("""
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            gimimo_metai INTEGER,
            tautybe TEXT,
            priskirtas_vilkikas TEXT
        )
    """)

    # Darbuotojai
    c.execute("""
        CREATE TABLE IF NOT EXISTS darbuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            pareigybe TEXT,
            el_pastas TEXT,
            telefonas TEXT,
            grupe TEXT
        )
    """)

    # DISPO – Planavimo lentelė
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            vilkikas TEXT,
            priekaba TEXT,
            ekspeditorius TEXT,
            vadybininkas TEXT,
            vieta TEXT,
            atvykimo_laikas TEXT,
            laikas_nuo TEXT,
            laikas_iki TEXT,
            tušti_km INTEGER,
            krauti_km INTEGER,
            frachtas REAL,
            pastabos TEXT
        )
    """)

    # Nauja lentelė vilkikų darbo laikui
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkiku_darbo_laikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkiko_numeris TEXT,
            data TEXT,
            darbo_laikas INTEGER,
            likes_laikas INTEGER,
            atvykimo_pakrovimas TEXT,
            atvykimo_iskrovimas TEXT
        )
    """)

    conn.commit()
    return conn, c
