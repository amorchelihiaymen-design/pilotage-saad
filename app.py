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

# Injection de CSS personnalisé pour améliorer l'esthétique des indicateurs (KPIs)
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
    """
    Convertit un nombre décimal (ex: 35.5) en format horaire lisible (35:30).
    Utile pour l'affichage final des totaux aux utilisateurs.
    """
    try:
        val = float(decimal_hours)
        abs_val = abs(val)
        hours = int(abs_val)
        minutes = int(round((abs_val - hours) * 60))
        # Gestion du cas limite où l'arrondi donne 60 minutes
        if minutes == 60: 
            hours += 1
            minutes = 0
        sign = "-" if val < 0 else ""
        return f"{sign}{hours:02d}:{minutes:02d}"
    except:
        return "00:00"

def hhmm_to_decimal(hhmm_str):
    """
    Convertit une chaîne horaire (ex: "35:30") issue de Ximi en nombre décimal (35.5).
    Indispensable pour pouvoir effectuer des calculs mathématiques sur les heures.
    """
    try:
        s = str(hhmm_str).strip()
        if not s or s in ['0', '0.0', '00:00', 'nan']: return 0.0
        if ':' in s:
            h, m = map(int, s.split(':'))
            return h + (m / 60)
        # Prise en charge des nombres avec virgule si Ximi exporte déjà en décimal
        return float(s.replace(',', '.'))
    except:
        return 0.0

def robust_read_csv(file):
    """
    Tente de lire l'export CSV Ximi. 
    Gère la problématique des accents français (latin-1) fréquents dans les vieux logiciels RH.
    """
    try:
        return pd.read_csv(file, sep=';', encoding='latin-1')
    except:
        # En cas d'échec, on rembobine le fichier et on tente en UTF-8 standard
        file.seek(0)
        return pd.read_csv(file, sep=';', encoding='utf-8')

def force_numeric(df, col):
    """
    Nettoie une colonne pandas pour s'assurer qu'elle est bien de type numérique.
    Remplace les virgules par des points et les valeurs vides par 0.0 pour éviter les crashs.
    """
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce').fillna(0.0)
    return pd.Series([0.0] * len(df))


# =====================================================================
# INITIALISATION DE LA MÉMOIRE (Session State)
# =====================================================================
# Stockage temporaire des données pour qu'elles ne soient pas perdues
# à chaque fois que l'utilisateur clique sur un bouton ou modifie un filtre.
if 'df_m' not in st.session_state: st.session_state.df_m = None
if 'df_h' not in st.session_state: st.session_state.df_h = None


# =====================================================================
# BARRE LATÉRALE (Sidebar) - Imports et Contrôles globaux
# =====================================================================
st.sidebar.title("📁 Importation Ximi")
f_m = st.sidebar.file_uploader("1. Export MENSUEL", type=['csv'])
f_h = st.sidebar.file_uploader("2. Export HEBDO", type=['csv'])

# Chargement en mémoire si un fichier est déposé
if f_m and st.session_state.df_m is None: st.session_state.df_m = robust_read_csv(f_m)
if f_h and st.session_state.df_h is None: st.session_state.df_h = robust_read_csv(f_h)

# Bouton de nettoyage de session (Hard Reset)
if st.sidebar.button("🗑️ Réinitialiser"):
    st.session_state.df_m = None
    st.session_state.df_h = None
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")


