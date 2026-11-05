# Manifests Kubernetes (PROPOSTA do Grupo 4)

> **Não foram executados em cluster.** O YAML foi validado sintaticamente, mas não foi aplicado com `kubectl`: o ambiente não tinha cluster.

| Arquivo | Conteúdo | Equivale no Compose |
|---|---|---|
| `00-namespace-config.yaml` | Namespace + ConfigMap | `environment` |
| `01-secret.example.yaml` | **Modelo** de Secret (sem senhas reais) | `secrets` / `.env` |
| `02-postgres.yaml` | StatefulSet + PVC + Service (só para laboratório) | `db` + volume |
| `03-init-job.yaml` | Job de inicialização | `init` |
| `04-web.yaml` | Deployment (2 réplicas, probes, limites) + Service + HPA + Ingress | `web` + `lb` |
| `05-eventos.yaml` | Notificações + publicador | `notificacoes`, `publicador` |
| `06-backup-cronjob.yaml` | CronJob diário de `pg_dump` | `backup` |

## Para testar em um cluster local (kind, minikube ou Docker Desktop)

```sh
docker build -t academia-cloud:2.0 .
kind load docker-image academia-cloud:2.0          # kind (minikube: minikube image load ...)
kubectl apply -f k8s/00-namespace-config.yaml
kubectl -n academia-cloud create secret generic academia-secrets \
  --from-literal=POSTGRES_ADMIN_USER=academia_admin --from-literal=POSTGRES_ADMIN_PASSWORD=... \
  --from-literal=APP_DB_USER=academic_app --from-literal=APP_DB_PASSWORD=... \
  --from-literal=NOTIF_DB_USER=notificacoes_app --from-literal=NOTIF_DB_PASSWORD=... \
  --from-literal=SECRET_KEY=... --from-literal=ADMIN_PASSWORD=... \
  --from-literal=SECRETARIA_PASSWORD=... --from-literal=PROFESSOR_PASSWORD=...
kubectl apply -f k8s/02-postgres.yaml
kubectl -n academia-cloud rollout status statefulset/academia-db
kubectl apply -f k8s/03-init-job.yaml
kubectl -n academia-cloud wait --for=condition=complete job/academia-init
kubectl apply -f k8s/04-web.yaml -f k8s/05-eventos.yaml -f k8s/06-backup-cronjob.yaml
kubectl -n academia-cloud port-forward svc/academia-web 8080:80
# autorrecuperação:
kubectl -n academia-cloud delete pod -l app=academia-web --wait=false; kubectl -n academia-cloud get pods -w
```

Pré-requisitos e cuidados:
- **HPA:** precisa do metrics-server. Sem ele, o HPA fica com `<unknown>`.
- **Ingress:** precisa de um Ingress Controller e do Secret TLS `academia-tls`. Em laboratório, use `port-forward`.
- **`COOKIE_SECURE=true`:** no ConfigMap, o login só funciona via HTTPS. Para testar com `port-forward` (HTTP), mude para `"false"`.
- **Banco:** o StatefulSet com 1 réplica é **ponto único de falha**. Em nuvem, use um banco gerenciado com standby em outra zona e aponte `DB_HOST` para ele.
- **Imagem:** em nuvem, publique em um registry (Grupo 1) e troque `image:` por `registry/academia-cloud:2.0`.
