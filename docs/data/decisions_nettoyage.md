# Décisions de nettoyage

Chaque décision part d'un constat chiffré du [rapport d'exploration](exploration_dataset.md) et sera appliquée par `scripts/cleaning.py` (#12) puis par le schéma de la base (#14, #16).

## Compétences (`required_skills`) — issue #10

| # | Constat | Décision | Justification |
|---|---|---|---|
| C1 | Les compétences sont séparées par `\|`. Le `/` apparaît dans `CI/CD` et `Cloud (AWS/GCP/Azure)` (rapport §6) | Découper **uniquement** sur `\|` | Découper aussi sur `/` casserait ces deux compétences en morceaux sans sens (`CI`, `CD`…) |
| C2 | 119 offres contiennent une compétence écrite deux fois, 120 mentions en trop (rapport §6.2). Exemple : `AIJOB0004`, `SQL` ×2 | **Dédoublonner** chaque liste en gardant la **première occurrence** | Une compétence est requise ou ne l'est pas : la répéter n'a pas de sens. Sans dédoublonnage, le top des compétences est faussé (`SQL` compté 452 fois pour 422 offres, soit +7 %). La clé primaire `(job_id, skill_id)` de la table de liaison l'interdirait de toute façon |
| C3 | Les répétitions ne touchent que 7 compétences transverses : `SQL`, `Cloud`, `Leadership`, `Communication`, `Research`, `Agile`, `Statistics` | Pas de traitement en plus de C2 ; à citer dans le rapport | Hypothèse : à la génération du dataset, des compétences générales ont été ajoutées aux compétences du métier sans vérifier si elles y figuraient déjà. Cela confirme que les répétitions sont des erreurs de saisie, pas une information |
| C4 | Aucune variante d'écriture (casse, espaces), aucune compétence vide (rapport §6) | **Aucune normalisation** ; garde-fou : retirer les espaces en début et fin, et **arrêter le nettoyage** si une même compétence apparaît sous deux écritures | Rien à corriger aujourd'hui. Si une variante apparaît dans une nouvelle version du CSV, mieux vaut échouer que choisir arbitrairement l'écriture à garder |
| C5 | Des libellés sont proches : `Cloud` / `Cloud (AWS/GCP/Azure)`, `Statistics` / `Advanced Statistics`, `Fine-tuning` / `LLM Fine-tuning`… (rapport §6.3) | **Ne pas fusionner** | Le dataset n'indique nulle part qu'ils sont équivalents, et il les traite comme distincts : `Cloud` et `Cloud (AWS/GCP/Azure)` sont demandés ensemble dans 9 offres, `Statistics` et `Advanced Statistics` dans 12. Une fusion serait un choix subjectif qui modifierait le top des compétences |
| C6 | L'ordre des compétences dans la liste n'est documenté nulle part | **Ne pas conserver l'ordre** | La table de liaison décrit un ensemble (une offre requiert ou non une compétence), pas une liste ordonnée |
| C7 | 93 compétences distinctes ; 9 428 couples offre–compétence après dédoublonnage ; nom le plus long : 23 caractères, uniquement des caractères ASCII (rapport §6.1) | **Éclater** la colonne en deux tables : `skills` (une ligne par compétence, nom unique) et `job_skills` (une ligne par couple offre–compétence). Retirer `required_skills` de `jobs` | Relation plusieurs-à-plusieurs : c'est la modélisation relationnelle attendue (sujet §6). Garder aussi la colonne d'origine créerait deux sources de vérité. La taille des noms permet un `VARCHAR` court (#16) |

## À citer dans le rapport (section 5, Préparation)

- La règle de dédoublonnage (C2), avec son effet chiffré sur le top des compétences.
- Le choix de ne pas fusionner les libellés proches (C5) : c'est une **limite** de l'analyse, car le classement des compétences dépend des libellés du dataset.
