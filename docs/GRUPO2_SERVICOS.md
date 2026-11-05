# Grupo 2: Configuração e comunicação entre serviços

**Integrantes:** Gustavo, Carlos e João Gomes
**Pergunta central:** quais partes devem permanecer na aplicação, e quais podem ser desacopladas?

Este documento segue o checklist de `Grupo_2_AcademiaCloud_Implementacao.md`.

## 1. Serviços do Compose

| Serviço | Papel | Porta |
|---|---|---|
| `db` | PostgreSQL 17 com volume `dados_postgres` | interna 5432 |
| `init` | Cria contas, tabelas e permissões e insere o seed. Termina com **código 0** | — |
| `web` ×2 | Aplicação e API | interna 8000 |
| `lb` | Nginx, a única entrada HTTP | `127.0.0.1:${APP_PORT}` |
| `publicador` | Lê a outbox e entrega os eventos | — |
| `notificacoes` | Consumidor do evento (simula uma FaaS) | interna 8001 |
| `backup` | `pg_dump` periódico | — |
| `pgadmin` | Opcional (perfil `admin`) | `127.0.0.1:${PGADMIN_PORT}` |

Ordem de inicialização com `depends_on`: `db` *healthy* → `init` *completed_successfully* → `web`, `publicador` e `notificacoes` → `lb` (espera `web` *healthy*).

## 2. Rede e DNS interno

Todos estão na rede `academia` (driver `bridge`). Os nomes dos serviços viram nomes DNS. Evidência real:
```
$ docker compose exec web python -c "import socket; ..."
db -> 172.25.0.2
web -> ['172.25.0.6', '172.25.0.7']      <- um nome, duas réplicas
notificacoes -> 172.25.0.5
$ docker network inspect academia-cloud_academia
bridge 172.25.0.0/16
```
Nenhum IP fica fixo no código. A conexão é montada a partir de `DB_HOST=db` e `DB_PORT=5432` ([app/config.py](../app/config.py)). Os containers web foram recriados durante os testes, ganharam IPs novos e tudo continuou funcionando, inclusive o Nginx, que refaz a resolução DNS a cada 5 s.

## 3. Configuração por ambiente

- **Imagem**: igual em todo ambiente. **Container**: recebe a configuração em tempo de execução (`environment`, `secrets`).
- O `.env` alimenta o Compose. As senhas viram secrets (veja o Grupo 3).
- As portas são configuráveis (`APP_PORT` e `PGADMIN_PORT`) sem mudar o código.

## 4. Notificação desacoplada (outbox transacional)

**Problema:** se a matrícula for gravada e a notificação for enviada logo depois, dentro da mesma requisição, uma queda entre os dois passos perde a notificação. E se o serviço de notificação estiver fora do ar, a matrícula falha à toa.

**Solução implementada:**
1. Em `POST /api/matriculas`, a matrícula **e** o evento `MatriculaCriada` são gravados na **mesma transação** (tabela `eventos`, status `pendente`). Se a matrícula for rejeitada (por duplicidade), o rollback descarta também o evento.
2. O `publicador` ([app/publicador.py](../app/publicador.py)) lê os eventos pendentes a cada 2 s, com `FOR UPDATE SKIP LOCKED`, e faz `POST http://notificacoes:8001/events` com o contrato JSON.
3. Em caso de falha, ele soma 1 em `tentativas`, espera `2^n` segundos (até 300) e, depois de 8 tentativas, marca o evento como `falho`. O administrador pode reprocessar.
4. O `notificacoes` ([app/notificacoes.py](../app/notificacoes.py)) grava a notificação **simulada** com `evento_id UNIQUE`. Se o mesmo evento chegar de novo, responde `200 duplicado` sem criar outra notificação.

Contrato do evento:
```json
{"evento_id": "076ad22a-...", "tipo": "MatriculaCriada",
 "dados": {"matricula_id": 3, "aluno_id": 4, "aluno": "Aluno Evento", "aluno_email": "...",
           "disciplina_id": 1, "disciplina": "Docker", "ocorrido_em": "2026-11-05T17:45:00+00:00"}}
```

## 5. Demonstração

```sh
bash scripts/demo-eventos.sh
```
Saída real (05/11/2026):
```
1. docker compose stop notificacoes
2. POST /api/matriculas -> HTTP 201            (a matrícula não depende do consumidor)
   evento 076ad22a... pendente
3. POST /api/matriculas (duplicada) -> HTTP 409 (nenhum evento novo)
4. docker compose start notificacoes
   evento 076ad22a... entregue tentativas=2
5. POST /api/eventos/076ad22a.../reprocessar -> HTTP 202
   notificacoes | evento=076ad22a... duplicado: ignorado (idempotencia)
   notificações deste evento: 1
```
Na interface, o perfil **admin** vê as tabelas "Eventos de matrícula", com o botão **Reenviar**, e "Notificações simuladas".

## 6. Checklist

- [x] `up -d --build` inicia tudo; `db` fica *healthy*; `init` termina com `Exited (0)`; `web` responde
- [x] `GET /api/alunos` (com login) e `GET /api/resumo` respondem
- [x] `/health/ready` reflete o estado do banco (503 com o banco parado)
- [x] `web` → `db:5432` por DNS, sem IP fixo
- [x] pgAdmin conecta com o host `db`
- [x] A matrícula válida gera um evento durável
- [x] O evento é consumido e a notificação fica consultável
- [x] O consumidor fora do ar não perde eventos
- [x] O reprocessamento não duplica a notificação
- [x] A matrícula rejeitada não gera evento
- [x] `down` / `up` preserva os dados

## 7. Contêiner persistente x FaaS

| | Serviço `notificacoes` (container) | Função FaaS (proposta) |
|---|---|---|
| Execução | Sempre ligado | Sob demanda, acionada pelo evento |
| Cobrança | Por tempo ligado | Por invocação e duração |
| Cold start | Não tem | Pode ter |
| Estado | Usa o PostgreSQL | Também precisa de armazenamento externo |
| Docker | Necessário | Não é necessário (o provedor executa o código) |

Em nuvem, o `publicador` poderia publicar em uma fila gerenciada (SQS, Pub/Sub, Service Bus) que aciona a função. A outbox continua necessária para garantir a gravação do evento junto com a matrícula. **Uma função serverless não substitui o banco.**

## Referências
- Docker. *Networking in Compose*. https://docs.docker.com/compose/how-tos/networking/
- Docker. *Control startup order*. https://docs.docker.com/compose/how-tos/startup-order/
- Richardson, C. *Pattern: Transactional outbox*. https://microservices.io/patterns/data/transactional-outbox.html
- PostgreSQL 17. *SELECT ... FOR UPDATE SKIP LOCKED*. https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE
