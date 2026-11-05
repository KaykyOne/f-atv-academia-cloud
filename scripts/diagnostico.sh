#!/usr/bin/env bash
# Grupo 6: coleta evidências de diagnóstico em evidencias/diagnostico_<data>.txt
. "$(dirname "$0")/_comum.sh"
mkdir -p evidencias
SAIDA="evidencias/diagnostico_$(date +%Y%m%dT%H%M%S).txt"
exec > >(tee "$SAIDA") 2>&1
titulo "Estado dos serviços"; passo "docker compose ps -a"; docker compose ps -a --format 'table {{.Service}}\t{{.Name}}\t{{.Status}}'
titulo "Consumo de CPU e memória"; passo "docker stats --no-stream"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}' $(docker compose ps -q)
titulo "Limites configurados (FinOps: dimensionamento)"
for c in $(docker compose ps -q); do docker inspect -f '{{.Name}}  cpus={{.HostConfig.NanoCpus}}  mem={{.HostConfig.Memory}}  restart={{.HostConfig.RestartPolicy.Name}}' "$c"; done | sed 's#^/##'
titulo "Saúde"
for p in /lb/health /health/live /health/ready; do printf '%-15s ' "$p"; curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$URL$p"; done
titulo "Requisição inválida (deve gerar HTTP 400 e aparecer no log)"
login admin "$ADMIN_PASSWORD"
passo "POST /api/alunos {}"; api -w '  HTTP %{http_code}\n' -d '{}' "$URL/api/alunos"
sleep 1
passo "docker compose logs --tail 200 web | grep status=400"; docker compose logs --tail 200 web | grep 'status=400' | tail -2
titulo "Fila de eventos (outbox)"
api "$URL/api/eventos" | python3 -c 'import sys,json,collections; print(dict(collections.Counter(e["status"] for e in json.load(sys.stdin))))'
titulo "Backups disponíveis"; ls -lh backups/ | tail -5
titulo "Volumes do projeto"; docker volume ls --filter name=academia-cloud
titulo "Últimos erros/avisos"; docker compose logs --tail 300 2>/dev/null | grep -E 'ERROR|WARNING|error' | tail -10 || echo "(nenhum)"
echo; echo "Evidência salva em $SAIDA"
