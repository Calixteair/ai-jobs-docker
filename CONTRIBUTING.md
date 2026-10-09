# Contribuer au projet

## Mise en place

Prérequis : Git, Docker (avec Compose v2), Python 3.12+, `make`.

```bash
git clone https://github.com/Calixteair/ai-jobs-docker.git
cd ai-jobs-docker
make venv      # environnement Python de dev dans .venv
make hooks     # (optionnel) vérifications automatiques avant chaque commit
make env       # crée .env depuis .env.example
make help      # liste toutes les commandes
```

## Organisation

- Le travail est suivi sur le [GitHub Project](https://github.com/users/Calixteair/projects/3) : une carte = une issue.
- Avant de commencer une issue : l'assigner à soi et la passer en **In progress**.
- Une issue est prête (*Definition of Ready*) quand son objectif et ses critères d'acceptation sont clairs et qu'elle n'est bloquée par rien.

## Branches

```
feature/<n°>-<slug> ──PR──► dev (staging) ──PR de release──► main (production)
```

| Branche | Usage |
|---|---|
| `main` | Production. Uniquement via une PR depuis `dev`. |
| `dev` | Intégration, branche par défaut. Uniquement via PR. |
| `feature/<n°>-<slug>` | Une issue = une branche, créée depuis `dev` à jour. |
| `fix/<n°>-<slug>` | Correctif. |
| `docs/<n°>-<slug>` | Documentation / rapport. |

```bash
git switch dev && git pull
git switch -c feature/27-filtres-dashboard
```

## Commits

Format [Conventional Commits](https://www.conventionalcommits.org/fr/) :

```
<type>(<portée optionnelle>): <résumé à l'impératif, en minuscules>

<détail optionnel : pourquoi, pas comment>

Closes #27
```

Types : `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`.
Exemples : `feat(app): filtres pays et secteur`, `fix(db): healthcheck en TCP`.

## Pull requests

1. `make lint test` passe en local.
2. PR vers `dev`, description remplie (le modèle s'affiche automatiquement), `Closes #<n°>`.
3. Carte en **In review**, un autre membre relit et approuve.
4. CI verte et conversations résolues → merge, la branche est supprimée automatiquement.

Relire une PR, c'est : comprendre le changement, lancer les commandes de test, vérifier l'absence de secret et poser des questions plutôt que deviner.

## Definition of Done

- Code mergé dans `dev` via une PR relue, CI verte.
- Tests ajoutés, ou absence justifiée dans la PR.
- Documentation à jour si le comportement change.
- Preuve dans `rapport/preuves/` si la tâche sert un test T1–T8 du sujet.

## Secrets

Jamais de mot de passe, token ou clé dans le dépôt (il est public) : uniquement dans `.env`, qui est ignoré par Git. La CI lance `gitleaks` sur tout l'historique.
