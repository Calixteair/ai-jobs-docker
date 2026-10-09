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
