# Dictionnaire des données — AI Jobs Market 2025-2026

Source : `data/ai_jobs_market_2025_2026.csv` — **1 500 lignes × 25 colonnes**, une ligne = une offre d'emploi.

Les chiffres détaillés (types, manquants, doublons, plages) sont produits par `scripts/explore_dataset.py`. Ce document décrit le **sens** et le **rôle** de chaque variable dans le projet.

## Rôles

| Rôle | Signification | Colonnes |
|---|---|---|
| Identifiant | Identifie une offre de façon unique | 1 |
| Dimension | Axe d'analyse : sert à filtrer et à regrouper (`GROUP BY`) | 9 |
| Mesure | Valeur numérique que l'on agrège (moyenne, médiane…) | 8 |
| Temps | Période de publication | 2 |
| Liste | Plusieurs valeurs dans une même cellule | 1 |
| Dérivée | Se déduit d'autres colonnes du dataset | 4 |

## Variables

| # | Variable | Rôle | Type | Description | Valeurs / plage | Usage prévu |
|---|---|---|---|---|---|---|
| 1 | `job_id` | Identifiant | texte | Identifiant de l'offre | `AIJOB0001` … `AIJOB1500` | Clé primaire, KPI « nombre d'offres » |
| 2 | `job_title` | Dimension | texte | Intitulé du poste | 25 métiers (ex. `LLM Engineer`, `Data Scientist`) | Filtre « métier », graphiques par métier |
| 3 | `job_category` | Dimension | texte | Famille de métiers | 12 familles (ex. `AI Engineering`, `Research`) | Filtre « catégorie de métier » |
| 4 | `experience_level` | Dimension (ordonnée) | texte | Niveau d'expérience demandé | `Entry (0-2 yrs)`, `Mid (3-5 yrs)`, `Senior (6-9 yrs)`, `Lead (10+ yrs)` | Filtre obligatoire, salaire par niveau |
| 5 | `years_of_experience` | Mesure | entier | Années d'expérience demandées | 1 à 15 | Descriptif |
| 6 | `education_required` | Dimension (ordonnée) | texte | Diplôme demandé | `Bootcamp/Self-taught`, `Associate's`, `Bachelor's`, `Master's`, `PhD` | Analyse complémentaire |
| 7 | `annual_salary_usd` | Mesure | décimal | Salaire annuel proposé, en dollars US | 90 000 à 384 000 | **KPI salaire moyen et médian**, la plupart des graphiques |
| 8 | `salary_min_usd` | Mesure | entier | Borne basse de la fourchette salariale | 90 000 à 180 000 | Contrôle de cohérence (#11) |
| 9 | `salary_max_usd` | Mesure | entier | Borne haute de la fourchette salariale | 180 000 à 320 000 | Contrôle de cohérence (#11) |
| 10 | `city` | Dimension | texte | Ville du poste | 20 villes, dont `Remote` | Descriptif |
| 11 | `country` | Dimension | texte | Pays du poste | 14 valeurs, dont `Global` (offres sans pays) | Filtre obligatoire, salaire par pays |
| 12 | `remote_work` | Dimension | texte | Mode de travail | `On-site`, `Hybrid`, `Fully Remote` | Filtre obligatoire, répartition du télétravail |
| 13 | `company_size` | Dimension (ordonnée) | texte | Taille de l'entreprise | `Startup (1-50)` … `Enterprise (5000+)`, `Big Tech (FAANG+)` | Analyse complémentaire |
| 14 | `industry` | Dimension | texte | Secteur d'activité de l'entreprise | 12 secteurs (ex. `Finance`, `Healthcare`) | Filtre obligatoire « secteur » |
| 15 | `required_skills` | Liste | texte | Compétences demandées, séparées par `\|` | ex. `Python\|SQL\|Cloud` | Top compétences (analysé dans #10) |
| 16 | `ai_salary_premium_pct` | Mesure | décimal | Prime salariale liée à l'IA, en % | 3,0 à 18,0 | Comparaison rôles LLM / autres |
| 17 | `demand_score` | Mesure | entier | Score de demande pour le poste | 68 à 98 | **KPI score moyen de demande** |
| 18 | `demand_growth_yoy_pct` | Mesure | décimal | Croissance de la demande sur un an, en % | 5,0 à 87,8 | Métiers en croissance |
| 19 | `benefits_score_10` | Mesure | décimal | Note des avantages sociaux, sur 10 | 6,0 à 9,8 | Analyse complémentaire |
| 20 | `posting_year` | Temps | entier | Année de publication | 2025, 2026 | Évolution dans le temps |
| 21 | `posting_month` | Temps | entier | Mois de publication | 1 à 12 | Évolution dans le temps |
| 22 | `is_senior` | Dérivée | 0/1 | 1 si le poste est de niveau Senior ou Lead | 0, 1 | À vérifier vs `experience_level` (#11) |
| 23 | `is_remote_friendly` | Dérivée | 0/1 | 1 si le poste est Hybrid ou Fully Remote | 0, 1 | À vérifier vs `remote_work` (#11) |
| 24 | `is_llm_role` | Dérivée | 0/1 | 1 si le métier est lié aux LLM / à l'IA générative | 0, 1 | Comparaison rôles LLM / autres |
| 25 | `salary_tier` | Dérivée | texte | Tranche de salaire | `Entry (<$100k)`, `Mid ($100-150k)`, `Upper-Mid ($150-200k)`, `Senior ($200-300k)`, `Elite (>$300k)` | À vérifier vs `annual_salary_usd` (#11) |

## Observations

- **`job_title` détermine `job_category` et `is_llm_role`** : chaque métier appartient à une seule famille, et `is_llm_role` vaut 1 exactement pour 5 métiers (`AI Agent Developer`, `Generative AI Engineer`, `LLM Engineer`, `Prompt Engineer`, `RAG Engineer`). Les filtres « catégorie » et « métier » sont donc hiérarchiques.
- **`country = Global` et `city = Remote`** ne sont pas de vrais lieux : à traiter comme une catégorie à part dans les graphiques par pays (#11).
- **`annual_salary_usd` est lu en décimal** alors que les autres salaires sont entiers : contrôlé à l'étape « types ».
