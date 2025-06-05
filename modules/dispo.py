# modules/dispo.py

import streamlit as st
from datetime import date, timedelta
import random
import hashlib

def show(conn, c):
    st.title("DISPO – Planavimo lentelė su grupėmis")

    lt_weekdays = {
        0: "Pirmadienis", 1: "Antradienis", 2: "Trečiadienis",
        3: "Ketvirtadienis", 4: "Penktadienis", 5: "Šeštadienis", 6: "Sekmadienis"
    }

    def col_letter(n: int) -> str:
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    def iso_monday(d: date) -> date:
        return d - timedelta(days=(d.isoweekday() - 1))

    today = date.today()
    this_monday = iso_monday(today)
    start_default = this_monday - timedelta(weeks=2)
    end_default = this_monday + timedelta(weeks=2, days=6)

    c1, c2 = st.columns(2)
    with c1:
        start_sel = st.date_input("Pradžios data:", value=start_default)
    with c2:
        end_sel = st.date_input("Pabaigos data:", value=end_default)

    if end_sel < start_sel:
        start_date, end_date = end_sel, start_sel
    else:
        start_date, end_date = start_sel, end_sel

    num_days = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    st.write(f"Rodyti {num_days} dienų nuo {start_date} iki {end_date}.")

    common_headers = [
        "Transporto grupė", "Ekspedicijos grupės nr.",
        "Vilkiko nr.", "Ekspeditorius",
        "Trans. vadybininkas", "Priekabos nr.",
        "Vair. sk.", "Savaitinė atstova", "Pastabos"
    ]
    day_headers = [
        "B. d. laikas", "L. d. laikas", "Atvykimo laikas",
        "Laikas nuo", "Laikas iki", "Vieta",
        "Atsakingas", "Tušti km", "Krauti km",
        "Kelių išlaidos", "Frachtas"
    ]

    trucks_info = c.execute("""
        SELECT
            tg.numeris AS trans_grupe,
            eg.numeris AS eksp_grupe,
            v.numeris,
            e.vardas || ' ' || e.pavarde AS ekspeditorius,
            t.vardas || ' ' || t.pavarde AS vadybininkas,
            v.priekaba,
            (SELECT COUNT(*) FROM vairuotojai WHERE priskirtas_vilkikas = v.numeris) AS vair_sk,
            42 AS savaitine_atstova
        FROM vilkikai v
        LEFT JOIN darbuotojai t ON v.vadybininkas = t.vardas
        LEFT JOIN grupes tg ON t.grupe = tg.pavadinimas
        LEFT JOIN darbuotojai e ON v.vairuotojai LIKE '%' || e.vardas || '%'
        LEFT JOIN grupes eg ON e.grupe = eg.pavadinimas
    """).fetchall()

    all_eksp = sorted({t[3] for t in trucks_info})
    sel_eksp = st.multiselect("Filtruok pagal ekspeditorius", options=all_eksp, default=all_eksp)

    st.markdown("""
    <style>
      .table-container { overflow-x: auto; }
      .table-container table {
        border-collapse: collapse;
        display: inline-block;
        white-space: nowrap;
      }
      th, td {
        border:1px solid #ccc;
        padding:4px;
        text-align:center;
      }
      th {
        background:#f5f5f5;
        position:sticky;
        top:0;
        z-index:1;
      }
    </style>
    """, unsafe_allow_html=True)

    def get_rnd(truck: str, day: str) -> random.Random:
        seed = int(hashlib.md5(f"{truck}-{day}".encode()).hexdigest(), 16)
        return random.Random(seed)

    total_common = len(common_headers)
    total_day_cols = len(dates) * len(day_headers)
    total_all_cols = 1 + total_common + total_day_cols

    html = '<div class="table-container"><table>\n'
    html += "<tr>" + "".join(f"<th>{col_letter(i)}</th>" for i in range(1, total_all_cols + 1)) + "</tr>\n"
    html += "<tr><th></th><th colspan=\"{}\"></th>".format(total_common)
    for d in dates:
        wd = lt_weekdays[d.weekday()]
        html += f'<th colspan="{len(day_headers)}">{d:%Y-%m-%d} {wd}</th>'
    html += "</tr>\n"

    html += "<tr><th>#</th>" + "".join(f"<th>{h}</th>" for h in common_headers)
    for _ in dates:
        for hh in day_headers:
            html += f"<th>{hh}</th>"
    html += "</tr>\n"

    row_num = 1
    for row in trucks_info:
        if row[3] not in sel_eksp:
            continue
        html += f"<tr><td>{row_num}</td>"
        for val in row:
            html += f'<td rowspan="2">{val}</td>'
        html += "<td></td>"
        for d in dates:
            key = d.strftime("%Y-%m-%d")
            rnd = get_rnd(row[2], key)
            atv = f"{rnd.randint(0, 23):02d}:{rnd.randint(0, 59):02d}"
            city = rnd.choice(["Vilnius", "Kaunas", "Berlin"])
            html += ("<td></td><td></td>"
                     f"<td>{atv}</td><td></td><td></td>"
                     f"<td>{city}</td>" + "<td></td>" * 5)
        html += "</tr>\n"

        html += f"<tr><td>{row_num + 1}</td>" + "<td></td>" * total_common
        for d in dates:
            key = d.strftime("%Y-%m-%d")
            rnd = get_rnd(row[2], key)
            t1 = f"{rnd.randint(7, 9):02d}:00"
            kms = rnd.randint(20, 120)
            costs = kms * 5
            fr = round(rnd.uniform(800, 1200), 2)
            dest = rnd.choice(["Riga", "Poznan"])
            html += ("<td>9</td><td>6</td>"
                     f"<td>{t1}</td><td>{t1}</td><td>16:00</td>"
                     f"<td>{dest}</td><td></td>"
                     f"<td>{kms}</td><td>{costs}</td><td></td><td>{fr}</td>")
        html += "</tr>\n"
        row_num += 2

    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)
