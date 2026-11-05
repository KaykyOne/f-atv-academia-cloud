# AcademiaCloud — estudo de caso de Docker e Computação em Nuvem

Aplicação acadêmica didática com interface em português, API HTTP e PostgreSQL.
Tecnologias: Python 3.12, Flask, SQLAlchemy, Gunicorn, PostgreSQL 17 e Docker Compose v2.
A escolha de Python reduz a configuração necessária: os alunos podem concentrar o estudo na infraestrutura, mesmo sem alterar o backend.

## 1. Executar

Instale previamente Docker Engine/Desktop e Docker Compose v2. Extraia o ZIP e abra o terminal dentro da pasta AcademiaCloud.

Linux/macOS:
```sh
cp .env.example .env
```
Windows PowerShell:
```powershell
Copy-Item .env.example .env
```
Edite `.env` e substitua as duas senhas. Nesta base, use senhas longas alfanuméricas: caracteres reservados em URLs exigiriam codificação na DATABASE_URL.

```sh
docker compose up -d --build
docker compose ps -a
docker compose logs init web
```
A primeira execução precisa de internet para baixar imagens e dependências.
Abra **http://localhost:8080**. Há dois alunos e duas disciplinas fictícias. Cadastre uma matrícula para observar as relações.
O serviço `init` terminar com código 0 é normal: ele cria as tabelas e dados iniciais, antes de iniciar a aplicação. Ele não apaga registros existentes.

Para encerrar, preservando os dados:
```sh
docker compose down
```
Para iniciar novamente:
```sh
docker compose up -d
```
**`docker compose down -v` apaga os volumes e todos os dados deste projeto.** Não é necessário para uso normal. Alterar POSTGRES_PASSWORD no .env não altera automaticamente a senha de um banco já inicializado.

## 2. pgAdmin opcional

```sh
docker compose --profile admin up -d
```
Abra http://localhost:5050 e entre com PGADMIN_EMAIL / PGADMIN_PASSWORD do `.env`.
Em Register > Server, informe:
- Name: AcademiaCloud
- Host: db (DNS interno da rede Docker)
- Port: 5432
- Maintenance database: academia (ou POSTGRES_DB do .env)
- Username e Password: POSTGRES_USER e POSTGRES_PASSWORD do .env

O PostgreSQL não publica porta no computador. A aplicação e o pgAdmin conectam-se por `db:5432` dentro da rede.

## 3. Funcionalidades

- Cadastro, listagem e exclusão de alunos e disciplinas.
- Matrícula e cancelamento, com bloqueio de duplicidade.
- Exclusão de aluno ou disciplina vinculados é bloqueada até remover as matrículas.
- Painel com totais e identificação da instância.
- Validação no backend, SQL parametrizado e resposta de erro sem senha/conexão.
- Logs em stdout; endpoints de liveness e readiness.

## 4. Arquitetura inicial

Navegador → aplicação web/API (porta local 8080 → 8000 no container) → PostgreSQL (db:5432).
O frontend é servido pela própria aplicação. Trata-se de **monólito containerizado**, não de microsserviços; separação futura é uma tarefa de estudo.
`init` executa a inicialização antes do servidor. `pgadmin` é ferramenta administrativa opcional.
Dados do banco residem em `dados_postgres`, um named volume. Cada container web é stateless.

## 5. API

| Método | Rota | Uso |
|---|---|---|
| GET | /api/resumo | Contadores e instância |
| GET / POST | /api/alunos | Listar / cadastrar |
| GET / POST | /api/disciplinas | Listar / cadastrar |
| GET / POST | /api/matriculas | Listar / matricular |
| DELETE | /api/alunos/{id} | Excluir aluno sem vínculos |
| DELETE | /api/disciplinas/{id} | Excluir disciplina sem vínculos |
| DELETE | /api/matriculas/{id} | Cancelar matrícula |
| GET | /health/live | Processo ativo |
| GET | /health/ready | Conexão com o banco |

```sh
curl http://localhost:8080/health/ready
curl http://localhost:8080/api/resumo
curl -X POST http://localhost:8080/api/alunos -H 'Content-Type: application/json' -d '{"nome":"Carla Exemplo","email":"carla@example.test"}'
```
PowerShell: use `curl.exe` ou `Invoke-RestMethod`.
Status: 201 criação; 204 exclusão; 400 validação; 404 inexistente; 409 duplicidade/vínculo; 503 banco indisponível.
Não há edição nesta versão: o escopo é cadastro, listagem e exclusão.

## 6. Diagnóstico

```sh
docker compose logs -f web
docker compose logs db
docker compose exec web id
docker compose exec web python -c "import socket; print(socket.gethostbyname('db'))"
docker stats
```
Logs não registram o corpo enviado nem credenciais. `docker stats` mostra uso dos containers do computador.
Se a porta 8080 estiver ocupada, altere APP_PORT no .env e execute `docker compose up -d`.
Se `init` falhar, consulte os logs de init e db; confirme senhas e nome do banco.
Readiness verifica a conexão, não a integridade de todas as tabelas.

## 7. Backup e restauração (Linux/macOS ou WSL)

Crie um backup lógico consistente usando pg_dump, em vez de copiar arquivos do banco em execução:
```sh
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' > backups/academia.sql
```
Confirme que o comando terminou com sucesso e que o arquivo contém SQL. Um arquivo vazio não é backup válido.
Restauração: **substitui tabelas e dados de alunos, disciplinas e matrículas pelo conteúdo do backup**. Faça em um ambiente de laboratório separado, ou guarde um backup atual primeiro.
```sh
docker compose stop web
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/academia.sql
docker compose start web
```
Reabra a interface e confirme os registros. Para recuperar após perda do volume: inicie primeiro o projeto para recriar o banco vazio, depois restaure.

## 8. Limites da base e evolução

Uso local com dados fictícios. Não há login, RBAC, TLS, gestão de secrets, Kubernetes, balanceador nem implantação em provedor. As portas são vinculadas a 127.0.0.1. Esses itens são atividades dos grupos, não funcionalidades prontas.
Credenciais por .env são configuração de laboratório, não um mecanismo de secrets. O usuário inicial do PostgreSQL criado por POSTGRES_USER tem privilégios elevados: o grupo 3 deve separar conta administrativa e conta da aplicação.
O Dockerfile já roda como usuário não root. Para ensinar otimização, compare uma variante básica e uma otimizada, sem alterar a base distribuída.
Escalar `web` diretamente com a mesma porta publicada causa conflito. Grupo 4 deve retirar essa publicação por réplica e introduzir balanceador ou Kubernetes.
Em produção, utilize migrações, conta com menor privilégio, autenticação, autorização, proteção contra abuso, TLS, backups testados e gestão segura de credenciais.

## 9. Testes

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
```
Por padrão, os testes usam SQLite temporário, sem alterar o banco da aplicação. Para repetir com PostgreSQL, aponte TEST_DATABASE_URL para um **banco exclusivo e vazio de testes**. O teste cria e apaga tabelas desse banco. Não use o banco de aula.

## 10. Materiais

- docs/SEMINARIOS.md: temas, desafios, evidências e rubrica.
- docs/GUIA_PROFESSOR.md: condução e conferência da base.
- docs/VALIDACAO.md: escopo da validação realizada no pacote.

Referências oficiais consultadas:
- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.docker.com/reference/compose-file/services/
- https://flask.palletsprojects.com/en/stable/deploying/
