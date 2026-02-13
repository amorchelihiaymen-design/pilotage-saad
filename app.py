import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE VISUEL ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION SESSION STATE ---
if 'df_mensuel' not in st.session_state:
    st.session_state.df_mensuel = None
if 'df_hebdo' not in st.session_state:
    st.session_state.df_hebdo = None

# --- FONCTION DE CHARGEMENT ROBUSTE ---
def robust_read_csv(file):
    try:
        # On essaie d'abord en Latin-1 (standard Excel/Windows souvent utilisé par Ximi)
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        if len(df.columns) < 2: # Si le séparateur n'est pas bon
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='latin-1')
        return df
    except Exception:
        try:
            # Deuxième essai en UTF-8
            file.seek(0)
            return pd.read_csv(file, sep=';', encoding='utf-8')
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")
            return None

def clean_numeric_col(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

# --- SIDEBAR : IMPORTATION ---
st.sidebar.title("📁 Importation Ximi")
file_mensuel = st.sidebar.file_uploader("1. Export MENSUEL (Modulation)", type=['csv', 'xlsx'])
file_hebdo = st.sidebar.file_uploader("2. Export HEBDO (Alertes)", type=['csv', 'xlsx'])

# Logique de chargement
if file_mensuel and st.session_state.df_mensuel is None:
    if file_mensuel.name.endswith('.csv'):
        st.session_state.df_mensuel = robust_read_csv(file_mensuel)
    else:
        st.session_state.df_mensuel = pd.read_excel(file_mensuel)

if file_hebdo and st.session_state.df_hebdo is None:
    if file_hebdo.name.endswith('.csv'):
        st.session_state.df_hebdo = robust_read_csv(file_hebdo)
    else:
        st.session_state.df_hebdo = pd.read_excel(file_hebdo)

if st.sidebar.button("🗑️ Réinitialiser tout"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- CORPS DE L'APPLICATION ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos fichiers CSV dans la barre latérale.")
else:
    tab_mois, tab_semaine = st.tabs(["📊 Suivi Mensuel (Modulation)", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_mois:
        if st.session_state.df_mensuel is not None:
            df_m = st.session_state.df_mensuel
            
            # Filtre par Secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df_m.columns else df_m.columns[1]
            secteurs = ["Tous"] + sorted(list(df_m[col_sec].unique()))
            sel_sec = st.selectbox("Auditer un Secteur", secteurs, key="m_sec")
            
            df_m_filtered = df_m if sel_sec == "Tous" else df_m[df_m[col_sec] == sel_sec]

            # Calcul des Metrics avec nettoyage des virgules
            h_travail = clean_numeric_col(df_m_filtered, 'Total heures travail effectif').sum()
            modulation = clean_numeric_col(df_m_filtered, 'Déviation').sum()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Heures Travail Effectif", f"{round(h_travail, 2)}h")
            with c2:
                st.metric("Modulation Cumulée", f"{round(modulation, 2)}h")
            with c3:
                st.metric("Effectif", f"{len(df_m_filtered)}")

            st.divider()

            # Éditeur
            st.subheader(f"📝 Modifications : {sel_sec}")
            edited_m = st.data_editor(df_m_filtered, use_container_width=True, num_rows="dynamic", key="editor_m")
            
            if st.button("💾 Enregistrer les modifs Mensuelles"):
                # Mise à jour globale
                st.session_state.df_mensuel.update(edited_m)
                st.success("Données mémorisées.")

            # Download
            csv_m = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger Export MENSUEL Corrigé", data=csv_m, file_name="Modulation_Mensuelle_MAJ.csv", mime="text/csv")

            # Graphique
            if 'Intervenant' in df_m_filtered.columns:
                st.divider()
                st.subheader("📈 Vue Graphique de la Modulation")
                # Préparation données graphiques
                df_chart = df_m_filtered.copy()
                df_chart['Déviation'] = clean_numeric_col(df_chart, 'Déviation')
                st.bar_chart(df_chart, x='Intervenant', y='Déviation')
        else:
            st.warning("Export Mensuel manquant.")

    # --- ONGLET HEBDO ---
    with tab_semaine:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo
            
            st.subheader("📝 Analyse Hebdomadaire (Alertes)")
            
            # Éditeur Hebdo
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="editor_h")
            
            if st.button("💾 Enregistrer les modifs Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Données hebdomadaires mémorisées.")

            # Download
            csv_h = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger Export HEBDO Corrigé", data=csv_h, file_name="Alertes_Hebdo_MAJ.csv", mime="text/csv")
