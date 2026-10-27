#!/usr/bin/env bash
# Produit le compose d'un environnement du VPS à partir du gabarit.
# Usage : deploy/render.sh staging|prod > compose.<env>.yaml
set -euo pipefail
env=${1:-}
[[ "$env" == staging || "$env" == prod ]] || { echo "usage: $0 staging|prod" >&2; exit 1; }
sed "/^#/!s/__ENV__/$env/g" "$(dirname "$0")/compose.vps.yaml"
