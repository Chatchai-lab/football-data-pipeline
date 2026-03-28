import streamlit as st

def apply_custom_style():
    st.markdown("""
        <style>
        /* Hintergrundfarbe (Dunkles Stadion-Grün) */
        .stApp {
            background-color: #0e2a14;
            color: white;
        }
        
        /* KPI Karten Styling */
        div[data-testid="stMetric"] {
            background-color: #1a4a25;
            border: 2px solid #2e7d32;
            border-radius: 15px;
            padding: 15px;
            color: white !important;
        }
        
        /* Titel & Texte weiß machen */
        h1, h2, h3, p, .stCaption, .stMarkdown, label {
            color: #ffffff !important;
        }

        /* Plotly Chart Achsbeschriftungen und Legende heller machen */
        .js-plotly-plot .plotly .xtick text, 
        .js-plotly-plot .plotly .ytick text,
        .js-plotly-plot .plotly .g-xtitle,
        .js-plotly-plot .plotly .g-ytitle,
        .js-plotly-plot .plotly .g-titletext,
        .js-plotly-plot .plotly .legendtext,
        .js-plotly-plot .plotly .annotation-text {
            fill: #ffffff !important;
            color: #ffffff !important;
        }

        /* SVG Texte innerhalb von Plotly erzwingen */
        .js-plotly-plot .plotly text {
            fill: #ffffff !important;
        }

        /* Divider Farbe anpassen */
        hr {
            border-color: #2e7d32;
        }
        
        /* Plotly Chart Background transparent machen */
        .js-plotly-plot .plotly .main-svg {
            background-color: transparent !important;
        }
        
        /* Sidebar Styling: Weißer Hintergrund und dunkler Text für Kontrast */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
        }
        
        /* Text in der Sidebar schwarz machen */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #000000 !important;
        }
        </style>
        """, unsafe_allow_html=True)
