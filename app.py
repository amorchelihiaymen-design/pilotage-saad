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
    """Convertit un nombre (12.5) en texte propre (12:30)"""
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

# --- BARRE LATÉRALE : FILTRES ET TRIS ---
st.sidebar.header("1. Gestion des Cellules")
secteurs_map = {
    "Toutes": "Toutes les cellules",
    "11": "Secteur 1 (011)",
    "12": "Secteur 2 (012)",
    "13": "Secteur 3 (013)"
}
choix_code = st.sidebar.selectbox("Sélectionner la Cellule", options=list(secteurs_map.keys()), format_func=lambda x: secteurs_map[x])

st.sidebar.markdown("---")
st.sidebar.header("2. Options de Tri Mensuel")
tri_col_m = st.sidebar.selectbox("Trier le Mensuel par :", 
                               options=['Déviation à date', 'Déviation mensuelle', 'Potentiel heures', 'Nom'])
tri_ordre_m = st.sidebar.radio("Ordre Mensuel :", ["Décroissant", "Croissant"], key="tri_m")

st.sidebar.markdown("---")
st.sidebar.header("3. Options de Tri Hebdo")
tri_col_h = st.sidebar.selectbox("Trier l'Hebdo par :", 
                               options=['Heures totales', 'Heures contrat', 'Date', 'Intervenant'])
tri_ordre_h = st.sidebar.radio("Ordre Hebdo :", ["Décroissant", "Croissant"], key="tri_h")

# --- CHARGEMENT DES FICHIERS ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    files_hebdo = st.file_uploader("📂 Exports HEBDOMADAIRES", type="csv", accept_multiple_files=True)
with col_f2:
    file_mensuel = st.file_uploader("📂 Export MENSUEL", type="csv")

