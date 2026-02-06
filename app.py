import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pilotage Expert Modulation", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    if pd.isna(val) or val == "" or "Somme" in str(val): return 0.0
    try:
        if ":" in str(val):
            parts = str(val).split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(str(val).replace(',', '.'))
    except: return 0.0

def decimal_to_hhmm(dec):
    if pd.isna(dec) or dec == 0: return "00:00"
    abs_dec = abs(dec)
    h = int(abs_dec)
    m = int(round((abs_dec - h) * 60))
    if m == 60: h += 1; m = 0
    sign = "-" if dec < 0 else ""
    return f"{sign}{h:02d}:{m:02d}"

# --- INTERFACE ---
st.title("🚀 Pilotage Expert : Modulation & Conformité")
st.sidebar.header("Options de la Cellule")

secteurs = {"Toutes": "Toutes", "011": "Secteur 1", "012": "Secteur 2", "013": "Secteur 3"}
choix_secteur = st.sidebar.selectbox("Filtrer par Cellule", options=list(secteurs.keys()), format_func=lambda x: secteurs[x])

col_f1, col_f2 = st.columns(2)
with col_f1:
    file_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES (Plusieurs possibles)", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL (Modulation)", type="csv")

if file_hebdo and file_mensuel:
    # 1. Traitement Mensuel (Base pour les calculs de modulation)
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].str.contains('Somme')]
    
    # Conversion numérique pour les calculs
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_dec'] = df_m[col].apply(hhmm_to_decimal)

    # Filtre Secteur
    if choix_secteur != "Toutes":
        df_m = df_m[df_m['Code'].astype(str).str.contains(choix_secteur)]

    # 2. Traitement Hebdo (Cumul et Tris)
    list_df_h = [pd.read_csv(f, sep=";", encoding="latin1") for f in file_hebdo]
    df_h = pd.concat(list_df_h)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].str.contains('Somme')]
    
    # Tri par date de début
    df_h['Début'] = pd.to_datetime(df_h['Début'], dayfirst=True)
    df_h = df_h.sort_values(by='Début', ascending=False)
    
    # Calculs Hebdo
    df_h['Total_dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_dec'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_dec'] = df_h['Total_dec'] - df_h['Contrat_dec']

    # --- SECTION ALERTES HEBDO ---
    st.header("⚠️ Analyse des Dépassements Hebdomadaires")
    
    def check_alerte(row):
        if row['Contrat_dec'] >= 35:
            return "🛑 TEMPS PLEIN > 40H" if row['Total_dec'] > 40 else "OK"
        else:
            if row['Total_dec'] > 34: return "🛑 TEMPS PARTIEL > 34H"
            if row['Ecart_dec'] > (row['Contrat_dec'] / 3): return "🟠 DÉPASSEMENT 1/3"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    
    # Affichage en hh:mm
    df_h_display = df_h.copy()
    df_h_display['Heures totales'] = df_h_display['Total_dec'].apply(decimal_to_hhmm)
    df_h_display['Heures hebdo contrat'] = df_h_display['Contrat_dec'].apply(decimal_to_hhmm)
    df_h_display['Date'] = df_h_display['Début'].dt.strftime('%d/%m/%Y')

    alertes_only = df_h_display[df_h_display['Statut'] != "OK"]
    st.dataframe(alertes_only[['Date', 'Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Statut']].style.apply(
        lambda x: ['background-color: #ff4b4b' if '🛑' in v else 'background-color: #ffa500' if '🟠' in v else '' for v in x], subset=['Statut']
    ))

    # --- SECTION MODULATION MENSUELLE ---
    st.header("🎯 Suivi de la Modulation (Objectif Zéro)")
    
    # Ajout colonne "Explication" pour l'utilisateur
    if 'explications' not in st.session_state:
        st.session_state.explications = {}

    df_m['Explication'] = df_m['Nom'].map(st.session_state.explications).fillna("")
    
    # Filtre réactif : Tout voir ou seulement les dév > 5h
    show_all = st.checkbox("Afficher tout le monde (sinon seulement > 5h)", value=False)
    if not show_all:
        df_m_filtered = df_m[(df_m['Déviation mensuelle_dec'] > 5) | (df_m['Déviation mensuelle_dec'] < -5)]
    else:
        df_m_filtered = df_m

    # Éditeur de données pour ajouter des explications
    edited_df = st.data_editor(
        df_m_filtered[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures', 'Explication']],
        column_config={"Explication": st.column_config.TextColumn("Commentaires / Justification")},
        disabled=["Nom", "Déviation mensuelle", "Déviation à date", "Potentiel heures"],
        key="editor"
    )
    
    # Sauvegarde des explications
    for i, row in edited_df.iterrows():
        st.session_state.explications[row['Nom']] = row['Explication']

    # --- SYNTHÈSE GLOBALE DE LA CELLULE ---
    st.divider()
    st.subheader(f"📈 Bilan Global - {secteurs[choix_secteur]}")
    
    pos = df_m[df_m['Déviation à date_dec'] > 0]['Déviation à date_dec'].sum()
    neg = df_m[df_m['Déviation à date_dec'] < 0]['Déviation à date_dec'].sum()
    ratio = pos + neg # Le solde réel à combler
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Cumul Positif (+)", decimal_to_hhmm(pos))
    c2.metric("Cumul Négatif (-)", decimal_to_hhmm(neg))
    c3.metric("Solde Net (Rapport)", decimal_to_hhmm(ratio), delta="À combler" if ratio < 0 else "Surplus", delta_color="inverse")

else:
    st.info("👋 Bonjour ! Veuillez glisser vos fichiers hebdo et mensuel pour démarrer le pilotage.")
