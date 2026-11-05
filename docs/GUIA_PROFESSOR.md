# Guia do professor

## Antes de distribuir
1. Leia README.md e execute a base em um computador com Docker.
2. Confira cadastro de aluno, disciplina e matrícula; tente matrícula duplicada.
3. Exclua uma matrícula e depois o aluno; confirme proteção dos vínculos.
4. Reinicie containers e confira a persistência.
5. Entregue o mesmo ZIP para todos; cada grupo trabalha em sua cópia.

## Orientação inicial sugerida — 30 minutos
- 5 min: cenário acadêmico e propósito das duas disciplinas.
- 10 min: execução, interface e API.
- 10 min: Dockerfile, Compose, .env, rede e volumes.
- 5 min: distribuição dos temas e evidências esperadas.

## Ordem de apresentação
1 → 2 → 3 → 4 → 5 → 6, seguida de discussão de arquitetura integrada.
O nível de implementação pode ser ajustado: todos devem explicar os conceitos; demonstrações avançadas podem ser substituídas por simulação e arquivos comentados.

## Escopo recebido
CRUD parcial (criar/listar/excluir), dados fictícios, persistência, validação e observação básica. Dockerfile, rede, volume, init e healthchecks prontos garantem uma base comum. O objetivo é compreender e evoluir, não criar todos os componentes do zero.
Não há autenticação nem serviços de nuvem contratados. Não use dados de alunos reais.
