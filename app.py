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

# --- FONCTIONS DE CONVERSION ---

def to_hhmm(decimal_hours):
    """Convertit 151.67 en '151:40'"""
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
    """Lecture avec gestion des encodages Windows/Ximi"""
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def clean_numeric(df, col):
    """Transforme les textes '151,67' en nombres réels"""
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
file_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
file_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

if file_m and st.session_state.df_mensuel is None:
    st.session_state.df_mensuel = robust_read_csv(file_m)
if file_h and st.session_state.df_hebdo is None:
    st.session_state.df_hebdo = robust_read_csv(file_h)

if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- CORPS DE L'APPLI ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos fichiers CSV pour commencer.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_mensuel is not None:
            df = st.session_state.df_mensuel
            
            # Correction du TypeError : Conversion en string avant le tri
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique() if pd.notna(s)])
            sel_sec = st.selectbox("Secteur", list_secteurs, key="m_sec")
            
            df_filt = df if sel_sec == "Tous" else df[df[col_sec].astype(str) == sel_sec]

            # Calculs et Conversion en hh:mm
            h_base_val = clean_numeric(df_filt, 'Hres de base').sum()
            h_trav_val = clean_numeric(df_filt, 'Total heures travail effectif').sum()
            dev_val = clean_numeric(df_filt, 'Déviation').sum()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Hres de base total", to_hhmm(h_base_val))
            with c2:
                st.metric("Travail Effectif", to_hhmm(h_trav_val))
            with c3:
                st.metric("Modulation (Déviation)", to_hhmm(dev_val))

            st.divider()
            
            st.subheader("📝 Édition")
            edited = st.data_editor(df_filt, use_container_width=True, num_rows="dynamic", key="ed_m")
            
            if st.button("💾 Enregistrer Mois"):
                st.session_state.df_mensuel.update(edited)
                st.success("Modifié !")

            # Export
            csv = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV Mensuel", data=csv, file_name="Modulation_MAJ.csv")
            
            # Graphique (en heures décimales pour l'axe)
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
            
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h")
            
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifié !")

            csv_h = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV Hebdo", data=csv_h, file_name="Hebdo_MAJ.csv")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Process")
