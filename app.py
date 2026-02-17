import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS (DESIGN BLEU/GRIS) ---
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
    [data-testid="stMetricLabel"] { color: #4A4A4A !important; font-weight: 600 !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #1E3A8A !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CONVERSION ---

def to_hhmm(decimal_hours):
    """Affiche 151.67 sous la forme '151:40' pour les Metrics"""
    try:
        val = float(decimal_hours)
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
    """Lecture et forçage des types pour le tri"""
    try:
        # Lecture initiale
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        
        # Colonnes à transformer en NOMBRES pour permettre le tri numérique
        cols_numeriques = [
            'Hres de base', 'Hres trajet', 'Hres inactivité', 
            'Hres evts. interv.', 'Hres CP', 'Total heures travail effectif', 'Déviation'
        ]
        
        for col in df.columns:
            if col in cols_numeriques:
                # Nettoyage : on enlève les espaces, remplace la virgule, et force le nombre
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            else:
                # Pour les autres (Intervenant, Secteur), on force le texte pur pour le tri alphabétique
                df[col] = df[col].astype(str).fillna('')
                
        return df
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None

# --- INITIALISATION SESSION STATE ---
if 'df_mensuel' not in st.session_state:
    st.session_state.df_mensuel = None
if 'df_hebdo' not in st.session_state:
    st.session_state.df_hebdo = None

# --- SIDEBAR ---
st.sidebar.title("📁 Importation Ximi")
file_m = st.sidebar.file_uploader("1. Export MENSUEL (CSV)", type=['csv'])
file_h = st.sidebar.file_uploader("2. Export HEBDO (CSV)", type=['csv'])

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
    st.info("Veuillez charger vos fichiers CSV pour activer les fonctions de tri.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdomadaire"])

    with tab_m:
        if st.session_state.df_mensuel is not None:
            df = st.session_state.df_mensuel.copy()
            
            # Filtre Secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted(df[col_sec].unique())
            sel_sec = st.selectbox("Secteur principal", list_secteurs, key="m_sec")
            
            df_temp = df if sel_sec == "Tous" else df[df[col_sec] == sel_sec]

            # Recherche Type Excel
            search = st.text_input("🔍 Rechercher (Intervenant, Matricule...) :", key="search_m")
            if search:
                df_filt = df_temp[df_temp.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            else:
                df_filt = df_temp

            # Metrics (Calculées sur les vrais nombres)
            h_base_val = df_filt['Hres de base'].sum() if 'Hres de base' in df_filt.columns else 0
            h_trav_val = df_filt['Total heures travail effectif'].sum() if 'Total heures travail effectif' in df_filt.columns else 0
            dev_val = df_filt['Déviation'].sum() if 'Déviation' in df_filt.columns else 0

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Hres de base total", to_hhmm(h_base_val))
            with c2: st.metric("Travail Effectif", to_hhmm(h_trav_val))
            with c3: st.metric("Modulation (Déviation)", to_hhmm(dev_val))

            st.divider()
            
            # --- LE TABLEAU (TRI ENFIN FONCTIONNEL) ---
            st.subheader("📝 Analyse & Édition")
            st.caption("✅ **Tri :** Cliquez sur le titre de la colonne. | **Filtre :** Utilisez la barre de recherche ci-dessus.")
            
            edited = st.data_editor(
                df_filt, 
                use_container_width=True, 
                num_rows="dynamic", 
                key="ed_m",
                hide_index=True,
                column_config={
                    "Intervenant": st.column_config.TextColumn("Intervenant", width="large"),
                    "Déviation": st.column_config.NumberColumn("Déviation", format="%.2f")
                }
            )
            
            if st.button("💾 Enregistrer les modifications"):
                # On utilise l'index pour être sûr de mettre à jour la bonne ligne
                st.session_state.df_mensuel.update(edited)
                st.success("Données enregistrées !")

            # Export
            csv_data = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV corrigé", data=csv_data, file_name="Modulation_Mensuelle_MAJ.csv")

    with tab_h:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo.copy()
            st.subheader("📅 Audit Hebdomadaire")
            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h", hide_index=True)
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifié !")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process")
