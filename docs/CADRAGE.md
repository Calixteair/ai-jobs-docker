# Cadrage — Projet Docker 4A : AI Jobs Market 2025–2026

> Document de référence du groupe. Toute décision structurante qui le contredit doit d'abord le modifier (via PR).

| | |
|---|---|
| Promotion | ESIEA 4A — 2026–2027 |
| Groupe | 3 personnes |
| Démarrage | mercredi 7 octobre 2026 |
| **Rendu** | **mercredi 9 décembre 2026** (J+63) |
| Modalité | Rendu ZIP + rapport PDF, aucune soutenance |
| Sujet | `ESIEA_EN_Letter_Template_Learning_Agreement_Non_ERASMUS_30.06.pdf` (Projet Docker 4A) |

---

## 1. Contexte et objectif

Transformer le dataset *AI Jobs Market 2025–2026* (1 500 offres, 25 colonnes) en une **application Web d'analyse** conteneurisée :
Streamlit ↔ MySQL, orchestrés par Docker Compose, avec persistance des données.

Le correcteur doit pouvoir **cloner, suivre le README, `docker compose up --build`, et utiliser le dashboard** sans rien reconfigurer.

## 2. Périmètre

### 2.1 Obligatoire (noté /20)

| Bloc | Pts | Contenu |
|---|---|---|
| Analyse & préparation du dataset | 2 | Qualité, doublons, types, `required_skills`, traçabilité des transformations |
| Architecture & justification MySQL | 2 | Schéma logique, 2 avantages + 1 limite, ≥ 5 requêtes |
| Dockerfile de l'application | 2 | Image Python, couches, `.dockerignore`, port, commande |
| Conteneurisation de la base | 2 | Image officielle versionnée, variables, init/import |
| Docker Compose, réseau, communication | 3 | Services, réseau, DNS par nom de service, healthcheck, `depends_on` |
| Volumes & persistance | 2 | Volume nommé, données survivant à `down`/`up` |
| Application Streamlit | 3 | Accueil, connexion DB, filtres, KPI, gestion d'erreurs |
| Analyses & visualisations | 2 | ≥ 5 graphiques + 2 analyses originales interprétées |
| Tests, README, rapport | 2 | T1–T8 prouvés, README reproductible, rapport 15–20 p. |

### 2.2 Extensions retenues (hors barème, valorisent le rapport)

- **Bonus Kubernetes** (jusqu'à +2 pts) : Minikube ou Kind, namespace, PVC, Services, Job d'import.
- **CI GitHub Actions** : lint, tests unitaires/intégration, tests T1–T7 automatisés.
- **CD vers le VPS** : environnement *staging* (branche `dev`) et *prod* (branche `main`).
- **Gestion agile** : GitHub Projects (backlog, sprints, board).

### 2.3 Hors périmètre

- Écriture de données depuis l'interface (dashboard en lecture seule).
- Authentification utilisateurs dans l'app.
- Haute disponibilité / multi-nœuds (sujet MicroK8s distinct).
- Mise à jour du dataset en continu.

## 3. Contraintes non négociables (sujet §3.1, §13)

- Streamlit et MySQL dans **deux conteneurs distincts**.
- Communication APP ↔ DB via le **réseau Docker, par nom de service** — jamais d'IP.
- Le **CSV n'est pas la source du dashboard** : il sert uniquement à l'import.
- Données **persistantes** (volume nommé).
- Lancement global par **Docker Compose**, sans MySQL installé sur le poste.
- Paramètres externalisés dans `.env` ; **`.env.example` sans aucun secret réel**.
- `compose.yaml` **autonome** : il doit fonctionner chez le correcteur sans VPS, sans GHCR, sans CI.

## 4. Choix techniques

| Domaine | Choix | Justification courte |
|---|---|---|
| Base | **MySQL 8.4 LTS** (image officielle) | Données tabulaires à schéma fixe, agrégations `GROUP BY`, relation N-N pour les compétences |
| App | **Python 3.12 + Streamlit** | Imposé par le sujet |
| Connecteur | **SQLAlchemy + PyMySQL** | Pur Python (pas de lib C à compiler), compatible `st.connection` |
| Visualisation | **Plotly** | Graphiques interactifs, natif dans Streamlit |
| Tests | **pytest**, `streamlit.testing.AppTest`, testcontainers | Voir §8 |
| Qualité | **ruff** (lint + format) | Un seul outil, rapide |
| CI/CD | **GitHub Actions** + **GHCR** | Intégré au repo et au board |
| Orchestration bonus | **Kind** (ou Minikube) | Cluster local léger |

### 4.1 Justification MySQL (réponse à la question obligatoire §6)

**Avantages**
1. Données **tabulaires à schéma stable** : types forts (`DECIMAL`, `TINYINT`, `BOOL`) qui valident les données dès l'import.
2. Dashboard fondé sur des **agrégations et filtres combinés** : `GROUP BY`, `WHERE`, index sur les colonnes filtrées.
3. `required_skills` modélisé proprement en **relation plusieurs-à-plusieurs** (`skills` + `job_skills`) avec clés étrangères → top compétences par simple jointure.

**Limites**
- La liste de compétences doit être **éclatée** à l'import (MongoDB l'aurait stockée telle quelle dans un tableau).
- Pas de fonction `MEDIAN` native : médiane via fonctions de fenêtre ou calcul côté Python.
- Schéma rigide si le dataset évolue (nouvelles colonnes = migration).

