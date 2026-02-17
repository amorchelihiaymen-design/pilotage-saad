import streamlit as st
import pandas as pd
import altair as alt
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
    """Convertit 151.67 en '151:40'"""
    try:
        val = float(decimal_hours)
        abs_val = abs(val)
        hours = int(abs_val)
        minutes = int(round((abs_val - hours) * 60))
        if minutes == 60: hours += 1; minutes = 0
        sign = "-" if val < 0 else ""
        return f"{sign}{hours:02d}:{minutes:02d}"
    except:
        return "00:00"

def robust_read_csv(file):
    """Lecture et nettoyage des exports Ximi"""
    try:
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        cols_numeriques = [
            'Hres de base', 'Hres trajet', 'Hres inactivité', 
            'Hres evts. interv.', 'Hres CP', 'Total heures travail effectif', 'Déviation',
            'Heures hebdo contrat'
        ]
        for col in df.columns:
            if col in cols_numeriques:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            else:
                df[col] = df[col].astype(str).str.strip()
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
    st.info("Veuillez charger vos fichiers CSV pour activer le tableau de bord.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_mensuel is not None:
            df = st.session_state.df_mensuel.copy()
            
            # Filtre Secteur
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique()])
            sel_sec = st.selectbox("Secteur principal", list_secteurs, key="m_sec")
            
            df_temp = df if sel_sec == "Tous" else df[df[col_sec] == sel_sec]

            # Recherche Type Excel
            search = st.text_input("🔍 Rechercher un intervenant :", key="search_m")
            if search:
                df_filt = df_temp[df_temp.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            else:
                df_filt = df_temp

            # CALCUL DES WIDGETS (Déviations +/-)
            if 'Déviation' in df_filt.columns:
                series_dev = df_filt['Déviation']
                pos_dev = series_dev[series_dev > 0].sum()
                neg_dev = series_dev[series_dev < 0].sum()
                total_dev = series_dev.sum()
            else:
                pos_dev, neg_dev, total_dev = 0, 0, 0

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Déviations (+) (A payer)", to_hhmm(pos_dev))
            with c2: st.metric("Déviations (-) (A rattraper)", to_hhmm(neg_dev))
            with c3: st.metric("Balance Globale", to_hhmm(total_dev))

            st.divider()
            
            # --- ANALYSE & ÉDITION (Colonnes Masquées) ---
            st.subheader("📝 Analyse & Édition")
            hidden_mensuel = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
            visible_mensuel = [c for c in df_filt.columns if c not in hidden_mensuel]
            
            edited = st.data_editor(
                df_filt, 
                use_container_width=True, 
                num_rows="dynamic", 
                key="ed_m",
                hide_index=True,
                column_order=visible_mensuel,
                column_config={
                    "Intervenant": st.column_config.TextColumn("Intervenant", width="large"),
                    "Déviation": st.column_config.NumberColumn("Déviation", format="%.2f")
                }
            )
            
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("💾 Enregistrer"):
                    st.session_state.df_mensuel.update(edited)
                    st.success("Enregistré !")
            with col_btn2:
                csv_data = st.session_state.df_mensuel.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Télécharger CSV", data=csv_data, file_name="Modulation_Mensuelle_MAJ.csv")

            # --- GRAPHIQUE AVEC VALEURS APPARENTES ---
            st.divider()
            st.subheader("📈 Vue d'ensemble (Valeurs apparentes)")
            
            if not df_filt.empty and 'Déviation' in df_filt.columns:
                df_chart = df_filt[['Intervenant', 'Déviation']].copy()
                df_chart = df_chart.sort_values(by='Déviation', ascending=False)
                
                # Création du graphique avec Altair
                base = alt.Chart(df_chart).encode(
                    x=alt.X('Intervenant:N', sort='-y', title="Intervenant"),
                    y=alt.Y('Déviation:Q', title="Déviation (heures)")
                )

                bars = base.mark_bar(color='#1E3A8A')

                # Ajout des labels (valeurs apparentes)
                text = base.mark_text(
                    align='center',
                    baseline='bottom',
                    dy=alt.condition(alt.datum.Déviation >= 0, alt.value(-5), alt.value(15)),
                    color='#4A4A4A',
                    fontWeight='bold'
                ).encode(
                    text=alt.Text('Déviation:Q', format='.2f')
                )

                st.altair_chart((bars + text), use_container_width=True)
            else:
                st.info("Chargez des données pour afficher le graphique.")

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo.copy()
            st.subheader("📅 Audit Hebdomadaire")
            
            hidden_hebdo = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            visible_hebdo = [c for c in df_h.columns if c not in hidden_hebdo]

            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h", hide_index=True, column_order=visible_hebdo)
            
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifié !")

            csv_h_out = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV Hebdo", data=csv_h_out, file_name="Hebdo_MAJ.csv")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process")
