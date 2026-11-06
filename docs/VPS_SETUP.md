# Mise en place VPS — environnements staging & production

> Cible : VPS `calixteair.fr` (Debian 13, Docker, NPM, OpenBao, Harbor `registry.calixteair.fr`).
> Principe : **même modèle que les autres projets du VPS** (kalidoku, assistant, portfolio, DevSecVault) :
> images sur Harbor, secrets dans OpenBao, production déployée seulement depuis un **tag signé**.
> Mis à jour le 2026-11-05 (passage de GHCR et de l'approbation Jenkins à Harbor et `stack-sync`).

## 1. Vue d'ensemble

```
Jenkins (jenkins.calixteair.fr)                       VPS calixteair.fr (SSH :5485)
───────────────────────────────                       ─────────────────────────────
merge signé dans dev ─► tests ─► Harbor :app-sha-*, :db-sha-* ─► ssh ci-ai-jobs-staging ─► stack-sync ai-jobs-staging <commit>
push main ─► tests ─► Harbor :app-latest, :db-latest      (pas de déploiement)
tag vX.Y.Z signé ─► tests ─► Harbor :vX.Y.Z-app, :vX.Y.Z-db ─► ssh ci-ai-jobs ─► stack-sync ai-jobs vX.Y.Z

stack-sync ai-jobs vX.Y.Z (root, code fixe dans vps-soc-config) :
  1. récupère le dépôt lui-même (clé de déploiement en lecture seule)
  2. vérifie que le tag est signé par Calixteair et que son commit est sur main
  3. vérifie deploy/prod/compose.yaml et agent.hcl contre sa politique, épingle les images vX.Y.Z-*
  4. sauvegarde, installe, bao-deploy.sh ai-jobs, contrôle de santé, retour arrière si échec

Navigateur ─► NPM (:443, réseau nginx-reverse-proxy) ─► ai-jobs[-staging]-app:8501 ─► ai-jobs[-staging]-db:3306
```

| | Staging | Production |
|---|---|---|
| Déclencheur | commit sur `dev` signé par le bot de review ou Calixteair | tag `vX.Y.Z` signé par Calixteair (commit sur `main`) |
| Stack / dossier | `projects/ai-jobs-staging/` | `projects/ai-jobs/` |
| Fichiers du dépôt | `deploy/staging/` (installés par `stack-sync`, mode commit) | `deploy/prod/` (installés par `stack-sync`) |
| Utilisateur CI | `ci-ai-jobs-staging` | `ci-ai-jobs` |
| Images | `:app-sha-<commit>`, `:db-sha-<commit>` (épinglées par `stack-sync`) | `:vX.Y.Z-app`, `:vX.Y.Z-db` (immuables) |
| Secrets OpenBao | `secret/ai-jobs/staging/mysql` | `secret/ai-jobs/prod/mysql` |
| URL | `ai-jobs-staging.calixteair.fr` (basic auth) | `ai-jobs.calixteair.fr` |

Isolation : chaque environnement a ses propres conteneurs, réseau interne, volume MySQL, secrets, clé SSH et utilisateur CI. Une clé CI compromise ne peut redéployer **que** son environnement ; celle de la prod ne peut déployer qu'un tag existant **signé**.

## 2. Images

Deux images dans le projet Harbor `ai-jobs` (`registry.calixteair.fr/ai-jobs/ai-jobs`), distinguées par un préfixe de tag :
- `app-*` : Streamlit (`Dockerfile`) ;
- `db-*` : `FROM mysql:8.4` + scripts d'initialisation (`database/Dockerfile`). `bao-deploy.sh` ne copie aucun fichier : les scripts d'init voyagent dans l'image.

Chaque commit publié a aussi ses images `:<préfixe>-sha-<commit>`. Le `compose.yaml` du correcteur garde `build:` : il ne dépend pas du VPS.

## 3. Choix techniques

### 3.1 Fichiers de déploiement

- `deploy/prod/compose.yaml` et `deploy/prod/agent.hcl` : installés par `stack-sync` à chaque release. Une modification passe par une PR, puis un tag.
- `deploy/staging/compose.yaml` et `deploy/staging/agent.hcl` : installés par `stack-sync` (mode commit) à chaque commit de `dev`, s'il est signé par le bot de review (`review-bot@calixteair.fr`) ou par Calixteair. Un merge par le bouton de GitHub n'est jamais déployé.

### 3.2 Réinitialisation des données

Les scripts d'init MySQL ne s'exécutent que si le volume est vide. Si le schéma ou l'import changent :
- **staging** : `docker compose down -v && up -d` (données réimportables, pas de risque).
- **prod** : idem, mais seulement lors d'une release planifiée (les données viennent du CSV, aucune donnée utilisateur à perdre).

## 4. Mise en place de la production (une fois, par Calixteair)

1. **DNS** : `ai-jobs.calixteair.fr` → IP du VPS.
2. **OpenBao** : `vps-soc-config/ai-jobs/setup-bao.sh` (secret `secret/ai-jobs/prod/mysql` généré, policy `ai-jobs-prod-read`, AppRole `ai-jobs-prod`, `/etc/bao/ai-jobs/role_id` et `secret_id`).
3. **VPS** : `ansible-playbook … --tags stack_sync` (politique `ai-jobs`, utilisateur `ci-ai-jobs`, clé de déploiement GitHub), puis ajouter la clé publique affichée comme *deploy key* (lecture seule) du dépôt.
4. **Jenkins** : clé privée de `ci-ai-jobs` dans OpenBao `secret/cicd/groupes/ai-jobs/deploy` (clé `ssh_key_b64`).
5. **NPM** : proxy host `ai-jobs.calixteair.fr` → `http://ai-jobs-app:8501`, **Websockets Support : ON** (sinon Streamlit reste bloqué sur « Please wait… »), SSL Let's Encrypt, Force SSL.
6. **Release** : `git tag -s vX.Y.Z -m "…" <commit de main>`, `git verify-tag vX.Y.Z`, `git push origin vX.Y.Z`.

## 5. Identifiants de la CI

Lus dans OpenBao par l'AppRole des projets de groupe (`secret/cicd/groupes/*` seulement) :

| Chemin | Contenu |
|---|---|
| `cicd/groupes/harbor/ai-jobs` | robot Harbor du projet `ai-jobs` (`username`, `token`) |
| `cicd/groupes/ai-jobs/staging-deploy` | clé privée de `ci-ai-jobs-staging` (`ssh_key_b64`) |
| `cicd/groupes/ai-jobs/staging-access` | compte de l'access list NPM du staging (`user`, `password`) |
| `cicd/groupes/ai-jobs/deploy` | clé privée de `ci-ai-jobs` (`ssh_key_b64`) |
| `cicd/groupes/ai-jobs/reviewer` | bot de review : clé OpenRouter (`openrouter_key`, plafonnée) et clé SSH de signature des merges (`ssh_key_b64`) |

Les builds de PR (dossier Jenkins `groupes-pr/`) n'ont accès à aucun de ces chemins.

## 6. Checklist de validation

- [ ] PR vers `dev` verte → review du bot → merge signé par le bot → images `:app-sha-<commit>` et `:db-sha-<commit>` sur Harbor → `stack-sync ai-jobs-staging <commit>` → `/_stcore/health` 200
- [ ] Merge par le bouton de GitHub sur `dev` → `stack-sync` refuse (signature web-flow), le staging ne bouge pas
- [ ] Merge `dev` → `main` → images `:*-latest`, aucun déploiement
- [ ] Tag signé `vX.Y.Z` → prod déployée, `journalctl -t stack-sync` trace le déploiement
- [ ] Tag non signé → `stack-sync` refuse, la prod ne bouge pas
- [ ] `ssh` avec la clé staging ne peut pas déployer la prod (stack déduite du user)
- [ ] Aucun port MySQL exposé : `ss -tlnp | grep 3306` vide côté hôte
