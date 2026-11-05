# Grupo 5: Persistência, backup e recuperação de desastres

**Integrantes:** Gabriel, Yasmin e Enzo
**Pergunta central:** quanto dado pode ser perdido, e em quanto tempo o serviço deve voltar?

Este documento segue o checklist de `grupo_5_atividades_no_academiacloud.md`.

## 1. Onde os dados ficam (item 2 do roteiro)

Em [compose.yaml](../compose.yaml), no serviço `db`:
```yaml
volumes: [dados_postgres:/var/lib/postgresql/data]   # volume NOMEADO
...
volumes:
  dados_postgres:
```
É um **named volume** gerenciado pelo Docker (`docker volume ls` mostra `academia-cloud_dados_postgres`), e não um bind mount. Ele existe independentemente do container: `docker compose down` remove o container, mas mantém o volume.

Os backups, ao contrário, usam um **bind mount** (`./backups:/backups`), para que os arquivos fiquem em uma pasta comum do computador, **fora** do volume do banco.

## 2. Teste de persistência (item 3)

```sh
docker compose down          # SEM -v
docker compose up -d
```
Resultado real (05/11/2026):
```
ANTES:  {"alunos":4,"disciplinas":2,"matriculas":2,"instancia":"eb47152bbb1b"}
$ docker compose down   ->  containers e rede removidos; volume academia-cloud_dados_postgres mantido
$ docker compose up -d
DEPOIS: {"alunos":4,"disciplinas":2,"matriculas":2,"instancia":"8445479e48ff"}
```
A instância mudou (containers novos), mas os dados, incluindo o aluno "ALUNO TESTE GRUPO 5" e a matrícula dele, continuaram lá.

## 3. Backup (item 4)

**Automático:** o serviço `backup` executa [infra/backup/backup.sh](../infra/backup/backup.sh) ao subir e depois a cada `BACKUP_INTERVAL_SECONDS` (padrão: 24 h). A cada execução, o script:
1. roda `pg_dump --clean --if-exists --no-owner`, que gera um **backup lógico consistente** mesmo com o banco em uso;
2. compacta (`.sql.gz`), verifica com `gzip -t` e grava primeiro em um arquivo `.parcial`, para que um backup interrompido nunca pareça válido;
3. nomeia o arquivo com data e hora UTC (`academia_20261105T174851Z.sql.gz`) e cria um `.sha256`;
4. mantém os `BACKUP_RETENTION` arquivos mais recentes (padrão: 14) e apaga os mais antigos.

**Manual:**
```sh
bash scripts/backup-agora.sh
# ou, em qualquer sistema:
docker compose exec backup /bin/sh /scripts/backup.sh --uma-vez
```
Saída real:
```
academia_20261105T174851Z.sql.gz: SUCESSO          <- SHA-256 conferido
Tabelas com dados no backup:
  notificacoes.notificacoes  public.alunos  public.auditoria  public.disciplinas
  public.eventos  public.matriculas  public.usuarios
```

Equivalente ao comando do roteiro (PowerShell), em SQL puro:
```powershell
New-Item -ItemType Directory -Force -Path .\backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' > .\backups\academia-backup.sql
```

**Por que não copiar a pasta do volume?** Copiar `/var/lib/postgresql/data` com o PostgreSQL rodando pode gerar arquivos inconsistentes, porque o banco escreve em vários arquivos ao mesmo tempo. O `pg_dump` lê uma fotografia transacional consistente.

## 4. Restauração em ambiente isolado (item 5)

```sh
bash scripts/teste-restauracao.sh                       # usa o backup mais recente
bash scripts/teste-restauracao.sh backups/academia_X.sql.gz
```
O script sobe uma **segunda cópia** do AcademiaCloud com outro nome de projeto (`-p academia-lab`), outro volume e a porta 8090, **sem tocar no banco principal**. Em seguida:

1. confere o SHA-256 do backup;
2. inicia o cronômetro;
3. para `web`, `publicador` e `notificacoes` do laboratório;
4. restaura com `psql -v ON_ERROR_STOP=1`;
5. roda o `init` de novo para reaplicar contas e permissões;
6. reinicia os serviços e espera `/health/ready` responder 200;
7. para o cronômetro, compara os dados e salva o relatório em `evidencias/`.

Resultado real (05/11/2026):
```
Antes da restauração (laboratório): {"alunos":2,"disciplinas":2,"matriculas":0}
Laboratório restaurado:             {"alunos":4,"disciplinas":2,"matriculas":2}
Ambiente principal:                 {"alunos":4,"disciplinas":2,"matriculas":2}
Alunos no laboratório: Ana Exemplo, Bruno Exemplo, ALUNO TESTE GRUPO 5, Aluno Evento 10879
Matrículas: ALUNO TESTE GRUPO 5 -> Docker ; Aluno Evento 10879 -> Docker
Tempo entre iniciar a restauração e a aplicação voltar a responder: 18.7s
```
Remover o laboratório depois (apaga **apenas** o volume `academia-lab_dados_postgres`):
```sh
docker compose -p academia-lab down -v
```

