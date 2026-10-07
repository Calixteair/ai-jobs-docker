# Mise en place VPS — environnements staging & production

> Cible : VPS `calixteair.fr` (Debian 11, Docker 29.4, Compose 5.1, NPM, OpenBao).
> Principe : **réutiliser le pattern de déploiement existant** du VPS (déjà en place pour `kalidoku` et `assistant`) plutôt que d'en créer un nouveau.
> Audit en lecture seule réalisé le 2026-10-07 — aucune modification faite à ce stade.

## 1. Vue d'ensemble

```
GitHub Actions                                   VPS calixteair.fr (SSH :5485)
──────────────                                   ─────────────────────────────
push dev  ─► build ─► ghcr.io/…:staging ─┐
                                         ├─ ssh ci-ai-jobs-staging ─► sudo ci-deploy-self.sh
push main ─► build ─► ghcr.io/…:prod  ───┤                              └► bao-deploy.sh ai-jobs-staging
  (approbation manuelle)                 └─ ssh ci-ai-jobs-prod ─────► sudo ci-deploy-self.sh
                                                                        └► bao-deploy.sh ai-jobs-prod

bao-deploy.sh <stack> :
  1. vérifie OpenBao, démarre bao-agent@<stack> si besoin
  2. attend /run/<stack>/.env (rendu en tmpfs par bao-agent depuis OpenBao)
  3. cd /home/calixteair/docker/projects/<stack> && docker compose pull && up -d

Navigateur ─► NPM (:443, réseau nginx-reverse-proxy) ─► ai-jobs-<env>-app:8501 ─► ai-jobs-<env>-db:3306
```

| | Staging | Production |
|---|---|---|
| Branche | `dev` | `main` |
| Stack / dossier | `projects/ai-jobs-staging/` | `projects/ai-jobs-prod/` |
| Utilisateur CI | `ci-ai-jobs-staging` | `ci-ai-jobs-prod` |
| Tag d'image | `:staging` (+ `:sha-<court>`) | `:prod` (+ `:vX.Y.Z`, `:sha-<court>`) |
| Secrets OpenBao | `secret/ai-jobs/staging/mysql` | `secret/ai-jobs/prod/mysql` |
| URL | `ai-jobs-staging.calixteair.fr` (basic auth) | `ai-jobs.calixteair.fr` |
| GitHub Environment | `staging` | `production` (required reviewer) |

Isolation : chaque environnement a ses propres conteneurs, réseau interne, volume MySQL, secrets, clé SSH et utilisateur CI. Une clé CI compromise ne peut redéployer **que** son environnement (le wrapper déduit la stack de `$SUDO_USER`).

## 2. Constat de l'audit

| Élément | État | Impact pour le projet |
|---|---|---|
| OS / Docker / Compose | Debian 11, Docker 29.4.2, Compose 5.1.3 | OK |
| RAM | 15 Gi, ~11 Gi disponibles | OK pour 2 MySQL (limiter à ~512 Mo chacun) |
| Disque `/` | **83 % utilisé, 33 Go libres** | Surveiller ; `docker image prune` après déploiements |
| SSH | port `5485`, clé uniquement, root interdit | Secret `DEPLOY_PORT=5485` côté GitHub |
| Réseau NPM | `nginx-reverse-proxy` | Le service `app` doit le rejoindre (réseau externe) |
| Pattern CI | groupe `ci-deployers`, `ci-deploy-self.sh` → `bao-deploy.sh` | Réutilisé tel quel, aucune modif sudoers |
| OpenBao | conteneur `openbao`, `bao-agent@<stack>`, `/etc/bao/<stack>/agent.hcl` | Secrets MySQL gérés comme les autres stacks |
| Dossiers | `/home/calixteair/docker/projects/<stack>/` | Auto-découvert par `bao-deploy.sh` |

## 3. Choix techniques liés au VPS

### 3.1 Deux images publiées sur GHCR

`bao-deploy.sh` ne fait que `pull` + `up -d` : il **ne synchronise aucun fichier** du dépôt (gotcha connu, cf. wiki `vps-ci-deployers-pattern`). Les scripts d'init MySQL doivent donc voyager **dans une image** :

- `ghcr.io/calixteair/ai-jobs-docker-app` : Streamlit.
- `ghcr.io/calixteair/ai-jobs-docker-db` : `FROM mysql:8.4` + `COPY database/scripts_initialisation/ /docker-entrypoint-initdb.d/`.

Le `compose.yaml` du correcteur peut utiliser `build:` sur les deux, ou `mysql:8.4` + bind mount : au choix du groupe, sans impact sur le VPS.

### 3.2 Packages GHCR publics

Le repo est public : rendre les deux packages **publics** évite toute authentification `docker login` côté VPS. (GitHub → Packages → *Package settings* → *Change visibility*.)

### 3.3 Fichiers à synchroniser à la main

