#!/bin/sh
# Rotina de backup lógico do AcademiaCloud (Grupo 5).
# Uso dentro do container `backup`:
#   backup.sh            -> laço: um backup a cada BACKUP_INTERVAL_SECONDS
#   backup.sh --uma-vez  -> um único backup (manual)
# Cada arquivo leva data/hora UTC, é verificado (gzip -t), recebe um SHA-256 e
# os mais antigos além de BACKUP_RETENTION são removidos.
set -eu
set -o pipefail

DESTINO=/backups
INTERVALO=${BACKUP_INTERVAL_SECONDS:-86400}
RETENCAO=${BACKUP_RETENTION:-14}
PGPASSWORD="$(cat "$PGPASSWORD_FILE")"
export PGPASSWORD

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup $*"; }

fazer_backup() {
    ts=$(date -u +%Y%m%dT%H%M%SZ)
    nome="academia_${ts}.sql.gz"
    tmp="$DESTINO/.${nome}.parcial"
    inicio=$(date +%s)
    # pg_dump gera uma cópia CONSISTENTE mesmo com o banco em uso
    # (ao contrário de copiar o diretório de dados com o PostgreSQL rodando).
    if ! pg_dump --clean --if-exists --no-owner | gzip -6 > "$tmp"; then
        rm -f "$tmp"; log "ERRO: pg_dump falhou"; return 1
    fi
    gzip -t "$tmp"
    mv "$tmp" "$DESTINO/$nome"
    (cd "$DESTINO" && sha256sum "$nome" > "$nome.sha256")
    tamanho=$(wc -c < "$DESTINO/$nome")
    log "OK arquivo=$nome bytes=$tamanho duracao_s=$(( $(date +%s) - inicio ))"
    # Retenção: mantém os N mais recentes.
    ls -1t "$DESTINO"/academia_*.sql.gz 2>/dev/null | tail -n +$((RETENCAO + 1)) | while read -r antigo; do
        rm -f "$antigo" "$antigo.sha256"; log "retencao removeu $(basename "$antigo")"
    done
}

until pg_isready -q; do log "aguardando banco"; sleep 2; done

if [ "${1:-}" = "--uma-vez" ]; then
    fazer_backup
    exit $?
fi

log "rotina iniciada intervalo_s=$INTERVALO retencao=$RETENCAO"
while true; do
    fazer_backup || log "nova tentativa no próximo ciclo"
    sleep "$INTERVALO"
done