Restaurar no **ambiente principal** (só com orientação do professor, porque substitui os dados):
```sh
docker compose stop web publicador notificacoes
gzip -dc backups/academia_X.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose run --rm init
docker compose start web publicador notificacoes
```

## 5. Análise de falhas (item 6)

| Cenário | O que acontece | Como recuperar |
|---|---|---|
| Container `db` removido, volume intacto | Nada se perde. `docker compose up -d` cria um container novo que usa o mesmo volume | Automático (testado no item 2) |
| Volume perdido ou corrompido (ou `down -v`) | O banco volta **vazio**: o `init` recria só os dados fictícios | Restaurar o último backup. Perde-se tudo que foi criado depois dele (RPO) |
| Erro lógico (exclusão indevida) | O volume guarda o erro fielmente | Restaurar o backup em laboratório e copiar os registros necessários |
| Computador com defeito | Volume **e** `./backups` são perdidos juntos | Só é possível se houver cópia **externa** do backup (veja o item 7) |

## 6. RPO e RTO

- **RPO** (*Recovery Point Objective*): quanto dado se aceita perder, medido em tempo.
- **RTO** (*Recovery Time Objective*): em quanto tempo o serviço precisa voltar.

| | Configuração atual | Meta proposta (didática) |
|---|---|---|
| RPO | Até **24 h** (1 backup por dia) | **1 h**: `BACKUP_INTERVAL_SECONDS=3600`, ou PITR com WAL em nuvem |
| RTO | **18,7 s** medidos (banco pequeno, mesmo computador, imagem já baixada) | **1 h** para reconstruir em outro computador ou região, incluindo baixar imagens e copiar o backup |

O RTO medido vale **só** para este ensaio. Com mais dados, em outro computador ou com download das imagens, o tempo será maior. Por isso a meta é bem mais folgada do que a medida.

## 7. Melhorias avaliadas (item 7)

| Melhoria | Situação |
|---|---|
| Backups frequentes | ✅ Implementado e testado (serviço `backup`, intervalo configurável) |
| Histórico com data e hora | ✅ Implementado (nome em UTC + retenção de N arquivos) |
| Integridade verificável | ✅ Implementado (`gzip -t` + SHA-256) |
| Teste de restauração | ✅ Implementado e testado (`teste-restauracao.sh`, com relatório) |
| Recuperação em outro ambiente | ✅ Documentado e testado (projeto isolado `academia-lab`) |
| Cópia externa | ⚠️ Procedimento manual: copiar `backups/*.sql.gz` e `.sha256` para um disco externo ou nuvem (ex.: `rclone copy backups remoto:academia-backups`). **Não automatizado** |
| Proteção dos arquivos | ⚠️ `./backups` está no `.gitignore` e no `.dockerignore`. O backup contém hashes de senha e e-mails: em nuvem, usar bucket privado, criptografado e com versionamento ou bloqueio contra exclusão |

## 8. Em nuvem (proposta)

- **Snapshots** de disco ou do banco gerenciado: restauração rápida, mas ficam na mesma conta e, muitas vezes, na mesma região.
- **PITR** (*point-in-time recovery*, via WAL): reduz o RPO para minutos.
- **Replicação para outra zona:** é alta disponibilidade, **não** backup, porque também replica erros.
- **Cópia do backup para outra região**, com retenção e bloqueio contra exclusão (proteção contra ransomware e contra exclusão acidental).
- **CronJob** de backup no Kubernetes: [k8s/06-backup-cronjob.yaml](../k8s/06-backup-cronjob.yaml).

## 9. Checklist (item 8)

- [x] Aplicação iniciando normalmente
- [x] Volume do PostgreSQL localizado no `compose.yaml`
- [x] Persistência testada após `down` / `up -d`
- [x] Backup `.sql.gz` gerado com `pg_dump`
- [x] Backup conferido (SHA-256) e guardado fora do volume (`./backups`)
- [x] Restauração realizada em ambiente isolado
- [x] Registros conferidos depois da restauração
- [x] Tempo de recuperação registrado (18,7 s no ensaio)
- [x] Melhorias de armazenamento e rotina avaliadas

## Referências
- PostgreSQL 17. *Backup and Restore: SQL Dump*. https://www.postgresql.org/docs/17/backup-dump.html
- PostgreSQL 17. *pg_dump*. https://www.postgresql.org/docs/17/app-pgdump.html
- Docker. *Volumes*. https://docs.docker.com/engine/storage/volumes/
- Docker. *Bind mounts*. https://docs.docker.com/engine/storage/bind-mounts/