Seuls deux fichiers par environnement vivent sur le VPS hors CI, et changent rarement :
- `projects/ai-jobs-<env>/compose.yaml` (copie de `deploy/compose.vps.yaml` avec le bon tag)
- `/etc/bao/ai-jobs-<env>/agent.hcl`

Toute modification de ces fichiers dans le repo ⇒ re-synchronisation manuelle **avant** le prochain déploiement CI.

### 3.4 Réinitialisation des données

Les scripts d'init MySQL ne s'exécutent que si le volume est vide. Si le schéma ou l'import changent :
- **staging** : `docker compose down -v && up -d` (données réimportables, pas de risque).
- **prod** : idem, mais seulement lors d'une release planifiée (les données viennent du CSV, aucune donnée utilisateur à perdre).

## 4. Procédure de mise en place

> À exécuter par l'admin du VPS (ou Claude via `vps-manager`, après confirmation). Répéter les étapes 4.2 à 4.6 pour `staging` puis `prod` (`ENV=staging|prod`).

### 4.1 DNS

- [ ] Enregistrements `A` (et `AAAA` si IPv6) `ai-jobs-staging` et `ai-jobs` → IP du VPS (vérifier d'abord si un wildcard `*.calixteair.fr` existe déjà).

### 4.2 Dossier de la stack

```bash
STACK=ai-jobs-$ENV
sudo install -d -o calixteair -g calixteair -m 0755 /home/calixteair/docker/projects/$STACK
sudo install -o calixteair -g calixteair -m 0644 /tmp/compose.$ENV.yaml /home/calixteair/docker/projects/$STACK/compose.yaml
sudo -u calixteair ln -s /home/calixteair/docker/projects/$STACK /home/calixteair/dockge-stacks/$STACK   # visibilité Dockge
```

Contenu attendu de `compose.yaml` (versionné dans le repo sous `deploy/compose.vps.yaml`, tag substitué) :

```yaml
name: ai-jobs-staging            # ai-jobs-prod pour la prod

services:
  db:
    image: ghcr.io/calixteair/ai-jobs-docker-db:staging
    container_name: ai-jobs-staging-db
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    networks: [internal]
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -u root -p$${MYSQL_ROOT_PASSWORD} --silent"]
      interval: 10s
      retries: 10
    mem_limit: 512m
    restart: unless-stopped

  app:
    image: ghcr.io/calixteair/ai-jobs-docker-app:staging
    container_name: ai-jobs-staging-app
    environment:
      DB_HOST: db
      DB_PORT: 3306
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    depends_on:
      db: { condition: service_healthy }
    networks: [internal, nginx-reverse-proxy]
    mem_limit: 512m
    restart: unless-stopped
    # aucun port publié : accès uniquement via NPM

volumes:
  mysql_data:

networks:
  internal:
  nginx-reverse-proxy:
    external: true
```

### 4.3 Secrets OpenBao

Suivre la procédure standard du wiki (`lab-openbao`, `vps-chantier-bao-migration`) :

- [ ] Secret KV `secret/ai-jobs/$ENV/mysql` : `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` (mots de passe générés, **différents** entre staging et prod).
- [ ] Policy `ai-jobs-$ENV` : `read` sur ce seul chemin.
- [ ] AppRole `ai-jobs-$ENV` liée à cette policy.
- [ ] `/etc/bao/ai-jobs-$ENV/agent.hcl` (root:root, 0640) : template qui rend `/run/ai-jobs-$ENV/.env`.
- [ ] Role-id / secret-id (wrappé) installés, `systemctl enable --now bao-agent@ai-jobs-$ENV`.
- [ ] Vérifier : `/run/ai-jobs-$ENV/.env` non vide (sans l'afficher).

### 4.4 Utilisateur CI dédié

Clé générée **en local**, jamais sur le VPS ; une clé par environnement :

```bash
ssh-keygen -t ed25519 -N '' -C "ci-ai-jobs-$ENV@github-actions" -f ./ci-ai-jobs-$ENV
```

Sur le VPS :

```bash
sudo useradd -m -s /bin/bash -g ci-deployers ci-ai-jobs-$ENV      # /bin/bash obligatoire (gotcha nologin)
sudo install -d -o ci-ai-jobs-$ENV -g ci-deployers -m 0700 /home/ci-ai-jobs-$ENV/.ssh
# authorized_keys (0600), une seule ligne :
# command="sudo /usr/local/sbin/ci-deploy-self.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA… ci-ai-jobs-$ENV@github-actions
```

- Pas d'ajout au groupe `docker` (inutile : tout passe par le wrapper sudo).
- Pas de modification du sudoers : `%ci-deployers` couvre déjà le nouvel utilisateur.
- Test : `ssh -p 5485 -i ./ci-ai-jobs-$ENV ci-ai-jobs-$ENV@calixteair.fr` → doit lancer le déploiement et rien d'autre.

### 4.5 Premier démarrage manuel

```bash
sudo /usr/local/sbin/bao-deploy.sh ai-jobs-$ENV
sudo docker compose -p ai-jobs-$ENV ps            # db healthy, app running
sudo docker exec ai-jobs-$ENV-app python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8501/_stcore/health').read())"
```

### 4.6 Nginx Proxy Manager

Admin via tunnel : `ssh -L 81:127.0.0.1:81 vps-claude` → `http://localhost:81`.

- [ ] Proxy host `ai-jobs-$ENV…calixteair.fr` → `http://ai-jobs-$ENV-app:8501`
- [ ] **Websockets Support : ON** (sinon Streamlit reste bloqué sur « Please wait… »)
- [ ] SSL Let's Encrypt, Force SSL, HTTP/2
- [ ] Staging uniquement : Access List (basic auth, un compte pour le groupe)

### 4.7 Côté GitHub

- [ ] Packages GHCR `ai-jobs-docker-app` et `ai-jobs-docker-db` en visibilité publique (après le premier push).
- [ ] Environment **`staging`** : branche autorisée `dev`.
- [ ] Environment **`production`** : branche autorisée `main`, *Required reviewers* = toi.
- [ ] Secrets par environment :

| Secret | staging | production |
|---|---|---|
| `DEPLOY_HOST` | `calixteair.fr` | `calixteair.fr` |
| `DEPLOY_PORT` | `5485` | `5485` |
| `DEPLOY_USER` | `ci-ai-jobs-staging` | `ci-ai-jobs-prod` |
| `DEPLOY_SSH_KEY` | clé privée staging | clé privée prod |
| `DEPLOY_KNOWN_HOSTS` | sortie de `ssh-keyscan -p 5485 calixteair.fr` | idem |
| `SMOKE_BASIC_AUTH` | `user:pass` de l'access list NPM | — |
| *variable* `APP_URL` | `https://ai-jobs-staging.calixteair.fr` | `https://ai-jobs.calixteair.fr` |

`DEPLOY_KNOWN_HOSTS` évite `StrictHostKeyChecking=no`.

## 5. Workflow de déploiement (esquisse)

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [dev, main]

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.t.outputs.tag }}
    steps:
      - uses: actions/checkout@v4
      - id: t
        run: echo "tag=${{ github.ref_name == 'main' && 'prod' || 'staging' }}" >> "$GITHUB_OUTPUT"
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: app/Dockerfile
          push: true
          tags: |
            ghcr.io/calixteair/ai-jobs-docker-app:${{ steps.t.outputs.tag }}
            ghcr.io/calixteair/ai-jobs-docker-app:sha-${{ github.sha }}
      # idem pour l'image db (database/Dockerfile)

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}
    concurrency: deploy-${{ github.ref_name }}
    steps:
      - name: Déclencher le déploiement
        run: |
          install -m 700 -d ~/.ssh
          echo "${{ secrets.DEPLOY_KNOWN_HOSTS }}" > ~/.ssh/known_hosts
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
          ssh -p "${{ secrets.DEPLOY_PORT }}" "${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }}"
      - name: Smoke test
        env:
          URL: ${{ vars.APP_URL }}                     # variable d'environment GitHub
          SMOKE_AUTH: ${{ secrets.SMOKE_BASIC_AUTH }}  # staging uniquement (user:pass de l'access list)
        run: |
          for i in $(seq 1 30); do
            curl -fsS ${SMOKE_AUTH:+-u "$SMOKE_AUTH"} "$URL/_stcore/health" && exit 0
            sleep 5
          done
          exit 1
```

La commande SSH n'envoie rien : le `command=` forcé décide de ce qui s'exécute.

## 6. Checklist de validation

- [ ] Push sur `dev` → image `:staging` publiée → staging redéployé → smoke test vert
- [ ] Merge `dev` → `main` → job en attente d'approbation → approuvé → prod redéployée
- [ ] `ssh` avec la clé staging ne peut pas déployer la prod (stack déduite du user)
- [ ] `docker compose -p ai-jobs-prod restart` → données toujours présentes
- [ ] Aucun port MySQL exposé : `ss -tlnp | grep 3306` vide côté hôte
- [ ] `journalctl -t ci-deploy` trace chaque déploiement

## 7. Observations hors périmètre (à traiter séparément)

- UFW autorise `5432/tcp` depuis partout (aucun service n'écoute actuellement) et contient deux règles contradictoires sur le port `81`. Docker contournant UFW pour les ports publiés, ces règles sont trompeuses : à nettoyer.
- `ci-kalidoku` est membre du groupe `docker` alors que le pattern n'en a pas besoin : équivalent root si sa clé fuit. À retirer.
- Disque à 83 % : prévoir un nettoyage (`docker system df`).
