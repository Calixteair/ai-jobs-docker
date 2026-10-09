# Profil du dataset — AI Jobs Market 2025-2026

> Généré par `scripts/explore.py` à partir de `data/ai_jobs_market_2025_2026.csv`. Ne pas éditer à la main.

## 1. Dimensions et colonnes

- **1500 lignes**, **25 colonnes**
- Valeurs manquantes au total : **0**

| colonne | type pandas | valeurs distinctes | manquants | exemple |
|---|---|---|---|---|
| job_id | object | 1500 | 0 | AIJOB0001 |
| job_title | object | 25 | 0 | AI Agent Developer |
| job_category | object | 12 | 0 | AI Engineering |
| experience_level | object | 4 | 0 | Senior (6-9 yrs) |
| years_of_experience | int64 | 15 | 0 | 7 |
| education_required | object | 5 | 0 | Master's |
| annual_salary_usd | float64 | 248 | 0 | 239000.0 |
| salary_min_usd | int64 | 17 | 0 | 155000 |
| salary_max_usd | int64 | 16 | 0 | 290000 |
| city | object | 20 | 0 | Boston |
| country | object | 14 | 0 | USA |
| remote_work | object | 3 | 0 | On-site |
| company_size | object | 5 | 0 | Startup (1-50) |
| industry | object | 12 | 0 | Finance |
| required_skills | object | 1500 | 0 | APIs\|Planning Systems\|Python\|Cloud\|SQL\|Leadership |
| ai_salary_premium_pct | float64 | 151 | 0 | 13.1 |
| demand_score | int64 | 20 | 0 | 96 |
| demand_growth_yoy_pct | float64 | 565 | 0 | 16.9 |
| benefits_score_10 | float64 | 39 | 0 | 6.8 |
| posting_year | int64 | 2 | 0 | 2026 |
| posting_month | int64 | 12 | 0 | 3 |
| is_senior | int64 | 2 | 0 | 1 |
| is_remote_friendly | int64 | 2 | 0 | 0 |
| is_llm_role | int64 | 2 | 0 | 1 |
| salary_tier | object | 5 | 0 | Senior ($200-300k) |

## 2. Doublons et identifiants

- Doublons de `job_id` : **0**
- Lignes identiques hors `job_id` : **0**
- Format `AIJOB` + 4 chiffres respecté partout : **oui**

## 3. Variables numériques

| colonne | min | moyenne | médiane | max |
|---|---|---|---|---|
| years_of_experience | 1.0 | 6.22 | 6.0 | 15.0 |
| annual_salary_usd | 90000.0 | 194892.0 | 180000.0 | 384000.0 |
| salary_min_usd | 90000.0 | 135448.67 | 140000.0 | 180000.0 |
| salary_max_usd | 180000.0 | 257537.33 | 270000.0 | 320000.0 |
| ai_salary_premium_pct | 3.0 | 10.86 | 10.5 | 18.0 |
| demand_score | 68.0 | 87.52 | 89.0 | 98.0 |
| demand_growth_yoy_pct | 5.0 | 31.12 | 23.4 | 87.8 |
| benefits_score_10 | 6.0 | 7.9 | 7.9 | 9.8 |
| posting_year | 2025.0 | 2025.58 | 2026.0 | 2026.0 |
| posting_month | 1.0 | 3.97 | 3.0 | 12.0 |
| is_senior | 0.0 | 0.5 | 0.0 | 1.0 |
| is_remote_friendly | 0.0 | 0.75 | 1.0 | 1.0 |
| is_llm_role | 0.0 | 0.22 | 0.0 | 1.0 |

## 4. Variables catégorielles

### `job_category` (12 valeurs)

| job_category | offres |
|---|---|
| AI Engineering | 736 |
| Data Science | 127 |
| Governance | 122 |
| Robotics | 74 |
| Product | 70 |
| Business | 62 |
| Infrastructure | 55 |
| Architecture | 52 |
| ML Operations | 51 |
| Data Engineering | 51 |
| Security | 50 |
| Research | 50 |

### `experience_level` (4 valeurs)

| experience_level | offres |
|---|---|
| Entry (0-2 yrs) | 385 |
| Lead (10+ yrs) | 381 |
| Mid (3-5 yrs) | 370 |
| Senior (6-9 yrs) | 364 |

### `education_required` (5 valeurs)

| education_required | offres |
|---|---|
| Master's | 316 |
| Bachelor's | 311 |
| Bootcamp/Self-taught | 297 |
| Associate's | 296 |
| PhD | 280 |

### `remote_work` (3 valeurs)

| remote_work | offres |
|---|---|
| Hybrid | 686 |
| Fully Remote | 445 |
| On-site | 369 |

### `company_size` (5 valeurs)

| company_size | offres |
|---|---|
| Mid-size (501-5000) | 312 |
| SME (51-500) | 300 |
| Big Tech (FAANG+) | 299 |
| Enterprise (5000+) | 297 |
| Startup (1-50) | 292 |

### `industry` (12 valeurs)

