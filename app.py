"""
Application Streamlit : Suivi de Modulation & Conformité Opérationnelle
Objectif : Analyser les exports Ximi pour piloter les heures et garantir la conformité légale.
Auteur : Aymen Amor | Expert Data & Process | emlyon business school
"""

import streamlit as st
import pandas as pd
import io
import altair as alt

# =====================================================================
# CONFIGURATION DE LA PAGE & INTERFACE VISUELLE
# =====================================================================
st.set_page_config(page_title="Suivi de Modulation", layout="wide")

# Injection de CSS personnalisé pour les indicateurs (KPIs)
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


# =====================================================================
# FONCTIONS UTILITAIRES (Nettoyage et Conversion des données Ximi)
# =====================================================================

def to_hhmm(decimal_hours):
    """Convertit un nombre décimal en format horaire lisible (HH:MM)."""
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
    """Convertit une chaîne horaire (HH:MM) en nombre décimal."""
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
    """Lit l'export CSV Ximi avec gestion des encodages (latin-1/utf-8)."""
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def force_numeric(df, col):
    """Force une colonne en type numérique pour éviter les erreurs de calcul."""
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
    return pd.Series([0.0] * len(df))


# =====================================================================
# INITIALISATION & BARRE LATÉRALE
# =====================================================================
if 'df_m' not in st.session_state: st.session_state.df_m = None
if 'df_h' not in st.session_state: st.session_state.df_h = None

st.sidebar.title("📁 Importation Ximi")
f_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
f_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

if f_m and st.session_state.df_m is None: st.session_state.df_m = robust_read_csv(f_m)
if f_h and st.session_state.df_h is None: st.session_state.df_h = robust_read_csv(f_h)

if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_m = None; st.session_state.df_h = None; st.rerun()

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")


# =====================================================================
# EN-TÊTE DE L'APPLICATION (Toujours visible)
# =====================================================================
st.title("🚀 Suivi de Modulation & Conformité")

# --- MODE D'EMPLOI (Pour les usagers) ---
with st.expander("ℹ️ Comment utiliser cet outil ?", expanded=True):
    st.markdown("""
    **Bienvenue dans l'outil de Suivi de Modulation & Conformité !**
    
    Voici comment piloter votre périmètre en 4 étapes :
    
    1. 📁 **Importez vos fichiers :** Utilisez le panneau à gauche pour charger les exports Ximi **Mensuel** et **Hebdo**.
    2. 🎯 **Sélectionnez votre Cellule :** Une fois les fichiers chargés, choisissez votre équipe dans le menu déroulant.
    3. 🔍 **Analysez & Simulez :** - L'onglet **Mensuel** montre l'état de la modulation globale.
       - L'onglet **Hebdo** détecte les anomalies (sous-activité, dépassements).
       - **Correction en direct :** Modifiez les valeurs dans les tableaux pour simuler des régularisations.
    4. 💾 **Sauvegardez :** Cliquez sur "Enregistrer..." pour figer vos modifications le temps de votre session.
    """)

