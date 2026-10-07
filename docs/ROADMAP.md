# Roadmap — Projet Docker 4A

**Du mercredi 7 octobre au mercredi 9 décembre 2026** — 9 semaines, 1 Sprint 0 + 4 sprints de 2 semaines.

```
Oct 7        Oct 14            Oct 28            Nov 11            Nov 25            Dec 9
  │ Sprint 0  │    Sprint 1      │    Sprint 2      │    Sprint 3      │    Sprint 4      │
  │ Cadrage   │ Données & base   │ App & Compose    │ Qualité & bonus  │ Rapport & rendu  │
  ▼           ▼                  ▼                  ▼                  ▼                  ▼
             M0                 M1                 M2                 M3                 M4/M5
```

## Jalons

| Jalon | Date | Critère de validation |
|---|---|---|
| **M0** Projet outillé | mar. 13/10 | Repo, branches protégées, board, CI qui tourne (même vide) |
| **M1** Base opérationnelle | mar. 27/10 | `docker compose up db` → 1 500 offres en base, persistance vérifiée |
| **M2** MVP complet | mar. 10/11 | App + DB via Compose, KPI + filtres + 5 graphiques, staging déployé |
| **M3** Feature freeze | mar. 24/11 | Tout le noté terminé, T1–T8 verts, prod déployée, bonus K8s en cours/fini |
| **M4** Rapport finalisé | lun. 07/12 | Rapport relu, README testé par un membre sur machine propre |
| **M5** Rendu | **mer. 09/12** | ZIP déposé |

---

## Sprint 0 — Cadrage & outillage (07/10 → 13/10)

Objectif : tout le monde peut cloner, lancer et contribuer.

| Tâche | Area | Rôle |
|---|---|---|
| Valider le cadrage et attribuer les rôles | docs | tous |
| Créer le repo GitHub, branches `main`/`dev`, protections | devops | DevOps |
| Créer le GitHub Project (champs, vues, itérations) + backlog initial | devops | DevOps |
| Arborescence du sujet, `.gitignore`, `.env.example`, `README` squelette | devops | DevOps |
| Templates issue / PR, `CONTRIBUTING.md` (conventions §6 du cadrage) | docs | DevOps |
| `Makefile` + `ci.yml` minimal (ruff + pytest vide) | ci | DevOps |
| Chacun : clone, `feature/*` de test, PR vers `dev` | — | tous |

## Sprint 1 — Données & base (14/10 → 27/10)

Objectif : un MySQL conteneurisé contenant des données propres.

| Tâche | Sujet | Area | Rôle |
|---|---|---|---|
| Exploration du dataset : dimensions, types, manquants, doublons `job_id` | Phase 1 | data | Data |
| Analyse de `required_skills` (format, doublons intra-ligne, normalisation) | Phase 1 | data | Data |
| `scripts/cleaning.py` reproductible + tests unitaires | Phase 1 | data / test | Data |
| Schéma logique + justification MySQL (2 avantages, 1 limite) | Phase 2 | data / docs | Data |
| Script SQL de création (tables, PK/FK, index) | Phase 2 | data | Data |
| Script d'import (CSV nettoyé → `jobs`, `skills`, `job_skills`) | Phase 2/4 | data | Data |
| Liste des ≥ 5 requêtes du dashboard, en SQL brut | Phase 2 | data | Data + App |
| Service `db` dans Compose : image versionnée, env, volume, healthcheck, init | Phase 4 | devops | DevOps |
| Test T7 manuel : `down` / `up` → données présentes | Phase 8 | test | DevOps |
| Maquette papier/Figma du dashboard (pages, KPI, filtres, 5+ graphiques) | Phase 7 | app | App |
| Squelette Streamlit (`app.py`, `db.py`) connecté à la base locale | Phase 3 | app | App |
| CI : job d'intégration MySQL (service container) | — | ci | DevOps |
| **Rapport** : sections 2 (Dataset) et 5 (Préparation) en brouillon | — | docs | Data |

## Sprint 2 — Application & Compose (28/10 → 10/11)

Objectif : MVP fonctionnel de bout en bout, déployé en staging.

