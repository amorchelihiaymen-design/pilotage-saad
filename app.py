import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS (COULEURS DES METRICS) ---
st.markdown("""
    <style>
    /* Fond de l'application */
    .main { background-color: #f5f7f9; }
    
    /* Conteneur des metrics */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }

    /* Couleur du TEXTE des metrics (Labels) - Gris Anthracite */
    [data-testid="stMetricLabel"] {
        color: #4A4A4A !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }

    /* Couleur des CHIFFRES des metrics (Valeurs) - Bleu Marine */
    [data-testid="stMetricValue"] {
        color: #1E3A8A !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CONVERSION & NETTOYAGE ---

def to_hhmm(decimal_hours):
    """Convertit une durée décimale (ex: 151.67) en format horaire (ex: '151:40')"""
    try:
        val = float(str(decimal_hours).replace(',', '.'))
        abs_val = abs(val)
        hours = int(abs_val)
        minutes = int(round((abs_val - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        sign = "-" if val < 0 else ""
        return f"{sign}{hours:02d}:{minutes:02d}"
    except:
        return "00:00"

def robust_read_csv(file):
    """Lecture avec gestion des encodages Windows (Latin-1) et UTF-8"""
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def clean_numeric(df, col):
    """Nettoie les colonnes numériques contenant des virgules (ex: '151,67')"""
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

# --- INITIALISATION MÉMOIRE (SESSION STATE) ---
if 'df_mensuel' not in st.session_state:
    st.session_state.df_mensuel = None
if 'df_hebdo' not in st.session_state:
    st.session_state.df_hebdo = None

# --- SIDEBAR : IMPORTATION ---
st.sidebar.title("📁 Importation Ximi")
file_m = st.sidebar.file_uploader("1. Export MENSUEL (CSV)", type=['csv'])
file_h = st.sidebar.file_uploader("2. Export HEBDO (CSV)", type=['csv'])

if file_m and st.session_state.df_mensuel is None:
    st.session_state.df_mensuel = robust_read_csv(file_m)
if file_h and st.session_state.df_hebdo is None:
    st.session_state.df_hebdo = robust_read_csv(file_h)

if st.sidebar.button("🗑️ Réinitialiser les données"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- CORPS DE L'APPLI ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos fichiers CSV pour activer le tableau de bord.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_mensuel is not None:
            df = st.session_state.df_mensuel
            
            # Correction du TypeError : Conversion en string pour éviter les conflits lors du tri
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique() if pd.notna(s)])
            sel_sec = st.selectbox("Choisir un Secteur", list_secteurs, key="m_sec")
            
            df_filt = df if sel_sec == "Tous" else df[df[col_sec].astype(str) == sel_sec]

            # Calculs avec conversion immédiate en hh:mm pour l'affichage
            h_base_val = clean_numeric(df_filt, 'Hres de base').sum()
            h_trav_val = clean_numeric(df_filt, 'Total heures travail effectif').sum()
            dev_val = clean_numeric(df_filt, 'Déviation').sum()

            # Affichage des Metrics avec le nouveau style visuel
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Hres de base total", to_hhmm(h_base_val))
            with c2:
                st.metric("Travail Effectif", to_hhmm(h_trav_val))
            with c3:
                st.metric("Modulation (Déviation)", to_hhmm(dev_val))

            st.divider()
            
            st.subheader("📝 Édition des données")
            edited = st.data_editor(df_filt, use_container_width=True, num_rows="dynamic", key="ed_m")
            
            if st.button("💾 Enregistrer les modifications du mois"):
                st.session_state.df_mensuel.update(edited)
                st.success("Modifications enregistrées !")

            # Bouton d'export
            csv_out = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger l'export CSV Mensuel", data=csv_out, file_name="Modulation_Mensuelle_MAJ.csv")
            
            # Graphique de Modulation
            st.divider()
            st.subheader("📈 Graphique de Modulation par Intervenant")
            df_chart = df_filt.copy()
            df_chart['Modul_Num'] = clean_numeric(df_chart, 'Déviation')
            st.bar_chart(df_chart, x='Intervenant', y='Modul_Num')

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo
            st.subheader("📅 Audit Hebdomadaire")
            
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h")
            
            if st.button("💾 Enregistrer les modifications Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifications hebdomadaires enregistrées !")

            csv_h_out = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger l'export CSV Hebdo", data=csv_h_out, file_name="Hebdo_MAJ.csv")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")
