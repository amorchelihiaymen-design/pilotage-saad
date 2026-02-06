import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Pilotage Cellules - Modulation & Conformité", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    """Convertit HH:MM ou '33,46' en float decimal"""
    if pd.isna(val) or val == "" or "Somme" in str(val): return 0.0
    try:
        val_str = str(val).strip()
        if ":" in val_str:
            parts = val_str.split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(val_str.replace(',', '.'))
    except: return 0.0

def decimal_to_hhmm(dec):
    """Convertit décimal en HH:MM"""
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

# --- CHARGEMENT ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    files_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL (Modulation)", type="csv")

if files_hebdo and file_mensuel:
    # 1. Traitement Mensuel
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].astype(str).str.contains('Somme', case=False, na=False)]
    
    # --- CORRECTION AUTOMATIQUE DES COLONNES (V1 vs V2) ---
    # 1. Gestion "Déviation à date" vs "Déviation cumulée"
    if 'Déviation cumulée' in df_m.columns:
        df_m = df_m.rename(columns={'Déviation cumulée': 'Déviation à date'})
    
    # 2. Gestion "Code" vs "Code.1" pour le secteur
    # On cherche la colonne qui contient des valeurs comme '011', '012'
    col_secteur = None
    for col in df_m.columns:
        if 'Code' in col:
            # On regarde si la première valeur ressemble à un code secteur (contient 11, 12, 13)
            first_val = str(df_m[col].iloc[0])
            if any(x in first_val for x in ['011', '012', '013', '11', '12', '13']):
                col_secteur = col
                break
    
    if not col_secteur:
        # Fallback : on prend la 2ème colonne si elle existe, sinon la 1ère
        col_secteur = df_m.columns[1] if len(df_m.columns) > 1 else df_m.columns[0]

    # Lien Nom -> Code Secteur
    mapping_cellule = df_m.set_index('Nom')[col_secteur].astype(str).to_dict()

    # 2. Traitement Hebdo
    list_dfs = [pd.read_csv(f, sep=";", encoding="latin1") for f in files_hebdo]
    df_h = pd.concat(list_dfs)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].astype(str).str.contains('Somme', case=False, na=False)]
    df_h['Code_Cellule'] = df_h['Intervenant'].map(mapping_cellule)
    df_h['Début_dt'] = pd.to_datetime(df_h['Début'], dayfirst=True)
    df_h = df_h.sort_values(by='Début_dt', ascending=False)

    # --- APPLICATION DU FILTRE ---
    if choix_code != "Toutes":
        df_m = df_m[df_m[col_secteur].astype(str).str.contains(choix_code, na=False)].copy()
        df_h = df_h[df_h['Code_Cellule'].astype(str).str.contains(choix_code, na=False)].copy()

    # --- CALCULS ---
    # Conversion initiale en décimal
    df_m['Déviation mensuelle_dec'] = df_m['Déviation mensuelle'].apply(hhmm_to_decimal)
    df_m['Déviation à date_dec'] = df_m['Déviation à date'].apply(hhmm_to_decimal)

    df_h['Total_dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_dec'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_dec'] = df_h['Total_dec'] - df_h['Contrat_dec']

    # --- SECTION ALERTES HEBDO ---
    st.header(f"⚠️ Dépassements Hebdo - {secteurs_map[choix_code]}")
    
    def check_alerte(row):
        if row['Contrat_dec'] >= 35:
            return "🛑 TEMPS PLEIN > 40H" if row['Total_dec'] > 40 else "OK"
        else:
            if row['Total_dec'] > 34: return "🛑 TEMPS PARTIEL > 34H"
            if row['Ecart_dec'] > (row['Contrat_dec'] / 3): return "🟠 DÉPASSEMENT 1/3 CONTRAT"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    df_h_disp = df_h[df_h['Statut'] != "OK"].copy()
    df_h_disp['Heures'] = df_h_disp['Total_dec'].apply(decimal_to_hhmm)
    df_h_disp['Contrat'] = df_h_disp['Contrat_dec'].apply(decimal_to_hhmm)
    df_h_disp['Semaine du'] = df_h_disp['Début_dt'].dt.strftime('%d/%m/%Y')

    if not df_h_disp.empty:
        st.dataframe(df_h_disp[['Semaine du', 'Intervenant', 'Contrat', 'Heures', 'Statut']].style.apply(
            lambda x: ['background-color: #ff4b4b' if '🛑' in str(v) else 'background-color: #ffa500' if '🟠' in str(v) else '' for v in x], subset=['Statut']
        ), use_container_width=True, hide_index=True)
    else:
        st.success("Aucune alerte hebdomadaire.")

    # --- SECTION MODULATION MENSUELLE ---
    st.markdown("---")
    st.header(f"🎯 Suivi Modulation - {secteurs_map[choix_code]}")
    
    if 'notes' not in st.session_state: st.session_state.notes = {}
    df_m['Justification'] = df_m['Nom'].map(st.session_state.notes).fillna("")
    
    show_all = st.toggle("Afficher tous les salariés de la cellule", value=False)
    
    mask_ecart = (df_m['Déviation mensuelle_dec'] > 5) | (df_m['Déviation mensuelle_dec'] < -5)
    df_display = df_m if show_all else df_m[mask_ecart]

    # ÉDITEUR REACTIF
    st.info("Vous pouvez modifier 'Déviation à date' pour ajuster le bilan ou ajouter une justification.")
    edited_df = st.data_editor(
        df_display[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures', 'Justification']],
        column_config={
            "Déviation à date": st.column_config.TextColumn("Déviation à date (Modifiable HH:MM)"),
            "Justification": st.column_config.TextColumn("Commentaire", width="large")
        },
        use_container_width=True, hide_index=True, key="mod_editor"
    )

    # RE-CALCUL DES TOTAUX BASÉ SUR L'ÉDITEUR
    df_updated = df_m.copy()
    # On met à jour df_updated avec les valeurs modifiées dans l'éditeur
    for i, row in edited_df.iterrows():
        # On retrouve la ligne correspondante dans df_updated par le Nom
        idx = df_updated[df_updated['Nom'] == row['Nom']].index
        if not idx.empty:
             new_val_dec = hhmm_to_decimal(row['Déviation à date'])
             df_updated.loc[idx, 'Déviation à date_dec'] = new_val_dec
             # Sauvegarde note
             st.session_state.notes[row['Nom']] = row['Justification']

    # --- BILAN CELLULE RÉACTIF ---
    st.markdown("---")
    st.subheader(f"📊 Bilan de la Cellule : {secteurs_map[choix_code]}")
    
    # On recalcule les sommes sur df_updated (qui contient les valeurs modifiées)
    # Important : on doit ré-appliquer le filtre de secteur si on est en mode filtré
    if choix_code != "Toutes":
         df_bilan = df_updated[df_updated[col_secteur].astype(str).str.contains(choix_code, na=False)]
    else:
         df_bilan = df_updated

    pos = df_bilan[df_bilan['Déviation à date_dec'] > 0]['Déviation à date_dec'].sum()
    neg = df_bilan[df_bilan['Déviation à date_dec'] < 0]['Déviation à date_dec'].sum()
    solde = pos + neg
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Cumul Positif (+)", decimal_to_hhmm(pos))
    m2.metric("Cumul Négatif (-)", decimal_to_hhmm(neg))
    m3.metric("Solde Cellule", decimal_to_hhmm(solde), 
              delta="Déficit" if solde < 0 else "Surplus", 
              delta_color="inverse" if solde < 0 else "normal")

else:
    st.info("👋 Bonjour ! Importez vos fichiers pour piloter vos cellules.")
