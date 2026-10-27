# Image de l'application Streamlit.
# Construite depuis la racine du dépôt :  docker build -t ai-jobs-app .

# python:3.12-slim : Python officiel sur Debian minimale. Plus léger que l'image
# complète (pas de compilateurs ni de docs), et compatible avec les roues
# précompilées de pandas / cryptography, contrairement à Alpine (musl).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Dépendances d'abord : cette couche reste en cache tant que requirements.txt
# ne change pas, même si le code est modifié.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Utilisateur sans privilèges : un processus compromis ne serait pas root.
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app app/ .
USER app

EXPOSE 8501

# Point de santé natif de Streamlit (aucun outil à installer : Python suffit).
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"]

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
