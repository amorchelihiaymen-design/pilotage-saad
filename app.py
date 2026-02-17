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

def hhmm_to_decimal(hhmm_str):
    """Convertit '33:24' en 33.4"""
    try:
        if pd.isna(hhmm_str) or str(hhmm_str).strip() == "": return 0.0
        h, m = map(int, str(hhmm_str).split(':'))
        return h + (m / 60)
    except:
        return 0.0

def robust_read_csv(file):
    """Lecture et nettoyage Ximi"""
    try:
        df = pd.read_csv(file, sep=';', encoding='latin-1')
        cols_numeriques = ['Hres de base', 'Total heures travail effectif', 'Déviation', 'Heures hebdo contrat']
        for col in df.columns:
            if col in cols_numeriques:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            else:
                df[col] = df[col].astype(str).str.strip()
        return df
    except:
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

# --- INITIALISATION ---
if 'df_mensuel' not in st.session_state: st.session_state.df_mensuel = None
if 'df_hebdo' not in st.session_state: st.session_state.df_hebdo = None

# --- SIDEBAR ---
st.sidebar.title("📁 Importation Ximi")
file_m = st.sidebar.file_uploader("1. Export MENSUEL (CSV)", type=['csv'])
file_h = st.sidebar.file_uploader("2. Export HEBDO (CSV)", type=['csv'])

if file_m and st.session_state.df_mensuel is None: st.session_state.df_mensuel = robust_read_csv(file_m)
if file_h and st.session_state.df_hebdo is None: st.session_state.df_hebdo = robust_read_csv(file_h)

if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_mensuel = None
    st.session_state.df_hebdo = None
    st.rerun()

# --- CORPS DE L'APPLI ---
st.title("🚀 Pilotage & Optimisation IDF")

if st.session_state.df_mensuel is None and st.session_state.df_hebdo is None:
    st.info("Veuillez charger vos fichiers CSV pour activer les outils de conformité.")
else:
    tab_m, tab_h = st.tabs(["📊 Suivi Mensuel", "📅 Suivi Hebdomadaire"])

    # --- ONGLET MENSUEL ---
    with tab_m:
        if st.session_state.df_mensuel is not None:
            df = st.session_state.df_mensuel.copy()
            col_sec = 'Secteur intervenant' if 'Secteur intervenant' in df.columns else df.columns[1]
            list_secteurs = ["Tous"] + sorted([str(s) for s in df[col_sec].unique()])
            sel_sec = st.selectbox("Secteur", list_secteurs, key="m_sec")
            df_filt = df if sel_sec == "Tous" else df[df[col_sec] == sel_sec]

            search = st.text_input("🔍 Rechercher un intervenant :", key="search_m")
            if search:
                df_filt = df_filt[df_filt.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

            if 'Déviation' in df_filt.columns:
                pos_dev = df_filt['Déviation'][df_filt['Déviation'] > 0].sum()
                neg_dev = df_filt['Déviation'][df_filt['Déviation'] < 0].sum()
                total_dev = df_filt['Déviation'].sum()
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Somme Déviations (+)", to_hhmm(pos_dev))
                with c2: st.metric("Somme Déviations (-)", to_hhmm(neg_dev))
                with c3: st.metric("Balance Modulation", to_hhmm(total_dev))

            st.divider()
            st.subheader("📝 Analyse & Édition")
            hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
            visible_m = [c for c in df_filt.columns if c not in hidden_m]
            
            edited = st.data_editor(df_filt, use_container_width=True, num_rows="dynamic", key="ed_m", hide_index=True, column_order=visible_m)
            
            if st.button("💾 Enregistrer"):
                st.session_state.df_mensuel.update(edited)
                st.success("Modifications mensuelles enregistrées !")

            # Graphique
            st.divider()
            st.subheader("📈 Vue d'ensemble de la Modulation")
            if not df_filt.empty and 'Déviation' in df_filt.columns:
                st.bar_chart(data=df_filt.sort_values(by='Déviation', ascending=False), x='Intervenant', y='Déviation')

    # --- ONGLET HEBDO ---
    with tab_h:
        if st.session_state.df_hebdo is not None:
            df_h = st.session_state.df_hebdo.copy()
            st.subheader("📅 Audit Hebdomadaire")
            
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            visible_h = [c for c in df_h.columns if c not in hidden_h]

            edited_h = st.data_editor(df_h, use_container_width=True, num_rows="dynamic", key="ed_h", hide_index=True, column_order=visible_h)
            
            if st.button("💾 Enregistrer Hebdo"):
                st.session_state.df_hebdo.update(edited_h)
                st.success("Modifications hebdo enregistrées !")

            # --- NOUVELLE SECTION : ALERTES DE CONFORMITÉ ---
            st.divider()
            st.subheader("⚠️ Alertes de Conformité (Secteur)")
            
            # Calcul des alertes
            df_h['Total_Dec'] = df_h['Heures totales'].apply(hhmm_to_decimal)
            df_h['Seuil_1_3'] = df_h['Heures hebdo contrat'] * (1/3)
            df_h['Surplus'] = df_h['Total_Dec'] - df_h['Heures hebdo contrat']
            
            # Filtre des alertes
            alert_1_3 = df_h['Surplus'] > df_h['Seuil_1_3']
            alert_34h = df_h['Total_Dec'] > 34
            
            df_alerts = df_h[alert_1_3 | alert_34h].copy()
            
            if not df_alerts.empty:
                # On crée une colonne de diagnostic
                def get_diagnostic(row):
                    diag = []
                    if row['Total_Dec'] > 34: diag.append("Dépassement 34H")
                    if (row['Total_Dec'] - row['Heures hebdo contrat']) > (row['Heures hebdo contrat'] / 3): diag.append("Dépassement 1/3 Contrat")
                    return " & ".join(diag)

                df_alerts['Diagnostic'] = df_alerts.apply(get_diagnostic, axis=1)
                
                st.warning(f"Il y a {len(df_alerts)} salariés en situation d'alerte sur ce secteur.")
                st.dataframe(
                    df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("Aucune alerte de conformité détectée sur ce secteur pour le moment.")

            csv_h = st.session_state.df_hebdo.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Télécharger CSV Hebdo", data=csv_h, file_name="Hebdo_MAJ.csv")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process")
