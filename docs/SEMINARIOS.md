# Seminários integrados — seis grupos

## Caso comum
A instituição usa o AcademiaCloud em um único computador. Pretende disponibilizá-lo na nuvem, atender picos de matrícula, proteger os dados e recuperar o serviço após falhas. Cada grupo recebe a mesma base, faz sua própria cópia e propõe uma evolução.
Não é necessário contratar serviços pagos. Diagramas, simulações locais e comparação fundamentada de serviços podem substituir implantação real.

Apresentação sugerida: 20–25 minutos. Entrega: slides, diagrama, relatório curto, comandos/arquivos alterados e evidências. Toda demonstração deve utilizar dados fictícios.

## Grupo 1 — Construção e distribuição de imagens
Conteúdos Docker: Dockerfile; FROM, WORKDIR, COPY, ADD, RUN, EXPOSE, CMD e ENTRYPOINT; .dockerignore; build; camadas e cache; slim/Alpine; multi-stage; registry; tags; login, push e pull.
Nuvem: cloud-native; monólito/microsserviços; independência de implantação.
Desafio: explicar o Dockerfile recebido, construir a imagem e comparar uma variante com alteração no cache/tamanho. Discutir se multi-stage traz benefício para esta aplicação Python; pode usar exemplo complementar de aplicação compilada. Comparar slim e Alpine considerando compatibilidade, não apenas tamanho. Explicar por que o projeto ainda é monolítico.
Evidências: build, execução, comparação de tamanho, estratégia de tags e fluxo para registry. Publicação em registry é opcional; não publicar .env ou credenciais.
Pergunta central: como uma imagem reproduzível facilita distribuir e implantar a aplicação na nuvem?

## Grupo 2 — Configuração e comunicação entre serviços
Docker: Compose aprofundado; services, ports, volumes, networks, environment; .env; dependências; up/down/ps/logs/exec; DNS interno; redes bridge; isolamento; connection strings.
Nuvem: APIs, desacoplamento, microsserviços e serverless/FaaS; eventos, vantagens e limitações.
Desafio: explicar a conexão web→db, demonstrar resolução por nome de serviço e propor um serviço separado de notificações. Desenhar uma função acionada por evento de matrícula, com entrega confiável (por exemplo, outbox/fila) para evitar perda do evento após confirmar a matrícula. A função pode ser apenas simulada.
Evidências: mapa de rede, requisição à API, composição dos serviços e fluxo de evento. Comparar serviço containerizado persistente e FaaS. Serverless não exige Docker; uma função serverless não substitui automaticamente o banco.
Pergunta central: quais partes devem permanecer na aplicação e quais podem ser desacopladas?

## Grupo 3 — Segurança de containers e nuvem
Docker: usuário não root; permissões; portas; imagens e dependências atualizadas; vulnerabilidades; configuração e secrets.
Nuvem: CIA; responsabilidade compartilhada; criptografia em trânsito e repouso; IAM, MFA, roles, políticas e menor privilégio.
Desafio: analisar a base, separar o usuário administrativo do PostgreSQL da conta da aplicação e propor login e autorização por perfil (secretaria, professor e administrador). Demonstrar pelo menos uma melhoria local. Distinguir IAM do provedor, permissões do banco e autorização da aplicação.
Evidências: riscos observados, matriz de acesso, melhoria aplicada e diagrama de TLS/secrets. Nunca registrar credenciais nos slides.
Pergunta central: quem pode acessar cada recurso e quais responsabilidades pertencem à instituição e ao provedor?

## Grupo 4 — Escalabilidade, alta disponibilidade e Kubernetes
Docker: múltiplas instâncias; healthchecks; limites de Compose; containers stateless.
Nuvem: escala vertical/horizontal, elasticidade; regiões/zonas; balanceamento; failover; Kubernetes: cluster/node/pod/deployment/service; autorrecuperação.
Desafio: propor duas réplicas da aplicação atrás de balanceador. Demonstrar localmente ou apresentar manifests comentados para cluster de laboratório. Remover a publicação fixa de porta por réplica. Simular indisponibilidade de uma instância e mostrar o encaminhamento à outra. Separar liveness de readiness.
Evidências: arquitetura, observação da instância respondente, falha/recuperação e proposta de elasticidade. Explicar por que duplicar web não elimina o ponto único de falha do banco. Multi-zona e DR devem ser propostas explícitas, não propriedades presumidas do Compose.
Pergunta central: o que acontece durante um pico de acessos ou a falha de uma instância?

## Grupo 5 — Persistência, backup e recuperação
Docker: named volumes/bind mounts; ciclo de vida; PostgreSQL; backup e restauração.
Nuvem: snapshots; replicação; redundância geográfica; DR; RPO/RTO; continuidade.
Desafio: cadastrar dados, recriar o container preservando o volume, gerar backup lógico e restaurar em ambiente de laboratório. Definir RPO e RTO e medir o tempo de recuperação no ensaio.
Evidências: dados antes/depois, backup válido, restauração conferida e plano de recuperação. Explicar por que volume, replicação e backup são coisas diferentes. Evitar copiar diretório de PostgreSQL em execução como se fosse backup consistente.
Pergunta central: quanto dado pode ser perdido e em quanto tempo o serviço deve voltar?

## Grupo 6 — Diagnóstico, custos e governança
Docker: logs, stats, inspect, exec e investigação de falhas/consumo.
Nuvem: cobrança de computação, armazenamento, tráfego e serviços; pay-as-you-go; FinOps; dimensionamento; SLA; governança; auditoria; LGPD.
Desafio: observar os logs de uma requisição inválida, analisar recursos e simular interrupção do banco. Montar estimativa de custo para dois cenários, especificando provedor, região, moeda, data, premissas e fonte. Não contratar infraestrutura. Propor orçamento, alertas, retenção e políticas de acesso/auditoria.
Evidências: diagnóstico documentado, planilha/tabela de custos, SLA proposto e regras de governança. Um endpoint de saúde não é monitoramento completo. SLA contratado do provedor não equivale automaticamente à disponibilidade da aplicação. Abordar LGPD como governança e proteção, com fontes oficiais para afirmações jurídicas.
Pergunta central: como saber se o serviço está saudável, quanto custa e se atende às regras da instituição?

## Entrega comum
1. Contextualização e conceitos das duas disciplinas.
2. Diagrama da base e diagrama da evolução.
3. Demonstração ou simulação explicada.
4. Evidências reproduzíveis (comandos, arquivos e resultados).
5. Limitações, impactos e ligação com pelo menos outro grupo.
6. Referências técnicas oficiais e data de consulta.

## Rubrica sugerida — 10 pontos
| Critério | Pontos |
|---|---:|
| Correção e profundidade conceitual | 2,5 |
| Integração Docker e Nuvem | 2,0 |
| Aplicação ao caso e evidências | 2,5 |
| Clareza e organização | 1,5 |
| Limitações e referências | 1,0 |
| Participação dos integrantes | 0,5 |

## Integração final
Reunir os seis diagramas em uma arquitetura proposta. Cada grupo indica dependências e conflitos: eventos após transação, acesso ao banco, réplicas, persistência, backup, observabilidade e custo. O projeto integrador é a síntese, não um sétimo tema.
