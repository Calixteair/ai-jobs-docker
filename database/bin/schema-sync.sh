#!/bin/bash
# Synchro du schéma sur un volume existant. MySQL n'exécute /docker-entrypoint-initdb.d que si le
# volume est vide : ici, les scripts *.sql sont rejoués quand leur empreinte a changé depuis la
# dernière application (table _schema_sync). Ils doivent donc être rejouables (DROP TABLE IF EXISTS,
# CREATE, insertion). Sur un volume neuf, ils passent une 2e fois juste après l'init (sans effet).
set -euo pipefail

INIT_DIR=/docker-entrypoint-initdb.d
# Mot de passe par variable d'environnement : jamais visible dans la liste des processus
export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"

log() { echo "[schema-sync] $*"; }
# TCP (-h 127.0.0.1) : pendant l'init, MySQL tourne sans réseau, on attend donc le vrai serveur
sql() { mysql -h 127.0.0.1 -uroot --database="$MYSQL_DATABASE" "$@"; }

# Init d'un volume neuf comprise ; au-delà, le conteneur reste unhealthy avec ce message
WAIT_MAX=${SCHEMA_SYNC_WAIT_MAX:-600}
waited=0
until mysqladmin ping -h 127.0.0.1 -uroot --silent 2>/dev/null; do
  if [ "$waited" -ge "$WAIT_MAX" ]; then
    log "ÉCHEC : MySQL injoignable en TCP après ${WAIT_MAX} s, synchro abandonnée"
    exit 1
  fi
  if [ "$waited" -gt 0 ] && [ $((waited % 30)) -eq 0 ]; then
    log "attente de MySQL (${waited} s)"
  fi
  sleep 1
  waited=$((waited + 1))
done

shopt -s nullglob
scripts=("$INIT_DIR"/*.sql)
# Noms et contenus : renommer un script (donc changer l'ordre) change aussi l'empreinte
hash=$(for f in "${scripts[@]}"; do basename "$f"; sha256sum <"$f"; done | sha256sum | cut -c1-64)

sql -e "CREATE TABLE IF NOT EXISTS _schema_sync (
          id TINYINT PRIMARY KEY, hash CHAR(64) NOT NULL, applied_at DATETIME NOT NULL)"
applied=$(sql -N -e "SELECT hash FROM _schema_sync WHERE id = 1")

if [ "$applied" = "$hash" ]; then
  log "schéma à jour (${hash:0:12}), rien à rejouer"
else
  log "empreinte ${applied:0:12} → ${hash:0:12} : ${#scripts[@]} script(s) rejoué(s)"
  for f in "${scripts[@]}"; do
    log "  $(basename "$f")"
    sql <"$f"
  done
  sql -e "REPLACE INTO _schema_sync VALUES (1, '$hash', NOW())"
fi
touch /tmp/ai-jobs-schema-ok
