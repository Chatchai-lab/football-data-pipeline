import streamlit as st
from src.utils.data_loaders import get_seasons, get_teams

def get_global_filters():
    # Close-Button (×) wird per JS in style.py injiziert
    st.sidebar.header("Globale Filter")
    
    # 1. Saisons dynamisch aus dem neuen View laden
    season_list = get_seasons()
    
    # Helfer-Funktion für die Anzeige (2025 -> Saison 2025/26)
    def format_season(s):
        if not s: return "Unbekannt"
        try:
            year = int(s)
            return f"Saison {year}/{str(year+1)[2:]}"
        except:
            return s

    # Initialisierung der Session State Werte, falls sie noch nicht existieren
    if 'global_season' not in st.session_state and season_list:
        st.session_state['global_season'] = season_list[0]

    selected_season = st.sidebar.selectbox(
        "Saison wählen", 
        options=season_list, 
        format_func=format_season,
        key="global_season_widget",
        index=season_list.index(st.session_state['global_season']) if 'global_season' in st.session_state and st.session_state['global_season'] in season_list else 0
    )
    st.session_state['global_season'] = selected_season
    
    # 2. Teams passend zur gewählten Saison laden
    team_list = get_teams(selected_season)
    
    if 'global_team' not in st.session_state and team_list:
        st.session_state['global_team'] = team_list[0]

    selected_team = st.sidebar.selectbox(
        "Primäres Team", 
        options=team_list, 
        key="global_team_widget",
        index=team_list.index(st.session_state['global_team']) if 'global_team' in st.session_state and st.session_state['global_team'] in team_list else 0
    )
    st.session_state['global_team'] = selected_team
    
    # 3. Vergleichs-Teams
    if 'global_comparisons' not in st.session_state:
        st.session_state['global_comparisons'] = []

    comparison_teams = st.sidebar.multiselect(
        "Vergleichs-Teams",
        options=[t for t in team_list if t != selected_team],
        key="global_comparisons_widget",
        default=[t for t in st.session_state['global_comparisons'] if t in team_list and t != selected_team]
    )
    st.session_state['global_comparisons'] = comparison_teams

    return {
        "season": st.session_state['global_season'],
        "team": st.session_state['global_team'],
        "comparisons": st.session_state['global_comparisons']
    }
