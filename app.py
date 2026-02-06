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

# C'EST ICI QUE L'ERREUR S'ETAIT PRODUITE (Ligne 47) :
choix_secteur = st.sidebar.selectbox("Filtrer par Cellule", options=list(secteurs.keys()), format_func=lambda x: secteurs[x])

# --- CHARGEMENT DES FICHIERS ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    file_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES (Sélectionnez plusieurs fichiers)", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL (Modulation)", type="csv")

if file_hebdo and file_mensuel:
    # 1. Traitement Mensuel (Sécurisé)
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna()]
    df_m = df_m[~df_m['Nom'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # Conversion numérique pour les calculs internes
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_dec'] = df_m[col].apply(hhmm_to_decimal)

    # Filtre Secteur basé sur le Code
    if choix_secteur != "Toutes":
        df_m = df_m[df_m['Code'].astype(str).str.contains(choix_secteur, na=False)]

    # 2. Traitement Hebdo (Multi-fichiers et Tri)
    list_df_h = [pd.read_csv(f, sep=";", encoding="latin1") for f in file_hebdo]
    df_h = pd.concat(list_df_h)
    df_h = df_h[df_h['Intervenant'].notna()]
    df_h = df_h[~df_h['Intervenant'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # Tri par date de début (Récent en haut)
    df_h['Début_dt'] = pd.to_datetime(df_h['Début'], dayfirst=True)
    df_h = df_h.sort_values(by='Début_dt', ascending=False)
    
    # Calculs Hebdo internes
    df_h['Total_dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_dec'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_dec'] = df_h['Total_dec'] - df_h['Contrat_dec']

    # --- SECTION ALERTES HEBDO ---
    st.header(f"⚠️ Analyse des Dépassements Hebdo ({secteurs[choix_secteur]})")
    
    def check_alerte(row):
        # Temps plein (35h)
        if row['Contrat_dec'] >= 35:
            return "🛑 TEMPS PLEIN > 40H" if row['Total_dec'] > 40 else "OK"
        # Temps partiel (< 35h)
        else:
            if row['Total_dec'] > 34: return "🛑 TEMPS PARTIEL > 34H"
            if row['Ecart_dec'] > (row['Contrat_dec'] / 3): return "🟠 DÉPASSEMENT 1/3"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    
    # Préparation affichage Hebdo (Format HH:MM)
    df_h_disp = df_h.copy()
    df_h_disp['Heures totales'] = df_h_disp['Total_dec'].apply(decimal_to_hhmm)
    df_h_disp['Heures hebdo contrat'] = df_h_disp['Contrat_dec'].apply(decimal_to_hhmm)
    df_h_disp['Date'] = df_h_disp['Début_dt'].dt.strftime('%d/%m/%Y')

    alertes_only = df_h_disp[df_h_disp['Statut'] != "OK"]
    
    if not alertes_only.empty:
        st.dataframe(
            alertes_only[['Date', 'Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Statut']]
            .style.apply(lambda x: ['background-color: #ff4b4b' if '🛑' in str(v) else 'background-color: #ffa500' if '🟠' in str(v) else '' for v in x], subset=['Statut']),
            use_container_width=True
        )
    else:
        st.success("Aucune anomalie détectée sur les semaines sélectionnées.")

    # --- SECTION MODULATION MENSUELLE ---
    st.markdown("---")
    st.header("🎯 Suivi de la Modulation (Objectif Zéro)")

    # Gestion des explications persistantes
    if 'notes' not in st.session_state:
        st.session_state.notes = {}

    df_m['Justification'] = df_m['Nom'].map(st.session_state.notes).fillna("")
    
    # Filtre réactif (Tout voir ou seulement les écarts)
    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        show_all = st.toggle("Afficher tous les salariés", value=False)
    
    if not show_all:
        df_m_f = df_m[(df_m['Déviation mensuelle_dec'] > 5) | (df_m['Déviation mensuelle_dec'] < -5)]
    else:
        df_m_f = df_m

    # Éditeur interactif
    st.write("Modifiez la colonne 'Justification' pour ignorer ou expliquer un écart :")
    edited_df = st.data_editor(
        df_m_f[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures', 'Justification']],
        column_config={
            "Nom": st.column_config.TextColumn(disabled=True),
            "Déviation mensuelle": st.column_config.TextColumn(disabled=True),
            "Justification": st.column_config.TextColumn("Commentaire / Explication", width="large")
        },
        use_container_width=True,
        hide_index=True,
        key="mod_editor"
    )
    
    # Sauvegarde automatique des commentaires
    for i, row in edited_df.iterrows():
        st.session_state.notes[row['Nom']] = row['Justification']

    # --- BILAN GLOBAL DE LA CELLULE ---
    st.markdown("---")
    st.subheader(f"📊 Bilan Global de la Cellule : {secteurs[choix_secteur]}")
    
    pos = df_m[df_m['Déviation à date_dec'] > 0]['Déviation à date_dec'].sum()
    neg = df_m[df_m['Déviation à date_dec'] < 0]['Déviation à date_dec'].sum()
    solde = pos + neg
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Cumul Positif (+)", decimal_to_hhmm(pos))
    m2.metric("Cumul Négatif (-)", decimal_to_hhmm(neg))
    m3.metric("Rapport Net (Solde)", decimal_to_hhmm(solde), 
              delta="Surplus" if solde > 0 else "Déficit", 
              delta_color="inverse" if solde < 0 else "normal")

else:
    st.info("💡 Pour commencer, importez vos fichiers CSV. L'outil analysera automatiquement les dépassements et la modulation par secteur.")
