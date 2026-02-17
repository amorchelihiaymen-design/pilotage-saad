import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS (METRICS & DESIGN) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }

    [data-testid="stMetricLabel"] {
        color: #4A4A4A !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #1E3A8A !important;
        font-weight: bold !important;
    }
    
    /* Style pour rendre le tableau plus grand par défaut */
    .stDataFrame {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CONVERSION ---

def to_hhmm(decimal_hours):
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
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def clean_numeric(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

# --- INITIALISATION SESSION STATE ---
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
            
            # Filtre Secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique() if pd.notna(s)])
            sel_sec = st.selectbox("Filtrer par Secteur", list_secteurs, key="m_sec")
            
            df_filt = df if sel_sec == "Tous" else df[df[col_sec].astype(str) == sel_sec]

            # Metrics
            h_base_val = clean_numeric(df_filt, 'Hres de base').sum()
            h_trav_val = clean_numeric(df_filt, 'Total heures travail effectif').sum()
            dev_val = clean_numeric(df_filt, 'Déviation').sum()

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Hres de base total", to_hhmm(h_base_val))
            with c2: st.metric("Travail Effectif", to_hhmm(h_trav_val))
            with c3: st.metric("Modulation (Déviation)", to_hhmm(dev_val))

            st.divider()
            
            # --- AJOUT DE LA RECHERCHE STYLE EXCEL ---
            st.subheader("📝 Analyse & Édition")
            st.caption("💡 Astuce : Cliquez sur les en-têtes pour trier. Utilisez la loupe en haut à droite du tableau pour filtrer.")
            
            # Utilisation de st.data_editor avec tri activé
            edited = st.data_editor(
                df_filt, 
                use_container_width=True, 
                num_rows="dynamic", 
                key="ed_m",
                hide_index=True # Pour un look plus Excel/Tableau pro
            )
            
            if st.button("💾 Enregistrer les modifications"):
                st.session_state.df_mensuel.update(edited)
                st.success("Données enregistrées !")

            # Export
            csv_out = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV", data=csv_out, file_name="Modulation_Mensuelle_MAJ.csv")
            
            # Graphique
            st.divider()
            st.subheader("📈 Graphique de Modulation")
            df_chart = df_filt.copy()
            df_chart['Modul_Num'] = clean_numeric(df_chart, 'Déviation')
            st.bar_chart(df_chart, x='Intervenant', y='Modul_Num')

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo
            st.subheader("📅 Audit Hebdomadaire")
            
            edited_h = st.data_editor(
                df_h, 
                use_container_width=True, 
                num_rows="dynamic", 
                key="ed_h",
                hide_index=True
            )
            
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifié !")

            csv_h_out = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV Hebdo", data=csv_h_out, file_name="Hebdo_MAJ.csv")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expertise Data & Process")
