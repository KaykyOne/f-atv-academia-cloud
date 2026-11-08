#!/usr/bin/env bash
# Grupo 4: duas réplicas atrás do Nginx, falha de uma instância e recuperação.
. "$(dirname "$0")/_comum.sh"
CORPO="$(mktemp)"
contar() { # UMA requisição por vez: status HTTP / réplica que respondeu / tempo
  for _ in $(seq 1 "${1:-10}"); do
    info=$(curl -s -m 20 -o "$CORPO" -w '%{http_code} %{time_total}s' "$URL/api/resumo")
    inst=$(grep -o '"instancia":"[^"]*"' "$CORPO" | cut -d'"' -f4)
    echo "  ${info%% *}  ${inst:-(erro do balanceador)}  ${info##* }"
  done; }

titulo "1. Réplicas em execução"
docker compose ps web
titulo "2. Requisições a /api/resumo (status/instância que respondeu)"
contar 6
ALVO=$(docker compose ps -q web | head -1); NOME=$(docker inspect -f '{{.Name}}' "$ALVO" | tr -d /)
titulo "3. Derrubando a réplica $NOME (docker stop)"
passo "docker stop $NOME"; docker stop "$NOME" >/dev/null
contar 6
echo "-> O Nginx marca a réplica como indisponível após a falha de conexão (max_fails=1) e repete a requisição na outra (proxy_next_upstream)."
titulo "4. Restaurando a réplica"
passo "docker start $NOME"; docker start "$NOME" >/dev/null
echo "aguardando fail_timeout (10 s) + nova resolução DNS (2 s)..."; sleep 13
contar 6
titulo "5. Banco indisponível NÃO é mascarado pelo balanceador"
passo "docker compose stop db"; docker compose stop db >/dev/null 2>&1
for _ in 1 2 3 4; do curl -s -w '  HTTP %{http_code}\n' "$URL/health/ready"; done
passo "docker compose start db"; docker compose start db >/dev/null 2>&1
sleep 6; curl -s -w '  HTTP %{http_code}\n' "$URL/health/ready"
