"""Serviço `init`: prepara o banco e termina com código 0.

Executa com a conta ADMINISTRATIVA do PostgreSQL e:
  1. obtém um advisory lock (evita duas inicializações concorrentes - Grupo 4);
  2. cria/atualiza as contas de menor privilégio da aplicação e das notificações (Grupo 3);
  3. cria tabelas e o schema `notificacoes` (Grupo 2);
  4. aplica GRANTs mínimos (Grupo 3);
  5. insere dados fictícios e os usuários iniciais, sem apagar nada existente.
É idempotente: pode ser executado de novo (por exemplo, depois de uma restauração - Grupo 5).
"""
import logging
import os
import sys

from sqlalchemy import select, func, text
from werkzeug.security import generate_password_hash

from app.config import secret, database_url
from app.models import (metadata, notif_metadata, alunos, disciplinas, usuarios,
                        make_engine, is_sqlite, NOTIF_SCHEMA)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s init %(message)s')

USUARIOS_INICIAIS = [
    ('admin', 'Administrador do Sistema', 'administrador', 'ADMIN_PASSWORD'),
    ('secretaria', 'Secretaria Acadêmica', 'secretaria', 'SECRETARIA_PASSWORD'),
    ('professor', 'Professor Exemplo', 'professor', 'PROFESSOR_PASSWORD'),
]


def seed(conn, senhas=None):
    """Dados fictícios + usuários iniciais. Não altera registros existentes."""
    if conn.scalar(select(func.count()).select_from(alunos)) == 0:
        conn.execute(alunos.insert(), [{'nome': 'Ana Exemplo', 'email': 'ana@example.test'},
                                       {'nome': 'Bruno Exemplo', 'email': 'bruno@example.test'}])
    if conn.scalar(select(func.count()).select_from(disciplinas)) == 0:
        conn.execute(disciplinas.insert(), [{'nome': 'Docker', 'carga_horaria': 40},
                                            {'nome': 'Computação em Nuvem', 'carga_horaria': 40}])
    senhas = senhas or {}
    for login, nome, perfil, var in USUARIOS_INICIAIS:
        if conn.scalar(select(usuarios.c.id).where(usuarios.c.login == login)):
            continue
        senha = senhas.get(login) or secret(var)
        if not senha:
            logging.warning('usuario=%s ignorado: %s não configurada', login, var)
            continue
        conn.execute(usuarios.insert().values(login=login, nome=nome, perfil=perfil, ativo=True,
                                              senha_hash=generate_password_hash(senha)))
        logging.info('usuario=%s perfil=%s criado', login, perfil)


def initialize(engine, senhas=None):
    """Versão usada nos testes (SQLite) e também pelo PostgreSQL."""
    with engine.begin() as conn:
        metadata.create_all(conn)
        notif_metadata.create_all(conn)
        seed(conn, senhas)


# ----------------------------------------------------------------- PostgreSQL
def _ensure_role(cur, sql, nome, senha):
    cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (nome,))
    verbo = 'ALTER' if cur.fetchone() else 'CREATE'
    cur.execute(sql.SQL(verbo + ' ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}')
                .format(sql.Identifier(nome), sql.Literal(senha)))
    logging.info('conta do banco %s: %s', nome, 'atualizada' if verbo == 'ALTER' else 'criada')


def initialize_postgres(engine):
    from psycopg import sql
    app_user, notif_user = os.environ['APP_DB_USER'], os.environ['NOTIF_DB_USER']
    db_name = os.environ['DB_NAME']
    ident = sql.Identifier
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(4242)'))
        cur = conn.connection.driver_connection.cursor()
        _ensure_role(cur, sql, app_user, secret('APP_DB_PASSWORD'))
        _ensure_role(cur, sql, notif_user, secret('NOTIF_DB_PASSWORD'))
        cur.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(ident(NOTIF_SCHEMA)))

        metadata.create_all(conn)
        notif_metadata.create_all(conn)

        g = lambda q, *ids: cur.execute(sql.SQL(q).format(*[ident(i) for i in ids]))
        # Ninguém além das contas previstas conecta ao banco.
        g('REVOKE ALL ON DATABASE {} FROM PUBLIC', db_name)
        g('GRANT CONNECT ON DATABASE {} TO {}, {}', db_name, app_user, notif_user)
        g('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        # Conta da aplicação: somente DML nas tabelas necessárias (sem DDL, sem UPDATE em cadastros).
        g('GRANT USAGE ON SCHEMA public TO {}', app_user)
        g('GRANT SELECT, INSERT, DELETE ON alunos, disciplinas, matriculas TO {}', app_user)
        g('GRANT SELECT, INSERT, UPDATE ON eventos TO {}', app_user)
        g('GRANT SELECT ON usuarios TO {}', app_user)
        g('GRANT SELECT, INSERT ON auditoria TO {}', app_user)
        g('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}', app_user)
        # Conta das notificações: só enxerga o próprio schema.
        g('REVOKE ALL ON SCHEMA {} FROM PUBLIC', NOTIF_SCHEMA)
        g('GRANT USAGE ON SCHEMA {} TO {}', NOTIF_SCHEMA, notif_user)
        cur.execute(sql.SQL('GRANT SELECT, INSERT ON {}.notificacoes TO {}')
                    .format(ident(NOTIF_SCHEMA), ident(notif_user)))
        g('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}', NOTIF_SCHEMA, notif_user)

        seed(conn)


def main():
    url = database_url()
    engine = make_engine(url)
    if is_sqlite(url):
        initialize(engine)
    else:
        initialize_postgres(engine)
    engine.dispose()
    print('Banco inicializado: contas, permissões, tabelas e dados fictícios prontos.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # mensagem curta, sem expor senha/URL
        logging.error('falha na inicialização: %s', type(e).__name__)
        raise
    sys.exit(0)
