#!/usr/bin/env bash
# Smoke tests T1 à T5 (sujet §12) sur la stack complète, depuis zéro.
#   T1 build des images · T2 démarrage · T3 état (healthchecks) · T4 accès web · T5 connexion app → base
#
# Variables : SMOKE_HOST (défaut localhost ; « docker » en CI Jenkins, où les
# conteneurs tournent dans dind), APP_PORT (défaut 8501), KEEP_STACK=1 pour ne
# pas supprimer la stack à la fin. COMPOSE_PROJECT_NAME isole deux exécutions.
set -euo pipefail

HOST=${SMOKE_HOST:-localhost}
PORT=${APP_PORT:-8501}
EXPECTED_JOBS=1500
COMPOSE=(docker compose)

step() { echo "[$1] $2"; }
fail() { echo "[$1] ÉCHEC : $2" >&2; "${COMPOSE[@]}" logs --tail=50 >&2 || true; exit 1; }
cleanup() { [[ "${KEEP_STACK:-0}" == 1 ]] || "${COMPOSE[@]}" down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

step T1 "Construction des images"
"${COMPOSE[@]}" build --quiet || fail T1 "build impossible"

step T2 "Démarrage de la stack (attente des healthchecks)"
"${COMPOSE[@]}" up -d --wait --wait-timeout 180 || fail T2 "la stack ne démarre pas"

step T3 "État des conteneurs"
for svc in app db; do
  state=$("${COMPOSE[@]}" ps --format '{{.Health}}' "$svc")
  [[ "$state" == "healthy" ]] || fail T3 "$svc est « $state »"
  echo "     $svc : $state"
done

step T4 "Accès web sur http://$HOST:$PORT"
code=$(curl -s -o /dev/null -w '%{http_code}' --retry 5 --retry-delay 2 --retry-all-errors "http://$HOST:$PORT/_stcore/health")
[[ "$code" == 200 ]] || fail T4 "/_stcore/health répond $code"
code=$(curl -s -o /dev/null -w '%{http_code}' "http://$HOST:$PORT/")
[[ "$code" == 200 ]] || fail T4 "page d'accueil : $code"
echo "     /_stcore/health et / : 200"

step T5 "Connexion de l'application à la base (par le nom de service)"
# Le script Python est passé en argument pour ne pas dépendre des guillemets du shell.
# shellcheck disable=SC2016
result=$("${COMPOSE[@]}" exec -T app python -c '
import os, pymysql
conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
                       user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                       database=os.environ["DB_NAME"], connect_timeout=5)
with conn.cursor() as cur:
    cur.execute("SELECT VERSION()")
    version = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = %s", ("jobs",))
    jobs = None
    if cur.fetchone()[0]:
        cur.execute("SELECT COUNT(*) FROM jobs")
        jobs = cur.fetchone()[0]
print(version, jobs)
') || fail T5 "connexion impossible"
read -r version jobs <<<"$result"
echo "     MySQL $version joint par le nom de service db"
if [[ "$jobs" == "None" ]]; then
  echo "     table jobs absente : contrôle des $EXPECTED_JOBS offres ignoré tant que l'import (#17) n'est pas livré"
elif [[ "$jobs" != "$EXPECTED_JOBS" ]]; then
  fail T5 "$jobs offres en base, $EXPECTED_JOBS attendues"
else
  echo "     $jobs offres en base"
fi

echo "[OK] T1 à T5 validés"