| Tâche | Sujet | Area | Rôle |
|---|---|---|---|
| `queries.py` : KPI (nb offres, salaire moyen/médian, demand score) + tests | Phase 7 | data / test | Data |
| `queries.py` : requêtes des graphiques + tests d'intégration | Phase 7 | data / test | Data |
| Page d'accueil (projet, dataset) | Phase 3 | app | App |
| Filtres : pays, expérience, secteur, mode de travail, métier/catégorie | Phase 7 | app | App |
| 5 visualisations (métiers, pays, télétravail, compétences, expérience…) | Phase 7 | app | App |
| Gestion d'erreurs : base indisponible, aucun résultat | Phase 3 | app | App |
| `Dockerfile` app + `.dockerignore` | Phase 5 | devops | DevOps |
| `compose.yaml` complet : réseau, `depends_on`, restart, variables | Phase 6 | devops | DevOps |
| CI : build images + `compose up --wait` + smoke T1–T5 | Phase 8 | ci | DevOps |
| VPS : utilisateur `deploy`, projet staging, `.env`, NPM (WebSockets + access list) | — | devops | DevOps |
| `deploy.yml` : GHCR + déploiement staging sur push `dev` | — | ci | DevOps |
| **Rapport** : sections 3 (Architecture), 4 (Choix base), 7 (Dockerfile) | — | docs | Data + DevOps |

## Sprint 3 — Qualité, analyses & bonus (11/11 → 24/11)

Objectif : tout le noté est terminé et prouvé ; prod en ligne ; bonus K8s.

| Tâche | Sujet | Area | Rôle |
|---|---|---|---|
| 2 analyses originales (question → indicateur → résultat → interprétation) | Phase 7 | app / data | App + Data |
| Zone d'analyse / interprétation dans le dashboard | Phase 3 | app | App |
| Tests UI `AppTest` (rendu, filtres → KPI, erreur DB) | Phase 8 | test | App |
| CI : T6 (filtres), T7 (persistance), T8 (rebuild from scratch) | Phase 8 | ci | DevOps |
| Environnement prod : approbation manuelle, tag `vX.Y.Z`, smoke URL publique | — | ci | DevOps |
| Release `v1.0.0` : merge `dev` → `main` | — | devops | tous |
| **Bonus K8s** : cluster Kind, namespace, MySQL + PVC + Service, app Deployment + Service | Bonus | devops | DevOps |
| **Bonus K8s** : Job d'import, tests résilience (delete pod) et persistance | Bonus | devops | DevOps |
| **Rapport** : sections 6 (App), 8 (Compose), 9 (Dashboard) | — | docs | App + DevOps |
| Collecte des preuves T1–T8 dans `rapport/preuves/` | Phase 8 | test | tous |

## Sprint 4 — Rapport & rendu (25/11 → 09/12)

Objectif : livrable propre, reproductible, sans surprise. **Pas de nouvelle fonctionnalité.**

| Tâche | Area | Rôle |
|---|---|---|
| README final : prérequis, lancement, arrêt, reconstruction, dépannage | docs | DevOps |
| Test à blanc : un membre clone sur machine propre et suit **uniquement** le README | test | App |
| **Rapport** : intro, 10 (Tests), 11 (Difficultés), 12 (Conclusion), annexes | docs | tous |
| **Rapport** : section bonus Kubernetes (schéma + captures) | docs | DevOps |
| Relecture croisée du rapport (cohérence, figures nommées, 15–20 pages) | docs | tous |
| Vérification checklist finale du sujet (§16) | — | tous |
| Audit secrets (repo, historique, rapport, `.env.example`) | devops | DevOps |
| Génération du ZIP + dépôt | — | Lead |
| *Buffer* : corrections de dernière minute | — | tous |

---

## Règles de pilotage

- Le **noté passe avant le bonus** : CD prod et K8s ne démarrent pas tant que M2 n'est pas atteint.
- Un jalon manqué → la rétro décide quoi couper (ordre de sacrifice : K8s → CD prod → CD staging → tests UI).
- Le rapport s'écrit **pendant** les sprints, pas à la fin : chaque sprint a ses sections.