### 4.2 Modèle logique (à affiner en Phase 2)

```
jobs (job_id PK, job_title, job_category, experience_level, years_of_experience,
      education_required, annual_salary_usd, salary_min_usd, salary_max_usd,
      city, country, remote_work, company_size, industry, ai_salary_premium_pct,
      demand_score, demand_growth_yoy_pct, benefits_score_10, posting_year,
      posting_month, is_senior, is_remote_friendly, is_llm_role, salary_tier)

skills (skill_id PK, name UNIQUE)

job_skills (job_id FK → jobs, skill_id FK → skills, PK(job_id, skill_id))
```

Index : `country`, `job_category`, `experience_level`, `industry`, `remote_work`.

Point de vigilance déjà identifié : doublons de compétences dans une même offre (ex. `AIJOB0004` : `SQL` ×2) → dédoublonnage à l'import, documenté dans le rapport.

## 5. Architecture

### 5.1 Local / correcteur (obligatoire)

```
Navigateur ──► :8501 ┌──────────────┐  réseau "backend"  ┌──────────────┐
                     │  app         │ ─────────────────► │  db          │
                     │  Streamlit   │   DB_HOST=db       │  MySQL 8.4   │
                     └──────────────┘                    └──────┬───────┘
                                                                │
                                                     volume nommé mysql_data
```

- `db` : healthcheck `mysqladmin ping`, scripts d'init montés sur `/docker-entrypoint-initdb.d` (exécutés **uniquement au premier démarrage**, volume vide).
- `app` : `depends_on: db: condition: service_healthy`, `restart: unless-stopped`.
- MySQL **n'est pas publié** sur l'hôte.

### 5.2 Environnements déployés (VPS `calixteair.fr`)

| Environnement | Branche | Déclencheur | URL (à confirmer) | Accès |
|---|---|---|---|---|
| **local** | toutes | `docker compose up --build` | `localhost:8501` | — |
| **staging** | `dev` | push sur `dev` (automatique) | `ai-jobs-staging.calixteair.fr` | protégé (access list NPM) |
| **prod** | `main` | push sur `main` + **approbation manuelle** | `ai-jobs.calixteair.fr` | public |

Sur le VPS : deux projets Compose isolés (`ai-jobs-staging`, `ai-jobs-prod`), chacun avec **son propre `.env`, son volume et son réseau**. Exposition via Nginx Proxy Manager (**WebSockets activés**, requis par Streamlit).
Fichier dédié `compose.prod.yaml` qui remplace `build:` par `image: ghcr.io/<owner>/ai-jobs-docker:<tag>` — le `compose.yaml` du correcteur reste inchangé.

## 6. Stratégie Git

```
feature/<n°-issue>-<slug> ──PR──► dev ──PR (release)──► main
       │                          │                     │
       CI (lint + tests)          CI + deploy staging    CI + deploy prod (approbation)
```

| Branche | Rôle | Règles de protection |
|---|---|---|
| `main` | Production, toujours déployable | PR obligatoire depuis `dev`, CI verte, 1 review, pas de push direct |
| `dev` | Intégration, déployée en staging | PR obligatoire, CI verte, 1 review |
| `feature/*` | Une issue = une branche | Créée depuis `dev`, supprimée après merge |
| `fix/*` | Correctif | Idem `feature/*` |

Conventions :
- Nom de branche : `feature/12-import-mysql`.
- Commits : **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`).
- PR : description + `Closes #12` → l'issue passe en *Done* automatiquement.
- Merge : *squash* vers `dev`, *merge commit* de `dev` vers `main`.
- Versions : tag `vX.Y.Z` sur `main` à chaque release.

## 7. CI/CD

| Workflow | Déclencheur | Étapes |
|---|---|---|
| `ci.yml` | PR + push sur toutes branches | `ruff check` → `pytest` (unit) → `docker compose build` → `compose up --wait` → tests intégration + smoke T1–T7 → `down -v` |
| `deploy.yml` | push sur `dev` / `main` | build + push image GHCR (`:sha`, `:dev` ou `:prod`) → SSH VPS → `docker compose pull && up -d` → smoke test URL publique |

- **GitHub Environments** `staging` et `production` : secrets séparés (clé SSH de déploiement, hôte), `production` avec *required reviewer*.
- Sur le VPS : utilisateur `deploy` dédié (groupe docker, aucun sudo), clé SSH réservée au déploiement.
- Les secrets MySQL ne transitent **jamais** par la CI : `.env` présent uniquement sur le VPS.
- Toutes les commandes passent par un **`Makefile`** (`make lint`, `make test`, `make smoke`) → portable vers Jenkins si l'école en fournit un (`pytest --junitxml`).

