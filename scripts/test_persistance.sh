#!/usr/bin/env bash
# Test T7 — les données survivent à un arrêt / redémarrage des conteneurs.
#
# Compter les lignes d'une table avant/après ne suffit pas : si le volume était
# perdu, l'import initial se relancerait et redonnerait le même nombre de
# lignes. On écrit donc un marqueur unique dans la base, on supprime les
# conteneurs (sans -v, le volume est conservé), on redémarre, puis on vérifie
# que le marqueur est toujours là.
set -euo pipefail

COMPOSE=(docker compose -f compose.yaml -f compose.test.yaml)

sql() {
  "${COMPOSE[@]}" exec -T db sh -c \
    'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -N -e "$0"' "$1" 2>/dev/null
}

marker="t7-$(date +%s)-$RANDOM"

echo "[T7] Démarrage de la base"
"${COMPOSE[@]}" up -d --wait db >/dev/null 2>&1

echo "[T7] Écriture du marqueur $marker"
sql "CREATE TABLE IF NOT EXISTS t7_persistence (marker VARCHAR(64));
     INSERT INTO t7_persistence VALUES ('$marker');"
container_before=$("${COMPOSE[@]}" ps -q db)

echo "[T7] docker compose down (conteneurs supprimés, volume conservé)"
"${COMPOSE[@]}" down >/dev/null 2>&1

echo "[T7] docker compose up"
"${COMPOSE[@]}" up -d --wait db >/dev/null 2>&1
container_after=$("${COMPOSE[@]}" ps -q db)

found=$(sql "SELECT COUNT(*) FROM t7_persistence WHERE marker = '$marker'")
sql "DROP TABLE t7_persistence"

echo "[T7] Conteneur avant : ${container_before:0:12} / après : ${container_after:0:12}"
echo "[T7] Marqueur retrouvé : $found"
if [[ "$container_before" != "$container_after" && "$found" == "1" ]]; then
  echo "[T7] OK : nouveau conteneur, données conservées dans le volume"
else
  echo "[T7] ÉCHEC : données perdues" >&2
  exit 1
fi
