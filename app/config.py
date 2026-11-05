"""Leitura de configuração e segredos (Grupos 2 e 3).

Cada valor sensível pode chegar de duas formas:
  * NOME_FILE=/run/secrets/arquivo  -> lido de um Docker secret (preferido);
  * NOME=valor                      -> variável de ambiente (testes/laboratório).
A conexão é montada com URL.create, que codifica corretamente senhas com
caracteres especiais (a base original exigia senhas alfanuméricas).
"""
import os
from sqlalchemy.engine import URL


def secret(name, default=None):
    path = os.getenv(name + '_FILE')
    if path:
        with open(path, encoding='utf-8') as f:
            return f.read().strip()
    return os.getenv(name, default)


def database_url():
    """DATABASE_URL tem prioridade (testes); senão usa DB_* injetados pelo Compose."""
    if os.getenv('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    return URL.create(
        'postgresql+psycopg',
        username=os.environ['DB_USER'],
        password=secret('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'db'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.environ['DB_NAME'],
    )
