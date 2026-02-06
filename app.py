import streamlit as st
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Pilotage RH & Modulation SAAD", layout="wide")

st.title("📊 Pilotage de la Modulation et Conformité Légale")
st.markdown("---")

# --- FONCTION DE CONVERSION HH:MM EN DÉCIMAL ---
def to_decimal(val):
    if pd.isna(val) or val == "" or "Somme" in str(val):
        return 0.0
    try:
        if ":" in str(val):
            parts = str(val).split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        return float(str(val).replace(',', '.'))
    except:
        return 0.0

# --- BARRE LATÉRALE : FILTRES ---
st.sidebar.header("Configuration")
secteurs = {
    "Toutes": "Toutes les cellules",
    "011": "Secteur 1",
    "012": "Secteur 2",
    "013": "Secteur 3"
}
choix_secteur = st.sidebar.selectbox(
    "Filtrer par Cellule", 
    options=list(secteurs.keys()), 
    format_func=lambda x: secteurs[x]
)

# --- CHARGEMENT DES FICHIERS ---
st.subheader("1. Importation des données")
col_f1, col_f2 = st.columns(2)

with col_f1:
    file_hebdo = st.file_uploader("📁 Export HEBDOMADAIRE (Générale)", type="csv")
with col_f2:
    file_mensuel = st.file_uploader("📁 Export MENSUEL (Contrôle Modulation)", type="csv")

if file_hebdo and file_mensuel:
    # Lecture des fichiers
    df_h = pd.read_csv(file_hebdo, sep=";", encoding="latin1")
    df_m = pd.read_csv(file_mensuel, sep=";", encoding="latin1")

    # Nettoyage des données (suppression des lignes de total)
    df_h = df_h[df_h['Intervenant'].notna() & ~df_h['Intervenant'].str.contains('Somme', na=False)]
    df_m = df_m[df_m['Nom'].notna() & ~df_m['Nom'].str.contains('Somme', na=False)]

    # Application du filtre secteur via le code du fichier mensuel
    if choix_secteur != "Toutes":
        df_m = df_m[df_m['Code'].astype(str).str.contains(choix_secteur)]
        noms_secteur = df_m['Nom'].unique()
        df_h = df_h[df_h['Intervenant'].isin(noms_secteur)]

    # --- CALCULS HEBDO ---
    df_h['Heures Totales Dec'] = df_h['Heures totales'].apply(to_decimal)
    df_h['Contrat Dec'] = df_h['Heures hebdo contrat'].astype(str).str.replace(',', '.').astype(float)
    df_h['Depassement'] = df_h['Heures Totales Dec'] - df_h['Contrat Dec']

    # --- CALCULS MENSUELS ---
    df_m['Déviation mensuelle'] = df_m['Déviation mensuelle'].astype(str).str.replace(',', '.').astype(float)
    df_m['Déviation à date'] = df_m['Déviation à date'].astype(str).str.replace(',', '.').astype(float)

    # --- AFFICHAGE DES ALERTES HEBDO ---
    st.markdown("---")
    st.header(f"⚠️ Alertes Hebdomadaires - {secteurs[choix_secteur]}")
    
    c1, c2 = st.columns(2)
    
    # Alerte 1 : Plus de 34h
    alert_34 = df_h[df_h['Heures Totales Dec'] > 34].copy()
    with c1:
        st.error(f"🛑 Alerte 34h ({len(alert_34)} salariés)")
        if not alert_34.empty:
            st.dataframe(alert_34[['Intervenant', 'Heures hebdo contrat', 'Heures totales']])
        else:
            st.success("Aucun dépassement de 34h")

    # Alerte 2 : Dépassement du 1/3 du contrat
    alert_tier = df_h[(df_h['Contrat Dec'] < 35) & (df_h['Depassement'] > (df_h['Contrat Dec'] / 3))].copy()
    with c2:
        st.warning(f"🟠 Dépassement 1/3 contrat ({len(alert_tier)} salariés)")
        if not alert_tier.empty:
            st.dataframe(alert_tier[['Intervenant', 'Heures hebdo contrat', 'Heures totales']])
        else:
            st.success("Respect de la règle du 1/3")

    # --- AFFICHAGE MODULATION MENSUELLE ---
    st.markdown("---")
    st.header(f"🎯 Suivi Modulation Mensuelle (Seuil +/- 5h)")
    
    # Filtrer ceux qui s'éloignent du 0 (plus de 5h ou moins de -5h)
    hors_zone = df_m[(df_m['Déviation mensuelle'] > 5) | (df_m['Déviation mensuelle'] < -5)].copy()
    
    st.write(f"Nombre de salariés hors zone cible : **{len(hors_zone)}**")
    
    # Affichage avec couleurs
    def color_modulation(val):
        color = 'orange' if val > 5 or val < -5 else 'white'
        if val > 10 or val < -10: color = 'red'
        return f'background-color: {color}'

    st.dataframe(
        df_m[['Nom', 'Heures mensuelles de base', 'Déviation mensuelle', 'Déviation à date', 'Potentiel heures']]
        .style.applymap(color_modulation, subset=['Déviation mensuelle'])
    )

    # Indicateur Global
    st.markdown("---")
    total_h = df_h['Heures Totales Dec'].sum()
    st.metric("Total Heures Cellule (Semaine)", f"{total_h:.2f} h", help="Objectif annuel global : 9200h")

else:
    st.info("Veuillez importer les fichiers 'Hebdomadaire' et 'Mensuel' pour analyser la situation.")
