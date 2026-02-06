import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Pilotage Cellules - Modulation & Conformité", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    """Convertit HH:MM ou '33,46' en float decimal pour calculs"""
    if pd.isna(val) or val == "" or "Somme" in str(val): return 0.0
    try:
        val_str = str(val).strip()
        if ":" in val_str:
            parts = val_str.split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(val_str.replace(',', '.'))
    except: return 0.0

def decimal_to_hhmm(dec):
    """Convertit 33.5 en '33:30' (arrondi, sans secondes)"""
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
    "011": "Secteur 1",
    "012": "Secteur 2",
    "013": "Secteur 3"
}
choix_code = st.sidebar.selectbox("Sélectionner la Cellule", options=list(secteurs_map.keys()), format_func=lambda x: secteurs_map[x])

# --- CHARGEMENT ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    files_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES (Multi-sélection possible)", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL (Référence Modulation)", type="csv")

if files_hebdo and file_mensuel:
    # 1. Traitement Mensuel (Source de vérité pour les secteurs)
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # Création du dictionnaire de correspondance : Nom -> Code Secteur
    # On utilise la colonne 'Code' du mensuel
    mapping_cellule = df_m.set_index('Nom')['Code'].astype(str).to_dict()

    # 2. Traitement Hebdo
    list_dfs = [pd.read_csv(f, sep=";", encoding="latin1") for f in files_hebdo]
    df_h = pd.concat(list_dfs)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # INJECTION DU CODE SECTEUR DANS LE HEBDO
    df_h['Code_Cellule'] = df_h['Intervenant'].map(mapping_cellule)
    
    # Tri par date (Récent en haut)
    df_h['Début_dt'] = pd.to_datetime(df_h['Début'], dayfirst=True)
    df_h = df_h.sort_values(by='Début_dt', ascending=False)

    # --- APPLICATION DU FILTRE ---
    if choix_code != "Toutes":
        df_m = df_m[df_m['Code'].astype(str).str.contains(choix_code, na=False)]
        df_h = df_h[df_h['Code_Cellule'].astype(str).str.contains(choix_code, na=False)]

    # --- CALCULS ---
    # Mensuel
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_dec'] = df_m[col].apply(hhmm_to_decimal)

    # Hebdo
    df_h['Total_dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_dec'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_dec'] = df_h['Total_dec'] - df_h['Contrat_dec']

    # --- SECTION ALERTES HEBDO ---
    st.header(f"⚠️ Dépassements Hebdo - {secteurs_map[choix_code]}")
    
    def check_alerte(row):
        # Temps plein (35h)
        if row['Contrat_dec'] >= 35:
            return "🛑 TEMPS PLEIN > 40H" if row['Total_dec'] > 40 else "OK"
        # Temps partiel (<35h)
        else:
            if row['Total_dec'] > 34: return "🛑 TEMPS PARTIEL > 34H"
            if row['Ecart_dec'] > (row['Contrat_dec'] / 3): return "🟠 DÉPASSEMENT 1/3 CONTRAT"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    
    # Affichage hebdo
    df_h_disp = df_h[df_h['Statut'] != "OK"].copy()
    df_h_disp['Heures'] = df_h_disp['Total_dec'].apply(decimal_to_hhmm)
    df_h_disp['Contrat'] = df_h_disp['Contrat_dec'].apply(decimal_to_hhmm)
    df_h_disp['Semaine du'] = df_h_disp['Début_dt'].dt.strftime('%d/%m/%Y')

    if not df_h_disp.empty:
        st.dataframe(df_h_disp[['Semaine du', 'Intervenant', 'Contrat', 'Heures', 'Statut']].style.apply(
            lambda x: ['background-color: #ff4b4b' if '🛑' in str(v) else 'background-color: #ffa500' if '🟠' in str(v) else '' for v in x], subset=['Statut']
        ), use_container_width=True, hide_index=True)
    else:
        st.success("Aucune alerte hebdomadaire sur cette cellule.")

    # --- SECTION MODULATION MENSUELLE ---
    st.markdown("---")
    st.header(f"🎯 Suivi Modulation - {secteurs_map[choix_code]}")
    
    if 'notes' not in st.session_state: st.session_state.notes = {}
    df_m['Justification'] = df_m['Nom'].map(st.session_state.notes).fillna("")
    
    show_all = st.toggle("Afficher tous les salariés de la cellule", value=False)
    df_m_f = df_m if show_all else df_m[(df_m['Déviation mensuelle_dec'] > 5) | (df_m['Déviation mensuelle_dec'] < -5)]

    # Éditeur de données
    edited_df = st.data_editor(
        df_m_f[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures', 'Justification']],
        column_config={"Justification": st.column_config.TextColumn("Commentaire / Justification", width="large")},
        use_container_width=True, hide_index=True, key="mod_editor"
    )
    for i, row in edited_df.iterrows(): st.session_state.notes[row['Nom']] = row['Justification']

    # --- BILAN CELLULE ---
    st.markdown("---")
    st.subheader(f"📊 Bilan Global : {secteurs_map[choix_code]}")
    
    pos = df_m[df_m['Déviation à date_dec'] > 0]['Déviation à date_dec'].sum()
    neg = df_m[df_m['Déviation à date_dec'] < 0]['Déviation à date_dec'].sum()
    solde = pos + neg
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Modulation Positve (+)", decimal_to_hhmm(pos))
    m2.metric("Total Modulation Négative (-)", decimal_to_hhmm(neg))
    m3.metric("Rapport Net (Solde Cellule)", decimal_to_hhmm(solde), 
              delta="Déficit d'heures" if solde < 0 else "Surplus d'heures", 
              delta_color="inverse" if solde < 0 else "normal")

else:
    st.info("👋 Bonjour ! Importez vos fichiers hebdomadaires et mensuels pour piloter vos cellules.")
