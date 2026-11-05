"""Estrutura do banco do AcademiaCloud.

Tabelas originais: alunos, disciplinas, matriculas.
Acréscimos do projeto integrado:
  * usuarios   (Grupo 3) - login e perfil de acesso;
  * auditoria  (Grupos 3 e 6) - trilha de ações e tentativas de acesso;
  * eventos    (Grupo 2) - outbox transacional dos eventos de matrícula;
  * notificacoes.notificacoes (Grupo 2) - pertence ao serviço de notificações,
    em um schema separado, acessado por outra conta do PostgreSQL.
"""
import os
from datetime import datetime, timezone
from sqlalchemy import (MetaData, Table, Column, Integer, String, Text, Boolean, DateTime,
                        ForeignKey, UniqueConstraint, Index, create_engine, event)
from sqlalchemy.engine import make_url

metadata = MetaData()

alunos = Table('alunos', metadata,
               Column('id', Integer, primary_key=True),
               Column('nome', String(100), nullable=False),
               Column('email', String(160), unique=True, nullable=False))

disciplinas = Table('disciplinas', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('nome', String(100), unique=True, nullable=False),
                    Column('carga_horaria', Integer, nullable=False))

matriculas = Table('matriculas', metadata,
                   Column('id', Integer, primary_key=True),
                   Column('aluno_id', Integer, ForeignKey('alunos.id'), nullable=False),
                   Column('disciplina_id', Integer, ForeignKey('disciplinas.id'), nullable=False),
                   UniqueConstraint('aluno_id', 'disciplina_id'))

usuarios = Table('usuarios', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('login', String(40), unique=True, nullable=False),
                 Column('nome', String(100), nullable=False),
                 Column('perfil', String(20), nullable=False),
                 Column('senha_hash', String(255), nullable=False),
                 Column('ativo', Boolean, nullable=False, default=True))

auditoria = Table('auditoria', metadata,
                  Column('id', Integer, primary_key=True),
                  Column('quando', DateTime(timezone=True), nullable=False),
                  Column('usuario', String(40)),
                  Column('perfil', String(20)),
                  Column('acao', String(40), nullable=False),
                  Column('recurso', String(60)),
                  Column('resultado', String(20), nullable=False),
                  Column('detalhe', String(200)),
                  Column('ip', String(45)),
                  Column('instancia', String(64)),
                  Index('ix_auditoria_login', 'acao', 'usuario', 'quando'))

eventos = Table('eventos', metadata,
                Column('id', String(36), primary_key=True),          # UUID do evento
                Column('tipo', String(40), nullable=False),
                Column('payload', Text, nullable=False),              # JSON do contrato
                Column('status', String(12), nullable=False),         # pendente|entregue|falho
                Column('tentativas', Integer, nullable=False, default=0),
                Column('ultimo_erro', String(300)),
                Column('criado_em', DateTime(timezone=True), nullable=False),
                Column('proxima_tentativa', DateTime(timezone=True), nullable=False),
                Column('entregue_em', DateTime(timezone=True)),
                Index('ix_eventos_fila', 'status', 'proxima_tentativa'))

# Schema próprio do serviço de notificações (vazio = sem schema, usado no SQLite dos testes).
NOTIF_SCHEMA = os.getenv('NOTIF_SCHEMA', 'notificacoes') or None
notif_metadata = MetaData(schema=NOTIF_SCHEMA)
notificacoes = Table('notificacoes', notif_metadata,
                     Column('id', Integer, primary_key=True),
                     Column('evento_id', String(36), unique=True, nullable=False),  # idempotência
                     Column('tipo', String(40), nullable=False),
                     Column('destinatario', String(160), nullable=False),
                     Column('mensagem', Text, nullable=False),
                     Column('recebido_em', DateTime(timezone=True), nullable=False),
                     Column('instancia', String(64)))

TABELAS_ACADEMICAS = {'alunos': alunos, 'disciplinas': disciplinas, 'matriculas': matriculas}


def agora():
    return datetime.now(timezone.utc)


def is_sqlite(url):
    return make_url(url).get_backend_name() == 'sqlite'


def make_engine(url):
    engine = create_engine(url, pool_pre_ping=True)
    if is_sqlite(url):
        @event.listens_for(engine, 'connect')
        def foreign_keys(dbapi_conn, _):
            dbapi_conn.execute('PRAGMA foreign_keys=ON')
    return engine
