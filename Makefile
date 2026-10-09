# Commandes communes du projet — utilisées en local et par la CI.
# `make help` pour la liste.

VENV   ?= .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

COMPOSE      := docker compose
COMPOSE_TEST := $(COMPOSE) -f compose.yaml -f compose.test.yaml

.DEFAULT_GOAL := help
.PHONY: help venv lint format test env db-up db-down db-reset db-shell db-logs test-persistence run-app test-int

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(VENV)/.installed: requirements-dev.txt app/requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements-dev.txt
	touch $@

venv: $(VENV)/.installed ## Crée l'environnement virtuel de dev

lint: venv ## Vérifie le style (ruff)
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

format: venv ## Formate le code (ruff)
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

test: venv ## Lance les tests unitaires
	$(VENV)/bin/pytest tests/unit --junitxml=report.xml

test-int: venv db-up ## Lance les tests d'intégration contre MySQL (démarre la base)
	$(VENV)/bin/pytest tests/integration -m integration --junitxml=report-integration.xml

# --------------------------------------------------------------------------- #
# Base de données
# --------------------------------------------------------------------------- #

.env:
	cp .env.example .env
	@echo ".env créé depuis .env.example (valeurs factices)"

env: .env ## Crée .env depuis .env.example s'il n'existe pas

db-up: .env ## Construit et démarre MySQL (port 127.0.0.1:3307 pour les tests)
	$(COMPOSE_TEST) up -d --build --wait db

db-down: ## Arrête la base (les données sont conservées)
	$(COMPOSE_TEST) down

db-reset: ## Supprime la base ET son volume (réimport complet au prochain db-up)
	$(COMPOSE_TEST) down -v

db-shell: .env ## Ouvre un client MySQL dans le conteneur
	$(COMPOSE) exec db sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'

db-logs: ## Affiche les logs de la base
	$(COMPOSE) logs -f db

test-persistence: .env ## Test T7 : les données survivent à down/up
	./scripts/test_persistance.sh

# --------------------------------------------------------------------------- #
# Application
# --------------------------------------------------------------------------- #

run-app: .env venv ## Lance Streamlit en local (hors Docker) sur la base de make db-up
	set -a && . ./.env && set +a && \
	DB_HOST=127.0.0.1 DB_PORT=$${DB_TEST_PORT:-3307} $(VENV)/bin/streamlit run app/app.py
