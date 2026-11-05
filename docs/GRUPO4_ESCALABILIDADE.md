# Grupo 4: Escalabilidade, alta disponibilidade e Kubernetes

**Integrantes:** Guilherme, Samuel, Wendell e Adryan
**Pergunta central:** o que acontece durante um pico de acessos ou a falha de uma instância?

## 1. Análise da base

- A base tinha **uma** instância `web` publicada em `127.0.0.1:8080:8000`. Rodar `--scale web=2` geraria um conflito: duas réplicas não podem publicar a mesma porta do host.
- A `web` é **stateless**: nenhum dado fica em memória. Neste projeto, o login também usa um cookie assinado, sem sessão no servidor. Por isso qualquer réplica atende qualquer requisição. *Stateless* **não** significa independente do banco: todas usam o mesmo PostgreSQL.
- A criação de tabelas fica no `init` (um único container, com `pg_advisory_xact_lock`), e não em cada réplica. Assim, não há execução concorrente.

## 2. Implementação local

- O `web` não publica porta e usa `deploy.replicas: ${WEB_REPLICAS:-2}`.
- O `lb` (Nginx 1.28) é a **única** porta publicada. Configuração em [infra/nginx/default.conf](../infra/nginx/default.conf):
  - `server web:8000 resolve`: o DNS do Docker devolve os IPs de todas as réplicas, e `resolver ... valid=5s` atualiza a lista quando uma réplica muda de IP;
  - `max_fails=1 fail_timeout=10s`: verificação **passiva**. Depois de uma falha de conexão, a réplica sai da rotação por 10 s;
  - `proxy_next_upstream error timeout` e `tries 2`: se a conexão falhar, a requisição vai para a outra réplica. Isso só acontece com **erro de conexão**: um `503` da aplicação não é repetido, e POST não é reenviado;
  - o cabeçalho `X-Upstream` e o campo `instancia` em `/api/resumo` mostram qual réplica respondeu.
- O `lb` só sobe depois que as réplicas ficam *healthy*.

Para mudar o número de réplicas: `WEB_REPLICAS=3` no `.env`, e depois `docker compose up -d`.

## 3. Demonstração

```sh
bash scripts/demo-balanceamento.sh
```
Saída real (05/11/2026):
```
2. Requisições a /api/resumo          (status, réplica, tempo)
  200  8762fdb61f4a  0.009s
  200  eb47152bbb1b  0.006s           <- round-robin entre as 2 réplicas
  200  8762fdb61f4a  0.004s
  200  eb47152bbb1b  0.003s

3. docker stop academia-cloud-web-1
  200  eb47152bbb1b  2.005s           <- 1ª requisição: espera o timeout de conexão (2 s) e é reenviada
  200  eb47152bbb1b  0.004s           <- as demais vão direto para a réplica viva
  200  eb47152bbb1b  0.004s

4. docker start academia-cloud-web-1  (+16 s)
  200  eb47152bbb1b  0.004s
  200  8762fdb61f4a  0.033s           <- réplica de volta à rotação
  200  eb47152bbb1b  0.004s

5. docker compose stop db
  {"banco":"desconectado","instancia":"eb47152bbb1b"}  HTTP 503
  {"banco":"desconectado","instancia":"8762fdb61f4a"}  HTTP 503   <- as duas réplicas falham juntas
  docker compose start db
  {"banco":"conectado"}  HTTP 200
```

**O que realmente acontece quando uma réplica cai:**
- As requisições **em andamento** naquela réplica podem falhar. O `docker stop` envia SIGTERM e o Gunicorn tenta terminar o que está processando.
- A **primeira** requisição nova enviada para a réplica morta espera o `proxy_connect_timeout` (2 s) e então é reenviada para a outra. O cliente recebe 200, só que mais lento.
- Em uma execução anterior, com timeouts diferentes, observamos **uma** resposta 504 nesse momento de transição. Por isso, não prometemos "zero erro": prometemos que o serviço continua depois que o balanceador detecta a falha.
- Quando a réplica volta, ela retorna à rotação depois do `fail_timeout` (10 s) e da nova resolução DNS.

## 4. Liveness x readiness

| Endpoint | Pergunta | Quem usa |
|---|---|---|
| `/health/live` | O processo responde? | Kubernetes `livenessProbe`: se falhar, **reinicia** o Pod |
| `/health/ready` | Consegue atender? (testa o banco) | Healthcheck do Compose e `readinessProbe`: se falhar, o Pod **sai do balanceamento** |

Se a liveness verificasse o banco, uma queda do banco faria o Kubernetes reiniciar todos os Pods à toa.

| Mecanismo | O que faz |
|---|---|
| `restart: unless-stopped` | O Docker reinicia o container se o processo morrer |
| Healthcheck do Compose | Marca o container como *unhealthy*. **Não** tira a réplica do Nginx nem a reinicia sozinho |
| Verificação passiva do Nginx | Tira a réplica da rotação depois de uma falha de conexão |
| Kubernetes (Deployment + probes) | Recria Pods, remove do Service os que não estão Ready e redistribui entre nós |

## 5. Kubernetes (proposta, NÃO executada)

Os manifests comentados estão em [k8s/](../k8s/), com instruções em [k8s/README.md](../k8s/README.md).

| Conceito | No AcademiaCloud |
|---|---|
| Cluster / control plane / node | O control plane decide onde rodar; os nós executam os Pods |
| Pod | 1 container `web` |
| Deployment → ReplicaSet | `academia-web` mantém 2 Pods e recria os que morrem |
| Service | `academia-web`: IP e DNS estáveis, balanceia só entre Pods Ready |
| Ingress | Entrada HTTPS (precisa de um Ingress Controller) |
| HPA | 2 a 6 réplicas com CPU acima de 70%. **Exige metrics-server** e `requests` de CPU |
| requests/limits | `100m/128Mi` reservados, `500m/256Mi` de teto |
| Zonas | `topologySpreadConstraints` por `topology.kubernetes.io/zone`. Só tem efeito se o cluster tiver nós em mais de uma zona |

Dois Pods no **mesmo nó** não sobrevivem à queda desse nó.

## 6. Comparações

| | |
|---|---|
| **Vertical × horizontal** | Vertical: uma máquina maior (tem limite e costuma exigir reinício). Horizontal: mais réplicas (feito aqui) |
| **Escalabilidade × elasticidade** | Escalabilidade é *poder* crescer. Elasticidade é crescer e encolher **sozinho** conforme a demanda (HPA) |
| **Disponibilidade × tolerância a falhas** | Disponibilidade é o percentual de tempo atendendo. Tolerância a falhas é continuar funcionando **durante** uma falha |
| **Compose × Kubernetes** | Compose: um único host, sem reagendar em outro nó, healthcheck não tira do balanceador. Kubernetes: vários nós, autorrecuperação, probes, HPA, rolling update |
| **Réplicas web × HA completa** | As réplicas resolvem a queda de uma instância web. A HA completa exige também banco replicado, vários nós e zonas, e um balanceador redundante |

**Pontos únicos de falha que continuam:** `db`, `lb` (um único Nginx) e o próprio computador.

## Referências
- NGINX. *ngx_http_upstream_module* (`server ... resolve`, `max_fails`). https://nginx.org/en/docs/http/ngx_http_upstream_module.html
- NGINX. *proxy_next_upstream*. https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream
- Docker. *Compose deploy specification*. https://docs.docker.com/reference/compose-file/deploy/
- Kubernetes. *Liveness, Readiness and Startup Probes*. https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/
- Kubernetes. *Horizontal Pod Autoscaling*. https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
