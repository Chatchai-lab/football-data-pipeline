import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters
from src.utils.components import render_navbar, render_sidebar_close

# --- SETUP & DATEN ---
st.set_page_config(page_title="Liga-Übersicht", layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=False)
render_sidebar_close()
filters = get_global_filters()

engine = get_db_engine()

@st.cache_data
def get_league_data(season_val):
    from sqlalchemy import text
    query = text("""
    SELECT 
        s.*, 
        t.crest_url 
    FROM fct_standings s
    JOIN dim_teams t ON s.team_name = t.team_name
    WHERE s.season = :season_param
    ORDER BY s.total_points DESC, s.goal_diff DESC
    """)
    return pd.read_sql(query, engine.connect(), params={"season_param": season_val})

df = get_league_data(filters["season"])

# --- TITEL ---
st.title(f"🏆 Bundesliga Liga-Übersicht - Saison {filters['season']}")
st.caption("Live-Daten aus der Analytics-Pipeline")
# --- KPI-KARTEN (Task: KPI-Karten für...) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Anzahl Teams", len(df))
with col2:
    st.metric("Gesamtpunkte (Liga)", df['total_points'].sum())
with col3:
    st.metric("Gesamttore", df['total_goals_for'].sum())
with col4:
    avg_points = round(df['points_per_match'].mean(), 2)
    st.metric("Ø Punkte / Spiel", avg_points)

st.divider()

# --- TABELLE (Task: Position, Team, Punkte, Tore...) ---
st.subheader("Aktueller Tabellenstand")

# Wir fügen eine virtuelle Position hinzu, da fct_standings bereits sortiert ist
df.insert(0, 'Position', range(1, len(df) + 1))

st.dataframe(
    df[['Position', 'crest_url', 'team_name', 'matches_played', 'total_points', 'total_goals_for', 'total_goals_against', 'goal_diff']],
    column_config={
        "crest_url": st.column_config.ImageColumn(""),
        "team_name": "Team",
        "matches_played": "Spiele",
        "total_points": "Punkte",
        "total_goals_for": "Tore",
        "total_goals_against": "Gegentore",
        "goal_diff": "Diff."
    },
    hide_index=True,
    use_container_width=True
)

# --- VISUALISIERUNG (Task: Punkteverteilung ergänzen) ---
st.divider()
st.subheader("Visualisierung der Punkteverteilung")
fig = px.bar(
    df, 
    x='team_name', 
    y='total_points', 
    text='total_points',
    labels={'team_name': 'Team', 'total_points': 'Punkte'},
    color='total_points',
    color_continuous_scale='RdYlGn'
)
fig.update_traces(textposition='outside')
st.plotly_chart(fig, use_container_width=True)