# =====================================================================
# CORPS DE L'APPLICATION (S'affiche uniquement si le fichier Mensuel est chargé)
# =====================================================================
if st.session_state.df_m is not None:
    df_m_full = st.session_state.df_m
    
    # Identification de la colonne de rattachement dans l'export Ximi
    col_sec_src = 'Secteur intervenant' if 'Secteur intervenant' in df_m_full.columns else df_m_full.columns[1]
    
    # Création d'un dictionnaire pour lier chaque intervenant à sa cellule
    # (Sera réutilisé pour l'onglet Hebdo)
    mapping_cellules = df_m_full.drop_duplicates('Intervenant').set_index('Intervenant')[col_sec_src].to_dict()

    st.title("🚀 Suivi de Modulation & Conformité")
    
    # --- SÉLECTEUR DE CELLULE ---
    # Récupération de la liste unique des cellules depuis le fichier
    cellules = ["Toutes"] + sorted([str(s) for s in df_m_full[col_sec_src].unique() if pd.notna(s)])
    sel_sec = st.selectbox("🎯 Cellule", cellules, key="audit_sector")

    # Création des onglets de navigation principaux
    tab_m, tab_h = st.tabs(["📊 Pilotage Modulation (Mensuel)", "📅 Suivi de Conformité (Hebdo)"])

    # =================================================================
    # ONGLET 1 : PILOTAGE MENSUEL
    # =================================================================
    with tab_m:
        # Filtrage des données selon la cellule sélectionnée
        df_filt_m = df_m_full if sel_sec == "Toutes" else df_m_full[df_m_full[col_sec_src] == sel_sec]
        
        # Astuce UI : On réserve un conteneur vide en haut pour les indicateurs (KPIs),
        # mais on les calculera APRÈS avoir affiché le tableau éditable, 
        # pour qu'ils se mettent à jour en direct lors d'une modification.
        metric_container = st.container()
        
        st.divider()
        st.subheader("📝 Édition des Compteurs Mensuels")
        
        # Liste des colonnes non pertinentes à masquer pour alléger l'interface
        hidden_m = ['Entité', 'Type', 'Début période', 'Fin période', 'Hres inactivité', 'Hres CP', 'Bulletin de paie', 'Calcul manuel ?', 'A recalculer', 'Dernier recalcul']
        
        # Tableau interactif (Data Editor)
        edited_m = st.data_editor(
            df_filt_m, 
            use_container_width=True, 
            hide_index=True, 
            column_order=[c for c in df_filt_m.columns if c not in hidden_m], 
            key="ed_m"
        )

        # --- CALCULS EN DIRECT SUR LES DONNÉES ÉDITÉES ---
        h_base = force_numeric(edited_m, 'Hres de base')
        h_trav = force_numeric(edited_m, 'Total heures travail effectif')
        h_dev = force_numeric(edited_m, 'Déviation')

        # Injection des résultats dans le conteneur du haut
        with metric_container:
            c1, c2, c3 = st.columns(3)
            c1.metric("Heures de Base", to_hhmm(h_base.sum()))
            c2.metric("Travail Effectif", to_hhmm(h_trav.sum()))
            c3.metric("Effectif de la Cellule", f"{len(edited_m)} sal.")

            c4, c5, c6 = st.columns(3)
            c4.metric("Déviations Positives (+)", to_hhmm(h_dev[h_dev > 0].sum()))
            c5.metric("Déviations Négatives (-)", to_hhmm(h_dev[h_dev < 0].sum()))
            c6.metric("Balance de Modulation", to_hhmm(h_dev.sum()))

        # Sauvegarde en mémoire des corrections apportées dans le tableau
        if st.button("💾 Enregistrer définitivement pour cette session"):
            st.session_state.df_m.update(edited_m)
            st.success("Modifications sauvegardées en mémoire.")

        # --- GRAPHIQUE DE MODULATION ---
        st.divider()
        st.subheader("📈 Courbe de Modulation (Live)")
        chart_data = edited_m.copy()
        chart_data['Déviation'] = force_numeric(chart_data, 'Déviation')
        st.bar_chart(chart_data.sort_values(by='Déviation', ascending=False), x='Intervenant', y='Déviation')

    # =================================================================
    # ONGLET 2 : SUIVI HEBDOMADAIRE (Règles Métier)
    # =================================================================
    with tab_h:
        if st.session_state.df_h is not None:
            df_h_calc = st.session_state.df_h.copy()
            
            # Injection de la notion de "Cellule" dans l'export Hebdo 
            # grâce au mapping créé à partir de l'export Mensuel
            df_h_calc['Cellule'] = df_h_calc['Intervenant'].map(mapping_cellules).fillna("Non répertorié")
            
            # Filtrage par Cellule
            df_filt_h = df_h_calc if sel_sec == "Toutes" else df_h_calc[df_h_calc['Cellule'] == sel_sec]
            
            st.subheader(f"📅 Suivi Hebdomadaire : {sel_sec}")
            hidden_h = ['Contrat', 'Début contrat', 'Année', 'Heures inactivité', 'Heures internes', 'Heures absences', 'Heures absences maintien']
            
            # Tableau interactif Hebdo
            edited_h = st.data_editor(df_filt_h, use_container_width=True, hide_index=True, column_order=[c for c in df_filt_h.columns if c not in hidden_h], key="ed_h")
            
            # Préparation des données pour l'algorithme : conversion en décimales
            edited_h['Total_Dec'] = edited_h['Heures totales'].apply(hhmm_to_decimal)
            edited_h['Contract_Val'] = force_numeric(edited_h, 'Heures hebdo contrat')
            
            # --- ALGORITHME DE CONFORMITÉ (LE CŒUR MÉTIER) ---
            def check_risk(row):
                """
                Évalue la conformité opérationnelle des heures réalisées par rapport au contrat.
                Applique les règles légales spécifiques aux Temps Partiels et Temps Pleins.
                """
                t_realise = row['Total_Dec']
                t_contrat = row['Contract_Val']
                
                # BRANCHEMENT 1 : RÈGLES TEMPS PARTIEL (< 35h)
                if t_contrat < 35:
                    # Règle : Le réalisé ne doit pas être inférieur aux deux tiers du contrat cible
                    if t_realise < (t_contrat * 2 / 3): 
                        return "⚠️ Sous-activité (< 2/3 contrat)"
                        
                    # Règle légale : Éviter la requalification en temps plein
                    if t_realise > 34: 
                        return "🚫 Seuil 34h dépassé"
                        
                    # Règle : Les heures complémentaires ne peuvent dépasser le tiers de la durée contractuelle
                    if (t_realise - t_contrat) > (t_contrat / 3): 
                        return "🔴 Dépassement 1/3 Contrat"
                        
                # BRANCHEMENT 2 : RÈGLES TEMPS PLEIN (≥ 35h)
                else:
                    # Règle de la cellule : Plancher d'activité minimum pour justifier un TP
                    if t_realise < 24: 
                        return "⚠️ Plancher 24h non atteint"
                        
                    # Règle légale : Plafond d'activité maximale
                    if t_realise > 40: 
                        return "🚫 Dépassement 40h (Temps Plein)"
                    
                return "✅ Conforme"
            
            # Application de l'algorithme sur chaque ligne du tableau
            edited_h['Diagnostic'] = edited_h.apply(check_risk, axis=1)

            st.divider()
            st.markdown("### 🔔 Contrôle de Modulation (Alertes)")
            
            # --- AFFICHAGE DES KPIs D'ALERTE ---
            a1, a2, a3, a4, a5 = st.columns(5)
            a1.metric("Sous-activité (< 2/3)", len(edited_h[edited_h['Diagnostic'].str.contains("2/3")]))
            a2.metric("Plancher (< 24h)", len(edited_h[edited_h['Diagnostic'].str.contains("24h")]))
            a3.metric("Risque 34h", len(edited_h[edited_h['Diagnostic'].str.contains("34h")]))
            a4.metric("Dépas. 1/3 Contrat", len(edited_h[edited_h['Diagnostic'].str.contains("1/3")]))
            a5.metric("Plafond (> 40h)", len(edited_h[edited_h['Diagnostic'].str.contains("40h")]))

            # --- ISOLATION ET VISUALISATION DES ANOMALIES ---
            df_alerts = edited_h[edited_h['Diagnostic'] != "✅ Conforme"].copy()
            
            if not df_alerts.empty:
                # Affichage du tableau restreint aux personnes en anomalie
                st.dataframe(df_alerts[['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']], use_container_width=True, hide_index=True)
                
                # Génération du graphique Altair avec codes couleurs sémantiques
                chart_h = alt.Chart(df_alerts).mark_bar().encode(
                    x=alt.X('Intervenant:N', sort='-y', title="Intervenant"),
                    y=alt.Y('Total_Dec:Q', title="Heures Réalisées"),
                    color=alt.Color('Diagnostic:N', scale=alt.Scale(
                        domain=[
                            "⚠️ Sous-activité (< 2/3 contrat)",
                            "⚠️ Plancher 24h non atteint", 
                            "🚫 Seuil 34h dépassé", 
                            "🔴 Dépassement 1/3 Contrat", 
                            "🚫 Dépassement 40h (Temps Plein)"
                        ], 
                        # Couleurs : Bleu (sous-activité) -> Jaune/Rouge (sur-activité)
                        range=['#60a5fa', '#3b82f6', '#fbbf24', '#ef4444', '#7f1d1d']
                    )),
                    tooltip=['Intervenant', 'Heures hebdo contrat', 'Heures totales', 'Diagnostic']
                ).properties(height=400)
                
                st.altair_chart(chart_h, use_container_width=True)
            else:
                st.success("✅ Conformité opérationnelle totale sur cette cellule. Aucune anomalie détectée.")
                
st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Process | emlyon")
