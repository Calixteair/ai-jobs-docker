# Commandes communes du projet — utilisées en local et par la CI.
# `make help` pour la liste.

VENV   ?= .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help venv hooks lint format test

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(VENV)/.installed: requirements-dev.txt
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements-dev.txt
	touch $@

venv: $(VENV)/.installed ## Crée l'environnement virtuel de dev

hooks: venv ## Installe les hooks pre-commit (ruff, fichiers, clés privées)
	$(VENV)/bin/pre-commit install

lint: venv ## Vérifie le style (ruff)
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

format: venv ## Formate le code (ruff)
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

test: venv ## Lance les tests unitaires
	$(VENV)/bin/pytest tests/unit --junitxml=report.xml
