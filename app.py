import streamlit as st
import pandas as pd
import io
import altair as alt

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS ---
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
    [data-testid="stMetricLabel"] { color: #4A4A4A !important; font-weight: 600 !important; font-size: 1.1rem !important; }
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
        s = str(hhmm_str).strip()
        if not s or s in ['0', '0.0', '00:00', 'nan']: return 0.0
        if ':' in s:
            h, m = map(int, s.split(':'))
            return h + (m / 60)
        return float(s.replace(',', '.'))
    except:
        return 0.0

def robust_read_csv(file):
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def force_numeric(df, col):
    """Force une colonne en numérique pour éviter le TypeError"""
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
    return pd.Series([0.0] * len(df))

# --- INITIALISATION ---
if 'df_m' not in st.session_state: st.session_state.df_m = None
if 'df_h' not in st.session_state: st.session_state.df_h = None

# --- SIDEBAR ---
st.sidebar.title("📁 Importation Ximi")
f_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
f_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

if f_m and st.session_state.df_m is None: st.session_state.df_m = robust_read_csv(f_m)
if f_h and st.session_state.df_h is None: st.session_state.df_h = robust_read_csv(f_h)

if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_m = None; st.session_state.df_h = None; st.rerun()

# --- CORPS DE L'APPLI ---
if st.session_state.df_m is not None:
    df_m_full = st.session_state.df_m
    col_sec_src = 'Secteur intervenant' if 'Secteur intervenant' in df_m_full.columns else df_m_full.columns[1]
    mapping_secteurs = df_m_full.drop_duplicates('Intervenant').set_index('Intervenant')[col_sec_src].to_dict()

    st.title("🚀 Pilotage & Optimisation IDF")
    
    # Sélecteur de Secteur
    secteurs = ["Tous"] + sorted([str(s) for s in df_m_full[col_sec_src].unique() if pd.notna(s)])
    sel_sec = st.selectbox("🎯 Secteur d'Audit", secteurs, key="audit_sector")

    tab_m, tab_h = st.tabs(["📊 Suite Pilotage Mensuel", "📅 Audit Hebdo & Conformité"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        df_filt_m = df_m_full if sel_sec == "Tous" else df_m_full[df_m_full[col_sec_src] == sel_sec]
        
        # --- RÉACTIVITÉ : ON CRÉE LES INDICATEURS EN HAUT ---
        metric_container = st.container()
        
        st.divider()
        st.subheader("📝 Edition des Compteurs Mensuels")
        hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
        
        # On affiche l'éditeur et on récupère le contenu MODIFIÉ en direct
        edited_m = st.data_editor(
            df_filt_m, 
            use_container_width=True, 
            hide_index=True, 
            column_order=[c for c in df_filt_m.columns if c not in hidden_m], 
            key="ed_m"
        )

        # --- CALCULS SUR LES DONNÉES ÉDITÉES (LIVE) ---
        h_base = force_numeric(edited_m, 'Hres de base')
        h_trav = force_numeric(edited_m, 'Total heures travail effectif')
        h_dev = force_numeric(edited_m, 'Déviation')

        # On remplit le container du haut avec les calculs de 'edited_m'
        with metric_container:
            c1, c2, c3 = st.columns(3)
            c1.metric("Heures de Base", to_hhmm(h_base.sum()))
            c2.metric("Travail Effectif", to_hhmm(h_trav.sum()))
            c3.metric("Effectif", f"{len(edited_m)} sal.")

            c4, c5, c6 = st.columns(3)
            c4.metric("Déviations (+)", to_hhmm(h_dev[h_dev > 0].sum()))
            c5.metric("Déviations (-)", to_hhmm(h_dev[h_dev < 0].sum()))
            c6.metric("Balance Globale", to_hhmm(h_dev.sum()))

        if st.button("💾 Enregistrer définitivement"):
            st.session_state.df_m.update(edited_m); st.success("Données sauvegardées en mémoire.")

        # Graphique réactif
        st.divider()
        st.subheader("📈 Courbe de Modulation (Live)")
        chart_data = edited_m.copy()
        chart_data['Déviation'] = force_numeric(chart_data, 'Déviation')
        st.bar_chart(chart_data.sort_values(by='Déviation', ascending=False), x='Intervenant', y='Déviation')

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_h is not None:
            df_h_calc = st.session_state.df_h.copy()
            df_h_calc['Secteur'] = df_h_calc['Intervenant'].map(mapping_secteurs).fillna("Non répertorié")
            df_filt_h = df_h_calc if sel_sec == "Tous" else df_h_calc[df_h_calc['Secteur'] == sel_sec]
            
            st.subheader(f"📅 Audit Hebdomadaire : {sel_sec}")
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            
            # Editeur Hebdo
            edited_h = st.data_editor(df_filt_h, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_h.columns if c not in hidden_h], key="ed_h")
            
            # Calculs de conformité sur l'hebdo édité
            edited_h['Total_Dec'] = edited_h['Heures totales'].apply(hhmm_to_decimal)
            edited_h['Contract_Val'] = force_numeric(edited_h, 'Heures hebdo contrat')
            
            def check_risk(row):
                t_realise = row['Total_Dec']
                t_contrat = row['Contract_Val']
                if t_contrat < 35:
                    if t_realise > 34: return "🚫 Seuil 34h dépassé"
                    if (t_realise - t_contrat) > (t_contrat / 3): return "🔴 Dépassement 1/3 Contrat"
                else:
                    if t_realise > 40: return "🚫 Dépassement 40h (Temps Plein)"
                return "✅ Conforme"
            
            edited_h['Diagnostic'] = edited_h.apply(check_risk, axis=1)

            st.divider()
            st.markdown("### 🔔 Analyse de Conformité")
            a1, a2, a3 = st.columns(3)
            a1.metric("Alertes 34h", len(edited_h[edited_h['Diagnostic'].str.contains("34h")]))
            a2.metric("Alertes 1/3 Contrat", len(edited_h[edited_h['Diagnostic'].str.contains("1/3")]))
            a3.metric("Alertes 40h (TP)", len(edited_h[edited_h['Diagnostic'].str.contains("40h")]))

            df_alerts = edited_h[edited_h['Diagnostic'] != "✅ Conforme"].copy()
            if not df_alerts.empty:
                st.dataframe(df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']], use_container_width=True, hide_index=True)
                
                chart_h = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y'),
                    y=alt.Y('Total_Dec:Q', title="Heures Réalisées"),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(domain=["🚫 Seuil 34h dépassé", "🔴 Dépassement 1/3 Contrat", "🚫 Dépassement 40h (Temps Plein)"], range=['#fbbf24', '#ef4444', '#7f1d1d'])),
                    tooltip=['Intervenant', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                st.altair_chart(chart_h, use_container_width=True)
            else:
                st.success("✅ Conformité totale sur ce secteur.")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")
