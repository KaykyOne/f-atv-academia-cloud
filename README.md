# AcademiaCloud: projeto integrado (Docker + Computação em Nuvem)

Esta é a base AcademiaCloud com as contribuições dos **seis grupos** do seminário já implementadas e funcionando juntas:

| Grupo | Tema | O que foi implementado | Documento |
|---|---|---|---|
| 1 | Imagens | Dockerfile multi-stage com estágio de testes, usuário não root, cache de camadas e comparação com a imagem original | [docs/GRUPO1_IMAGENS.md](docs/GRUPO1_IMAGENS.md) |
| 2 | Serviços e redes | Compose com 8 serviços, DNS interno, outbox transacional, publicador e serviço de notificações idempotente | [docs/GRUPO2_SERVICOS.md](docs/GRUPO2_SERVICOS.md) |
| 3 | Segurança | Login com perfis (admin, secretaria e professor), contas do banco com menor privilégio, Docker secrets, auditoria, bloqueio de força bruta e cabeçalhos de segurança | [docs/GRUPO3_SEGURANCA.md](docs/GRUPO3_SEGURANCA.md) |
| 4 | Escalabilidade | 2 réplicas atrás de um balanceador Nginx, failover demonstrável e manifests Kubernetes | [docs/GRUPO4_ESCALABILIDADE.md](docs/GRUPO4_ESCALABILIDADE.md) |
| 5 | Backup e recuperação | Volume nomeado, backup automático com retenção e SHA-256, e teste de restauração isolado com medição do RTO | [docs/GRUPO5_BACKUP.md](docs/GRUPO5_BACKUP.md) |
| 6 | Diagnóstico e custos | Script de diagnóstico, limites de CPU e memória, retenção de logs, auditoria e modelo de custos e governança | [docs/GRUPO6_DIAGNOSTICO_CUSTOS.md](docs/GRUPO6_DIAGNOSTICO_CUSTOS.md) |

Arquitetura e diagramas: [docs/ARQUITETURA.md](docs/ARQUITETURA.md). Validação executada: [docs/VALIDACAO.md](docs/VALIDACAO.md).

```
navegador ──► lb (Nginx :8080) ──► web ×2 ──────────► db (PostgreSQL 17, volume dados_postgres)
                                     │ outbox            ▲          ▲
                                     ▼                   │          │
                                publicador ──► notificacoes         │
                                backup (pg_dump periódico) ─────────┴──► ./backups
```

## 1. Executar

Pré-requisitos: Docker Engine ou Docker Desktop, e Docker Compose v2.

**1) Criar o `.env` com senhas aleatórias:**

Linux, macOS ou WSL:
```sh
sh scripts/gerar-env.sh
```
Windows PowerShell (copie e edite manualmente, trocando **todas** as senhas):
```powershell
Copy-Item .env.example .env
notepad .env
```

**2) Subir:**
```sh
docker compose up -d --build
docker compose ps -a
```
Resultado esperado: `db`, `web-1`, `web-2`, `lb`, `notificacoes` e `publicador` ficam *healthy*, `backup` fica *Up*, e `init` termina com **`Exited (0)`**, que é o comportamento normal.

**3) Acessar http://localhost:8080** e entrar com um dos usuários abaixo. As senhas são as definidas no `.env`.

| Usuário | Perfil | Pode |
|---|---|---|
| `admin` | administrador | Tudo, além dos painéis de eventos, notificações e auditoria |
| `secretaria` | secretaria | Cadastrar e excluir alunos e matrículas |
| `professor` | professor | Cadastrar disciplinas e consultar tudo (com o e-mail dos alunos mascarado) |

**Parar sem perder dados:** `docker compose down`. **Nunca** use `docker compose down -v`, porque esse comando apaga o volume do banco.

## 2. Interface (frontend)

SPA em **React + TypeScript + Tailwind v4 + shadcn/ui** (componentes Radix), em [frontend/](frontend/):

| Rota | Página | Perfil |
|---|---|---|
| `/login` | Login | público |
| `/` | Visão geral: contadores, matrículas recentes e réplica que respondeu | todos |
| `/alunos`, `/disciplinas`, `/matriculas` | Tabela com busca, modal de cadastro e confirmação de exclusão | todos (cadastro conforme o perfil) |
| `/admin/eventos` | Outbox: status, tentativas e botão Reenviar (atualiza a cada 3 s) | admin |
| `/admin/notificacoes` | Notificações simuladas | admin |
| `/admin/auditoria` | Trilha de auditoria com filtro por resultado | admin |

Sidebar com navegação filtrada por perfil, menu lateral (*sheet*) no celular, menu do usuário, toasts (Sonner) e skeletons de carregamento. O build roda no estágio `frontend` do Dockerfile (Node 22), e só os arquivos estáticos vão para a imagem final, servidos pelo Flask na mesma origem da API (sem CORS). O Flask devolve o `index.html` para qualquer rota fora de `/api` e `/health`.

Desenvolvimento com hot reload (com o stack Docker rodando):
```sh
cd frontend && npm install && npm run dev     # http://localhost:5173, que redireciona /api para :8080
```
Para adicionar componentes: `npx shadcn@latest add <componente>` (configuração em `frontend/components.json`).

## 3. Roteiros de demonstração (um por grupo)

Os scripts são em bash (Linux, macOS, WSL ou Git Bash). Os comandos equivalentes para PowerShell estão no documento de cada grupo.

