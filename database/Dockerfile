# Image de la base : MySQL officiel + données nettoyées + scripts d'initialisation.
# Construite depuis la racine du dépôt :  docker build -f database/Dockerfile .

# --- Étape 1 : nettoyage du CSV brut avec le script Python du projet ---------
FROM python:3.12-slim AS prepare

WORKDIR /build
RUN pip install --no-cache-dir pandas==2.2.3

COPY scripts/cleaning.py scripts/
COPY data/ai_jobs_market_2025_2026.csv data/
RUN python scripts/cleaning.py data/ai_jobs_market_2025_2026.csv processed

# --- Étape 2 : image MySQL finale ---------------------------------------------
# 8.4 = version LTS (support long terme), épinglée pour un build reproductible.
FROM mysql:8.4

# Seul dossier lisible par LOAD DATA INFILE (option secure_file_priv)
COPY --from=prepare /build/processed/*.csv /var/lib/mysql-files/

# Exécutés par ordre alphabétique au premier démarrage, si le volume est vide
COPY database/scripts_initialisation/ /docker-entrypoint-initdb.d/
