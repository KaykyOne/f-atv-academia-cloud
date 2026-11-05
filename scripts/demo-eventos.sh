#!/usr/bin/env bash
# Grupo 2: outbox transacional, entrega confiável e consumidor idempotente.
. "$(dirname "$0")/_comum.sh"
ultimo() { api "$URL/api/eventos" | python3 -c 'import sys,json; e=json.load(sys.stdin)[0]; print(e["id"], e["status"], "tentativas="+str(e["tentativas"]), e["ultimo_erro"] or "")'; }
login admin "$ADMIN_PASSWORD"
SUF=$RANDOM
AID=$(api -d "{\"nome\":\"Aluno Evento $SUF\",\"email\":\"evento$SUF@example.test\"}" "$URL/api/alunos" | sed -E 's/.*"id":([0-9]+).*/\1/')

titulo "1. Consumidor (notificacoes) fora do ar"
passo "docker compose stop notificacoes"; docker compose stop notificacoes >/dev/null 2>&1
titulo "2. Matrícula confirmada mesmo assim (a resposta não espera a notificação)"
api -w '  HTTP %{http_code}\n' -d "{\"aluno_id\":$AID,\"disciplina_id\":1}" "$URL/api/matriculas"
sleep 9; passo "último evento"; ultimo
echo "-> evento continua 'pendente' na outbox; o publicador tenta de novo com espera exponencial."
docker compose logs --tail 2 publicador
titulo "3. Matrícula duplicada é rejeitada e NÃO gera evento"
api -w '  HTTP %{http_code}\n' -d "{\"aluno_id\":$AID,\"disciplina_id\":1}" "$URL/api/matriculas"
titulo "4. Consumidor volta"
passo "docker compose start notificacoes"; docker compose start notificacoes >/dev/null 2>&1
echo "aguardando próxima tentativa..."; for _ in $(seq 1 20); do sleep 2; ultimo | grep -q entregue && break; done
ultimo
EV=$(ultimo | cut -d' ' -f1)
titulo "5. Reenvio do MESMO evento (idempotência)"
api -w '  HTTP %{http_code}\n' -X POST -d '{}' "$URL/api/eventos/$EV/reprocessar"
sleep 4
docker compose logs --tail 3 notificacoes | grep -E "duplicado|SIMULADA" || true
passo "notificações deste evento"; api "$URL/api/notificacoes" | python3 -c "import sys,json; print(sum(1 for n in json.load(sys.stdin) if n['evento_id']=='$EV'))"
