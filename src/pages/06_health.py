"""
Health-Check-Endpunkt für Uptime-Monitoring (z. B. UptimeRobot).
Erreichbar unter: https://<app-url>/health

Gibt den DB-Status als JSON-ähnlichen Text zurück.
UptimeRobot prüft, ob das Keyword "healthy" im Response vorkommt.
"""

import streamlit as st
from src.utils.data_loaders import get_db_status

# Keine Sidebar, kein Layout – reiner Status-Endpunkt
st.set_page_config(page_title="Health", layout="centered", initial_sidebar_state="collapsed")

db = get_db_status()

if db["db_online"]:
    st.markdown(
        f'<pre style="color:#2d7a5e;">status: healthy\n'
        f'db: online\n'
        f'matches: {db["match_count"]}\n'
        f'teams: {db["team_count"]}\n'
        f'last_update: {db["last_update"] or "n/a"}</pre>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<pre style="color:#e74c3c;">status: unhealthy\ndb: offline</pre>',
        unsafe_allow_html=True,
    )
