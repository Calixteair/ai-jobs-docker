# Exploration du dataset — AI Jobs Market 2025-2026

> Généré par `scripts/explore_dataset.py` à partir de `data/ai_jobs_market_2025_2026.csv`. Ne pas éditer à la main : relancer le script.
>
> Sens et rôle de chaque variable : [dictionnaire des données](dictionnaire_donnees.md).

## Synthèse

- **1500 lignes × 25 colonnes**
- Valeurs manquantes : **0 anomalie(s)** sur 6 contrôles
- Doublons d'offres : **0 anomalie(s)** sur 7 contrôles
- Plages de valeurs : **0 anomalie(s)** sur 7 contrôles
- Types à convertir au nettoyage : **4 colonne(s)**
- Compétences : **93 distinctes**, format : **0 anomalie(s)** sur 5 contrôles, **119 offres** avec une compétence répétée

## 1. Dimensions et colonnes

| colonne | type lu | valeurs distinctes | exemple |
|---|---|---|---|
| job_id | object | 1500 | AIJOB0001 |
| job_title | object | 25 | AI Agent Developer |
| job_category | object | 12 | AI Engineering |
| experience_level | object | 4 | Senior (6-9 yrs) |
| years_of_experience | int64 | 15 | 7 |
| education_required | object | 5 | Master's |
| annual_salary_usd | float64 | 248 | 239000.0 |
| salary_min_usd | int64 | 17 | 155000 |
| salary_max_usd | int64 | 16 | 290000 |
| city | object | 20 | Boston |
| country | object | 14 | USA |
| remote_work | object | 3 | On-site |
| company_size | object | 5 | Startup (1-50) |
| industry | object | 12 | Finance |
| required_skills | object | 1500 | APIs\|Planning Systems\|Python\|Cloud\|SQL\|Leadership |
| ai_salary_premium_pct | float64 | 151 | 13.1 |
| demand_score | int64 | 20 | 96 |
| demand_growth_yoy_pct | float64 | 565 | 16.9 |
| benefits_score_10 | float64 | 39 | 6.8 |
| posting_year | int64 | 2 | 2026 |
| posting_month | int64 | 12 | 3 |
| is_senior | int64 | 2 | 1 |
| is_remote_friendly | int64 | 2 | 0 |
| is_llm_role | int64 | 2 | 1 |
| salary_tier | object | 5 | Senior ($200-300k) |

## 2. Valeurs manquantes

Le CSV est relu en texte brut, sans conversion, pour repérer aussi les valeurs remplies mais vides de sens.

| Contrôle | Résultat | Statut |
|---|---|---|
| Cellules `NaN` détectées par pandas | 0 | ✅ |
| Cellules vides ou ne contenant que des espaces | 0 | ✅ |
| Valeurs déguisées (`n/a`, `unknown`, `-`, `?`…) | 0 | ✅ |
| Salaires ou scores nuls ou négatifs | 0 | ✅ |
| Offres avec une compétence vide dans la liste | 0 | ✅ |
| Lignes du fichier qui n'ont pas 25 champs | 0 | ✅ |

## 3. Doublons

| Contrôle | Résultat | Statut |
|---|---|---|
| `job_id` en double | 0 | ✅ |
| `job_id` hors du format `AIJOB` + 4 chiffres | 0 | ✅ |
| Lignes identiques sur toutes les colonnes | 0 | ✅ |
| Lignes identiques hors `job_id` (même offre sous deux identifiants) | 0 | ✅ |
| Même poste, ville, entreprise, secteur et compétences | 0 | ✅ |
| Identiques hors `job_id`, compétences et mesures chiffrées | 0 | ✅ |
| Libellés écrits de plusieurs façons (casse, espaces) | 0 | ✅ |

**Faux positif écarté** : 153 offres partagent exactement la même liste de compétences avec au moins une autre offre (72 groupes). Dans 72 groupes sur 72, toutes les offres ont le même métier, et elles diffèrent par la ville, l'entreprise ou le salaire : ce sont des offres distinctes pour un même métier, pas des doublons.

