import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Pilotage IDF - Secteurs", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 1. GESTION DE L'UPLOAD ET DE LA MÉMOIRE ---
st.sidebar.title("📁 Importation des Données")
uploaded_file = st.sidebar.file_uploader("Charger le fichier Ximi (Excel ou CSV)", type=['xlsx', 'csv'])

# Initialisation du DataFrame dans la session s'il n'existe pas
if 'df_modulation' not in st.session_state:
    st.session_state.df_modulation = None

# Chargement initial du fichier
if uploaded_file is not None and st.session_state.df_modulation is None:
    if uploaded_file.name.endswith('.csv'):
        st.session_state.df_modulation = pd.read_csv(uploaded_file)
    else:
        st.session_state.df_modulation = pd.read_excel(uploaded_file)

# --- 2. FILTRES ET INTERFACE ---
if st.session_state.df_modulation is not None:
    # Nettoyage rapide (on s'assure que le terme Secteur est présent)
    df = st.session_state.df_modulation

    st.sidebar.divider()
    st.sidebar.title("🛠️ Paramètres de Pilotage")
    
    # On cherche la colonne Secteur (ou on la crée pour l'exemple si elle manque)
    col_secteur = 'Secteur' if 'Secteur' in df.columns else df.columns[0]
    
    secteurs_disponibles = ["Tous"] + list(df[col_secteur].unique())
    secteur_choisi = st.sidebar.selectbox("Sélectionner le Secteur", secteurs_disponibles)

    # Filtrage
    if secteur_choisi == "Tous":
        df_filtre = df
    else:
        df_filtre = df[df[col_secteur] == secteur_choisi]

    # --- 3. DASHBOARD VISUEL ---
    st.title(f"📊 Tableau de Bord : {secteur_choisi}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # On adapte les noms de colonnes selon ton fichier (ex: 'Heures Réalisées')
        val_h = df_filtre['Heures_Réalisées'].sum() if 'Heures_Réalisées' in df_filtre.columns else 0
        st.metric("Total Heures Réalisées", f"{val_h}h")
    with col2:
        alertes = len(df_filtre[df_filtre['Statut_34h_40h'] == 'ALERTE']) if 'Statut_34h_40h' in df_filtre.columns else 0
        st.metric("Alertes Conformité", alertes)
    with col3:
        mod_moy = df_filtre['Modulation_Cumulée'].mean() if 'Modulation_Cumulée' in df_filtre.columns else 0
        st.metric("Moyenne Modulation", f"{round(mod_moy, 2)}h")

    st.divider()

    # --- 4. ÉDITEUR (FONCTIONNEL) ---
    st.subheader("📝 Analyse et Ajustement des Secteurs")
    
    # L'éditeur modifie directement une COPIE de la session
    edited_df = st.data_editor(
        df_filtre,
        key="editor_modulation",
        use_container_width=True,
        num_rows="dynamic"
    )

    if st.button("💾 Enregistrer les modifications pour ce Secteur"):
        # On réintègre les lignes modifiées dans le DataFrame principal
        st.session_state.df_modulation.update(edited_df)
        st.success("Les modifications ont été mémorisées dans le système.")

    # --- 5. GRAPHIQUE (CELUI QUE TU AIMES) ---
    st.divider()
    st.subheader("📈 Visualisation de la Modulation par Salarié")
    
    if 'Salarié' in df_filtre.columns and 'Modulation_Cumulée' in df_filtre.columns:
        st.bar_chart(data=df_filtre, x='Salarié', y='Modulation_Cumulée')
    else:
        st.info("Veuillez vérifier que les colonnes 'Salarié' et 'Modulation_Cumulée' existent pour afficher le graphique.")

else:
    st.title("Bienvenue dans l'outil de Pilotage IDF")
    st.info("Veuillez charger un fichier dans la barre latérale pour commencer l'analyse par secteur.")

# Footer personnalisé
st.sidebar.divider()
st.sidebar.caption("Expertise Data & Optimisation Process | Aymen Amor")
