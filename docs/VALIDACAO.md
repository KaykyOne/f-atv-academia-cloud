# Validação do pacote

- Três testes automatizados de integração da API aprovados: cadastro/exclusão e relações; validação e duplicidades; saúde, seed idempotente e persistência entre instâncias.
- Backend executado com Flask/SQLAlchemy reais e banco SQLite temporário exclusivo de testes.
- JavaScript verificado sintaticamente com Node.js.
- Não foi possível executar Docker, PostgreSQL ou pgAdmin neste ambiente, pois Docker não estava disponível. Não houve validação visual da interface em navegador.
- A execução completa de `docker compose up -d --build` deve ser conferida pelo professor antes de distribuir em aula. O guia contém o roteiro de conferência.
- O pacote inclui somente a base: os seis temas avançados são evoluções a desenvolver pelos grupos.
