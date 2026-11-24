# AI Jobs Market 2025–2026 — Projet Docker 4A

Application Web d'analyse du marché de l'emploi IA : **Streamlit** + **MySQL**, orchestrés par **Docker Compose**.

> 🚧 En cours de développement — voir [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Documentation

- [Cadrage](docs/CADRAGE.md) — périmètre, choix techniques, organisation
- [Roadmap](docs/ROADMAP.md) — sprints et jalons

## Démarrage rapide

_À compléter (Sprint 2)._

```bash
cp .env.example .env
docker compose up --build
# http://localhost:8501
```

## Assistant IA (gateway LLM)

L'app n'appelle jamais un modèle directement : elle passe par le service `gateway`
(API compatible OpenAI, `POST http://gateway:8000/v1/chat/completions`), avec un **mode** dans `model` :

| Mode | Comportement |
|---|---|
| `auto` (défaut) | Ollama s'il est disponible, sinon OpenRouter |
| `ollama` | Ollama uniquement ; indisponible → 503, aucun traitement |
| `openrouter` | OpenRouter directement (nécessite `OPENROUTER_API_KEY`) |

- `GET /v1/backends` donne l'état des deux backends ; l'en-tête `X-LLM-Backend` indique qui a répondu.
- Seuls `messages`, `stream`, `temperature`, `top_p`, `max_tokens` et `stop` sont relayés ; `max_tokens` est plafonné à `LLM_MAX_TOKENS` (1024 par défaut).
- En local, `COMPOSE_PROFILES=ia` (dans `.env`) démarre un conteneur Ollama avec `qwen2.5:0.5b`.
  **Premier démarrage long** (~9 min mesurées : image Ollama de 5 Go + modèle de 400 Mo), puis tout reste en cache.
  Le modèle est téléchargé depuis le registre d'Ollama (`registry.ollama.ai`) : seul appel réseau sortant du profil.
- Sans IA : `COMPOSE_PROFILES=` dans `.env`. Le dashboard démarre normalement, la gateway répond 503.

## Workflow Git

`feature/<issue>-<slug>` → PR vers `dev` (staging) → PR vers `main` (production). Détails dans le [cadrage §6](docs/CADRAGE.md#6-stratégie-git).
