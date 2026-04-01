import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters
from src.utils.components import render_navbar, render_sidebar_close, get_favicon

# --- SETUP ---
st.set_page_config(page_title="Saisonverlauf", page_icon=get_favicon(), layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=False)
render_sidebar_close()
filters = get_global_filters()
engine = get_db_engine()

# --- DATENLADEN ---
@st.cache_data
def load_trend_data(season):
    from sqlalchemy import text
    query = text("""
        SELECT matchday, team_name, cumulative_points 
        FROM fct_season_trend 
        WHERE season = :s
        ORDER BY matchday ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"s": season})
    df['matchday'] = pd.to_numeric(df['matchday'])
    return df

df_all_trends = load_trend_data(filters["season"])

# --- TEAM-WAPPEN LADEN ---
@st.cache_data
def load_team_crests():
    from sqlalchemy import text
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT team_name, crest_url FROM dim_teams"), conn)
    return dict(zip(df['team_name'], df['crest_url']))

crests = load_team_crests()

# --- TITEL ---
st.title(f"📈 Saisonverlauf & Team-Vergleich ({filters['season']})")
st.caption("Daten basierend auf den globalen Filtern in der Sidebar.")

# --- FILTER-BEREICH ---
with st.container():
    st.subheader("🔍 Analyse-Einstellungen")
    
    # Verfügbare Teams für die aktuelle Saison
    all_teams = df_all_trends['team_name'].unique().tolist()
    all_teams.sort()

    # Standard-Auswahl: Primäres Team + vorherige Vergleiche aus der Sidebar
    default_selection = [t for t in [filters["team"]] + filters["comparisons"] if t in all_teams]

    # Lokaler Multi-Selektor auf der Seite
    selected_teams = st.multiselect(
        "Zusätzliche Vereine zum Vergleich hinzufügen:",
        options=all_teams,
        default=default_selection,
        help="Hier kannst du unabhängig von der Sidebar weitere Teams zum Chart hinzufügen."
    )
    
    show_benchmarks = st.toggle("Benchmarks (CL / Klassenerhalt) einblenden", value=True)

st.divider()

# --- LOGIK & VISUALISIERUNG ---
if not selected_teams:
    st.warning("⚠️ Bitte wähle mindestens ein Team aus, um die Daten zu visualisieren.")
else:
    # Ausgewählte Teams mit Wappen anzeigen
    team_cols = st.columns(min(len(selected_teams), 6))
    for idx, team in enumerate(selected_teams[:6]):
        with team_cols[idx]:
            crest = crests.get(team, '')
            if crest:
                st.image(crest, width=40)
            st.caption(team)

    # Daten filtern
    df_filtered = df_all_trends[df_all_trends['team_name'].isin(selected_teams)]

    # Chart erstellen
    fig = px.line(
        df_filtered,
        x="matchday",
        y="cumulative_points",
        color="team_name",
        markers=True,
        labels={
            "matchday": "Spieltag",
            "cumulative_points": "Gesamtpunkte",
            "team_name": "Verein"
        }
    )
    
    if show_benchmarks:
        max_md = int(df_all_trends['matchday'].max())
        matchdays = list(range(1, max_md + 1))
        
        # Benchmark 1: Champions League ca. 2 Punkte/Spiel
        cl_points = [md * 2.0 for md in matchdays]
        fig.add_trace(go.Scatter(
            x=matchdays, y=cl_points,
            mode='lines',
            name='Ø Champions League (2.0 Pkt)',
            line=dict(color='gold', width=2, dash='dash'),
            opacity=0.6
        ))
        
        # Benchmark 2: Klassenerhalt (ca. 1.1 Pkt/Spiel)
        relegation_points = [md * 1.1 for md in matchdays]
        fig.add_trace(go.Scatter(
            x=matchdays, y=relegation_points,
            mode='lines',
            name='Ø Klassenerhalt (1.1 Pkt)',
            line=dict(color='gray', width=2, dash='dot'),
            opacity=0.6
        ))

    # Styling (Stadion-Look)
    fig.update_layout(
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            orientation="h",       # Legende horizontal unter dem Chart
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=0, r=0, t=30, b=100)
    )
    
    fig.update_xaxes(dtick=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')

    st.plotly_chart(fig, use_container_width=True)

    # --- DATEN-TABELLE (Task: Achsen und Labels verständlich) ---
    with st.expander("Tabellarische Ansicht der kumulierten Punkte"):
        pivot_df = df_filtered.pivot(index='matchday', columns='team_name', values='cumulative_points')
        st.dataframe(pivot_df.style.format(precision=0), use_container_width=True)