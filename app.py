import streamlit as st
import pandas as pd
import io
import altair as alt

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE CSS (LE MEILLEUR DES DEUX MONDES) ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    /* Style des Metrics (Suite Pilotage) */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #1E3A8A;
    }
    [data-testid="stMetricLabel"] { color: #4A4A4A !important; font-weight: 600 !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #1E3A8A !important; font-weight: 800 !important; }
    
    /* Style pour les alertes Peps */
    .stAlert { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CONVERSION ---

def to_hhmm(decimal_hours):
    """Affiche 151.67 sous la forme '151:40'"""
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
    """Convertit '33:24' en 33.4"""
    try:
        if pd.isna(hhmm_str) or str(hhmm_str).strip() == "": return 0.0
        h, m = map(int, str(hhmm_str).split(':'))
        return h + (m / 60)
    except:
        return 0.0

def robust_read_csv(file):
    """Lecture et nettoyage intelligent Ximi"""
    try:
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        for col in df.columns:
            if any(k in col for k in ['Hres', 'Déviation', 'Heures', 'Total']):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
            else:
                df[col] = df[col].astype(str).str.strip()
        return df
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

# --- INITIALISATION SESSION STATE ---
if 'df_m' not in st.session_state: st.session_state.df_m = None
if 'df_h' not in st.session_state: st.session_state.df_h = None

# --- SIDEBAR : IMPORTATION ---
st.sidebar.title("📁 Importation Ximi")
f_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
f_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

if f_m and st.session_state.df_m is None: st.session_state.df_m = robust_read_csv(f_m)
if f_h and st.session_state.df_h is None: st.session_state.df_h = robust_read_csv(f_h)

if st.sidebar.button("🗑️ Réinitialiser tout"):
    st.session_state.df_m = None; st.session_state.df_h = None; st.rerun()

# --- CORPS DE L'APPLICATION ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_m is None:
    st.info("👋 Bonjour Aymen. Veuillez charger l'export Mensuel pour commencer l'audit.")
else:
    # --- LOGIQUE DE MAPPING SECTEURS ---
    df_m_full = st.session_state.df_m
    col_sec_src = 'Secteur intervenant' if 'Secteur intervenant' in df_m_full.columns else df_m_full.columns[1]
    mapping_secteurs = df_m_full.drop_duplicates('Intervenant').set_index('Intervenant')[col_sec_src].to_dict()

    # --- CALCUL DES ALERTES RÉGLEMENTAIRES (EN ARRIÈRE PLAN) ---
    df_h_calc = pd.DataFrame()
    if st.session_state.df_h is not None:
        df_h_calc = st.session_state.df_h.copy()
        df_h_calc['Secteur'] = df_h_calc['Intervenant'].map(mapping_secteurs).fillna("Non répertorié")
        df_h_calc['Total_Dec'] = df_h_calc['Heures totales'].apply(hhmm_to_decimal)
        df_h_calc['Is_TempsPlein'] = df_h_calc['Heures hebdo contrat'] >= 35
        
        def check_alert(row):
            if not row['Is_TempsPlein']:
                if row['Total_Dec'] > 34: return "⚠️ Seuil 34h dépassé"
                if (row['Total_Dec'] - row['Heures hebdo contrat']) > (row['Heures hebdo contrat'] / 3): return "🔴 Dépassement 1/3 Contrat"
            else:
                if row['Total_Dec'] > 40: return "🚫 Dépassement 40h (Temps Plein)"
            return "✅ Conforme"
        
        df_h_calc['Diagnostic'] = df_h_calc.apply(check_alert, axis=1)

    # --- SÉLECTEUR DE SECTEUR UNIQUE ---
    secteurs = ["Tous"] + sorted([str(s) for s in df_m_full[col_sec_src].unique() if pd.notna(s)])
    sel_sec = st.selectbox("🎯 Secteur d'Audit", secteurs, key="audit_sector")

    tab_m, tab_h = st.tabs(["📊 Suite Pilotage Mensuel", "📅 Audit Hebdo & Conformité"])

    # --- ONGLET MENSUEL (VUE PARFAITE) ---
    with tab_m:
        df_filt_m = df_m_full if sel_sec == "Tous" else df_m_full[df_m_full[col_sec_src] == sel_sec]
        
        # Suite Pilotage : 6 Widgets
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Heures de Base", to_hhmm(df_filt_m['Hres de base'].sum()))
        with c2: st.metric("Travail Effectif", to_hhmm(df_filt_m['Total heures travail effectif'].sum()))
        with c3: st.metric("Effectif", f"{len(df_filt_m)} sal.")

        c4, c5, c6 = st.columns(3)
        with c4: st.metric("Déviations (+)", to_hhmm(df_filt_m['Déviation'][df_filt_m['Déviation'] > 0].sum()))
        with c5: st.metric("Déviations (-)", to_hhmm(df_filt_m['Déviation'][df_filt_m['Déviation'] < 0].sum()))
        with c6: st.metric("Balance Globale", to_hhmm(df_filt_m['Déviation'].sum()))

        st.divider()
        st.subheader("📝 Edition des Compteurs Mensuels")
        hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
        edited_m = st.data_editor(df_filt_m, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_m.columns if c not in hidden_m], key="ed_m")
        
        if st.button("💾 Enregistrer Mensuel"):
            st.session_state.df_m.update(edited_m); st.success("Enregistré")

        st.divider()
        st.subheader("📈 Courbe de Modulation")
        st.bar_chart(df_filt_m.sort_values(by='Déviation', ascending=False), x='Intervenant', y='Déviation')

    # --- ONGLET HEBDO (VUE PEPS & INTERACTIVE) ---
    with tab_h:
        if st.session_state.df_h is not None:
            df_filt_h = df_h_calc if sel_sec == "Tous" else df_h_calc[df_h_calc['Secteur'] == sel_sec]
            
            st.subheader(f"📅 Audit Hebdomadaire : {sel_sec}")
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien', 'Total_Dec', 'Is_TempsPlein', 'Secteur', 'Diagnostic']
            edited_h = st.data_editor(df_filt_h, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_h.columns if c not in hidden_h], key="ed_h")
            
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_h.update(edited_h); st.success("Enregistré")

            # --- ALERTES PEPS ---
            st.divider()
            st.markdown("### 🔔 Analyse de Conformité")
            
            a1, a2, a3 = st.columns(3)
            with a1:
                nb_34 = len(df_filt_h[df_filt_h['Diagnostic'].str.contains("34h")])
                st.metric("Alertes 34h", nb_34, delta="Risque Requalif.", delta_color="inverse")
            with a2:
                nb_13 = len(df_filt_h[df_filt_h['Diagnostic'].str.contains("1/3")])
                st.metric("Alertes 1/3 Contrat", nb_13, delta="Limite Légale", delta_color="inverse")
            with a3:
                nb_40 = len(df_filt_h[df_filt_h['Diagnostic'].str.contains("40h")])
                st.metric("Alertes 40h (TP)", nb_40, delta="Alerte Sécurité", delta_color="inverse")

            df_alerts = df_filt_h[df_filt_h['Diagnostic'] != "✅ Conforme"].copy()
            
            if not df_alerts.empty:
                st.error(f"Attention : {len(df_alerts)} anomalies détectées sur ce secteur.")
                st.dataframe(df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']], use_container_width=True, hide_index=True)
                
                # Graphique Interactif Altair
                st.markdown("#### 📊 Graphique des Dépassements")
                chart = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y', title="Intervenant"),
                    y=alt.Y('Total_Dec:Q', title="Heures Réalisées"),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(domain=["⚠️ Seuil 34h dépassé", "🔴 Dépassement 1/3 Contrat", "🚫 Dépassement 40h (Temps Plein)"], range=['#fbbf24', '#ef4444', '#7f1d1d'])),
                    tooltip=['Intervenant', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                
                rule = alt.Chart(pd.DataFrame({'y': [34]})).mark_rule(color='orange', strokeDash=[5,5]).encode(y='y:Q')
                st.altair_chart(chart + rule, use_container_width=True)
            else:
                st.success("✅ Conformité totale : Aucune alerte sur ce secteur.")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process")
