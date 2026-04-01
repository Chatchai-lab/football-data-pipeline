import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters  # NEU: Filter importieren
from src.utils.components import render_navbar, render_sidebar_close, get_favicon

# --- SETUP ---
st.set_page_config(page_title="Team-Analyse", page_icon=get_favicon(), layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=False)
render_sidebar_close()

# --- GLOBALE FILTER ---
# Wir rufen die Filter ganz am Anfang auf, um season und team zu erhalten
filters = get_global_filters()
selected_season = filters["season"]

# --- LOKALES TEAM-DROPDOWN ---
# Wir erlauben es, auf dieser Seite ein anderes Team zu wählen als das globale standard-team
engine = get_db_engine()
from sqlalchemy import text
teams_query = text("SELECT DISTINCT team_name FROM fct_standings WHERE season = :s ORDER BY team_name")
teams_df = pd.read_sql(teams_query, engine.connect(), params={"s": selected_season})
team_list = teams_df['team_name'].tolist()

# Der Standardwert ist das global gewählte Team
st.markdown("###  Team wechseln")
selected_team = st.selectbox(
    "Team für Detail-Analyse wählen:", 
    options=team_list, 
    index=team_list.index(filters["team"]) if filters["team"] in team_list else 0
)

# --- DATENLADEN ---
@st.cache_data
def load_team_info(team_name):
    from sqlalchemy import text
    # Hilfsquery für Logo und TLA
    query = text("SELECT team_name, crest_url, tla FROM dim_teams WHERE team_name = :t")
    return pd.read_sql(query, engine.connect(), params={"t": team_name})

@st.cache_data
def load_team_details(team_name: str, season: str):
    from sqlalchemy import text
    # Alle Queries nutzen nun zusätzlich das Season-Feld
    params = {"team_name": team_name, "season": season}

    form_query = text("""
        SELECT form_trend
        FROM fct_team_form
        WHERE team_name = :team_name AND season = :season
    """)

    ratings_query = text("""
        SELECT *
        FROM fct_team_ratings
        WHERE team_name = :team_name AND season = :season
    """)

    trends_query = text("""
        SELECT matchday, cumulative_points
        FROM fct_season_trend
        WHERE team_name = :team_name AND season = :season
        ORDER BY matchday
    """)

    home_away_query = text("""
        SELECT *
        FROM fct_home_away_stats
        WHERE team_name = :team_name AND season = :season
    """)

    with engine.connect() as conn:
        form = pd.read_sql(form_query, conn, params=params)
        ratings = pd.read_sql(ratings_query, conn, params=params)
        trends = pd.read_sql(trends_query, conn, params=params)
        home_away = pd.read_sql(home_away_query, conn, params=params)

    return form, ratings, trends, home_away

# --- HILFSFUNKTIONEN (Form-Badges etc. bleiben gleich) ---
def parse_form_trend(form_str: str) -> list[str]:
    if not form_str or pd.isna(form_str): return []
    # Format: "L-W-D-W-L" -> split by "-"
    tokens = [t.strip().upper() for t in str(form_str).split("-") if t.strip()]
    return [t for t in tokens if t in {"W", "D", "L"}]

def render_form_badges(results: list[str]):
    label_map = {"W": ("Sieg", "#16a34a"), "D": ("Remis", "#f59e0b"), "L": ("Niederlage", "#dc2626")}
    html = "".join([f'<div style="display:inline-block;margin-right:8px;padding:8px 12px;border-radius:8px;background:{label_map[r][1]};color:white;font-weight:600;">{label_map[r][0]}</div>' for r in results])
    st.markdown(html, unsafe_allow_html=True)

# --- HEADER BEREICH ---
df_team_meta = load_team_info(selected_team)
if not df_team_meta.empty:
    team_info = df_team_meta.iloc[0]
    col_logo, col_text = st.columns([1, 5])
    with col_logo:
        if team_info["crest_url"]: st.image(team_info["crest_url"], width=90)
    with col_text:
        st.title(f"Team-Analyse: {selected_team}")
        st.subheader(f"Saison {selected_season} ({team_info['tla']})")
else:
    st.title(f"Team-Analyse: {selected_team}")

# --- DETAILDATEN LADEN ---
df_form, df_ratings, df_trends, df_ha = load_team_details(selected_team, selected_season)

st.divider()

# --- KPI & TREND ---
col_stats, col_chart = st.columns([1, 2])

with col_stats:
    st.subheader("Performance-Daten")
    if not df_ratings.empty:
        r = df_ratings.iloc[0]
        st.metric("Spiele gesamt", int(r["total_games"]))
        st.metric("Ø Tore pro Spiel", round(float(r["goals_per_game"]), 2))
        st.metric("Ø Gegentore", round(float(r["goals_conceded_per_game"]), 2))
        st.metric("Clean Sheets", int(r["clean_sheets"]))
    else:
        st.info("Keine Performance-Daten für diese Saison verfügbar.")

    st.divider()
    st.subheader("Form (Letzte Spiele)")
    if not df_form.empty:
        parsed_results = parse_form_trend(df_form["form_trend"].iloc[0])
        render_form_badges(parsed_results)
    else:
        st.info("Keine Formdaten verfügbar.")

with col_chart:
    st.subheader("Saisonverlauf")
    if not df_trends.empty:
        fig = px.line(df_trends, x="matchday", y="cumulative_points", markers=True, title="Punktentwicklung")
        fig.update_traces(line_color="#2e7d32") # Grün statt Rot für Konsistenz
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Trenddaten verfügbar.")

# --- HEIM VS AUSWÄRTS ---
st.divider()
st.subheader("Heim- vs. Auswärts-Stärke")
if not df_ha.empty:
    ha = df_ha.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Punkte zuhause", int(ha["home_points"]), delta=f"{ha['home_ppg']} PPG")
    c2.metric("Punkte auswärts", int(ha["away_points"]), delta=f"{ha['away_ppg']} PPG")
    c3.metric("Gesamtpunkte", int(ha["total_points"]))
else:
    st.info("Keine Heim-/Auswärtsdaten verfügbar.")