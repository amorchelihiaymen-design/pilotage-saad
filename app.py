import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION DE LA MÉMOIRE (SESSION STATE) ---
if 'df_mensuel' not in st.session_state:
    st.session_state.df_mensuel = None
if 'df_hebdo' not in st.session_state:
    st.session_state.df_hebdo = None

# --- SIDEBAR : IMPORTATION ---
st.sidebar.title("📁 Importation Ximi")
st.sidebar.info("Chargez les deux fichiers pour activer les exports correspondants.")

file_mensuel = st.sidebar.file_uploader("1. Export MENSUEL (Modulation)", type=['csv', 'xlsx'])
file_hebdo = st.sidebar.file_uploader("2. Export HEBDO (Alertes)", type=['csv', 'xlsx'])

# Chargement Mensuel (avec séparateur ;)
if file_mensuel and st.session_state.df_mensuel is None:
    if file_mensuel.name.endswith('.csv'):
        st.session_state.df_mensuel = pd.read_csv(file_mensuel, sep=';')
    else:
        st.session_state.df_mensuel = pd.read_excel(file_mensuel)

# Chargement Hebdo (avec séparateur ;)
if file_hebdo and st.session_state.df_hebdo is None:
    if file_hebdo.name.endswith('.csv'):
        st.session_state.df_hebdo = pd.read_csv(file_hebdo, sep=';')
    else:
        st.session_state.df_hebdo = pd.read_excel(file_hebdo)

# Bouton de réinitialisation
if st.sidebar.button("🗑️ Réinitialiser les données"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- INTERFACE PRINCIPALE ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos fichiers Ximi dans la barre latérale pour commencer.")
else:
    # Création des onglets pour séparer les deux flux
    tab_mois, tab_semaine = st.tabs(["📊 Suivi Mensuel (Modulation)", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_mois:
        if st.session_state.df_mensuel is not None:
            df_m = st.session_state.df_mensuel
            
            # Gestion du secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df_m.columns else df_m.columns[1]
            secteurs = ["Tous"] + sorted(list(df_m[col_sec].unique()))
            sel_sec = st.selectbox("Filtrer par Secteur", secteurs, key="sel_m")
            
            df_m_filtered = df_m if sel_sec == "Tous" else df_m[df_m[col_sec] == sel_sec]

            # Dashboard Visuel
            c1, c2, c3 = st.columns(3)
            with c1:
                h_eff = df_m_filtered['Total heures travail effectif'].replace(',', '.', regex=True).astype(float).sum() if 'Total heures travail effectif' in df_m_filtered.columns else 0
                st.metric("Total Travail Effectif", f"{round(h_eff, 2)}h")
            with c2:
                mod_total = df_m_filtered['Déviation'].replace(',', '.', regex=True).astype(float).sum() if 'Déviation' in df_m_filtered.columns else 0
                st.metric("Modulation Secteur", f"{round(mod_total, 2)}h")
            
            st.divider()
            
            # ÉDITEUR (MENSUEL)
            st.subheader("📝 Correction des compteurs Mensuels")
            edited_m = st.data_editor(df_m_filtered, use_container_width=True, num_rows="dynamic", key="editor_mensuel")
            
            if st.button("✅ Valider les modifs Mensuelles"):
                st.session_state.df_mensuel.update(edited_m)
                st.success("Données mensuelles mises à jour !")

            # BOUTON EXPORT CSV MENSUEL
            csv_m = st.session_state.df_mensuel.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Télécharger EXPORT MENSUEL (CSV)",
                data=csv_m,
                file_name='Export_Compteurs_Mensuels_MAJ.csv',
                mime='text/csv',
            )
        else:
            st.warning("En attente de l'export mensuel...")

    # --- ONGLET HEBDO ---
    with tab_semaine:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo
            
            st.subheader("📝 Analyse des compteurs Hebdomadaires")
            
            # ÉDITEUR (HEBDO)
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="editor_hebdo")
            
            if st.button("✅ Valider les modifs Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Données hebdomadaires mises à jour !")

            # BOUTON EXPORT CSV HEBDO
            csv_h = st.session_state.df_hebdo.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Télécharger EXPORT HEBDO (CSV)",
                data=csv_h,
                file_name='Export_Compteurs_Hebdo_MAJ.csv',
                mime='text/csv',
            )
        else:
            st.warning("En attente de l'export hebdomadaire...")

# Footer
st.sidebar.divider()
st.sidebar.caption("Aymen Amor | emlyon Data Science | Agence Saint-Denis")
