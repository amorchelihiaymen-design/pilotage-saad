import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE PERSONNALISÉ ---
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

# --- FONCTION DE LECTURE ROBUSTE (Gère les erreurs d'encodage) ---
def load_csv(file):
    try:
        # Tentative en UTF-8 (standard moderne)
        return pd.read_csv(file, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        # Si échec, tentative en Latin-1 (standard exports Excel/Windows)
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='latin1')

# --- SIDEBAR : IMPORTATION ---
st.sidebar.title("📁 Importation Ximi")
st.sidebar.info("Chargez les fichiers pour activer le pilotage par secteur.")

file_mensuel = st.sidebar.file_uploader("1. Export MENSUEL (Modulation)", type=['csv', 'xlsx'])
file_hebdo = st.sidebar.file_uploader("2. Export HEBDO (Alertes)", type=['csv', 'xlsx'])

# Chargement sécurisé des fichiers
if file_mensuel and st.session_state.df_mensuel is None:
    if file_mensuel.name.endswith('.csv'):
        st.session_state.df_mensuel = load_csv(file_mensuel)
    else:
        st.session_state.df_mensuel = pd.read_excel(file_mensuel)

if file_hebdo and st.session_state.df_hebdo is None:
    if file_hebdo.name.endswith('.csv'):
        st.session_state.df_hebdo = load_csv(file_hebdo)
    else:
        st.session_state.df_hebdo = pd.read_excel(file_hebdo)

if st.sidebar.button("🗑️ Réinitialiser l'application"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- INTERFACE PRINCIPALE ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos exports Ximi dans la barre latérale pour commencer l'audit.")
else:
    # Création des onglets pour séparer les flux de travail
    tab_mois, tab_semaine = st.tabs(["📊 Suivi Mensuel (Modulation)", "📅 Suivi Hebdomadaire"])

    # --- ONGLET 1 : MENSUEL (Modulation) ---
    with tab_mois:
        if st.session_state.df_mensuel is not None:
            df_m = st.session_state.df_mensuel
            
            # Identification automatique de la colonne Secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df_m.columns else df_m.columns[1]
            secteurs = ["Tous"] + sorted(list(df_m[col_sec].unique()))
            sel_sec = st.selectbox("Sélectionner le Secteur à auditer", secteurs, key="sel_m")
            
            df_m_filtered = df_m if sel_sec == "Tous" else df_m[df_m[col_sec] == sel_sec]

            # Indicateurs de performance (KPI)
            # Nettoyage des données numériques (remplacement virgule par point pour les calculs)
            def clean_num(df, col):
                if col in df.columns:
                    return df[col].astype(str).str.replace(',', '.').astype(float).sum()
                return 0

            c1, c2, c3 = st.columns(3)
            with c1:
                h_eff = clean_num(df_m_filtered, 'Total heures travail effectif')
                st.metric("Total Travail Effectif", f"{round(h_eff, 2)}h")
            with col2:
                # [Image of a balance scale representing work-hour modulation]
                mod_total = clean_num(df_m_filtered, 'Déviation')
                st.metric("Modulation du Secteur", f"{round(mod_total, 2)}h", delta=f"{round(mod_total, 1)}")
            with c3:
                nb_interv = len(df_m_filtered)
                st.metric("Intervenants actifs", nb_interv)
            
            st.divider()
            
            # ÉDITEUR DE DONNÉES (MENSUEL)
            st.subheader(f"📝 Ajustement des compteurs : {sel_sec}")
            edited_m = st.data_editor(df_m_filtered, use_container_width=True, num_rows="dynamic", key="editor_m")
            
            if st.button("✅ Enregistrer les modifications Mensuelles"):
                st.session_state.df_mensuel.update(edited_m)
                st.success("Données mensuelles mises à jour dans la mémoire.")

            # EXPORT CSV MENSUEL
            csv_m = st.session_state.df_mensuel.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Télécharger EXPORT MENSUEL CORRIGÉ (CSV)",
                data=csv_m,
                file_name='Export_Mensuel_Optimise.csv',
                mime='text/csv',
            )

            # GRAPHIQUE DE MODULATION
            st.divider()
            if 'Intervenant' in df_m_filtered.columns and 'Déviation' in df_m_filtered.columns:
                st.subheader("📈 Visualisation de la modulation par intervenant")
                # On prépare les données pour le graphique (conversion numérique)
                chart_data = df_m_filtered.copy()
                chart_data['Déviation'] = chart_data['Déviation'].astype(str).str.replace(',', '.').astype(float)
                st.bar_chart(chart_data, x='Intervenant', y='Déviation')
        else:
            st.warning("Veuillez charger l'export mensuel.")

    # --- ONGLET 2 : HEBDO (Alertes) ---
    with tab_semaine:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo
            
            st.subheader("📝 Audit des compteurs Hebdomadaires")
            
            # ÉDITEUR DE DONNÉES (HEBDO)
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="editor_h")
            
            if st.button("✅ Enregistrer les modifications Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Données hebdomadaires mises à jour dans la mémoire.")

            # EXPORT CSV HEBDO
            csv_h = st.session_state.df_hebdo.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Télécharger EXPORT HEBDO CORRIGÉ (CSV)",
                data=csv_h,
                file_name='Export_Hebdo_Optimise.csv',
                mime='text/csv',
            )
        else:
            st.warning("Veuillez charger l'export hebdomadaire.")

# FOOTER SIDEBAR
st.sidebar.divider()
st.sidebar.caption("Développé par Aymen Amor | MSc emlyon | Agence Saint-Denis")

