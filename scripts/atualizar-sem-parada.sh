#!/usr/bin/env bash
# Grupo 4: atualização gradual (rolling update) das réplicas web, sem indisponibilidade.
#
# `docker compose up -d --build` recria TODAS as réplicas ao mesmo tempo e deixa o
# balanceador alguns segundos sem nenhuma réplica viva (respostas 502). Este script:
#   1. constrói a imagem nova;
#   2. sobe réplicas NOVAS ao lado das antigas (o dobro do total);
#   3. espera as novas ficarem saudáveis (healthcheck /health/ready);
#   4. remove as antigas — o Nginx passa a usar só as novas (DNS relido a cada 2 s).
# É o que o Deployment do Kubernetes faz com maxSurge/maxUnavailable (k8s/04-web.yaml).
. "$(dirname "$0")/_comum.sh"
N=${WEB_REPLICAS:-2}

titulo "1. Construindo a imagem nova"
docker compose build web

ANTIGAS=$(docker compose ps -q web)
[ -n "$ANTIGAS" ] || { echo "Nenhuma réplica web em execução. Use: docker compose up -d"; exit 1; }

titulo "2. Subindo $N réplica(s) nova(s) ao lado das antigas"
passo "docker compose up -d --no-deps --no-recreate --scale web=$((N * 2)) web"
docker compose up -d --no-deps --no-recreate --scale web=$((N * 2)) web
NOVAS=$(docker compose ps -q web | grep -vxF "$ANTIGAS")

titulo "3. Aguardando as novas ficarem saudáveis"
for _ in $(seq 1 60); do
  prontas=0
  for c in $NOVAS; do [ "$(docker inspect -f '{{.State.Health.Status}}' "$c")" = healthy ] && prontas=$((prontas + 1)); done
  echo "  saudáveis: $prontas/$N"; [ "$prontas" -eq "$N" ] && break; sleep 2
done
if [ "$prontas" -ne "$N" ]; then
  echo "As réplicas novas não ficaram saudáveis: removendo-as e mantendo as antigas."
  docker rm -f $NOVAS >/dev/null; exit 1
fi
sleep 3   # dá tempo ao Nginx de descobrir os IPs novos

titulo "4. Removendo as réplicas antigas"
for c in $ANTIGAS; do
  passo "docker stop $(docker inspect -f '{{.Name}}' "$c" | tr -d /)"
  docker stop "$c" >/dev/null && docker rm "$c" >/dev/null
done
titulo "Concluído"
docker compose ps web