# =====================================================================
# ZONE D'ANALYSE (S'affiche uniquement après import)
# =====================================================================
if st.session_state.df_m is not None:
    df_m_full = st.session_state.df_m
    col_sec_src = 'Secteur intervenant' if 'Secteur intervenant' in df_m_full.columns else df_m_full.columns[1]
    mapping_cellules = df_m_full.drop_duplicates('Intervenant').set_index('Intervenant')[col_sec_src].to_dict()

    # --- SÉLECTEUR DE CELLULE ---
    cellules = ["Toutes"] + sorted([str(s) for s in df_m_full[col_sec_src].unique() if pd.notna(s)])
    sel_sec = st.selectbox("🎯 Cellule", cellules, key="audit_sector")

    tab_m, tab_h = st.tabs(["📊 Pilotage Modulation (Mensuel)", "📅 Suivi de Conformité (Hebdo)"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        df_filt_m = df_m_full if sel_sec == "Toutes" else df_m_full[df_m_full[col_sec_src] == sel_sec]
        metric_container = st.container()
        st.divider()
        st.subheader("📝 Édition des Compteurs Mensuels")
        hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
        
        edited_m = st.data_editor(df_filt_m, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_m.columns if c not in hidden_m], key="ed_m")

        h_base = force_numeric(edited_m, 'Hres de base'); h_trav = force_numeric(edited_m, 'Total heures travail effectif'); h_dev = force_numeric(edited_m, 'Déviation')

        with metric_container:
            c1, c2, c3 = st.columns(3)
            c1.metric("Heures de Base", to_hhmm(h_base.sum()))
            c2.metric("Travail Effectif", to_hhmm(h_trav.sum()))
            c3.metric("Effectif Cellule", f"{len(edited_m)} sal.")
            c4, c5, c6 = st.columns(3)
            c4.metric("Déviations (+)", to_hhmm(h_dev[h_dev > 0].sum()))
            c5.metric("Déviations (-)", to_hhmm(h_dev[h_dev < 0].sum()))
            c6.metric("Balance Globale", to_hhmm(h_dev.sum()))

        if st.button("💾 Enregistrer pour cette session"):
            st.session_state.df_m.update(edited_m); st.success("Données mises à jour en mémoire.")

        st.divider()
        st.subheader("📈 Courbe de Modulation")
        chart_data = edited_m.copy()
        chart_data['Déviation'] = force_numeric(chart_data, 'Déviation')
        st.bar_chart(chart_data.sort_values(by='Déviation', ascending=False), x='Intervenant', y='Déviation')

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_h is not None:
            df_h_calc = st.session_state.df_h.copy()
            df_h_calc['Cellule'] = df_h_calc['Intervenant'].map(mapping_cellules).fillna("Non répertorié")
            df_filt_h = df_h_calc if sel_sec == "Toutes" else df_h_calc[df_h_calc['Cellule'] == sel_sec]
            
            st.subheader(f"📅 Suivi Hebdomadaire : {sel_sec}")
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            
            edited_h = st.data_editor(df_filt_h, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_h.columns if c not in hidden_h], key="ed_h")
            
            edited_h['Total_Dec'] = edited_h['Heures totales'].apply(hhmm_to_decimal)
            edited_h['Contract_Val'] = force_numeric(edited_h, 'Heures hebdo contrat')
            
            def check_risk(row):
                t_realise = row['Total_Dec']; t_contrat = row['Contract_Val']
                if t_contrat < 35:
                    if t_realise < (t_contrat * 2 / 3): return "⚠️ Sous-activité (< 2/3 contrat)"
                    if t_realise > 34: return "🚫 Seuil 34h dépassé"
                    if (t_realise - t_contrat) > (t_contrat / 3): return "🔴 Dépassement 1/3 Contrat"
                else:
                    if t_realise < 24: return "⚠️ Plancher 24h non atteint"
                    if t_realise > 40: return "🚫 Dépassement 40h (Temps Plein)"
                return "✅ Conforme"
            
            edited_h['Diagnostic'] = edited_h.apply(check_risk, axis=1)

            st.divider()
            st.markdown("### 🔔 Contrôle de Modulation")
            a1, a2, a3, a4, a5 = st.columns(5)
            a1.metric("Sous-activité", len(edited_h[edited_h['Diagnostic'].str.contains("2/3")]))
            a2.metric("Plancher < 24h", len(edited_h[edited_h['Diagnostic'].str.contains("24h")]))
            a3.metric("Risque 34h", len(edited_h[edited_h['Diagnostic'].str.contains("34h")]))
            a4.metric("Dépas. 1/3", len(edited_h[edited_h['Diagnostic'].str.contains("1/3")]))
            a5.metric("Plafond > 40h", len(edited_h[edited_h['Diagnostic'].str.contains("40h")]))

            df_alerts = edited_h[edited_h['Diagnostic'] != "✅ Conforme"].copy()
            if not df_alerts.empty:
                st.dataframe(df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']], use_container_width=True, hide_index=True)
                chart_h = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y'), y=alt.Y('Total_Dec:Q'),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(
                        domain=["⚠️ Sous-activité (< 2/3 contrat)", "⚠️ Plancher 24h non atteint", "🚫 Seuil 34h dépassé", "🔴 Dépassement 1/3 Contrat", "🚫 Dépassement 40h (Temps Plein)"],
                        range=['#60a5fa', '#3b82f6', '#fbbf24', '#ef4444', '#7f1d1d']
                    )),
                    tooltip=['Intervenant', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                st.altair_chart(chart_h, use_container_width=True)
            else:
                st.success("✅ Conformité opérationnelle totale.")
        else:
            st.warning("⚠️ Veuillez importer l'export HEBDO pour accéder au suivi de conformité.")
else:
    # Message d'accueil quand aucun fichier n'est chargé
    st.info("👈 Pour commencer, veuillez importer vos exports Ximi dans la barre latérale.")
    
                
st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")
