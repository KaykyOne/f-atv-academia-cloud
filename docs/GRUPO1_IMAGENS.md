# Grupo 1: Construção e distribuição de imagens

**Integrantes:** Arthur, Felipe e Cristiano
**Pergunta central:** como uma imagem reproduzível facilita distribuir e implantar a aplicação na nuvem?

## 1. O que foi feito

[Dockerfile](../Dockerfile) com **4 estágios**:

| Estágio | Função |
|---|---|
| `frontend` | `node:22-alpine`: `npm ci` + `npm run build` do React/shadcn. **Node não vai para a imagem final**, só o `dist/` (~600 kB) |
| `deps` | Cria um venv **sem pip** e instala `requirements.txt` com versões fixas |
| `test` | Copia o código e os testes e roda os 8 testes. Se algum falhar, o build falha |
| `final` | `python:3.12-slim` + venv + código, com o usuário `academic` (uid 10001) |

Uma única imagem (`academia-cloud:2.0`) atende **4 serviços** (`web`, `init`, `publicador` e `notificacoes`): só muda o `command` no Compose. Isso é "construir uma vez, executar em vários ambientes".

| Instrução | Para que serve aqui |
|---|---|
| `FROM ... AS deps` | Imagem base e nome do estágio |
| `WORKDIR /srv` | Diretório de trabalho |
| `COPY requirements.txt` **antes** de `COPY app` | Cache: mudar o código não reinstala as dependências |
| `RUN pip ... install` | Instala as dependências (camada pesada, raramente muda) |
| `COPY --from=deps` | Leva para a imagem final só o resultado do estágio anterior |
| `USER academic` | O processo não roda como root |
| `EXPOSE 8000` | Documenta a porta (não publica nada) |
| `CMD [...]` | Comando padrão, que o Compose sobrescreve por serviço |

`ENTRYPOINT` não foi usado: com `CMD`, cada serviço troca o comando inteiro. `ADD` também não: `COPY` é mais previsível (não baixa URLs nem extrai arquivos).

[.dockerignore](../.dockerignore) tira do contexto de build o `.env`, `backups/`, `docs/`, `k8s/` e os scripts. Assim, segredos e backups **nunca** entram na imagem.

## 2. Comparação real (05/11/2026)

```sh
docker build -f infra/comparacao/Dockerfile.base-original -t academia-cloud:base .
docker compose build
docker image inspect academia-cloud:2.0 academia-cloud:base --format '{{index .RepoTags 0}} {{.Size}} layers={{len .RootFS.Layers}}'
```
| Imagem | Tamanho | Camadas |
|---|---|---|
| `academia-cloud:base` (original, estágio único) | 238,59 MB | 9 |
| `academia-cloud:2.0`, 1ª versão multi-stage (venv **com** pip) | 255,55 MB | 8 |
| `academia-cloud:2.0`, final (venv **sem** pip) | 238,62 MB | 8 |

> Medições feitas antes da inclusão do estágio `frontend`. O frontend acrescenta só os arquivos estáticos compilados; sem multi-stage, seria preciso instalar Node (~150 MB) na imagem final.

**Conclusão honesta:** no backend Python, o multi-stage **não reduziu o tamanho**. As dependências já vêm como *wheels* binárias e o original já usava `--no-cache-dir`. Na primeira tentativa, a imagem até **cresceu** 17 MB, por causa de uma segunda cópia do pip dentro do venv. O ganho real é outro: os **testes rodam no build** (estágio `test`) e o estágio final fica limpo. O multi-stage traz grande redução em linguagens compiladas (Go, Java, C#) e **no frontend deste projeto**: o Node, o TypeScript, o Vite e os ~100 pacotes de `node_modules` ficam no estágio de build, e só o JS/CSS minificado vai para a imagem.

**Slim x Alpine:** `python:3.12-slim` usa glibc. No Alpine (musl), pacotes como `psycopg[binary]` podem não ter *wheel* pronta e exigir compilação, o que aumenta o tempo de build e o risco de incompatibilidade. Para Python, o slim costuma ser a escolha mais segura.

## 3. Cache de camadas (evidência)

Alterando só `app/static/style.css` e reconstruindo:
```
#8 [deps 4/4] RUN pip --python /opt/venv/bin/python install -r requirements.txt
#8 CACHED
#7 [final 3/5] COPY --from=deps /opt/venv /opt/venv
#7 CACHED
```
Só a camada `COPY app` é refeita.

## 4. Tags e registry (fluxo proposto, não publicado)

```sh
docker tag academia-cloud:2.0 SEU_USUARIO/academia-cloud:2.0
docker tag academia-cloud:2.0 SEU_USUARIO/academia-cloud:2.0-$(git rev-parse --short HEAD)
docker login
docker push SEU_USUARIO/academia-cloud:2.0
# em outro computador/nuvem:
docker pull SEU_USUARIO/academia-cloud:2.0
```
Estratégia de tags: versão semântica (`2.0`) + commit, sem depender de `latest` em produção. A tag é configurável pela variável `IMAGE_TAG` no `.env`. **Nunca** publicar `.env` ou backups (o `.dockerignore` garante isso).

## 5. Monólito ou microsserviços?

O núcleo acadêmico (alunos, disciplinas e matrículas) continua sendo **um monólito containerizado**: um único código e um único banco. O serviço de notificações é o primeiro passo de desacoplamento (G2), mas ainda usa a mesma imagem e o mesmo servidor PostgreSQL, embora em outro schema e com outra conta. Microsserviços "de verdade" teriam implantação e banco independentes.

## Referências
- Docker. *Dockerfile reference*. https://docs.docker.com/reference/dockerfile/
- Docker. *Multi-stage builds*. https://docs.docker.com/build/building/multi-stage/
- Docker. *Build cache*. https://docs.docker.com/build/cache/
