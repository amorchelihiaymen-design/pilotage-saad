import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Pilotage Expert Modulation SAAD", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    """Convertit HH:MM ou '33,46' en float decimal"""
    if pd.isna(val) or val == "" or "Somme" in str(val):
        return 0.0
    try:
        val_str = str(val).strip()
        if ":" in val_str:
            parts = val_str.split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(val_str.replace(',', '.'))
    except:
        return 0.0

def decimal_to_hhmm(dec):
    """Convertit 33.5 en '33:30' (arrondi, pas de secondes)"""
    if pd.isna(dec) or dec == 0:
        return "00:00"
    abs_dec = abs(dec)
    h = int(abs_dec)
    m = int(round((abs_dec - h) * 60))
    if m == 60:
        h += 1
        m = 0
    sign = "-" if dec < -0.001 else "" # Petit seuil pour éviter le -00:00
    return f"{sign}{h:02d}:{m:02d}"

# --- INTERFACE ---
st.title("🚀 Pilotage Expert : Modulation & Conformité Légale")
st.markdown("---")

# --- FILTRES LATÉRAUX ---
st.sidebar.header("Options de la Cellule")
secteurs = {
    "Toutes": "Toutes les cellules",
    "011": "Secteur 1",
    "012": "Secteur 2",
    "013": "Secteur 3"
}
choix_secteur = st.sidebar.selectbox("Filtr
