#!/usr/bin/env bash
# Grupo 5: gera um backup imediato (além da rotina automática do serviço `backup`).
. "$(dirname "$0")/_comum.sh"
passo "docker compose exec backup /bin/sh /scripts/backup.sh --uma-vez"
docker compose exec -T backup /bin/sh /scripts/backup.sh --uma-vez
ULTIMO=$(ls -1t backups/academia_*.sql.gz | head -1)
titulo "Conferência do arquivo"
ls -l "$ULTIMO"
(cd backups && sha256sum -c "$(basename "$ULTIMO").sha256")
echo "Tabelas com dados no backup:"; gzip -dc "$ULTIMO" | grep -E '^COPY ' | sed -E 's/^COPY ([^ ]+).*/  \1/'
