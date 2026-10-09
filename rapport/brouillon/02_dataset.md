# 2. Dataset

> Brouillon — section 2 de la trame du sujet (§15). Chiffres issus de `docs/data/profil_dataset.md`, régénérable avec `python scripts/explore.py`.

## 2.1 Source et dimensions

Le jeu de données fourni, *AI Jobs Market 2025–2026*, est un fichier CSV de **1 500 lignes et 25 colonnes**. Chaque ligne décrit une offre d'emploi liée à l'intelligence artificielle, identifiée par un `job_id` au format `AIJOB0001` à `AIJOB1500`. Les offres couvrent la période de janvier 2025 à mars 2026.

## 2.2 Variables

Les 25 colonnes se regroupent en sept familles :

*Tableau 1 — Variables du dataset*

| Famille | Variables | Type |
|---|---|---|
| Identification | `job_id` | texte |
| Métier | `job_title` (25 titres), `job_category` (12 catégories), `is_llm_role` | texte, indicateur 0/1 |
| Profil demandé | `experience_level` (4 niveaux), `years_of_experience` (1 à 15), `education_required` (5 niveaux), `is_senior` | texte, entier, indicateur |
| Rémunération | `annual_salary_usd`, `salary_min_usd`, `salary_max_usd`, `salary_tier` (5 tranches), `ai_salary_premium_pct` | numérique, texte |
| Localisation | `city`, `country` (14 valeurs), `remote_work` (On-site, Hybrid, Fully Remote), `is_remote_friendly` | texte, indicateur |
| Entreprise | `company_size` (5 tailles), `industry` (12 secteurs), `benefits_score_10` | texte, décimal |
| Demande | `required_skills`, `demand_score` (68 à 98), `demand_growth_yoy_pct`, `posting_year`, `posting_month` | liste, entier, décimal |

Quelques ordres de grandeur :

- salaire annuel moyen de **194 892 $**, médian de **180 000 $**, de 90 000 $ à 384 000 $ ;
- score de demande moyen de **87,5 / 100** ;
- **75,4 %** des offres sont compatibles avec le télétravail (Hybrid ou Fully Remote) ;
- **21,8 %** des offres concernent des rôles LLM / GenAI ;
- la catégorie *AI Engineering* représente près de la moitié des offres (736) et les États-Unis plus d'un tiers (515).

## 2.3 Qualité des données

Les contrôles réalisés avant tout traitement donnent un dataset globalement propre :

- **aucune valeur manquante** sur les 37 500 cellules ;
- **aucun doublon** de `job_id`, ni de ligne identique hors identifiant ;
- des **types cohérents** : salaires, années et scores numériques, mois entre 1 et 12 ;
- **aucune variante d'écriture** dans les catégories (pas d'espaces parasites ni de différences de casse) ;
- des **colonnes dérivées cohérentes** avec leur source : `is_senior` correspond exactement aux niveaux Senior et Lead, `is_remote_friendly` aux modes Hybrid et Fully Remote, et `salary_tier` aux bornes de salaire annoncées.

Plusieurs anomalies demandent en revanche une décision :

*Tableau 2 — Anomalies détectées*

| Anomalie | Volume | Commentaire |
|---|---|---|
| Compétence répétée dans une même offre (ex. `SQL` deux fois pour `AIJOB0004`) | 119 offres | Erreur de saisie évidente |
| Salaire annuel supérieur à `salary_max_usd` | 288 offres (19,2 %) | Jamais inférieur au minimum ; surtout des postes Lead (167) et Senior (94) |
| Niveau d'expérience incohérent avec le nombre d'années (ex. *Entry* avec 7 ans) | 1 099 offres (73,3 %) | Seules 26,7 % des offres sont cohérentes |
| Offres « Global / Remote » marquées *On-site* | 18 offres sur 82 « Global » | Contradiction interne |
| Sur-représentation de janvier–mars 2026 | 58,4 % des offres | 3 mois sur 15 couverts |

L'analyse de la fourchette salariale a permis de mieux comprendre le deuxième point : `salary_min_usd` et `salary_max_usd` sont **identiques pour toutes les offres d'un même intitulé de poste**. Il s'agit donc d'une fourchette de référence du métier, et non de la fourchette propre à l'offre. Qu'un poste Lead dépasse le maximum de référence de son métier est plausible et ne constitue pas une erreur.

## 2.4 Limites

Ces constats indiquent que le dataset est **pédagogique et vraisemblablement généré** : la répartition presque uniforme des niveaux d'expérience, des tailles d'entreprise et des secteurs, ainsi que l'indépendance entre niveau et années d'expérience, ne ressemblent pas à des données réelles. Les résultats du dashboard décrivent donc ce jeu de données et **ne doivent pas être lus comme un état du marché réel**, conformément à l'avertissement du sujet.

La sur-représentation du premier trimestre 2026 interdit par ailleurs de comparer des volumes d'offres d'un mois à l'autre : seules des proportions ou des moyennes peuvent être comparées dans le temps.