## 4. Types et plages de valeurs

| colonne | type lu | non numériques | min | max | décimales écrites | valeurs entières |
|---|---|---|---|---|---|---|
| annual_salary_usd | float64 | 0 | 90000.0 | 384000.0 | 1 | oui |
| salary_min_usd | int64 | 0 | 90000 | 180000 | 0 | oui |
| salary_max_usd | int64 | 0 | 180000 | 320000 | 0 | oui |
| years_of_experience | int64 | 0 | 1 | 15 | 0 | oui |
| demand_score | int64 | 0 | 68 | 98 | 0 | oui |
| benefits_score_10 | float64 | 0 | 6.0 | 9.8 | 1 | non |
| ai_salary_premium_pct | float64 | 0 | 3.0 | 18.0 | 1 | non |
| demand_growth_yoy_pct | float64 | 0 | 5.0 | 87.8 | 1 | non |
| posting_year | int64 | 0 | 2025 | 2026 | 0 | oui |
| posting_month | int64 | 0 | 1 | 12 | 0 | oui |
| is_senior | int64 | 0 | 0 | 1 | 0 | oui |
| is_remote_friendly | int64 | 0 | 0 | 1 | 0 | oui |
| is_llm_role | int64 | 0 | 0 | 1 | 0 | oui |

`annual_salary_usd` est lu en décimal car 1500 valeurs sur 1500 sont écrites avec `.0` dans le fichier (ex. `239000.0`).

| Contrôle de plage | Statut |
|---|---|
| `posting_month` entre 1 et 12 | ✅ |
| `posting_year` égal à 2025 ou 2026 | ✅ |
| `demand_score` entre 0 et 100 | ✅ |
| `benefits_score_10` entre 0 et 10 | ✅ |
| `years_of_experience` entre 0 et 50 | ✅ |
| `salary_min_usd` ≤ `salary_max_usd` | ✅ |
| `is_senior`, `is_remote_friendly`, `is_llm_role` valent 0 ou 1 | ✅ |

Période couverte : de **2025-01** à **2026-03** (15 mois distincts). En 2026, seuls les mois 1, 2, 3 sont présents.

## 5. Conversions de types à prévoir au nettoyage

| colonne | type actuel | type cible |
|---|---|---|
| annual_salary_usd | décimal | entier |
| is_senior | entier 0/1 | booléen |
| is_remote_friendly | entier 0/1 | booléen |
| is_llm_role | entier 0/1 | booléen |

## 6. Compétences (`required_skills`)

Chaque offre liste ses compétences dans une seule cellule, séparées par `|` (ex. `APIs|Planning Systems|Python|Cloud|SQL|Leadership`). Le `/` n'est pas un séparateur : il fait partie du nom de 2 compétence(s) (`CI/CD`, `Cloud (AWS/GCP/Azure)`).

| Contrôle | Résultat | Statut |
|---|---|---|
| Offres sans séparateur `\|` (une seule compétence) | 0 | ✅ |
| Compétences contenant `,` ou `;` (autre séparateur possible) | 0 | ✅ |
| Compétences avec des espaces au début ou à la fin | 0 | ✅ |
| Compétences vides (`A\|\|B`, `\|` en fin de liste) | 0 | ✅ |
| Compétences écrites de plusieurs façons (casse, espaces) | 0 | ✅ |

### 6.1 Taille des listes

| listes | min | moyenne | max | total |
|---|---|---|---|---|
| telles qu'écrites | 4 | 6.37 | 10 | 9548 |
| après dédoublonnage | 3 | 6.29 | 10 | 9428 |

**93 compétences distinctes.** Après éclatement, la table `skills` comptera 93 lignes et la table de liaison `job_skills` 9428 lignes. Nom le plus long : 23 caractères (`Enterprise Architecture`) ; caractères non ASCII : aucun.

### 6.2 Compétences répétées dans une même offre