## 8. Stratégie de tests

| Niveau | Outil | Cible |
|---|---|---|
| Unitaire | pytest | `cleaning.py` (nettoyage CSV), construction des requêtes selon filtres |
| Intégration | pytest + MySQL (service Compose ou testcontainers) | Import = 1 500 offres, agrégats corrects vs pandas |
| UI | `streamlit.testing.v1.AppTest` | Rendu sans exception, filtres → KPI, base indisponible gérée |
| Smoke / E2E | script shell | T1–T8 du sujet |
| Couverture | pytest-cov | Objectif indicatif ≥ 70 % sur `cleaning.py` et `queries.py` |

Architecture applicative imposée pour la testabilité :

```
app/
├── app.py        # UI Streamlit uniquement
├── queries.py    # fonctions SQL pures (conn, filtres) → DataFrame
├── db.py         # connexion, gestion d'erreurs
└── tests/
database/
└── scripts_initialisation/   # schéma + import
scripts/
└── cleaning.py   # nettoyage CSV reproductible
```

Correspondance avec le sujet : T1 build · T2/T3 démarrage/état · T4 web · T5 connexion · T6 filtres · T7 persistance · T8 reconstruction from scratch (manuel + CI sur runner vierge).

## 9. Organisation agile

### 9.1 Rôles (proposition, à valider en groupe)

| Rôle | Responsabilités principales | Personne |
|---|---|---|
| **Data & DB** | Analyse/nettoyage, schéma, scripts d'import, `queries.py` | _à attribuer_ |
| **App & Dataviz** | Streamlit, KPI, filtres, graphiques, analyses originales | _à attribuer_ |
| **DevOps & Lead** | Dockerfile, Compose, CI/CD, VPS, Kubernetes, board | _à attribuer_ |

Chacun teste son périmètre et rédige les sections correspondantes du rapport. Toute PR est relue par un autre membre.

### 9.2 Cadence

- **Sprints de 2 semaines** (Sprint 0 d'une semaine), voir `ROADMAP.md`.
- *Sprint planning* : début de sprint, 30 min.
- *Daily* asynchrone : un message court sur le canal du groupe (fait / à faire / bloquant).
- *Review + rétro* : fin de sprint, 30 min, notes dans une issue `Sprint N – rétro`.

### 9.3 GitHub Projects

- Colonnes : `Backlog` → `Ready` → `In progress` → `In review` → `Done`.
- Champs : `Iteration` (sprint), `Estimate` (points 1/2/3/5/8), `Priority` (P0/P1/P2), `Area` (data, app, devops, docs, test).
- Milestones = jalons M1–M5 de la roadmap.
- Labels : `type:feature`, `type:bug`, `type:docs`, `type:test`, `type:ci`, `bonus:k8s`.

### 9.4 Definition of Ready

- User story ou objectif clair, critères d'acceptation listés, estimée, pas de dépendance bloquante.

### 9.5 Definition of Done

- Code mergé dans `dev` via PR relue, CI verte.
- Tests ajoutés ou justifiés.
- README / docs mis à jour si comportement modifié.
- Preuve (capture, log) déposée dans `rapport/preuves/` si elle sert un test T1–T8.

## 10. Livrables

- ZIP complet du projet
- `compose.yaml`, `Dockerfile`, sources Python, `requirements.txt`
- Scripts d'initialisation / import
- `.env.example` sans secret
- `README.md` : prérequis, lancement, arrêt, reconstruction
- **Rapport PDF 15–20 pages** selon la trame du sujet (§15)
- Captures ciblées et commentées
- *(bonus)* `k8s/` + section Kubernetes du rapport

## 11. Risques

| Risque | Proba | Impact | Mitigation |
|---|---|---|---|
| Rapport rédigé trop tard | Haute | Fort | Rédaction au fil de l'eau, sprint 4 dédié, preuves collectées dès S1 |
| Scripts d'init non rejoués (volume existant) | Moyenne | Moyen | Documenté dans README, `make reset` = `down -v` |
| App démarre avant MySQL prêt | Moyenne | Moyen | Healthcheck + `depends_on: service_healthy` + retry dans `db.py` |
| CD/VPS chronophage au détriment du noté | Moyenne | Fort | CD seulement après MVP (M2), timeboxé ; jamais bloquant pour le rendu |
| Secret commité | Faible | Fort | `.gitignore`, `.env.example`, revue PR, scan secrets en CI |
| Charge inégale dans le groupe | Moyenne | Moyen | Board visible, rétro par sprint, rôles explicites |
| Bonus K8s non terminé | Moyenne | Faible | Démarré après feature freeze uniquement s'il reste du temps |

## 12. Décisions ouvertes

- [ ] Attribution des rôles
- [ ] Nom du repo GitHub et propriétaire (compte perso ou organisation)
- [ ] Sous-domaines staging/prod définitifs
- [ ] Kind ou Minikube pour le bonus
- [ ] Jenkins école disponible ? (Docker sur agents, accès sortant, webhook)
