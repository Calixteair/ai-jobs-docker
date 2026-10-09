# Décisions de nettoyage

Chaque décision s'appuie sur un constat chiffré de [`profil_dataset.md`](profil_dataset.md) et est implémentée dans `scripts/cleaning.py`.

| # | Constat | Décision | Justification |
|---|---|---|---|
| D1 | 119 offres contiennent une compétence en double (ex. `AIJOB0004` : `SQL` ×2) | **Dédoublonner** la liste en conservant l'ordre de première apparition | Une compétence n'est requise qu'une fois ; la clé primaire `(job_id, skill_id)` de `job_skills` l'impose de toute façon |
| D2 | 288 offres (19,2 %) ont un `annual_salary_usd` **au-dessus** de `salary_max_usd`, jamais en dessous | **Conserver** le salaire tel quel, ajouter l'indicateur `salary_above_range` | La fourchette min/max est identique pour toutes les offres d'un même `job_title` : c'est une **fourchette de référence du métier**, pas celle de l'offre. Les dépassements concernent surtout Lead (167) et Senior (94) : cas plausibles, pas des erreurs. `annual_salary_usd` est par ailleurs cohérent avec `salary_tier` |
| D3 | `experience_level` ne correspond aux années d'expérience que pour 26,7 % des offres | **Ne pas corriger**. `experience_level` reste la variable de référence pour les filtres et analyses ; `years_of_experience` est conservé à titre descriptif | Impossible de savoir laquelle des deux colonnes est juste. `experience_level` est cohérent avec `is_senior` et c'est le filtre demandé par le sujet. La limite est signalée dans le rapport |
| D4 | 58,4 % des offres datent de janvier–mars 2026 | **Conserver**, ajouter `posting_period` (`AAAA-MM`) | Biais d'échantillonnage du dataset, pas une erreur. Toute analyse temporelle devra raisonner en proportions et non en volumes |
| D5 | `annual_salary_usd` est stocké en flottant alors que toutes les valeurs sont entières | **Convertir en entier** | Type plus juste, évite les `239000.0` à l'affichage |
| D6 | `is_senior`, `is_remote_friendly`, `is_llm_role` sont des 0/1 | **Convertir en booléens** | Sémantique explicite ; stockés en `BOOLEAN` dans MySQL |
| D7 | `experience_level` est un libellé texte, ordre non alphabétique | Ajouter `experience_rank` (1 = Entry … 4 = Lead) | Permet de trier les graphiques dans l'ordre logique |
| D8 | Aucun manquant, aucun doublon d'identifiant, aucun espace parasite, aucune variante de casse | **Garde-fous** : le script échoue si l'une de ces anomalies apparaît, ainsi que si une valeur catégorielle sort des domaines connus | Le nettoyage reste fiable si le dataset est remplacé par une nouvelle version |
| D9 | `required_skills` est une liste dans une seule colonne | **Normaliser** en deux tables : `skills` (93 compétences) et `job_skills` (liaison) ; la colonne est retirée de `jobs` | Relation plusieurs-à-plusieurs, cf. choix MySQL |

## Limites à mentionner dans le rapport

- Le dataset est **pédagogique** et vraisemblablement synthétique (incohérences niveau/années, fourchettes par titre) : les résultats ne décrivent pas le marché réel.
- Les comparaisons temporelles sont biaisées par la sur-représentation du T1 2026.
