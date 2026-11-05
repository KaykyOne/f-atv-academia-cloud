#!/bin/sh
# Gera um .env com senhas aleatórias (Grupo 3). Não sobrescreve um .env existente.
# Uso: sh scripts/gerar-env.sh
set -eu
cd "$(dirname "$0")/.."
if [ -f .env ]; then echo ".env já existe; nada foi alterado."; exit 1; fi
gerar() { LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "${1:-24}"; }
sed -e "s/^POSTGRES_ADMIN_PASSWORD=.*/POSTGRES_ADMIN_PASSWORD=$(gerar)/" \
    -e "s/^APP_DB_PASSWORD=.*/APP_DB_PASSWORD=$(gerar)/" \
    -e "s/^NOTIF_DB_PASSWORD=.*/NOTIF_DB_PASSWORD=$(gerar)/" \
    -e "s/^SECRET_KEY=.*/SECRET_KEY=$(gerar 48)/" \
    -e "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$(gerar 16)/" \
    -e "s/^SECRETARIA_PASSWORD=.*/SECRETARIA_PASSWORD=$(gerar 16)/" \
    -e "s/^PROFESSOR_PASSWORD=.*/PROFESSOR_PASSWORD=$(gerar 16)/" \
    -e "s/^PGADMIN_PASSWORD=.*/PGADMIN_PASSWORD=$(gerar 16)/" \
    -e "s/^BACKUP_UID=.*/BACKUP_UID=$(id -u)/" \
    -e "s/^BACKUP_GID=.*/BACKUP_GID=$(id -g)/" \
    .env.example > .env
chmod 600 .env
echo ".env criado. Senhas de login da aplicação:"
grep -E '^(ADMIN|SECRETARIA|PROFESSOR)_PASSWORD=' .env
