import sqlite3
import os

def connect():
    """
    Prisijungia prie SQLite duomenų bazės.
    Jeigu duomenų bazės failas neegzistuoja, sukuria jį ir visas reikiamas lenteles.
    Grąžina atidarytą prisijungimą ir kursorių.
    """
    db_file = "main.db"
    db_exists = os.path.exists(db_file)
    conn = sqlite3.connect(db_file, check_same_thread=False)
    c = conn.cursor()
    if not db_exists:
        create_tables(c)
        conn.commit()
    return conn, c

def create_tables(c):
    """
    Sukuria pagrindines lenteles duomenų bazėje, jeigu jų nėra.
    """
    # Lentelė darbuotojams
    c.execute("""
        CREATE TABLE IF NOT EXISTS darbuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT NOT NULL,
            pavarde TEXT NOT NULL
        )
    """)
    # Lentelė vairuotojams
    c.execute("""
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT NOT NULL,
            pavarde TEXT NOT NULL,
            uzimtas INTEGER DEFAULT 0
        )
    """)
    # Lentelė grupėms
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT NOT NULL
        )
    """)
    # Lentelė klientams
    c.execute("""
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT NOT NULL,
            pavarde TEXT NOT NULL,
            imone TEXT,
            tel_nr TEXT
        )
    """)
    # Lentelė vilkikams
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marke TEXT NOT NULL,
            modelis TEXT NOT NULL,
            valstybinis_nr TEXT NOT NULL
        )
    """)
    # Lentelė priekaboms
    c.execute("""
        CREATE TABLE IF NOT EXISTS priekabos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT NOT NULL,
            tipas TEXT NOT NULL
        )
    """)
    # Lentelė kroviniams
    c.execute("""
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aprasymas TEXT NOT NULL,
            priskirtas INTEGER DEFAULT 0,
            vairuotojo_id INTEGER,
            FOREIGN KEY (vairuotojo_id) REFERENCES vairuotojai(id)
        )
    """)
    # Pagalbinė lentelė konfigūracijai ar parametrams
    c.execute("""
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
    """)
    # Lentelė vilkikų darbo laikams
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkiku_darbo_laikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkiko_numeris TEXT,
            data TEXT,
            darbo_laikas INTEGER,
            poilsio_laikas INTEGER
        )
    """)

def close(conn, c):
    """
    Uždaro duomenų bazės kursorių ir prisijungimą.
    """
    c.close()
    conn.close()

def show(conn, c):
    """
    Atspausdina visas lenteles ir jų duomenis konsolėje.
    Naudojama testavimui ir duomenų peržiūrai.
    """
    # Gauname visas lenteles
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print('Duomenų bazės lentelės ir duomenys:')
    for table in tables:
        print(f'\nLentelė: {table[0]}')
        c.execute(f"SELECT * FROM {table[0]}")
        rows = c.fetchall()
        for row in rows:
            print(row)

def execute_query(conn, c, query: str, params=()):
    """
    Įvykdo bendrą SQL užklausą su pasirinktais parametrais.
    Patogu naudoti įvairiems SELECT, INSERT, UPDATE veiksmams.
    """
    c.execute(query, params)
    conn.commit()
    return c

def fetch_all(conn, c, query: str, params=()):
    """
    Grąžina visus duomenis pagal užklausą.
    Pvz., fetch_all(conn, c, 'SELECT * FROM darbuotojai')
    """
    c.execute(query, params)
    return c.fetchall()

def fetch_one(conn, c, query: str, params=()):
    """
    Grąžina vieną duomenų įrašą pagal užklausą.
    Pvz., fetch_one(conn, c, 'SELECT * FROM darbuotojai WHERE id=?', (1,))
    """
    c.execute(query, params)
    return c.fetchone()
