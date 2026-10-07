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

## Workflow Git

`feature/<issue>-<slug>` → PR vers `dev` (staging) → PR vers `main` (production). Détails dans le [cadrage §6](docs/CADRAGE.md#6-stratégie-git).
