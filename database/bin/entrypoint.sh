#!/bin/bash
# Entrypoint de l'image db : lance la synchro du schéma en arrière-plan, puis l'entrypoint officiel
# de MySQL (exec : mysqld reste le processus principal et reçoit les signaux d'arrêt).
set -euo pipefail

# Le healthcheck ne passe au vert qu'une fois la synchro de ce démarrage réussie
rm -f /tmp/ai-jobs-schema-ok
# Comme l'entrypoint officiel : « command: --option » veut dire mysqld --option
if [ "${1:0:1}" = - ]; then
  set -- mysqld "$@"
fi
if [ "${1:-}" = mysqld ]; then
  schema-sync.sh &
else
  echo "[schema-sync] commande « $1 » : pas de serveur, synchro ignorée"
fi
exec docker-entrypoint.sh "$@"
