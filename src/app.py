import streamlit as st
from src.utils.style import apply_custom_style

st.set_page_config(page_title="Bundesliga Hub", layout="wide")
apply_custom_style()

st.title("⚽ Bundesliga Data Engine")
st.markdown("""
### Willkommen im Kontrollzentrum
Wähle links in der Sidebar eine Analyse-Ansicht aus.
- **Liga-Tabelle:** Der aktuelle Stand direkt aus dem Gold-Layer.
- **Team-Analyse:** Deep-Dive in die Performance einzelner Vereine.
""")
