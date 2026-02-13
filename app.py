import streamlit as st
import pandas as pd
import io

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

if 'df_modulation' not in st.session_state:
    st.session_state.df_modulation = None

if uploaded_file is not None and st.session_state.df_modulation is None:
    if uploaded_file.name.endswith('.csv'):
        st.session_state.df_modulation = pd.read_csv(uploaded_file)
    else:
        st.session_state.df_modulation = pd.read_excel(uploaded_file)

# --- 2. INTERFACE DE PILOTAGE ---
if st.session_state.df_modulation is not None:
    df = st.session_state.df_modulation
    
    st.sidebar.divider()
    st.sidebar.title("🛠️ Paramètres")
    
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
        val_h = df_filtre['Heures_Réalisées'].sum() if 'Heures_Réalisées' in df_filtre.columns else 0
        st.metric("Total Heures Réalisées", f"{val_h}h")
    with col2:
        alertes = len(df_filtre[df_filtre['Statut_34h_40h'] == 'ALERTE']) if 'Statut_34h_40h' in df_filtre.columns else 0
        st.metric("Alertes Conformité", alertes)
    with col3:
        mod_moy = df_filtre['Modulation_Cumulée'].mean() if 'Modulation_Cumulée' in df_filtre.columns else 0
        st.metric("Moyenne Modulation", f"{round(mod_moy, 2)}h")

    st.divider()

    # --- 4. ÉDITEUR ---
    st.subheader("📝 Analyse et Ajustement")
    edited_df = st.data_editor(df_filtre, use_container_width=True, num_rows="dynamic", key="main_editor")

    if st.button("✅ Valider les modifications en mémoire"):
        if secteur_choisi == "Tous":
            st.session_state.df_modulation = edited_df
        else:
            st.session_state.df_modulation.update(edited_df)
        st.success("Données mises à jour dans l'application.")

    # --- 5. EXPORTATION DES DEUX DOCUMENTS ---
    st.sidebar.divider()
    st.sidebar.title("📤 Exporter les résultats")
    
    # Préparation du CSV
    csv = st.session_state.df_modulation.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name='modulation_idf_MAJ.csv',
        mime='text/csv',
    )

    # Préparation de l'Excel (plus complexe car nécessite un buffer)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        st.session_state.df_modulation.to_excel(writer, index=False, sheet_name='Modulation')
    
    st.sidebar.download_button(
        label="📥 Télécharger en Excel",
        data=buffer.getvalue(),
        file_name='modulation_idf_MAJ.xlsx',
        mime='application/vnd.ms-excel'
    )

    # --- 6. GRAPHIQUE ---
    st.divider()
    if 'Salarié' in df_filtre.columns and 'Modulation_Cumulée' in df_filtre.columns:
        st.subheader("📈 Vue graphique de la Modulation")
        st.bar_chart(data=df_filtre, x='Salarié', y='Modulation_Cumulée')

else:
    st.title("Bienvenue dans l'outil de Pilotage IDF")
    st.info("Veuillez charger un fichier Ximi pour activer les fonctions d'export.")

st.sidebar.divider()
st.sidebar.caption("Aymen Amor | Expert Data & Optimisation")
