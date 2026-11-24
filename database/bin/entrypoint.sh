#!/bin/bash
# Entrypoint de l'image db : lance la synchro du schéma en arrière-plan, puis l'entrypoint officiel
# de MySQL (exec : mysqld reste le processus principal et reçoit les signaux d'arrêt).
set -euo pipefail

# Le healthcheck ne passe au vert qu'une fois la synchro de ce démarrage réussie
rm -f /tmp/ai-jobs-schema-ok
if [ "${1:-}" = mysqld ]; then
  schema-sync.sh &
fi
exec docker-entrypoint.sh "$@"
