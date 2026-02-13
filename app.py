import streamlit as st
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Pilotage Modulation IDF", layout="wide")

# --- STYLE CSS POUR UN RENDU PROFESSIONNEL (SIÈGE) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 1. INITIALISATION DES DONNÉES (Session State) ---
# Ce bloc permet de garder les modifications en mémoire malgré les rechargements de Streamlit
if 'df_modulation' not in st.session_state:
    # Simulation de données (à remplacer par ton pd.read_excel ou pd.read_csv)
    data = {
        'Secteur': ['Secteur 011', 'Secteur 012', 'Secteur 011', 'Secteur 013', 'Secteur 012'],
        'Salarié': ['Amina B.', 'Thomas D.', 'Yacine K.', 'Julie L.', 'Marc O.'],
        'Heures_Contrat': [130, 151.67, 130, 100, 151.67],
        'Heures_Réalisées': [145, 140, 165, 95, 155],
        'Modulation_Cumulée': [15, -11.67, 35, -5, 3.33],
        'Statut_34h_40h': ['Conforme', 'Conforme', 'ALERTE', 'Conforme', 'Conforme']
    }
    st.session_state.df_modulation = pd.DataFrame(data)

# --- 2. BARRE LATÉRALE (FILTRES) ---
st.sidebar.title("🛠️ Paramètres de Pilotage")
st.sidebar.info("Outil d'optimisation des process - Région IDF")

# Filtre par Secteur
secteurs_disponibles = ["Tous"] + list(st.session_state.df_modulation['Secteur'].unique())
secteur_choisi = st.sidebar.selectbox("Sélectionner le Secteur", secteurs_disponibles)

# Filtrage du DataFrame pour l'affichage
if secteur_choisi == "Tous":
    df_a_afficher = st.session_state.df_modulation
else:
    df_a_afficher = st.session_state.df_modulation[st.session_state.df_modulation['Secteur'] == secteur_choisi]

# --- 3. DASHBOARD : INDICATEURS CLÉS (KPI) ---
st.title(f"📊 Tableau de Bord : {secteur_choisi}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Heures Réalisées", f"{df_a_afficher['Heures_Réalisées'].sum()}h")
with col2:
    alertes = len(df_a_afficher[df_a_afficher['Statut_34h_40h'] == 'ALERTE'])
    st.metric("Alertes Conformité (34h/40h)", alertes, delta="-2" if alertes > 0 else "0", delta_color="inverse")
with col3:
    st.metric("Moyenne Modulation", f"{round(df_a_afficher['Modulation_Cumulée'].mean(), 2)}h")

st.divider()

# --- 4. ÉDITEUR DE DONNÉES (CORRECTION DU BUG) ---
st.subheader("📝 Analyse et Ajustement des Secteurs")
st.write("Modifiez les valeurs ci-dessous pour simuler des régularisations ou corriger les saisies Ximi.")

# On utilise st.data_editor avec une clé unique. 
# Les changements sont capturés dans 'edited_df'
edited_df = st.data_editor(
    df_a_afficher,
    key="editor_modulation",
    num_rows="dynamic",
    use_container_width=True
)

# --- 5. SAUVEGARDE DES MODIFICATIONS ---
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("💾 Enregistrer les modifications"):
        # Mise à jour du dataframe principal dans le session_state
        if secteur_choisi == "Tous":
            st.session_state.df_modulation = edited_df
        else:
            # On met à jour uniquement les lignes du secteur choisi
            st.session_state.df_modulation.update(edited_df)
        
        st.success("Données du secteur mises à jour !")
        # Optionnel : décommenter pour sauvegarder réellement dans ton fichier
        # st.session_state.df_modulation.to_excel("suivi_modulation_idf.xlsx", index=False)

with col_btn2:
    if st.button("🚀 Générer Rapport Audit"):
        st.info("Génération du rapport d'optimisation en cours pour la direction de filière...")

# --- 6. VISUALISATION (DATA SCIENCE) ---
st.divider()
st.subheader("📈 Visualisation de la Modulation par Salarié")
if not df_a_afficher.empty:
    st.bar_chart(data=df_a_afficher, x='Salarié', y='Modulation_Cumulée')
else:
    st.warning("Aucune donnée disponible pour ce secteur.")

st.sidebar.divider()
st.sidebar.caption("Développé par Aymen Amor - Expertise Data & Optimisation Process")