- **119 offres** contiennent une compétence écrite plusieurs fois (120 mentions en trop, au plus ×2 ; 1 offre(s) avec plusieurs compétences répétées).
- Seules **7 compétences** sont concernées :

| compétence | offres |
|---|---|
| SQL | 30 |
| Cloud | 27 |
| Leadership | 17 |
| Communication | 13 |
| Research | 13 |
| Agile | 11 |
| Statistics | 9 |

Exemples :

| job_id | required_skills |
|---|---|
| AIJOB0004 | Feature Stores\|Spark\|ETL\|Airflow\|dbt\|SQL\|Python\|Statistics\|SQL\|Communication |
| AIJOB0011 | Cloud\|Python\|Leadership\|Enterprise Architecture\|Cloud |
| AIJOB0023 | SQL\|Communication\|Python\|Data Visualization\|Business Analysis\|Leadership\|Research\|SQL |
| AIJOB0029 | Communication\|Python\|SQL\|Agile\|Git\|SQL |
| AIJOB0030 | Research\|Ethics Frameworks\|Communication\|Research\|Problem Solving\|Cloud |

Effet sur les comptages si l'on ne dédoublonne pas :

| compétence | offres | % des offres | mentions brutes | surcompte |
|---|---|---|---|---|
| SQL | 422 | 28.1 | 452 | 30 |
| Cloud | 402 | 26.8 | 429 | 27 |
| Communication | 365 | 24.3 | 378 | 13 |
| Leadership | 363 | 24.2 | 380 | 17 |
| Research | 363 | 24.2 | 376 | 13 |
| Statistics | 341 | 22.7 | 350 | 9 |
| Agile | 340 | 22.7 | 351 | 11 |

### 6.3 Libellés proches

Paires repérées à la lecture de la liste. Une paire présente dans une même offre y est écrite comme deux compétences distinctes.

| libellé A | libellé B | offres avec A | offres avec B | offres avec les deux |
|---|---|---|---|---|
| Cloud | Cloud (AWS/GCP/Azure) | 402 | 51 | 9 |
| Statistics | Advanced Statistics | 341 | 46 | 12 |
| Fine-tuning | LLM Fine-tuning | 164 | 42 | 0 |
| Prompt Engineering | Prompt Design | 55 | 48 | 0 |
| ML | ML Algorithms | 89 | 43 | 0 |

Décisions de traitement : [décisions de nettoyage](decisions_nettoyage.md).

## Annexe — fréquence des 93 compétences

`offres` : nombre d'offres qui demandent la compétence (après dédoublonnage) ; `mentions brutes` : nombre d'apparitions dans le CSV tel qu'il est écrit.

