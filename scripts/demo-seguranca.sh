#!/usr/bin/env bash
# Grupo 3: menor privilégio no banco, perfis na aplicação, secrets e usuário não root.
. "$(dirname "$0")/_comum.sh"
q() { docker compose exec -T db sh -c "PGPASSWORD=\"\$1\" psql -h localhost -U \"\$2\" -d \"\$POSTGRES_DB\" -tAc \"\$3\"" _ "$1" "$2" "$3" 2>&1 | head -1 || true; }

titulo "1. Processo da aplicação roda sem root"
passo "docker compose exec web id"; docker compose exec -T web id
titulo "2. Senhas chegam como arquivos (Docker secrets), não como variáveis"
passo "docker compose exec web ls -l /run/secrets"; docker compose exec -T web ls -l /run/secrets
passo "docker compose exec web env | grep -i pass"; docker compose exec -T web env | grep -i pass || echo "(nenhuma senha nas variáveis de ambiente)"
titulo "3. Conta da aplicação ($APP_DB_USER) tem menor privilégio"
passo "SELECT count(*) FROM alunos";   q "$APP_DB_PASSWORD" "$APP_DB_USER" "SELECT count(*) FROM alunos"
passo "DROP TABLE alunos";             q "$APP_DB_PASSWORD" "$APP_DB_USER" "DROP TABLE alunos"
passo "UPDATE usuarios SET perfil='administrador'"; q "$APP_DB_PASSWORD" "$APP_DB_USER" "UPDATE usuarios SET perfil='administrador'"
passo "SELECT * FROM notificacoes.notificacoes"; q "$APP_DB_PASSWORD" "$APP_DB_USER" "SELECT count(*) FROM notificacoes.notificacoes"
titulo "4. Conta das notificações ($NOTIF_DB_USER) só vê o próprio schema"
passo "SELECT count(*) FROM alunos"; q "$NOTIF_DB_PASSWORD" "$NOTIF_DB_USER" "SELECT count(*) FROM alunos"
titulo "5. Autorização por perfil na API"
passo "GET /api/alunos sem login"; curl -s -w '  HTTP %{http_code}\n' "$URL/api/alunos"
login professor "$PROFESSOR_PASSWORD"
passo "professor: POST /api/alunos"; api -w '  HTTP %{http_code}\n' -d '{"nome":"Teste","email":"t@example.test"}' "$URL/api/alunos"
passo "professor: GET /api/alunos (e-mail mascarado)"; api "$URL/api/alunos" | head -c 160; echo
passo "professor: GET /api/auditoria"; api -w '  HTTP %{http_code}\n' "$URL/api/auditoria"
titulo "6. Proteção contra força bruta (bloqueio após 5 falhas em 5 min)"
for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "tentativa $i: HTTP %{http_code}\n" -H "$JSON" -d '{"usuario":"teste_bloqueio","senha":"errada"}' "$URL/api/login"; done
titulo "7. Cabeçalhos de segurança"
curl -sI "$URL/" | grep -iE 'content-security|x-frame|x-content-type|referrer|set-cookie|server:'
