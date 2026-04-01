"""
Wiederverwendbare UI-Komponenten für die Matchlytics-App.
Trennt HTML/CSS-Rendering von der Seitenlogik.
"""

import os
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# --- KONSTANTEN ---
WDAYS_DE = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}

# --- Projekt-Basispfad ---
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_favicon():
    """Gibt ein PIL.Image des Favicons (favicon.png, 32x32) zurück, oder None."""
    favicon_path = os.path.join(_BASE_DIR, "docs", "logo", "favicon.png")
    if os.path.exists(favicon_path):
        return Image.open(favicon_path)
    return None


def render_sidebar_close():
    """Kein custom X mehr nötig – der native Streamlit-Close-Button reicht."""
    pass


def render_navbar(is_landing=True):
    """Fixierte Top-Navigationsleiste mit Logo, Scroll-Links und Hamburger-Platz."""
    import base64
    import os

    logo_b64 = ""
    # Pfad relativ zur Projektstruktur – funktioniert lokal, in Docker und auf Render
    logo_path = os.path.join(_BASE_DIR, "docs", "logo", "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" height="200">'
        if logo_b64
        else '<span style="color:#2d7a5e; font-weight:700; font-size:3rem;">Matchlytics</span>'
    )

    logo_href = "#top" if is_landing else "/Landingpage"
    logo_target = '' if is_landing else ' target="_self"'

    if is_landing:
        links = (
            '<a href="#sinn-zweck">Sinn & Zweck</a>'
            '<a href="#historie">Historie</a>'
            '<a href="#liga-highlights">Liga-Highlights</a>'
            '<a href="#spielplan">Aktueller Spielplan</a>'
            '<a href="#kontakt">Kontakt</a>'
        )
    else:
        links = ""

    # Eigener Burger-Button direkt in der Navbar-HTML
    burger_html = '<div class="nav-burger">&#9776;</div>'

    st.markdown(
        f'<div class="matchlytics-nav">'
        f'<a href="{logo_href}" class="nav-logo"{logo_target}>{logo_img}</a>'
        f'<div class="nav-links">{links}</div>'
        f'{burger_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Event Delegation: Klick auf unseren Burger -> Streamlits nativen Button klicken
    components.html("""
        <script>
        (function() {
            var doc = window.parent.document;

            // Alten Handler entfernen falls vorhanden, dann frisch registrieren
            if (doc._mlBurgerHandler) {
                doc.removeEventListener('click', doc._mlBurgerHandler);
            }

            doc._mlBurgerHandler = function(e) {
                var burger = e.target.closest('.nav-burger');
                if (!burger) return;
                e.preventDefault();
                e.stopPropagation();

                // Fall 1: Sidebar ist ZU -> collapsedControl existiert -> öffnen
                var openBtn = doc.querySelector('[data-testid="collapsedControl"] button');
                if (openBtn) {
                    openBtn.click();
                    return;
                }

                // Fall 2: Sidebar ist AUF -> Close-Button suchen -> schließen
                var closeBtn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button')
                            || doc.querySelector('section[data-testid="stSidebar"] button[kind="header"]');
                if (closeBtn) {
                    closeBtn.click();
                    return;
                }
            };

            doc.addEventListener('click', doc._mlBurgerHandler);
        })();
        </script>
    """, height=0)


def render_match_card(
    row,
    crests: dict,
    *,
    show_date_label: bool = False,
    container=None,
):
    """
    Rendert eine einzelne Spiel-Karte mit Wappen, Ergebnis und optionalem Datum.

    Args:
        row: Pandas Series mit home_team_name, away_team_name, goals_home,
             goals_away, status, match_time, match_timestamp.
        crests: Dict {team_name: crest_url}.
        show_date_label: Zeige Wochentag + Datum über der Karte.
        container: Streamlit-Container (col, st, etc.). Default = st.
    """
    target = container or st

    is_fin = row["status"] in ("FINISHED", "AWARDED")
    score = (
        f"{int(row['goals_home'])} : {int(row['goals_away'])}"
        if is_fin
        else row["match_time"]
    )
    score_bg = "#2d7a5e" if is_fin else "#3a3f52"

    # Wappen
    home_crest = crests.get(row["home_team_name"], "")
    away_crest = crests.get(row["away_team_name"], "")
    home_img = (
        f'<img src="{home_crest}" height="22" '
        f'style="vertical-align:middle; margin-right:6px;">'
        if home_crest
        else ""
    )
    away_img = (
        f'<img src="{away_crest}" height="22" '
        f'style="vertical-align:middle; margin-left:6px;">'
        if away_crest
        else ""
    )

    # Optionale Datumszeile
    date_html = ""
    if show_date_label:
        mt = row["match_timestamp"]
        wday = WDAYS_DE[mt.weekday()]
        date_html = (
            f'<div style="color:#999; font-size:0.75rem; margin-bottom:6px;">'
            f"{wday}, {mt.day}.{mt.month}. {row['match_time']}</div>"
        )

    html = f'<div style="background:#242b3d; border:1px solid #2d7a5e; border-radius:10px; padding:12px 15px; margin-bottom:10px; color:#fff; font-family:sans-serif; overflow:hidden;">{date_html}<div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:nowrap;"><div style="flex:1; text-align:left; font-size:clamp(0.7rem,2.5vw,0.85rem); min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{home_img}<b>{row["home_team_name"]}</b></div><div style="flex:0 0 auto; min-width:55px; text-align:center; background:{score_bg}; border-radius:5px; padding:3px 6px; font-weight:bold; color:#fff; font-size:clamp(0.75rem,2.5vw,0.9rem);">{score}</div><div style="flex:1; text-align:right; font-size:clamp(0.7rem,2.5vw,0.85rem); min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"><b>{row["away_team_name"]}</b>{away_img}</div></div></div>'
    target.html(html)


def render_matchday_header(matchday: int, date_label: str):
    """Rendert einen Spieltag-Header mit grüner Akzentlinie."""
    st.markdown(
        f"""<div style="background:#1f2636; border-left:4px solid #2d7a5e;
                padding:10px 15px; margin:10px 0; border-radius:0 8px 8px 0;">
            <b style="font-size:1.05rem;">Spieltag {int(matchday)} von 34</b>
            <span style="color:#999; margin-left:12px; font-size:0.85rem;">{date_label}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def render_kpi_row(leader_df, home_df, attack_df, form_df):
    """Rendert die 4 KPI-Karten in einer Zeile."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if not leader_df.empty:
            st.metric(
                "Tabellenführer",
                leader_df.iloc[0]["team_name"],
                f"{leader_df.iloc[0]['total_points']} Pkt",
            )
    with col2:
        if not home_df.empty:
            st.metric(
                "Heimmacht",
                home_df.iloc[0]["team_name"],
                f"{home_df.iloc[0]['home_points']} Heim-Pkt",
            )
    with col3:
        if not attack_df.empty:
            st.metric(
                "Offensiv-König",
                attack_df.iloc[0]["team_name"],
                f"{attack_df.iloc[0]['goals_per_game']} Tore/Spiel",
            )
    with col4:
        if not form_df.empty:
            wins = form_df.iloc[0]["form_trend"].count("W")
            st.metric(
                "Formstark",
                form_df.iloc[0]["team_name"],
                f"{wins}/5 Siege",
            )

def render_project_info():
    """Zeigt den Sinn & Zweck sowie die Historie an (mit Scroll-Ankern)."""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div id="sinn-zweck"></div>', unsafe_allow_html=True)
        st.markdown("""
        ###  Sinn & Zweck
        **Matchlytics** schließt die Lücke zwischen rohen Sportdaten und Analysen:
        * **Mustererkennung:** Identifikation von Heim- und Auswärtstrends.
        * **Leistungsvergleich:** Objektive Ratings basierend auf Scoring-Effizienz.
        """)
    with col2:
        st.markdown('<div id="historie"></div>', unsafe_allow_html=True)
        st.markdown("""
        ###  Historie
        Lernprojekt von Chatchai Sirichot, entwickelt als **End-to-End Data Pipeline**:
        1. API-Staging → 2. Star-Schema Modellierung → 3. Modulares Frontend.
        """)

def render_db_style_footer():
    """Rendert den professionellen Footer mit Live-DB-Status, Social Links und Kontakt."""
    from src.utils.data_loaders import get_db_status

    db = get_db_status()
    status_color = "#2d7a5e" if db["db_online"] else "#e74c3c"
    status_label = "Online" if db["db_online"] else "Offline"
    last_update = db["last_update"] or "—"

    footer_html = f"""
    <div style="background:#0e1117; margin-top:60px; padding:50px 30px 30px; border-top:3px solid #2d7a5e; font-family:'Segoe UI',sans-serif;">
        <div style="max-width:1100px; margin:0 auto;">
            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:30px; margin-bottom:35px;">
                <div style="flex:1; min-width:200px;">
                    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:#2d7a5e; margin-bottom:12px; font-weight:700;">Dokumentation</div>
                    <p style="color:#8892a4; font-size:0.85rem; line-height:1.8; margin:0;">Star-Schema Modellierung<br>dbt Docs &amp; Lineage<br>API-Staging Pipeline</p>
                </div>
                <div style="flex:1; min-width:200px;">
                    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:#2d7a5e; margin-bottom:12px; font-weight:700;">Tech Stack</div>
                    <p style="color:#8892a4; font-size:0.85rem; line-height:1.8; margin:0;">Python · SQL · Streamlit<br>PostgreSQL · Docker<br>GitHub Actions CI/CD</p>
                </div>
                <div style="flex:1; min-width:200px;">
                    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:#2d7a5e; margin-bottom:12px; font-weight:700;">DB-Status</div>
                    <div style="display:inline-block; border:1px solid {status_color}; padding:6px 14px; color:{status_color}; font-size:0.8rem; border-radius:20px; font-weight:600; margin-bottom:10px;">● {status_label}</div>
                    <p style="color:#8892a4; font-size:0.78rem; line-height:1.8; margin:4px 0 0 0;">
                        Letztes Update: <b style="color:#c5cad3;">{last_update}</b><br>
                        {db["match_count"]} Spiele · {db["team_count"]} Teams · {db["season_count"]} Saisons
                    </p>
                </div>
                <div style="flex:1; min-width:200px;">
                    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:#2d7a5e; margin-bottom:12px; font-weight:700;">Connect</div>
                    <div style="display:flex; gap:14px; flex-wrap:wrap;">
                        <a href="https://www.linkedin.com/in/chatchai-sirichot" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; background:#1a1f2c; border:1px solid #2a3040; border-radius:8px; padding:8px 14px; color:#8892a4; font-size:0.8rem; transition:all 0.2s;">
                            <svg width="16" height="16" fill="#0A66C2" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                            LinkedIn
                        </a>
                        <a href="https://github.com/chatchai-lab" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; background:#1a1f2c; border:1px solid #2a3040; border-radius:8px; padding:8px 14px; color:#8892a4; font-size:0.8rem; transition:all 0.2s;">
                            <svg width="16" height="16" fill="#fff" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                            GitHub
                        </a>
                        <a href="https://www.instagram.com/c.srcht" target="_blank" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; background:#1a1f2c; border:1px solid #2a3040; border-radius:8px; padding:8px 14px; color:#8892a4; font-size:0.8rem; transition:all 0.2s;">
                            <svg width="16" height="16" fill="#E4405F" viewBox="0 0 24 24"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678a6.162 6.162 0 100 12.324 6.162 6.162 0 100-12.324zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405a1.441 1.441 0 11-2.88 0 1.441 1.441 0 012.88 0z"/></svg>
                            Instagram
                        </a>
                    </div>
                </div>
            </div>
            <div style="border-top:1px solid #1a2030; padding-top:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <p style="color:#555; font-size:0.75rem; margin:0;">© 2026 Chatchai Sirichot · Built with ❤️ and Python</p>
                <p style="color:#555; font-size:0.75rem; margin:0;">Matchlytics — Bundesliga Data Pipeline</p>
            </div>
        </div>
    </div>
    """
    st.html(footer_html)