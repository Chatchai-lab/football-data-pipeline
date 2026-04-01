# ─── Matchlytics Dockerfile ───
# Basis: schlankes Python 3.12 Image
FROM python:3.12-slim

# System-Abhängigkeiten für psycopg2-binary
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis setzen
WORKDIR /app

# Requirements zuerst kopieren (Docker Layer-Cache nutzen)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Gesamten Projektcode kopieren
COPY . .

# PYTHONPATH setzen, damit src/ Imports funktionieren
ENV PYTHONPATH=/app

# Streamlit-Konfiguration: Telemetrie aus, Server-Einstellungen
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501

# Port freigeben
EXPOSE 8501

# Health Check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Streamlit starten
CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
