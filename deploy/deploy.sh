#!/usr/bin/env bash
# Déclenche le redéploiement d'un environnement du VPS puis vérifie l'URL publique.
# Appelé par Jenkins (Jenkinsfile) dans un sshagent qui porte la clé ci-ai-jobs-<env>.
#
# La clé n'autorise qu'une commande forcée côté VPS (ci-deploy-self.sh → bao-deploy.sh
# ai-jobs-<env> : pull des images + up -d) : aucune commande n'est envoyée ici.
#
# Variables : KNOWN_HOSTS (fichier, clé d'hôte épinglée), APP_URL, BASIC_AUTH
# (« user:mot de passe », staging seulement), DEPLOY_HOST, DEPLOY_PORT.
set -euo pipefail

env=${1:-}
[[ "$env" == staging || "$env" == prod ]] || { echo "usage: $0 staging|prod" >&2; exit 1; }
: "${KNOWN_HOSTS:?fichier known_hosts requis}" "${APP_URL:?URL publique requise}"
host=${DEPLOY_HOST:-calixteair.fr}
port=${DEPLOY_PORT:-5485}

echo "[deploy] ci-ai-jobs-$env@$host : pull + up -d"
ssh -p "$port" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$KNOWN_HOSTS" \
  "ci-ai-jobs-$env@$host"

echo "[deploy] vérification de $APP_URL"
auth=()
[[ -n "${BASIC_AUTH:-}" ]] && auth=(--user "$BASIC_AUTH")
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "${auth[@]}" "$APP_URL/_stcore/health" || true)
  [[ "$code" == 200 ]] && { echo "[deploy] OK : $APP_URL répond"; exit 0; }
  sleep 5
done
echo "[deploy] ÉCHEC : $APP_URL/_stcore/health répond $code après 150 s" >&2
exit 1
