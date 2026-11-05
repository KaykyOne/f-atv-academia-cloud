#!/usr/bin/env bash
# Grupo 5: restaura um backup em uma CÓPIA ISOLADA do AcademiaCloud e mede o tempo (RTO do ensaio).
# O ambiente principal (projeto academia-cloud) NÃO é tocado.
# Uso: bash scripts/teste-restauracao.sh [backups/academia_XXXX.sql.gz]
. "$(dirname "$0")/_comum.sh"
LAB=academia-lab
export APP_PORT=${LAB_PORT:-8090}
LAB_URL="http://localhost:$APP_PORT"
ARQ=${1:-$(ls -1t backups/academia_*.sql.gz 2>/dev/null | head -1)}
[ -f "$ARQ" ] || { echo "Nenhum backup encontrado. Rode: bash scripts/backup-agora.sh"; exit 1; }
dc() { docker compose -p "$LAB" "$@"; }
esperar_ready() { for _ in $(seq 1 90); do [ "$(curl -s -o /dev/null -w '%{http_code}' "$LAB_URL/health/ready")" = 200 ] && return 0; sleep 1; done; return 1; }

titulo "0. Conferindo integridade do backup $ARQ"
(cd "$(dirname "$ARQ")" && sha256sum -c "$(basename "$ARQ").sha256")

titulo "1. Subindo ambiente de laboratório isolado (projeto $LAB, porta $APP_PORT, volume próprio)"
passo "docker compose -p $LAB up -d --scale backup=0"
dc up -d --build --scale backup=0 >/dev/null 2>&1
esperar_ready || { echo "laboratório não ficou pronto"; dc ps -a; exit 1; }
echo "Antes da restauração (banco do laboratório só com dados iniciais):"; curl -s "$LAB_URL/api/resumo"; echo

titulo "2. Restaurando (cronômetro iniciado)"
INICIO=$(date +%s.%N)
passo "docker compose -p $LAB stop web publicador notificacoes"
dc stop web publicador notificacoes >/dev/null 2>&1
passo "gzip -dc $ARQ | docker compose -p $LAB exec -T db psql -v ON_ERROR_STOP=1 ..."
gzip -dc "$ARQ" | dc exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
passo "docker compose -p $LAB run --rm init   (reaplica contas e permissões)"
dc run --rm init >/dev/null 2>&1
passo "docker compose -p $LAB start web publicador notificacoes"
dc start web publicador notificacoes >/dev/null 2>&1
esperar_ready
FIM=$(date +%s.%N)
RTO=$(python3 -c "print(f'{$FIM-$INICIO:.1f}')")

titulo "3. Conferência dos dados restaurados"
RES_LAB=$(curl -s "$LAB_URL/api/resumo")
echo "Laboratório restaurado: $RES_LAB"
echo "Ambiente principal:     $(curl -s "$URL/api/resumo" || echo indisponível)"
URL_SALVA=$URL; URL=$LAB_URL
login admin "$ADMIN_PASSWORD"   # os usuários também foram restaurados do backup
echo "Alunos no laboratório:"; api "$LAB_URL/api/alunos" | python3 -c 'import sys,json; [print("  -", a["nome"]) for a in json.load(sys.stdin)]'
echo "Matrículas no laboratório:"; api "$LAB_URL/api/matriculas" | python3 -c 'import sys,json; [print("  -", m["aluno"], "->", m["disciplina"]) for m in json.load(sys.stdin)]'
URL=$URL_SALVA

titulo "4. Resultado"
echo "Tempo entre iniciar a restauração e a aplicação voltar a responder: ${RTO}s"
mkdir -p evidencias
REL="evidencias/restauracao_$(date +%Y%m%dT%H%M%S).txt"
{ echo "Teste de restauração AcademiaCloud - $(date -Iseconds)"; echo "Backup: $ARQ";
  echo "Tamanho: $(wc -c < "$ARQ") bytes"; echo "Resumo restaurado: $RES_LAB"; echo "Tempo de restauração (RTO do ensaio): ${RTO}s"; } > "$REL"
echo "Relatório salvo em $REL"
echo
echo "Para acessar: $LAB_URL   |   Para remover o laboratório (apaga SÓ o volume do laboratório):"
echo "  docker compose -p $LAB down -v"