| Script | Grupo | O que mostra |
|---|---|---|
| `bash scripts/demo-eventos.sh` | 2 | Consumidor fora do ar, evento pendente, recuperação e idempotência |
| `bash scripts/demo-seguranca.sh` | 3 | Processo não root, secrets, menor privilégio no banco, perfis, força bruta e cabeçalhos |
| `bash scripts/demo-balanceamento.sh` | 4 | Alternância entre réplicas, queda e retorno de uma réplica, e banco fora (503 não mascarado) |
| `bash scripts/backup-agora.sh` | 5 | Backup imediato com conferência de SHA-256 |
| `bash scripts/teste-restauracao.sh` | 5 | Restauração em uma cópia isolada (porta 8090) com medição do tempo |
| `bash scripts/diagnostico.sh` | 6 | Estado, CPU e memória, limites, saúde, erro 400 no log e fila de eventos (salvos em `evidencias/`) |

## 4. API

| Método | Rota | Acesso |
|---|---|---|
| GET | `/health/live`, `/health/ready` | público |
| GET | `/api/resumo` (contadores + instância que respondeu) | público |
| POST | `/api/login`, `/api/logout` · GET `/api/me` | — |
| GET | `/api/alunos`, `/api/disciplinas`, `/api/matriculas` | usuário logado |
| POST / DELETE | `/api/alunos[/id]`, `/api/matriculas[/id]` | admin, secretaria |
| POST / DELETE | `/api/disciplinas[/id]` | admin, professor |
| GET | `/api/eventos`, `/api/notificacoes`, `/api/auditoria` | admin |
| POST | `/api/eventos/{id}/reprocessar` | admin |

Requisições POST e DELETE exigem `Content-Type: application/json` (proteção CSRF). Exemplo com curl:
```sh
curl -c c.txt -H 'Content-Type: application/json' -d '{"usuario":"admin","senha":"SENHA_DO_ENV"}' http://localhost:8080/api/login
curl -b c.txt http://localhost:8080/api/alunos
```
Códigos de status: 201 criado · 204 excluído · 400 validação · 401 sem login · 403 sem permissão · 404 inexistente · 409 duplicado ou vinculado · 415 sem JSON · 429 bloqueado · 503 banco indisponível.

## 5. Configuração (`.env`)

| Variável | Uso |
|---|---|
| `POSTGRES_ADMIN_USER/PASSWORD` | Conta administrativa do banco, usada **só** pelos serviços `init` e `backup` |
| `APP_DB_USER/PASSWORD` | Conta da aplicação: somente DML, sem DDL |
| `NOTIF_DB_USER/PASSWORD` | Conta do serviço de notificações: só acessa o schema `notificacoes` |
| `SECRET_KEY` | Assina o cookie de sessão. Deve ser igual em todas as réplicas |
| `ADMIN/SECRETARIA/PROFESSOR_PASSWORD` | Senhas iniciais dos usuários, aplicadas só na primeira inicialização |
| `APP_PORT` (8080) · `WEB_REPLICAS` (2) | Porta do balanceador e número de réplicas |
| `BACKUP_INTERVAL_SECONDS` (86400) · `BACKUP_RETENTION` (14) | Frequência e quantidade de backups mantidos |
| `BACKUP_UID/GID` | Dono dos arquivos criados em `./backups` |
| `PGADMIN_*` | pgAdmin opcional: `docker compose --profile admin up -d` |

As senhas chegam aos containers como **Docker secrets** (arquivos em `/run/secrets`), e não como variáveis de ambiente. Assim, aceitam qualquer caractere, porque a URL de conexão é montada com codificação.

**pgAdmin:** abra http://localhost:5050 e registre um servidor com host `db`, porta `5432`, usuário `POSTGRES_ADMIN_USER` e a senha correspondente.

## 6. Testes automatizados

Os testes rodam dentro do estágio `test` do Dockerfile, com Python 3.12 e SQLite temporário:
```sh
docker build --target test -t academia-cloud:test .
```
São 8 testes, cobrindo o fluxo original, validações, saúde e seed, autenticação, a matriz de permissões, CSRF, força bruta, outbox, consumidor fora do ar e idempotência.

## 7. Diagnóstico rápido

```sh
docker compose ps -a
docker compose logs -f web            # Ctrl+C sai sem parar nada
docker compose logs init publicador notificacoes backup lb
docker stats
```

| Problema | Causa provável e solução |
|---|---|
| `Crie o arquivo .env` | O `.env` não existe ou foi salvo como `.env.txt` |
| `init` com Exited (1) | Veja `docker compose logs init db`. Senhas trocadas após o banco já existir não alteram a conta administrativa |
| 502 ou 504 logo após subir | As réplicas ainda estão iniciando; aguarde o estado *healthy* |
| Porta 8080 ocupada | Altere `APP_PORT` no `.env` e rode `docker compose up -d` |
| `./backups` com permissão negada (Linux) | Ajuste `BACKUP_UID/GID` para a saída de `id -u` e `id -g` |

## 8. Limites (o que é proposta e não está implementado)

- Não há TLS (HTTPS) local. O cookie `Secure` depende de `COOKIE_SECURE=true` atrás de HTTPS, que está previsto no Ingress do Kubernetes.
- O banco é um único container, portanto continua sendo **ponto único de falha**. Réplicas web não resolvem isso; veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md).
- Tudo roda em um único host: não há alta disponibilidade de host, de zona ou de região.
- A cópia dos backups para fora do computador (outra região) está documentada como procedimento, mas não é automática.
- O Kubernetes está na forma de manifests revisados e **não foi executado em cluster**.
- Não há métricas históricas nem alertas automáticos: o endpoint de saúde não é monitoramento completo.
- Não há tela de gestão de usuários; as senhas iniciais vêm do `.env`.
- Use somente dados fictícios.
