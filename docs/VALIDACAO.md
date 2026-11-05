# Validação do projeto integrado

Executada em 05/11/2026 com Docker 29.9.2 e Docker Compose v5.6.1, em Linux (Fedora).

## Executado e aprovado

| Verificação | Como | Resultado |
|---|---|---|
| Testes automatizados (8) | `docker build --target test .` | OK: fluxo original, validação, saúde/seed, login, matriz de perfis, CSRF, força bruta, outbox/idempotência |
| Primeira subida do zero | `sh scripts/gerar-env.sh && docker compose up -d --build` | Todos *healthy*; `init` Exited (0); 1º backup gerado automaticamente |
| CRUD via balanceador, duplicidade, vínculo | curl | 201, 409 duplicada, 403 por perfil |
| Balanceamento e failover | `scripts/demo-balanceamento.sh` | Alternância entre 2 réplicas; queda de 1 → 1ª requisição em 2,0 s, demais normais; volta em ~16 s |
| Banco fora não mascarado | idem, passo 5 | As 2 réplicas respondem 503 em `/health/ready`; volta a 200 |
| Nginx acompanha IPs novos | Recriar `web` sem reiniciar `lb` | Continuou balanceando (`resolve`) |
| Outbox, retry, idempotência | `scripts/demo-eventos.sh` | Pendente → entregue (2 tentativas); reenvio = "duplicado", 1 notificação |
| Segurança | `scripts/demo-seguranca.sh` | uid 10001; secrets em arquivo; DROP/UPDATE negados; schema isolado; 401/403/429; cabeçalhos |
| Persistência | `down` + `up -d` | Contadores idênticos antes e depois |
| Backup | `scripts/backup-agora.sh` | `.sql.gz` + SHA-256 OK; 7 tabelas com dados |
| Restauração isolada | `scripts/teste-restauracao.sh` | Dados iguais ao principal; 18,7 s |
| Diagnóstico | `scripts/diagnostico.sh` | Evidência gerada; encontrou o 502 na subida, que foi corrigido |
| Manifests K8s | `yaml.safe_load_all` | 14 objetos com sintaxe válida |

## Executado e falhou (corrigido ou registrado)

| O quê | Causa | Ação |
|---|---|---|
| `lb` respondia 502 nos primeiros segundos | `depends_on: service_started` | Trocado por `service_healthy` |
| `read_only: true` nos serviços | O Compose não aceita secrets `environment` em serviço somente leitura | Revertido; mantido `no-new-privileges`; `readOnlyRootFilesystem` está no K8s |
| 1ª imagem multi-stage 17 MB maior | O venv carregava uma cópia do pip | `venv --without-pip` + `pip --python` |

## Não executado

- Kubernetes em cluster (não havia kind/minikube). Procedimento em `k8s/README.md`.
- Execução no Windows/PowerShell. Os comandos equivalentes estão nos documentos dos grupos; os scripts `.sh` exigem bash (WSL ou Git Bash).
- Teste de carga: as requisições do script de balanceamento **não** medem capacidade.
- Cotação real de custos (Grupo 6): o modelo está pronto, mas falta preencher com dados oficiais e a data.
