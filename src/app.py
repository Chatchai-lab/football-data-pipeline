"""
Matchlytics – Streamlit Entrypoint.
Konfiguriert die App und leitet zur Landingpage weiter.
Alle Seitenlogik liegt unter src/pages/.
"""

import streamlit as st
from src.utils.style import apply_custom_style

st.set_page_config(page_title="Matchlytics | Bundesliga", layout="wide", initial_sidebar_state="collapsed")
apply_custom_style()

# Automatisch zur Landingpage weiterleiten
st.switch_page("pages/00_Landingpage.py")

