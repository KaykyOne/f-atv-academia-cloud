# Funções compartilhadas pelos scripts de demonstração (bash).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Crie o .env primeiro (sh scripts/gerar-env.sh)"; exit 1; }
set -a; . ./.env; set +a
URL="http://localhost:${APP_PORT:-8080}"
JSON='Content-Type: application/json'
COOKIES="$(mktemp)"; trap 'rm -f "$COOKIES"' EXIT
titulo() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
passo()  { printf '\033[0;33m$ %s\033[0m\n' "$*"; }
login()  { # login <usuario> <senha>
  curl -s -c "$COOKIES" -H "$JSON" -d "{\"usuario\":\"$1\",\"senha\":\"$2\"}" "$URL/api/login" >/dev/null; }
api()    { curl -s -b "$COOKIES" -H "$JSON" "$@"; }
instancia() { curl -s "$URL/api/resumo" | sed -E 's/.*"instancia":"([^"]+)".*/\1/'; }
