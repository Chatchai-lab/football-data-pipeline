import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.data_loaders import get_ratings, get_team_crests
from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters
from src.utils.components import render_navbar, render_sidebar_close, get_favicon

# --- SETUP ---
st.set_page_config(page_title="Team Ratings", page_icon=get_favicon(), layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=False)
render_sidebar_close()
filters = get_global_filters()
# --- DATENLADEN ---
df_ratings = get_ratings(filters["season"])

# --- TEAM-WAPPEN LADEN ---
crests = get_team_crests()

# --- TITEL & BESCHREIBUNG ---
st.title(f" Team-Rating & Leistungsanalyse ({filters['season']})")

# Task: Beschreibung der Kennzahlen aufnehmen
with st.expander("ℹ️ Erläuterung der Kennzahlen"):
    st.markdown("""
    * **Goals per Game:** Durchschnittlich erzielte Tore pro Spiel.
    * **Goals Conceded:** Durchschnittlich kassierte Gegentore pro Spiel (weniger ist besser).
    * **Clean Sheets:** Anzahl der Spiele ohne Gegentor.
    * **Performance Score:** Differenz zwischen Tor- und Gegentorschnitt (Indikator für Dominanz).
    """)

st.divider()

# --- SEKTION 1: LIGA-RANKING (ÜBERSICHT) ---
st.subheader(" Globales Liga-Ranking")

# Task: Teams nach Rating sortierbar machen
sort_options = {
    'performance_score': 'Performance Score',
    'goals_per_game': 'Tore pro Spiel',
    'clean_sheets': 'Clean Sheets',
    'goals_conceded_per_game': 'Gegentore pro Spiel'
}

selected_sort = st.selectbox(
    "Sortiere das Ranking nach:",
    options=list(sort_options.keys()),
    format_func=lambda x: sort_options[x]
)

# Sortierung anwenden (Gegentore: aufsteigend ist besser, sonst absteigend)
is_ascending = True if selected_sort == 'goals_conceded_per_game' else False
df_sorted = df_ratings.sort_values(by=selected_sort, ascending=is_ascending)

# Balkendiagramm erstellen
fig_rank = px.bar(
    df_sorted,
    x=selected_sort,
    y='team_name',
    orientation='h',
    text_auto='.2f',
    color=selected_sort,
    color_continuous_scale='RdYlGn' if selected_sort != 'goals_conceded_per_game' else 'RdYlGn_r',
    labels={'team_name': 'Verein', selected_sort: 'Wert'}
)

fig_rank.update_layout(
    height=500,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    margin=dict(l=0, r=0, t=20, b=20)
)
st.plotly_chart(fig_rank, use_container_width=True)

st.divider()

# --- SEKTION 2: DETAIL-VERGLEICH (RADAR) ---
st.subheader(" Team-DNA im Direktvergleich")

# Nutze die globalen Filter als Standard (Primäres Team + Vergleichs-Teams)
default_teams = [filters["team"]] + filters["comparisons"]
all_teams_list = sorted(df_ratings['team_name'].unique().tolist())

# Das Dropdown bleibt erhalten, ist aber mit den globalen Filtern vor-ausgefüllt
selected_teams = st.multiselect(
    "Wähle Teams für den DNA-Vergleich aus (Voreinstellung aus Sidebar):",
    options=all_teams_list,
    default=[t for t in default_teams if t in all_teams_list],
    max_selections=5
)

if selected_teams:
    # Ausgewählte Teams mit Wappen anzeigen
    team_cols = st.columns(min(len(selected_teams), 5))
    for idx, team in enumerate(selected_teams[:5]):
        with team_cols[idx]:
            crest = crests.get(team, '')
            if crest:
                st.image(crest, width=50)
            st.caption(team)

    fig_radar = go.Figure()
    
    # Wir definieren die Achsen für das Radar
    categories = ['Tore / Spiel', 'Clean Sheets', 'Defensiv-Stärke', 'Performance']
    
    for team in selected_teams:
        t_data = df_ratings[df_ratings['team_name'] == team].iloc[0]
        
        # Normalisierung/Skalierung für das Radar-Chart
        # Defensiv-Stärke: Wir nehmen (3 - Gegentore), damit ein hoher Wert "gut" bedeutet
        def_val = max(0, 3 - t_data['goals_conceded_per_game'])
        
        fig_radar.add_trace(go.Scatterpolar(
            r=[
                t_data['goals_per_game'], 
                t_data['clean_sheets'] / 3, # Skaliert auf ca. 0-5 Bereich
                def_val, 
                t_data['performance_score'] + 2 # Offset für positive Darstellung
            ],
            theta=categories,
            fill='toself',
            name=team
        ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, gridcolor="rgba(255,255,255,0.2)", range=[0, 5]),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=600,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center")
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("Wähle oben mindestens ein Team aus, um die DNA-Analyse zu starten.")

# --- DATENTABELLE ---
with st.expander(" Alle Rating-Rohdaten anzeigen"):
    # Kopie für die Anzeige mit schöneren Namen erstellen
    display_ratings = df_sorted.copy()
    
    # Wappen-Spalte hinzufügen
    display_ratings['crest_url'] = display_ratings['team_name'].map(crests)

    # Spalten umbenennen für die Anzeige
    display_ratings = display_ratings.rename(columns={
        'crest_url': ' ',
        'team_name': 'Team',
        'total_games': 'Spiele Gesamt',
        'goals_per_game': 'Tore Ø / Spiel',
        'goals_conceded_per_game': 'Gegentore Ø / Spiel',
        'clean_sheets': 'Weiße Weste (Clean Sheets)',
        'performance_score': 'Leistungsscore (Performance)'
    })
    
    # Index entfernen (sieht sauberer aus)
    st.dataframe(
        display_ratings,
        column_config={
            " ": st.column_config.ImageColumn("", width="small")
        },
        hide_index=True,
        use_container_width=True
    )