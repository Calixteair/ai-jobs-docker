# 5. Préparation des données

> Brouillon — section 5 de la trame du sujet (§15). Détail des décisions : `docs/data/decisions_nettoyage.md`.

## 5.1 Démarche

La préparation suit trois principes :

1. **Comprendre avant de transformer** : un script de profilage (`scripts/explore.py`) produit un rapport chiffré de l'état du dataset brut. Chaque décision de nettoyage s'appuie sur un constat de ce rapport.
2. **Ne jamais modifier une valeur sans certitude** : quand deux colonnes se contredisent et qu'on ne peut pas savoir laquelle est juste, on conserve les données et on documente la limite plutôt que d'inventer une correction.
3. **Tout rendre reproductible** : le nettoyage est un script Python (`scripts/cleaning.py`) testé unitairement, exécuté automatiquement à chaque construction de l'image de la base. Aucune étape n'est manuelle.

## 5.2 Transformations retenues

*Tableau 3 — Transformations appliquées*

| Transformation | Lignes concernées | Raison |
|---|---|---|
| Dédoublonnage des compétences d'une offre | 119 | Une compétence n'est requise qu'une fois ; la clé primaire de la table de liaison l'impose |
| Salaire annuel converti en entier | 1 500 | Toutes les valeurs sont entières, le type flottant était inutile |
| Indicateurs 0/1 convertis en booléens | 1 500 | Sens explicite, stockage en `BOOLEAN` |
| Ajout de `experience_rank` (1 à 4) | 1 500 | Trier les graphiques dans l'ordre Entry → Lead plutôt qu'alphabétique |
| Ajout de `posting_period` (`AAAA-MM`) | 1 500 | Regrouper simplement par mois de publication |
| Ajout de `salary_above_range` | 288 | Signaler, sans les modifier, les salaires au-dessus de la fourchette de référence du métier |
| Éclatement de `required_skills` en tables `skills` et `job_skills` | 1 500 → 9 428 liaisons, 93 compétences | Relation plusieurs-à-plusieurs (cf. section 4) |

Les anomalies suivantes ont été **volontairement conservées** :

- **Niveau d'expérience incohérent avec les années** : impossible de savoir laquelle des deux colonnes est juste. `experience_level`, cohérent avec `is_senior` et demandé comme filtre par le sujet, sert de référence ; la limite sera rappelée sous les graphiques concernés.
- **Offres « Global / Remote » sur site** : la bonne valeur ne peut pas être déduite ; « Global » est traité comme une catégorie à part dans les analyses par pays.
- **Déséquilibre temporel** : il s'agit d'un biais d'échantillonnage, pas d'une erreur.

## 5.3 Garde-fous

Le script de nettoyage **échoue explicitement** si le dataset présente une anomalie bloquante : valeur manquante, identifiant en double, valeur catégorielle inconnue, salaire non entier ou indicateur différent de 0/1. Ces contrôles sont sans effet sur le dataset actuel, mais garantissent qu'une nouvelle version du fichier ne serait pas importée silencieusement avec des erreurs.

Le schéma MySQL ajoute une seconde ligne de défense : types non signés, `ENUM` pour le niveau d'expérience et le mode de travail, contraintes `CHECK` (score de demande entre 0 et 100, mois entre 1 et 12…) et clés étrangères. Un test d'intégration vérifie que ces contraintes rejettent bien les valeurs invalides.

## 5.4 Contrôles avant / après

*Tableau 4 — Contrôles avant / après nettoyage*

| Contrôle | Avant | Après |
|---|---|---|
| Nombre d'offres | 1 500 | 1 500 (table `jobs`) |
| Liaisons offre ↔ compétence | 9 548 | 9 428 (120 doublons retirés dans 119 offres) |
| Compétences distinctes | 93 | 93 (table `skills`) |
| Offres avec une compétence en double | 119 | 0 |
| Type de `annual_salary_usd` | `float64` (`239000.0`) | entier (`239000`) |
| Salaire moyen | 194 892 $ | 194 892 $ (inchangé) |
| Salaire médian | 180 000 $ | 180 000 $ (inchangé, calculé en SQL) |

Ces valeurs « après » sont vérifiées automatiquement par les tests d'intégration, qui comparent la base MySQL importée aux résultats du script de nettoyage et aux calculs pandas.

## 5.5 Stratégie d'import

Le nettoyage et l'import sont intégrés à l'image Docker de la base, construite en deux étapes (*multi-stage build*) :

1. une image Python temporaire exécute `cleaning.py` sur le CSV brut et produit trois fichiers : `jobs.csv`, `skills.csv`, `job_skills.csv` ;
2. l'image finale, basée sur l'image officielle `mysql:8.4`, reçoit ces fichiers ainsi que deux scripts SQL placés dans `/docker-entrypoint-initdb.d` : `01_schema.sql` crée les tables, `02_import.sql` les remplit avec `LOAD DATA INFILE`.

Au premier démarrage du conteneur, MySQL exécute ces scripts. Ils ne sont **pas rejoués** aux démarrages suivants tant que le volume de données existe : c'est ce qui garantit la persistance (test T7), mais cela impose de supprimer le volume (`make db-reset`) pour réimporter des données modifiées.

Ce choix présente deux avantages : l'import est entièrement reproductible à partir du seul CSV brut, et l'application n'a jamais besoin du CSV, conformément au sujet qui interdit d'en faire la source du dashboard.
