import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style

# --- SETUP ---
st.set_page_config(page_title="Team-Analyse", layout="wide")
apply_custom_style()

engine = get_db_engine()


# --- DATENLADEN ---
@st.cache_data
def load_teams():
    query = """
        SELECT team_name, crest_url, tla
        FROM dim_teams
        ORDER BY team_name
    """
    return pd.read_sql(query, engine)


@st.cache_data
def load_team_details(team_name: str):
    form_query = """
        SELECT form_trend
        FROM fct_team_form
        WHERE team_name = %(team_name)s
    """

    ratings_query = """
        SELECT *
        FROM fct_team_ratings
        WHERE team_name = %(team_name)s
    """

    trends_query = """
        SELECT matchday, cumulative_points
        FROM fct_season_trend
        WHERE team_name = %(team_name)s
        ORDER BY matchday
    """

    home_away_query = """
        SELECT *
        FROM fct_home_away_stats
        WHERE team_name = %(team_name)s
    """

    params = {"team_name": team_name}

    form = pd.read_sql(form_query, engine, params=params)
    ratings = pd.read_sql(ratings_query, engine, params=params)
    trends = pd.read_sql(trends_query, engine, params=params)
    home_away = pd.read_sql(home_away_query, engine, params=params)

    return form, ratings, trends, home_away


# --- HILFSFUNKTIONEN ---
def parse_form_trend(form_str: str) -> list[str]:
    if not form_str or pd.isna(form_str):
        return []

    form_str = str(form_str).strip()

    if "-" in form_str:
        tokens = [token.strip().upper() for token in form_str.split("-") if token.strip()]
    else:
        tokens = [char.upper() for char in form_str if char.strip()]

    allowed = {"W", "D", "L"}
    return [token for token in tokens if token in allowed]


def render_form_badges(results: list[str]):
    if not results:
        st.info("Keine Formdaten verfügbar.")
        return

    label_map = {
        "W": ("Sieg", "#16a34a"),
        "D": ("Remis", "#f59e0b"),
        "L": ("Niederlage", "#dc2626"),
    }

    html = ""
    for result in results:
        label, color = label_map[result]
        html += f"""
        <div style="
            display:inline-block;
            margin-right:8px;
            margin-bottom:8px;
            padding:10px 14px;
            border-radius:10px;
            background:{color};
            color:white;
            font-weight:600;
            font-size:14px;">
            {label}
        </div>
        """

    st.markdown(html, unsafe_allow_html=True)
    st.caption("Verlauf der letzten Spiele")


def calculate_form_score(results: list[str]) -> tuple[int, int]:
    score_map = {"W": 3, "D": 1, "L": 0}
    score = sum(score_map.get(result, 0) for result in results)
    max_score = len(results) * 3
    return score, max_score


# --- TEAMDATEN ---
df_teams = load_teams()

st.title("Team-Analyse")

filter_col_1, filter_col_2 = st.columns([3, 5])

with filter_col_1:
    selected_team = st.selectbox(
        "Wähle ein Team",
        df_teams["team_name"],
        index=0
    )

team_info = df_teams[df_teams["team_name"] == selected_team].iloc[0]

with filter_col_2:
    st.markdown("####")
    st.caption("Analyse von Form, Ratings, Saisontrend sowie Heim-/Auswärtsleistung")

# --- HEADER ---
col_header_1, col_header_2 = st.columns([1, 5])

with col_header_1:
    if pd.notna(team_info["crest_url"]) and team_info["crest_url"]:
        st.image(team_info["crest_url"], width=90)

with col_header_2:
    st.subheader(f"{selected_team} ({team_info['tla']})")

# --- DETAILDATEN LADEN ---
df_form, df_ratings, df_trends, df_ha = load_team_details(selected_team)

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
        st.info("Keine Performance-Daten verfügbar.")

    st.divider()
    st.subheader("Form der letzten Spiele")

    if not df_form.empty:
        form_str = df_form["form_trend"].iloc[0]
        parsed_results = parse_form_trend(form_str)
        render_form_badges(parsed_results)

        form_score, max_score = calculate_form_score(parsed_results)
        st.metric("Formscore", f"{form_score}/{max_score}")
    else:
        st.info("Keine Formdaten verfügbar.")

with col_chart:
    st.subheader("Saisonverlauf (kumulierte Punkte)")

    if not df_trends.empty:
        df_trends["matchday"] = pd.to_numeric(df_trends["matchday"], errors="coerce")
        df_trends["cumulative_points"] = pd.to_numeric(
            df_trends["cumulative_points"], errors="coerce"
        )
        df_trends = df_trends.dropna(subset=["matchday", "cumulative_points"])
        df_trends = df_trends.sort_values("matchday")

        fig = px.line(
            df_trends,
            x="matchday",
            y="cumulative_points",
            markers=True,
            labels={
                "matchday": "Spieltag",
                "cumulative_points": "Kumulierte Punkte"
            },
            title=f"Punktentwicklung von {selected_team}"
        )

        fig.update_traces(
            line_color="#e30613",
            marker=dict(size=8)
        )

        fig.update_layout(
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e0e0e0")
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Trenddaten verfügbar.")

# --- HEIM VS AUSWÄRTS ---
st.divider()
st.subheader("Heim- vs. Auswärts-Stärke")

if not df_ha.empty:
    ha = df_ha.iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Punkte zuhause", int(ha["home_points"]), help=f"{ha['home_ppg']} Punkte pro Heimspiel")
    c2.metric("Punkte auswärts", int(ha["away_points"]), help=f"{ha['away_ppg']} Punkte pro Auswärtsspiel")
    c3.metric("Gesamtpunkte", int(ha["total_points"]))
else:
    st.info("Keine Heim-/Auswärtsdaten verfügbar.")