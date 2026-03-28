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
        
       /* STYLING FÜR DEN EXPANDER (DROPDOWN) */
        
        /* 1. Der Header (das anklickbare Feld) */
        div[data-testid="stExpander"] details summary {
            background-color: #2e7d32 !important; /* Helleres Grün für Sichtbarkeit */
            border: 1px solid #3fb34f !important; /* Noch hellere Kante */
            border-radius: 10px !important;
            padding: 10px !important;
            transition: all 0.3s ease;
        }

        /* 2. Hover-Effekt: Wenn man mit der Maus drüberfährt */
        div[data-testid="stExpander"] details summary:hover {
            background-color: #3fb34f !important;
            border-color: #ffffff !important;
        }

        /* 3. Text im Header weiß und fett */
        div[data-testid="stExpander"] details summary p {
            color: white !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
        }

        /* 4. Den roten Rahmen (Focus) komplett eliminieren */
        div[data-testid="stExpander"] details summary:focus,
        div[data-testid="stExpander"] details {
            outline: none !important;
            box-shadow: none !important;
            border-color: #3fb34f !important;
        }

        /* 5. Der Inhaltsbereich (wenn aufgeklappt) */
        div[data-testid="stExpander"] details[open] > div {
            background-color: #1a4a25 !important;
            border: 1px solid #2e7d32 !important;
            border-top: none !important;
            border-radius: 0 0 10px 10px !important;
            color: white !important;
        }

        /* 6. Das Icon (Pfeil) weiß färben */
        div[data-testid="stExpander"] svg {
            fill: white !important;
        }
        
        </style>
        """, unsafe_allow_html=True)
