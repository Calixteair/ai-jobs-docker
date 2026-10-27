# Journal de nettoyage

> Généré par `scripts/cleaning.py` à partir de `data/ai_jobs_market_2025_2026.csv`. Ne pas éditer à la main.
>
> Décisions appliquées : [décisions de nettoyage](decisions_nettoyage.md).

## Transformations

| # | Étape | Décision | Lignes concernées | Avant | Après |
|---|---|---|---|---|---|
| 1 | Contrôles d'intégrité | C4, K4 | 1500 | — | manquants, doublons de job_id, domaines, colonnes dérivées, variantes : OK |
| 2 | Espaces en début et fin de texte retirés | C4 | 0 | — | — |
| 3 | Salaire annuel converti en entier | exploration §5 | 1500 | `239000.0` (décimal) | `239000` (entier) |
| 4 | Indicateurs convertis en booléens | exploration §5 | 1500 | `0` / `1` (entier) | `False` / `True` (is_senior, is_remote_friendly, is_llm_role) |
| 5 | Compétences découpées et dédoublonnées | C1, C2 | 119 | `AIJOB0004` : `Feature Stores\|Spark\|ETL\|Airflow\|dbt\|SQL\|Python\|Statistics\|SQL\|Communication` | `Feature Stores, Spark, ETL, Airflow, dbt, SQL, Python, Statistics, Communication` |
| 6 | Ajout de `experience_rank` | tri Entry → Lead | 1500 | — | Entry = 1, Mid = 2, Senior = 3, Lead = 4 |
| 7 | Ajout de `posting_period` | K5 | 1500 | `posting_year` = 2026, `posting_month` = 3 | `2026-03` |
| 8 | Ajout de `salary_above_range` (salaires conservés) | K1 | 288 | — | `True` si `annual_salary_usd` > `salary_max_usd` |
| 9 | Éclatement en tables `jobs`, `skills`, `job_skills` | C7 | 9428 | 1 colonne `required_skills` par offre | 93 compétences, 9428 couples |

## Fichiers produits (`data/processed/`)

| Fichier | Lignes | Colonnes |
|---|---|---|
| `jobs.csv` | 1500 | `job_id`, `job_title`, `job_category`, `experience_level`, `years_of_experience`, `education_required`, `annual_salary_usd`, `salary_min_usd`, `salary_max_usd`, `city`, `country`, `remote_work`, `company_size`, `industry`, `ai_salary_premium_pct`, `demand_score`, `demand_growth_yoy_pct`, `benefits_score_10`, `posting_year`, `posting_month`, `is_senior`, `is_remote_friendly`, `is_llm_role`, `salary_tier`, `experience_rank`, `posting_period`, `salary_above_range` |
| `skills.csv` | 93 | `skill_id`, `name` |
| `job_skills.csv` | 9428 | `job_id`, `skill_id` |