| compétence | offres | % des offres | mentions brutes |
|---|---|---|---|
| Python | 942 | 62.8 | 942 |
| SQL | 422 | 28.1 | 452 |
| Cloud | 402 | 26.8 | 429 |
| Communication | 365 | 24.3 | 378 |
| Leadership | 363 | 24.2 | 380 |
| Research | 363 | 24.2 | 376 |
| Statistics | 341 | 22.7 | 350 |
| Agile | 340 | 22.7 | 351 |
| Linux | 320 | 21.3 | 320 |
| Problem Solving | 314 | 20.9 | 314 |
| PyTorch | 302 | 20.1 | 302 |
| Git | 295 | 19.7 | 295 |
| Fine-tuning | 164 | 10.9 | 164 |
| LLMs | 125 | 8.3 | 125 |
| Kubernetes | 123 | 8.2 | 123 |
| CUDA | 117 | 7.8 | 117 |
| Documentation | 108 | 7.2 | 108 |
| LLM APIs | 103 | 6.9 | 103 |
| Distributed Systems | 99 | 6.6 | 99 |
| APIs | 98 | 6.5 | 98 |
| System Design | 96 | 6.4 | 96 |
| Vector DBs | 95 | 6.3 | 95 |
| Docker | 93 | 6.2 | 93 |
| Data Visualization | 91 | 6.1 | 91 |
| Deep Learning | 91 | 6.1 | 91 |
| ML | 89 | 5.9 | 89 |
| MLOps | 88 | 5.9 | 88 |
| TensorFlow | 86 | 5.7 | 86 |
| LangChain | 77 | 5.1 | 77 |
| RAG | 63 | 4.2 | 63 |
| Data Analysis | 61 | 4.1 | 61 |
| Stakeholder Mgmt | 61 | 4.1 | 61 |
| GenAI APIs | 58 | 3.9 | 58 |
| Simulation | 58 | 3.9 | 58 |
| Product Strategy | 57 | 3.8 | 57 |
| AI Literacy | 55 | 3.7 | 55 |
| Diffusion Models | 55 | 3.7 | 55 |
| NLP | 55 | 3.7 | 55 |
| Prompt Engineering | 55 | 3.7 | 55 |
| Auditing | 54 | 3.6 | 54 |
| C++ | 54 | 3.6 | 54 |
| Control Systems | 54 | 3.6 | 54 |
| Deployment | 53 | 3.5 | 53 |
| EU AI Act | 53 | 3.5 | 53 |
| Legal Knowledge | 53 | 3.5 | 53 |
| Testing | 53 | 3.5 | 53 |
| Business Analysis | 52 | 3.5 | 52 |
| LLM Integration | 52 | 3.5 | 52 |
| Cloud (AWS/GCP/Azure) | 51 | 3.4 | 51 |
| Computer Vision | 51 | 3.4 | 51 |
| Causal Inference | 50 | 3.3 | 50 |
| Risk Management | 50 | 3.3 | 50 |
| Neural Networks | 49 | 3.3 | 49 |
| Scikit-learn | 49 | 3.3 | 49 |
| Vision-Language Models | 49 | 3.3 | 49 |
| Prompt Design | 48 | 3.2 | 48 |
| AI Policy | 46 | 3.1 | 46 |
| Advanced Statistics | 46 | 3.1 | 46 |
| ROS | 46 | 3.1 | 46 |
| AutoGen | 44 | 2.9 | 44 |
| Ethics Frameworks | 44 | 2.9 | 44 |
| Risk Analysis | 44 | 2.9 | 44 |
| Tool Use | 44 | 2.9 | 44 |
| Transformers | 44 | 2.9 | 44 |
| Cybersecurity | 43 | 2.9 | 43 |
| ML Algorithms | 43 | 2.9 | 43 |
| ML Security | 43 | 2.9 | 43 |
| GPU Computing | 42 | 2.8 | 42 |
| Hugging Face | 42 | 2.8 | 42 |
| LLM Fine-tuning | 42 | 2.8 | 42 |
| Networking | 42 | 2.8 | 42 |
| Planning Systems | 42 | 2.8 | 42 |
| Red Teaming | 42 | 2.8 | 42 |
| Publishing | 41 | 2.7 | 41 |
| Search Systems | 40 | 2.7 | 40 |
| BERT | 39 | 2.6 | 39 |
| Mathematics | 39 | 2.6 | 39 |
| Feature Stores | 38 | 2.5 | 38 |
| Storage | 38 | 2.5 | 38 |
| CNNs | 37 | 2.5 | 37 |
| Image Processing | 37 | 2.5 | 37 |
| Text Processing | 37 | 2.5 | 37 |
| Airflow | 36 | 2.4 | 36 |
| Embeddings | 36 | 2.4 | 36 |
| MLflow | 36 | 2.4 | 36 |
| Monitoring | 36 | 2.4 | 36 |
| dbt | 36 | 2.4 | 36 |
| CI/CD | 35 | 2.3 | 35 |
| OpenCV | 34 | 2.3 | 34 |
| Risk Assessment | 34 | 2.3 | 34 |
| ETL | 33 | 2.2 | 33 |
| Enterprise Architecture | 31 | 2.1 | 31 |
| Spark | 31 | 2.1 | 31 |
