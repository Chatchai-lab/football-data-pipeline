import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style

# --- SETUP ---
st.set_page_config(page_title="Saisonverlauf", layout="wide")
apply_custom_style()
engine = get_db_engine()

# --- DATENLADEN ---
@st.cache_data
def load_trend_data():
    query = """
        SELECT matchday, team_name, cumulative_points 
        FROM fct_season_trend 
        ORDER BY matchday ASC
    """
    df = pd.read_sql(query, engine)
    df['matchday'] = pd.to_numeric(df['matchday'])
    return df

df_all_trends = load_trend_data()

# --- TITEL ---
st.title("📈 Saisonverlauf & Team-Vergleich")
st.caption("Wähle unten die Teams aus, die du im direkten Vergleich sehen möchtest.")

# --- FILTER-BEREICH ---
with st.container():
    st.subheader("🔍 Analyse-Einstellungen")
    # Wir erstellen zwei Spalten: Eine für die Teams, eine für den Schalter
    col_teams, col_toggle = st.columns([3, 1])
    
    with col_teams:
        all_teams = sorted(df_all_trends['team_name'].unique())
        selected_teams = st.multiselect(
            "Vergleiche mehrere Teams miteinander:",
            options=all_teams,
            default=all_teams[:3]
        )
    
    with col_toggle:
        st.write("####") # Kleiner Abstandshalter für die Optik
        # WICHTIG: Hier definieren wir die Variable, die unten in der IF-Abfrage genutzt wird
        show_benchmarks = st.toggle("Benchmarks einblenden", value=True)

st.divider()

# --- LOGIK & VISUALISIERUNG ---
if not selected_teams:
    st.warning("⚠️ Bitte wähle mindestens ein Team aus, um die Daten zu visualisieren.")
else:
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