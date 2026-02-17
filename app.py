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
    
    .alert-card {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #ef4444;
        background-color: #fef2f2;
    }
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
f_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
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
    st.info("👋 Bienvenue Aymen. Veuillez charger vos exports pour démarrer l'audit.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel (Modulation)", "📅 Suivi Hebdo (Alertes)"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_m is not None:
            df = st.session_state.df_m.copy()
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique()])
            sel_sec = st.selectbox("Filtrer par Secteur", list_secteurs, key="m_sec")
            df_filt = df if sel_sec == "Tous" else df[df[col_sec] == sel_sec]

            # Metrics
            dev_pos = df_filt['Déviation'][df_filt['Déviation'] > 0].sum()
            dev_neg = df_filt['Déviation'][df_filt['Déviation'] < 0].sum()
            balance = df_filt['Déviation'].sum()

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Déviations (+) (A payer)", to_hhmm(dev_pos))
            with c2: st.metric("Déviations (-) (A rattraper)", to_hhmm(dev_neg))
            with c3: st.metric("Balance Globale", to_hhmm(balance), delta=to_hhmm(balance))

            st.divider()
            st.subheader("📝 Analyse & Édition")
            hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
            visible_m = [c for c in df_filt.columns if c not in hidden_m]
            
            edited_m = st.data_editor(df_filt, use_container_width=True, num_rows="dynamic", key="ed_m", hide_index=True, column_order=visible_m)
            
            if st.button("💾 Enregistrer le Mensuel"):
                st.session_state.df_m.update(edited_m)
                st.success("Modifications enregistrées !")

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_h is not None:
            df_h = st.session_state.df_h.copy()
            st.subheader("📅 Audit Hebdomadaire")
            
            # Masquage colonnes hebdo
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            visible_h = [c for c in df_h.columns if c not in hidden_h]

            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h", hide_index=True, column_order=visible_h)
            
            if st.button("💾 Enregistrer l'Hebdo"):
                st.session_state.df_h.update(edited_h)
                st.success("Modifications hebdo enregistrées !")

            # --- SECTION ALERTES PEPS & INTERACTIF ---
            st.divider()
            st.markdown("### 🔔 Analyse de Conformité Réglementaire")
            
            # Calcul de la logique métier
            df_h['Total_Dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
            df_h['Is_TempsPlein'] = df_h['Heures hebdo contrat'] >= 35
            
            # Conditions d'alertes
            def check_alert(row):
                if not row['Is_TempsPlein']:
                    # Temps partiel
                    if row['Total_Dec'] > 34: return "⚠️ Seuil 34h dépassé"
                    if (row['Total_Dec'] - row['Heures hebdo contrat']) > (row['Heures hebdo contrat'] / 3): 
                        return "🔴 Dépassement 1/3 Contrat"
                else:
                    # Temps plein
                    if row['Total_Dec'] > 40: return "🚫 Dépassement 40h (Temps Plein)"
                return "✅ Conforme"

            df_h['Diagnostic'] = df_h.apply(check_alert, axis=1)
            df_alerts = df_h[df_h['Diagnostic'] != "✅ Conforme"].copy()

            # Widgets d'alertes "Peps"
            a1, a2, a3 = st.columns(3)
            with a1:
                nb_34 = len(df_h[df_h['Diagnostic'].str.contains("34h")])
                st.metric("Alertes 34h", nb_34, delta="Risque Requalif.", delta_color="inverse")
            with a2:
                nb_13 = len(df_h[df_h['Diagnostic'].str.contains("1/3")])
                st.metric("Alertes 1/3 Contrat", nb_13, delta="Limite Légale", delta_color="inverse")
            with a3:
                nb_40 = len(df_h[df_h['Diagnostic'].str.contains("40h")])
                st.metric("Alertes 40h (TP)", nb_40, delta="Alerte Sécurité", delta_color="inverse")

            if not df_alerts.empty:
                st.error(f"Attention : {len(df_alerts)} anomalies détectées nécessitant une action immédiate.")
                
                # Tableau interactif des alertes avec style
                st.dataframe(
                    df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']].sort_values(by='Diagnostic'),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Graphique interactif Altair pour les alertes
                st.markdown("#### 📊 Visualisation des dépassements")
                chart = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y', title="Intervenant"),
                    y=alt.Y('Total_Dec:Q', title="Heures Réalisées"),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(domain=["⚠️ Seuil 34h dépassé", "🔴 Dépassement 1/3 Contrat", "🚫 Dépassement 40h (Temps Plein)"], range=['#fbbf24', '#ef4444', '#7f1d1d'])),
                    tooltip=['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                
                # Ligne de seuil 34h
                rule = alt.Chart(pd.DataFrame({'y': [34]})).mark_rule(color='orange', strokeDash=[5,5]).encode(y='y:Q')
                
                st.altair_chart(chart + rule, use_container_width=True)
            else:
                st.success("Félicitations ! Le secteur est 100% conforme cette semaine.")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expertise Data & Process | emlyon")
