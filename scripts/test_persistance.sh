#!/usr/bin/env bash
# Test T7 — les données survivent à un arrêt / redémarrage des conteneurs.
#
# Compter les offres avant/après ne suffit pas : si le volume était perdu,
# l'import se relancerait et redonnerait 1500 lignes. On écrit donc un
# marqueur unique dans la base, on supprime les conteneurs (sans -v), on
# redémarre, puis on vérifie que le marqueur est toujours là.
set -euo pipefail

COMPOSE=(docker compose -f compose.yaml -f compose.test.yaml)

sql() {
  "${COMPOSE[@]}" exec -T db sh -c \
    'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -N -e "$0"' "$1" 2>/dev/null
}

marker="t7-$(date +%s)-$RANDOM"

echo "[T7] Démarrage de la base"
"${COMPOSE[@]}" up -d --wait db >/dev/null

echo "[T7] Écriture du marqueur $marker"
sql "CREATE TABLE IF NOT EXISTS t7_persistence (marker VARCHAR(64));
     INSERT INTO t7_persistence VALUES ('$marker');"
jobs_before=$(sql "SELECT COUNT(*) FROM jobs")

echo "[T7] docker compose down (conteneurs supprimés, volume conservé)"
"${COMPOSE[@]}" down >/dev/null

echo "[T7] docker compose up"
"${COMPOSE[@]}" up -d --wait db >/dev/null

found=$(sql "SELECT COUNT(*) FROM t7_persistence WHERE marker = '$marker'")
jobs_after=$(sql "SELECT COUNT(*) FROM jobs")
sql "DROP TABLE t7_persistence"

echo "[T7] Offres avant : $jobs_before / après : $jobs_after — marqueur retrouvé : $found"
if [[ "$found" == "1" && "$jobs_before" == "$jobs_after" ]]; then
  echo "[T7] OK : les données ont survécu au redémarrage"
else
  echo "[T7] ÉCHEC : données perdues" >&2
  exit 1
fi
