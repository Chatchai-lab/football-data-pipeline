"""
Landingpage – Übersicht mit KPIs und Spielplan.
Nutzt data_loaders für Datenabfragen und components für UI-Bausteine.
"""

import streamlit as st
import pandas as pd
from datetime import date


from src.utils.style import apply_custom_style
from src.utils.filters import get_global_filters
from src.utils.data_loaders import (
    get_league_highlights,
    get_match_schedule,
    get_team_crests,
)
from src.utils.components import (
    WDAYS_DE,
    get_favicon,
    render_kpi_row,
    render_match_card,
    render_matchday_header,
    render_navbar,
    render_sidebar_close,
    render_project_info,
    render_db_style_footer
)

# --- SETUP ---
st.set_page_config(page_title="Matchlytics | Bundesliga", page_icon=get_favicon(), layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()
render_navbar(is_landing=True)
render_sidebar_close()

# --- GLOBALE FILTER ---
filters = get_global_filters()
selected_season = filters["season"]

render_project_info()

st.divider()

# ──────────────────────────────────────────────
# KPI-BEREICH
# ──────────────────────────────────────────────
st.markdown('<div id="liga-highlights"></div>', unsafe_allow_html=True)
st.subheader(f"🏆 Liga-Highlights ({selected_season})")
leader_df, home_df, attack_df, form_df = get_league_highlights(selected_season)
render_kpi_row(leader_df, home_df, attack_df, form_df)

st.divider()




# ──────────────────────────────────────────────
# SPIELPLAN
# ──────────────────────────────────────────────
st.markdown('<div id="spielplan"></div>', unsafe_allow_html=True)
st.subheader("🗓️ Aktueller Spielplan")

df_matches = get_match_schedule(selected_season)
crests = get_team_crests()

if not df_matches.empty:
    today = date.today()
    df_matches["match_timestamp"] = pd.to_datetime(df_matches["match_timestamp"])
    future = df_matches[df_matches["match_timestamp"].dt.date >= today]
    next_md = future["matchday"].min() if not future.empty else df_matches["matchday"].max()

    # --- Nächster Spieltag (Preview) ---
    df_next = df_matches[df_matches["matchday"] == next_md]
    first_ts = df_next.iloc[0]["match_timestamp"]
    wday = WDAYS_DE[first_ts.weekday()]
    st.markdown(f"**Spieltag {int(next_md)} von 34 — {wday}, {first_ts.day}.{first_ts.month}.**")

    cols = st.columns(2)
    for i, (_, row) in enumerate(df_next.iterrows()):
        render_match_card(row, crests, show_date_label=True, container=cols[i % 2])

    # --- Gesamter Spielplan (Expander) ---
    with st.expander(f" Gesamter Spielplan ({selected_season})"):
        for md in sorted(df_matches["matchday"].unique(), reverse=True):
            df_md = df_matches[df_matches["matchday"] == md]
            render_matchday_header(md, str(df_md.iloc[0]["match_date"]))

            match_rows = list(df_md.iterrows())
            for i in range(0, len(match_rows), 2):
                col_l, col_r = st.columns(2)
                for j, col in enumerate([col_l, col_r]):
                    if i + j < len(match_rows):
                        render_match_card(match_rows[i + j][1], crests, container=col)
else:
    st.info("Keine Spieldaten gefunden.")


st.markdown('<div id="kontakt"></div>', unsafe_allow_html=True)
render_db_style_footer()