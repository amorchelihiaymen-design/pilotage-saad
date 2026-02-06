import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Pilotage Cellules - Modulation & Conformité", layout="wide")

# --- FONCTIONS DE CONVERSION ---
def hhmm_to_decimal(val):
    if pd.isna(val) or val == "" or "Somme" in str(val): return 0.0
    try:
        val_str = str(val).strip()
        if ":" in val_str:
            parts = val_str.split(':')
            return int(parts[0]) + (int(parts[1]) / 60.0 if len(parts) > 1 else 0.0)
        return float(val_str.replace(',', '.'))
    except: return 0.0

def decimal_to_hhmm(dec):
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
    
    # Correction V2 : Déviation cumulée -> Déviation à date
    if 'Déviation cumulée' in df_m.columns:
        df_m = df_m.rename(columns={'Déviation cumulée': 'Déviation à date'})
    
    # Identification de la colonne secteur (Code.1 ou Code)
    col_secteur = 'Code'
    for c in df_m.columns:
        if 'Code' in c:
            if any(s in str(df_m[c].iloc[0]) for s in ['11', '12', '13']):
                col_secteur = c
                break

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
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_dec'] = df_m[col].apply(hhmm_to_decimal)

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
            if row['Ecart_dec'] > (row['Contrat_dec'] / 3): return "🟠 DÉPASSEMENT 1/3"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    df_h_disp = df_h[df_h['Statut'] != "OK"].copy()
    
    # Affichage Hebdo
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

    # PREPARATION AFFICHAGE HH:MM POUR LE TABLEAU (TOUT EN GARDANT LE TRI NUMERIQUE)
    # On crée des colonnes de texte pour l'édition mais on gardera les dec pour le calcul
    df_edit = df_display.copy()
    df_edit['Déviation mensuelle'] = df_edit['Déviation mensuelle_dec'].apply(decimal_to_hhmm)
    df_edit['Déviation à date'] = df_edit['Déviation à date_dec'].apply(decimal_to_hhmm)
    df_edit['Potentiel heures'] = df_edit['Potentiel heures_dec'].apply(decimal_to_hhmm)

    st.info("💡 Modifiez 'Déviation à date' (ex: 00:00) pour voir les compteurs en bas s'ajuster.")
    edited_df = st.data_editor(
        df_edit[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures', 'Justification']],
        column_config={
            "Déviation à date": st.column_config.TextColumn("Déviation à date (HH:MM)"),
            "Justification": st.column_config.TextColumn("Commentaire", width="large")
        },
        use_container_width=True, hide_index=True, key="mod_editor"
    )

    # RE-CALCUL DES TOTAUX BASÉ SUR L'ÉDITEUR
    # On reconstruit un dataframe global mis à jour
    df_updated = df_m.copy()
    for _, row in edited_df.iterrows():
        # Mise à jour des valeurs éditées
        new_dec = hhmm_to_decimal(row['Déviation à date'])
        df_updated.loc[df_updated['Nom'] == row['Nom'], 'Déviation à date_dec'] = new_dec
        st.session_state.notes[row['Nom']] = row['Justification']

    # --- BILAN CELLULE RÉACTIF ---
    st.markdown("---")
    st.subheader(f"📊 Bilan Global de la Cellule : {secteurs_map[choix_code]}")
    
    # Le calcul se fait sur TOUTES les lignes de la cellule, avec les modifs de l'éditeur
    pos = df_updated[df_updated['Déviation à date_dec'] > 0]['Déviation à date_dec'].sum()
    neg = df_updated[df_updated['Déviation à date_dec'] < 0]['Déviation à date_dec'].sum()
    solde = pos + neg
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Cumul Positif (+)", decimal_to_hhmm(pos))
    m2.metric("Cumul Négatif (-)", decimal_to_hhmm(neg))
    m3.metric("Solde Net Cellule", decimal_to_hhmm(solde), 
              delta="Déficit" if solde < 0 else "Surplus", 
              delta_color="inverse" if solde < 0 else "normal")

else:
    st.info("👋 Bonjour ! Importez vos fichiers pour piloter vos cellules. Cette solution arrive quand elle doit arriver pour vous simplifier la vie !")