| industry | offres |
|---|---|
| Automotive | 138 |
| Healthcare | 138 |
| Government | 136 |
| Finance | 131 |
| Retail | 131 |
| Energy | 130 |
| Consulting | 126 |
| Media | 120 |
| Education | 120 |
| Manufacturing | 114 |
| Research | 110 |
| Technology | 106 |

### `salary_tier` (5 valeurs)

| salary_tier | offres |
|---|---|
| Senior ($200-300k) | 467 |
| Upper-Mid ($150-200k) | 430 |
| Mid ($100-150k) | 396 |
| Elite (>$300k) | 140 |
| Entry (<$100k) | 67 |

### `country` (14 valeurs)

| country | offres |
|---|---|
| USA | 515 |
| UK | 90 |
| China | 87 |
| Canada | 85 |
| Global | 82 |
| Germany | 81 |
| Australia | 78 |
| Switzerland | 76 |
| Japan | 76 |
| Netherlands | 74 |
| Singapore | 71 |
| France | 66 |
| UAE | 62 |
| India | 57 |

## 5. Compétences (`required_skills`)

- Format : liste de compétences séparées par `|`
- Compétences par offre : min 4, moyenne 6.4, max 10
- Compétences distinctes : **93**
- Espaces parasites : **0**
- Variantes de casse (ex. `sql` / `SQL`) : **0**
- Offres contenant une compétence en double : **119**

Exemples de doublons :

| job_id | required_skills |
|---|---|
| AIJOB0004 | Feature Stores\|Spark\|ETL\|Airflow\|dbt\|SQL\|Python\|Statistics\|SQL\|Communication |
| AIJOB0011 | Cloud\|Python\|Leadership\|Enterprise Architecture\|Cloud |
| AIJOB0023 | SQL\|Communication\|Python\|Data Visualization\|Business Analysis\|Leadership\|Research\|SQL |
| AIJOB0029 | Communication\|Python\|SQL\|Agile\|Git\|SQL |
| AIJOB0030 | Research\|Ethics Frameworks\|Communication\|Research\|Problem Solving\|Cloud |

Top 15 :

| compétence | offres |
|---|---|
| Python | 942 |
| SQL | 452 |
| Cloud | 429 |
| Leadership | 380 |
| Communication | 378 |
| Research | 376 |
| Agile | 351 |
| Statistics | 350 |
| Linux | 320 |
| Problem Solving | 314 |
| PyTorch | 302 |
| Git | 295 |
| Fine-tuning | 164 |
| LLMs | 125 |
| Kubernetes | 123 |

## 6. Contrôles de cohérence

### 6.1 Salaire annuel vs fourchette min/max

- Offres dont `annual_salary_usd` sort de `[salary_min_usd, salary_max_usd]` : **288** (19.2%)
- `salary_min_usd > salary_max_usd` : **0**
- Fourchette identique pour toutes les offres d'un même `job_title` : **oui** (25 titres)
- Dont au-dessus du maximum : **288**, en dessous du minimum : **0**

| experience_level | offres hors fourchette |
|---|---|
| Lead (10+ yrs) | 167 |
| Senior (6-9 yrs) | 94 |
| Mid (3-5 yrs) | 24 |
| Entry (0-2 yrs) | 3 |

### 6.2 Niveau d'expérience vs années d'expérience

| experience_level | 0-2 | 3-5 | 6-9 | 10+ |
|---|---|---|---|---|
| Entry (0-2 yrs) | 40 | 129 | 166 | 50 |
| Lead (10+ yrs) | 28 | 132 | 176 | 45 |
| Mid (3-5 yrs) | 18 | 135 | 176 | 41 |
| Senior (6-9 yrs) | 25 | 114 | 181 | 44 |

Offres où les années correspondent au libellé du niveau : **401** (26.7%).

### 6.3 Colonnes dérivées

- `is_senior` = niveau Senior ou Lead : **cohérent**
- `is_remote_friendly` = Hybrid ou Fully Remote : **cohérent**
- Bornes réelles de `annual_salary_usd` par `salary_tier` :

| salary_tier | min | max |
|---|---|---|
| Elite (>$300k) | 301000.0 | 384000.0 |
| Entry (<$100k) | 90000.0 | 100000.0 |
| Mid ($100-150k) | 101000.0 | 150000.0 |
| Senior ($200-300k) | 201000.0 | 300000.0 |
| Upper-Mid ($150-200k) | 151000.0 | 200000.0 |

### 6.4 Répartition temporelle

Part des offres publiées en 2026 : **58.4 %** (3 mois sur 15 couverts).

| période | offres |
|---|---|
| 2025-01 | 41 |
| 2025-02 | 55 |
| 2025-03 | 52 |
| 2025-04 | 41 |
| 2025-05 | 64 |
| 2025-06 | 57 |
| 2025-07 | 57 |
| 2025-08 | 39 |
| 2025-09 | 47 |
| 2025-10 | 44 |
| 2025-11 | 59 |
| 2025-12 | 68 |
| 2026-01 | 271 |
| 2026-02 | 306 |
| 2026-03 | 299 |
