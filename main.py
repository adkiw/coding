import streamlit as st
from darbuotojai import darbuotoju_modulis
from vairuotojai import vairuotoju_modulis
from grupes import grupiu_modulis
from klientai import klientu_modulis
from vilkikai import vilkiku_modulis
from priekabos import priekabu_modulis
from kroviniai import kroviniu_modulis
from planavimas import planavimo_modulis
from update import atnaujinimo_modulis

def main():
    """
    Pagrindinė Streamlit programos funkcija.
    Vykdo pagrindinį navigacijos meniu ir įkelia pasirinktą modulį.
    Kiekvienas meniu punktas atveria atskirą valdymo modulį.
    """
    st.set_page_config(page_title="DISPO – Valdymo sistema", page_icon="🚚", layout="wide")
    st.sidebar.title("DISPO")
    pasirinkimas = st.sidebar.radio(
        "Pasirinkite modulį:",
        (
            "Darbuotojai",
            "Vairuotojai",
            "Grupės",
            "Klientai",
            "Vilkikai",
            "Priekabos",
            "Kroviniai",
            "Planavimas",
            "Duomenų atnaujinimas"
        )
    )

    # Pagal pasirinkimą kviečiamas atitinkamas modulis.
    if pasirinkimas == "Darbuotojai":
        darbuotoju_modulis()
    elif pasirinkimas == "Vairuotojai":
        vairuotoju_modulis()
    elif pasirinkimas == "Grupės":
        grupiu_modulis()
    elif pasirinkimas == "Klientai":
        klientu_modulis()
    elif pasirinkimas == "Vilkikai":
        vilkiku_modulis()
    elif pasirinkimas == "Priekabos":
        priekabu_modulis()
    elif pasirinkimas == "Kroviniai":
        kroviniu_modulis()
    elif pasirinkimas == "Planavimas":
        planavimo_modulis()
    elif pasirinkimas == "Duomenų atnaujinimas":
        atnaujinimo_modulis()
    else:
        st.warning("Nepavyko pasirinkti modulio.")

if __name__ == "__main__":
    main()
