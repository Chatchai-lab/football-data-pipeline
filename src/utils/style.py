import streamlit as st

def apply_custom_style():
    st.markdown("""
        <style>
        /* Matchlytics Style: Hintergrundfarbe (Dunkles Blau/Anthrazit passend zum Logo) */
        .stApp {
            background-color: #1a1f2c;
            color: #ffffff;
        }
        
        /* KPI Karten Styling (Matchlytics Grün Akzent) */
        div[data-testid="stMetric"] {
            background-color: #242b3d;
            border: 2px solid #2d7a5e;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        
        /* Metriken Texte */
        div[data-testid="stMetric"] label, 
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #ffffff !important;
        }

        /* Titel & Texte weiß machen */
        h1, h2, h3, p, .stCaption, .stMarkdown, label {
            color: #ffffff !important;
        }

        /* Plotly Chart Achsbeschriftungen und Legende */
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

        /* Sidebar Styling: Dunkelblau passend zum Logo-Hintergrund */
        section[data-testid="stSidebar"] {
            background-color: #141822 !important;
        }
        
        /* Text in der Sidebar weiß machen */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] a,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        section[data-testid="stSidebar"] .st-emotion-cache-1gwvy71 {
            color: #ffffff !important;
        }

        /* Selectbox / Multiselect Input-Text dunkel (weiße Boxen) */
        section[data-testid="stSidebar"] [data-baseweb="select"] span,
        section[data-testid="stSidebar"] [data-baseweb="select"] div,
        section[data-testid="stSidebar"] [data-baseweb="select"] input,
        section[data-testid="stSidebar"] [data-baseweb="input"] input {
            color: #1a1a2e !important;
        }
        
        /* Matchlytics Akzentfarbe für Divider */
        hr {
            border-color: #2d7a5e;
        }

        /* Tabellen Styling */
        [data-testid="stTable"] thead tr th {
            color: #ffffff !important;
            background-color: #2d7a5e !important;
        }

        /* Expander Styling */
        div[data-testid="stExpander"] details summary {
            background-color: #242b3d !important;
            border: 1px solid #2d7a5e !important;
            border-radius: 8px !important;
            color: white !important;
        }
        
        div[data-testid="stExpander"] details summary p {
            color: white !important;
            font-weight: 700 !important;
        }
        
        div[data-testid="stExpander"] details[open] > div {
            background-color: #1f2636 !important;
            border: 1px solid #2d7a5e !important;
            border-top: none !important;
            color: white !important;
        }

        div[data-testid="stExpander"] svg {
            fill: white !important;
        }

        /* "app" Eintrag in der Sidebar-Navigation ausblenden */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child {
            display: none !important;
        }

        /* ─── Smooth Scrolling ─── */
        html {
            scroll-behavior: smooth !important;
        }

        /* ─── Streamlit Header (Deploy, Menu, etc.) komplett ausblenden ─── */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* ─── Platz für statische Navbar ─── */
        .main .block-container {
            padding-top: 20px !important; /* Weniger Padding oben, da Navbar nicht mehr fixiert ist */
        }

        /* ─── Navbar Styling (NICHT MEHR FIXIERT) ─── */
        .matchlytics-nav {
            position: relative;
            top: 0;
            left: 0;
            right: 0;
            z-index: 99 !important;
            background: #0e1117;
            border-bottom: 2px solid #2d7a5e;
            padding: 10px 48px; /* Normales Padding, Burger ist jetzt Teil der Navbar */
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'Segoe UI', sans-serif;
            min-height: 180px;
        }

        /* Logo ein Stück nach rechts schieben */
        .matchlytics-nav .nav-logo {
            margin-left: 30px;
        }

        /* ─── Streamlit Burger-Button: unsichtbar aber klickbar (kein pointer-events:none!) ─── */
        [data-testid="collapsedControl"] {
            opacity: 0 !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
        }

        /* ─── Eigener Burger-Button in der Navbar ─── */
        .nav-burger {
            font-size: 2rem;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 55px;
            height: 55px;
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            transition: background 0.2s;
            flex-shrink: 0;
            user-select: none;
            line-height: 1;
        }
        .nav-burger:hover {
            background: rgba(255,255,255,0.12);
        }

        /* ─── Navbar Sub-Elemente ─── */
        .matchlytics-nav .nav-logo {
            text-decoration: none;
            display: flex;
            align-items: center;
        }
        .matchlytics-nav .nav-links {
            display: flex;
            gap: 30px;
            margin-left: auto;
            margin-right: 40px;
            align-items: center;
        }
        .matchlytics-nav .nav-links a {
            color: #8892a4 !important;
            text-decoration: none !important;
            font-size: 0.95rem;
            font-weight: 500;
            transition: color 0.2s;
            white-space: nowrap;
        }
        .matchlytics-nav .nav-links a:hover {
            color: #2d7a5e !important;
        }

        /* ─── Standard-Schließ-Button (Pfeil) in der Sidebar verstecken ─── */
        section[data-testid="stSidebar"] {
            z-index: 999999 !important;
        }
        </style>
    """, unsafe_allow_html=True)
