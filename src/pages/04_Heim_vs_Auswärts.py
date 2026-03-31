import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.db_client import get_db_engine
from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters
from src.utils.components import render_navbar, render_sidebar_close

# --- SETUP ---
st.set_page_config(page_title="Heim vs. Auswärts", layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=False)
render_sidebar_close()
filters = get_global_filters()
engine = get_db_engine()

# --- DATENLADEN (MIT LOGO JOIN) ---
@st.cache_data
def load_ha_data_with_crests(season):
    from sqlalchemy import text
    query = text("""
        SELECT 
            ha.*, 
            t.crest_url, 
            t.tla
        FROM fct_home_away_stats ha
        JOIN dim_teams t ON ha.team_name = t.team_name
        WHERE ha.season = :s
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"s": season})

df_ha = load_ha_data_with_crests(filters["season"])

# --- HEADER (MIT LOGO) ---
selected_team = filters["team"]

# Daten für das gewählte Team extrahieren
# Falls das Team in der Saison nicht existiert (z.B. Abstieg), nehmen wir das erste verfügbare
if df_ha[df_ha['team_name'] == selected_team].empty:
    team_data = df_ha.iloc[0]
    selected_team = team_data['team_name']
else:
    team_data = df_ha[df_ha['team_name'] == selected_team].iloc[0]


col_logo, col_title = st.columns([1, 6])

with col_logo:
    # 2. Logo anzeigen (falls vorhanden und gültig)
    if pd.notna(team_data['crest_url']) and team_data['crest_url']:
        st.image(team_data['crest_url'], width=100)
    else:
        st.warning("Kein Logo")

with col_title:
    # 3. Titel und TLA (Kürzel) anzeigen
    st.title(f"{selected_team} ({team_data['tla']})")
    st.caption("Detaillierter Vergleich der Performance im eigenen Stadion vs. in der Fremde.")

st.divider()

# --- KPI-REIHE (Zahlen im Überblick) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Punkte Heim", int(team_data['home_points']), help="Punkte im eigenen Stadion")
    st.metric("Punkte Auswärts", int(team_data['away_points']), help="Punkte in fremden Stadien")

with col2:
    st.metric("Tore Heim", int(team_data['home_goals_for']))
    st.metric("Tore Auswärts", int(team_data['away_goals_for']))

with col3:
    # Task: Siegquote zuhause vs. auswärts (Berechnet aus Stats)
    h_win_rate = round((team_data['home_wins'] / team_data['home_matches']) * 100, 1)
    a_win_rate = round((team_data['away_wins'] / team_data['away_matches']) * 100, 1)
    st.metric("Siegquote Heim", f"{h_win_rate}%")
    st.metric("Siegquote Auswärts", f"{a_win_rate}%")

st.divider()

# --- BERECHNUNG HEIM-VORTEIL-INDEX ---
# PPG = Points Per Game
home_ppg = team_data['home_points'] / team_data['home_matches']
away_ppg = team_data['away_points'] / team_data['away_matches']

# Index berechnen (Vermeidung von Division durch Null, falls away_ppg 0 ist)
if away_ppg > 0:
    hv_index = round(((home_ppg / away_ppg) - 1) * 100, 1)
else:
    hv_index = 100.0 # Maximaler Wert, wenn auswärts gar nichts geholt wurde

st.divider()

# --- ANZEIGE DES INDEX ---
idx_col1, idx_col2 = st.columns([1, 2])

with idx_col1:
    # Farbauswahl basierend auf dem Wert
    color = "inverse" if hv_index < 0 else "normal"
    st.metric(
        label="Heim-Vorteil-Index", 
        value=f"{hv_index}%", 
        delta=f"{round(home_ppg - away_ppg, 2)} PPG Differenz",
        delta_color=color
    )

with idx_col2:
    if hv_index > 20:
        st.success(f"🔥 **Festung {team_data['team_name']}:** Dieses Team ist im eigenen Stadion deutlich dominanter.")
    elif hv_index < -10:
        st.warning(f"✈️ **Auswärtsspezialist:** {team_data['team_name']} performt in der Fremde überraschend stark.")
    else:
        st.info(f"⚖️ **Balanced:** Die Leistung von {team_data['team_name']} ist stabil, egal wo gespielt wird.")

# --- VISUALISIERUNG (Task: Heim- und Auswärtspunkte / Tore darstellen) ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Punkte & Tore Vergleich")
    
    # Vorbereitung der Daten für ein gruppiertes Balkendiagramm
    plot_data = pd.DataFrame({
        'Kategorie': ['Punkte', 'Tore Erzielt', 'Tore Kassiert'],
        'Heim': [team_data['home_points'], team_data['home_goals_for'], team_data['home_goals_against']],
        'Auswärts': [team_data['away_points'], team_data['away_goals_for'], team_data['away_goals_against']]
    }).melt(id_vars='Kategorie', var_name='Ort', value_name='Anzahl')

    fig_bar = px.bar(
        plot_data, 
        x='Kategorie', 
        y='Anzahl', 
        color='Ort',
        barmode='group',
        color_discrete_map={'Heim': '#2e7d32', 'Auswärts': '#3fb34f'},
        text_auto=True
    )
    
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("🎯 Tor-Verhältnis (Radar/Spider)")
    
    # Radar Chart für eine intuitive "Balance"-Ansicht
    categories = ['Punkte', 'Siege', 'Tore+', 'Tore-']
    
    fig_radar = go.Figure()

    fig_radar.add_trace(go.Scatterpolar(
        r=[team_data['home_points'], team_data['home_wins'], team_data['home_goals_for'], team_data['home_goals_against']],
        theta=categories,
        fill='toself',
        name='Heim',
        line_color='#2e7d32'
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=[team_data['away_points'], team_data['away_wins'], team_data['away_goals_for'], team_data['away_goals_against']],
        theta=categories,
        fill='toself',
        name='Auswärts',
        line_color='#ffffff'
    ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, gridcolor="rgba(255,255,255,0.2)"),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        showlegend=True
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# --- EXPANDER (Rohdaten anzeigen) ---
with st.expander("📝 Alle Rohdaten für " + selected_team):
    # Spaltennamen für die Anzeige verschönern
    display_df = pd.DataFrame([team_data]).rename(columns={
        'team_name': 'Team',
        'home_matches': 'Spiele (Heim)',
        'home_points': 'Punkte (Heim)',
        'home_goals_for': 'Tore+ (Heim)',
        'home_goals_against': 'Tore- (Heim)',
        'home_wins': 'Siege (Heim)',
        'home_ppg': 'Ø Pkt (Heim)',
        'away_matches': 'Spiele (Gast)',
        'away_points': 'Punkte (Gast)',
        'away_goals_for': 'Tore+ (Gast)',
        'away_goals_against': 'Tore- (Gast)',
        'away_wins': 'Siege (Gast)',
        'away_ppg': 'Ø Pkt (Gast)',
        'total_points': 'Gesamtpunkte'
    })
    st.table(display_df)