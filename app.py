import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Pilotage Expert - Cellules SAAD", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    """Convertit tout format (HH:MM ou 12,50) en nombre décimal pour les calculs"""
    if pd.isna(val) or val == "" or "Somme" in str(val): return 0.0
    try:
        val_str = str(val).strip().replace(',', '.')
        if ":" in val_str:
            parts = val_str.split(':')
            return int(parts[0]) + (int(parts[1]) / 60.0 if len(parts) > 1 else 0.0)
        return float(val_str)
    except: return 0.0

def decimal_to_hhmm(dec):
    """Convertit un nombre (12.5) en texte propre (12:30) avec gestion du signe"""
    if pd.isna(dec) or abs(dec) < 0.001: return "00:00"
    abs_dec = abs(dec)
    h = int(abs_dec)
    m = int(round((abs_dec - h) * 60))
    if m == 60: h += 1; m = 0
    sign = "-" if dec < -0.001 else ""
    return f"{sign}{h:02d}:{m:02d}"

# --- INTERFACE ---
st.title("🚀 Pilotage Expert : Modulation & Conformité Légale")
st.markdown("---")

# --- FILTRES LATÉRAUX (CELLULES) ---
st.sidebar.header("Gestion des Cellules")
secteurs_map = {
    "Toutes": "Toutes les cellules",
    "11": "Secteur 1 (011)",
    "12": "Secteur 2 (012)",
    "13": "Secteur 3 (013)"
}
choix_code = st.sidebar.selectbox("Sélectionner la Cellule", options=list(secteurs_map.keys()), format_func=lambda x: secteurs_map[x])

col_f1, col_f2 = st.columns(2)
with col_f1:
    files_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL", type="csv")

if files_hebdo and file_mensuel:
    # 1. Traitement Mensuel
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # Correction automatique des colonnes V2
    if 'Déviation cumulée' in df_m.columns:
        df_m = df_m.rename(columns={'Déviation cumulée': 'Déviation à date'})
    
    # Identification de la colonne Secteur (Code.1 ou Code)
    col_secteur = 'Code'
    for c in df_m.columns:
        if 'Code' in c:
            sample = str(df_m[c].iloc[0])
            if any(s in sample for s in ['11', '12', '13']):
                col_secteur = c
                break

    mapping_cellule = df_m.set_index('Nom')[col_secteur].astype(str).to_dict()

    # 2. Traitement Hebdo
    list_dfs = [pd.read_csv(f, sep=";", encoding="latin1") for f in files_hebdo]
    df_h = pd.concat(list_dfs)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].astype(str).str.contains('Somme', case=False, na=False)]
    df_h['Code_Cellule'] = df_h['Intervenant'].map(mapping_cellule)
    df_h['Début_dt'] = pd.to_datetime(df_h['Début'], dayfirst=True)

    # --- APPLICATION DU FILTRE ---
    if choix_code != "Toutes":
        df_m = df_m[df_m[col_secteur].astype(str).str.contains(choix_code, na=False)].copy()
        df_h = df_h[df_h['Code_Cellule'].astype(str).str.contains(choix_code, na=False)].copy()

    # --- CALCULS NUMÉRIQUES (POUR LE TRI) ---
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_num'] = df_m[col].apply(hhmm_to_decimal)

    df_h['Total_num'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_num'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_num'] = df_h['Total_num'] - df_h['Contrat_num']

    # --- SECTION ALERTES HEBDO
