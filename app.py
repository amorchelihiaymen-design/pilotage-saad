import streamlit as st
import pandas as pd
import io
import altair as alt

# --- CONFIGURATION ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS (DESIGN PEPS & PRO) ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #1E3A8A;
    }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { color: #1E3A8A !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CONVERSION ---

def to_hhmm(decimal_hours):
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

def hhmm_to_decimal(hhmm_str):
    try:
        if pd.isna(hhmm_str) or str(hhmm_str).strip() == "": return 0.0
        h, m = map(int, str(hhmm_str).split(':'))
        return h + (m / 60)
    except:
        return 0.0

def robust_read_csv(file):
    try:
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        cols_num = ['Hres de base', 'Total heures travail effectif', 'Déviation', 'Heures hebdo contrat']
        for col in df.columns:
            if col in cols_num:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
            else:
                df[col] = df[col].astype(str).str.strip()
        return df
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

# --- INITIALISATION ---
if 'df_m' not in st.session_state: st.session_state.df_m = None
if 'df_h' not in st.session_state: st.session_state.df_h = None

# --- SIDEBAR ---
st.sidebar.title("📁 Importation Ximi")
f_m = st.sidebar.file_uploader("1. Export MENSUEL (Source Secteurs)", type=['csv'])
f_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

if f_m and st.session_state.df_m is None: st.session_state.df_m = robust_read_csv(f_m)
if f_h and st.session_state.df_h is None: st.session_state.df_h = robust_read_csv(f_h)

if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_m = None
    st.session_state.df_h = None
    st.rerun()

# --- CORPS DE L'APPLI ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_m is None and st.session_state.df_h is None:
    st.info("Veuillez charger vos exports pour démarrer l'audit par secteur.")
else:
    # --- LOGIQUE DE MAPPING DES SECTEURS ---
    # On crée un dictionnaire {Nom Intervenant: Secteur} à partir du mensuel
    mapping_secteurs = {}
    if st.session_state.df_m is not None:
        df_src = st.session_state.df_m
        col_sec_src = 'Secteur intervenant' if 'Secteur intervenant' in df_src.columns else df_src.columns[1]
        mapping_secteurs = df_src.drop_duplicates('Intervenant').set_index('Intervenant')[col_sec_src].to_dict()

    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdo & Alertes"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_m is not None:
            df = st.session_state.df_m.copy()
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique() if pd.notna(s)])
            sel_sec_m = st.selectbox("Secteur (Mensuel)", secteurs, key="m_sec")
            df_filt_m = df if sel_sec_m == "Tous" else df[df[col_sec] == sel_sec_m]

            # Metrics
            dev_pos = df_filt_m['Déviation'][df_filt_m['Déviation'] > 0].sum()
            dev_neg = df_filt_m['Déviation'][df_filt_m['Déviation'] < 0].sum()
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Déviations (+)", to_hhmm(dev_pos))
            with c2: st.metric("Déviations (-)", to_hhmm(dev_neg))
            with c3: st.metric("Balance", to_hhmm(df_filt_m['Déviation'].sum()))

            st.divider()
            hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
            st.data_editor(df_filt_m, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_m.columns if c not in hidden_m])

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_h is not None:
            df_h = st.session_state.df_h.copy()
            
            # Application du Secteur dans l'Hebdo via le mapping
            df_h['Secteur'] = df_h['Intervenant'].map(mapping_secteurs).fillna("Non répertorié")
            
            # Filtre par Secteur (Synchronisé ou indépendant)
            list_sec_h = ["Tous"] + sorted([str(s) for s in df_h['Secteur'].unique()])
            sel_sec_h = st.selectbox("Filtrer l'Hebdo par Secteur", list_sec_h, key="h_sec")
            df_filt_h = df_h if sel_sec_h == "Tous" else df_h[df_h['Secteur'] == sel_sec_h]

            st.subheader(f"📅 Audit Hebdomadaire : {sel_sec_h}")
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            st.data_editor(df_filt_h, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_h.columns if c not in hidden_h])

            # --- ANALYSE DE CONFORMITÉ (34H/40H/TIERS) ---
            st.divider()
            st.markdown("### 🔔 Alertes de Conformité")
            
            df_filt_h['Total_Dec'] = df_filt_h['Heures totales'].apply(hhmm_to_decimal)
            df_filt_h['Is_TempsPlein'] = df_filt_h['Heures hebdo contrat'] >= 35
            
            def analyze_risk(row):
                if not row['Is_TempsPlein']:
                    if row['Total_Dec'] > 34: return "🚫 Dépassement Seuil 34h"
                    if (row['Total_Dec'] - row['Heures hebdo contrat']) > (row['Heures hebdo contrat'] / 3): 
                        return "🔴 > 1/3 Temps Partiel"
                else:
                    if row['Total_Dec'] > 40: return "🚫 Dépassement 40h (Temps Plein)"
                return "✅ Conforme"

            df_filt_h['Diagnostic'] = df_filt_h.apply(analyze_risk, axis=1)
            df_alerts = df_filt_h[df_filt_h['Diagnostic'] != "✅ Conforme"].copy()

            # Affichage des KPIs d'alertes
            a1, a2, a3 = st.columns(3)
            with a1: st.metric("Alertes 34h", len(df_filt_h[df_filt_h['Diagnostic'].str.contains("34h")]))
            with a2: st.metric("Alertes 1/3 Contrat", len(df_filt_h[df_filt_h['Diagnostic'].str.contains("1/3")]))
            with a3: st.metric("Alertes 40h (TP)", len(df_filt_h[df_filt_h['Diagnostic'].str.contains("40h")]))

            if not df_alerts.empty:
                st.dataframe(df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']], use_container_width=True, hide_index=True)
                
                # Graphique Interactif
                chart = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y'),
                    y=alt.Y('Total_Dec:Q', title="Heures Réalisées"),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(domain=["🚫 Dépassement Seuil 34h", "🔴 > 1/3 Temps Partiel", "🚫 Dépassement 40h (Temps Plein)"], range=['#fbbf24', '#ef4444', '#7f1d1d'])),
                    tooltip=['Intervenant', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.success("Toutes les tournées de ce secteur sont conformes aux règles 34h/40h et 1/3 contrat.")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process")