if files_hebdo and file_mensuel:
    # --- TRAITEMENT MENSUEL ---
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].astype(str).str.contains('Somme', case=False, na=False)]
    
    if 'Déviation cumulée' in df_m.columns:
        df_m = df_m.rename(columns={'Déviation cumulée': 'Déviation à date'})
    
    col_secteur = 'Code'
    for c in df_m.columns:
        if 'Code' in c:
            sample = str(df_m[c].iloc[0])
            if any(s in sample for s in ['11', '12', '13']):
                col_secteur = c
                break

    mapping_cellule = df_m.set_index('Nom')[col_secteur].astype(str).to_dict()

    # --- TRAITEMENT HEBDO ---
    list_dfs = [pd.read_csv(f, sep=";", encoding="latin1") for f in files_hebdo]
    df_h = pd.concat(list_dfs)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].astype(str).str.contains('Somme', case=False, na=False)]
    df_h['Code_Cellule'] = df_h['Intervenant'].map(mapping_cellule)
    df_h['Début_dt'] = pd.to_datetime(df_h['Début'], dayfirst=True)

    # --- APPLICATION DU FILTRE CELLULE ---
    if choix_code != "Toutes":
        df_m = df_m[df_m[col_secteur].astype(str).str.contains(choix_code, na=False)].copy()
        df_h = df_h[df_h['Code_Cellule'].astype(str).str.contains(choix_code, na=False)].copy()

    # --- CALCULS NUMÉRIQUES ---
    for col in ['Déviation mensuelle', 'Déviation à date', 'Potentiel heures']:
        df_m[col + '_num'] = df_m[col].apply(hhmm_to_decimal)

    df_h['Total_num'] = df_h['Heures totales'].apply(hhmm_to_decimal)
    df_h['Contrat_num'] = df_h['Heures hebdo contrat'].apply(hhmm_to_decimal)
    df_h['Ecart_num'] = df_h['Total_num'] - df_h['Contrat_num']

    # --- SECTION ALERTES HEBDO ---
    st.header(f"⚠️ Dépassements Hebdo - {secteurs_map[choix_code]}")
    
    def check_alerte(row):
        if row['Contrat_num'] >= 35:
            return "🛑 TEMPS PLEIN > 40H" if row['Total_num'] > 40 else "OK"
        else:
            if row['Total_num'] > 34: return "🛑 TEMPS PARTIEL > 34H"
            if row['Ecart_num'] > (row['Contrat_num'] / 3): return "🟠 DÉPASSEMENT 1/3"
            return "OK"

    df_h['Statut'] = df_h.apply(check_alerte, axis=1)
    
    # TRI NUMÉRIQUE HEBDO
    map_tri_h = {'Intervenant': 'Intervenant', 'Date': 'Début_dt', 
                 'Heures totales': 'Total_num', 'Heures contrat': 'Contrat_num'}
    df_h = df_h.sort_values(by=map_tri_h[tri_col_h], ascending=(tri_ordre_h == "Croissant"))
    
    df_h_disp = df_h[df_h['Statut'] != "OK"].copy()
    df_h_disp['Heures'] = df_h_disp['Total_num'].apply(decimal_to_hhmm)
    df_h_disp['Contrat'] = df_h_disp['Contrat_num'].apply(decimal_to_hhmm)
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
    
    # TRI NUMÉRIQUE MENSUEL
    map_tri_m = {'Nom': 'Nom', 'Déviation à date': 'Déviation à date_num', 
                 'Déviation mensuelle': 'Déviation mensuelle_num', 'Potentiel heures': 'Potentiel heures_num'}
    df_m = df_m.sort_values(by=map_tri_m[tri_col_m], ascending=(tri_ordre_m == "Croissant"))

    show_all = st.toggle("Afficher toute la cellule", value=False)
    mask_ecart = (df_m['Déviation mensuelle_num'] > 5) | (df_m['Déviation mensuelle_num'] < -5)
    df_display = df_m if show_all else df_m[mask_ecart]

    # Formatage HH:MM
    df_edit = df_display.copy()
    df_edit['Déviation mensuelle'] = df_edit['Déviation mensuelle_num'].apply(decimal_to_hhmm)
    df_edit['Déviation à date'] = df_edit['Déviation à date_num'].apply(decimal_to_hhmm)
    df_edit['Potentiel'] = df_edit['Potentiel heures_num'].apply(decimal_to_hhmm)

    st.info("💡 Modifiez la 'Déviation à date' ou ajoutez un commentaire.")
    edited_df = st.data_editor(
        df_edit[['Nom', 'Déviation mensuelle', 'Déviation à date', 'Potentiel', 'Justification']],
        column_config={
            "Déviation à date": st.column_config.TextColumn("Déviation à date (HH:MM)"),
            "Justification": st.column_config.TextColumn("Commentaire", width="large")
        },
        use_container_width=True, hide_index=True, key="mod_editor"
    )

    # --- MISE À JOUR DYNAMIQUE ---
    for _, row in edited_df.iterrows():
        new_dec = hhmm_to_decimal(row['Déviation à date'])
        df_m.loc[df_m['Nom'] == row['Nom'], 'Déviation à date_num'] = new_dec
        st.session_state.notes[row['Nom']] = row['Justification']

    # Bilan Global
    st.markdown("---")
    st.subheader(f"📊 Bilan Global de la Cellule : {secteurs_map[choix_code]}")
    
    pos = df_m[df_m['Déviation à date_num'] > 0]['Déviation à date_num'].sum()
    neg = df_m[df_m['Déviation à date_num'] < 0]['Déviation à date_num'].sum()
    solde = pos + neg
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Cumul Positif (+)", decimal_to_hhmm(pos))
    m2.metric("Cumul Négatif (-)", decimal_to_hhmm(neg))
    m3.metric("Solde Cellule", decimal_to_hhmm(solde), delta="Déficit" if solde < 0 else "Surplus", delta_color="inverse" if solde < 0 else "normal")

else:
    st.info("👋 Bonjour ! Importez vos fichiers pour piloter vos cellules.")
