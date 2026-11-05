"""Serviço `notificacoes` (Grupo 2): consumidor independente de eventos.

Representa localmente uma função orientada a eventos (como uma FaaS): recebe o
contrato JSON em POST /events e registra uma notificação SIMULADA (não envia
e-mail). É idempotente: o mesmo `evento_id` nunca gera duas notificações.
Usa uma conta própria do PostgreSQL, que só acessa o schema `notificacoes`.
"""
import logging
import socket
import uuid

from flask import Flask, request, jsonify
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import database_url
from app.models import notificacoes, agora, make_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s notificacoes %(message)s')
INSTANCIA = socket.gethostname()


def mensagem_para(tipo, dados):
    if tipo == 'MatriculaCriada':
        return (str(dados['aluno_email']),
                f"Olá, {dados['aluno']}! Sua matrícula em {dados['disciplina']} foi confirmada.")
    raise ValueError('tipo de evento não suportado')


def create_notif_app(url=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16384
    engine = make_engine(url or database_url())
    app.extensions['engine'] = engine

    @app.post('/events')
    def receber():
        data = request.get_json(silent=True)
        try:
            evento_id = str(uuid.UUID(str(data['evento_id'])))
            destinatario, mensagem = mensagem_para(data['tipo'], data['dados'])
        except (TypeError, KeyError, ValueError):
            return jsonify(erro='Evento inválido.'), 400
        try:
            with engine.begin() as c:
                c.execute(notificacoes.insert().values(
                    evento_id=evento_id, tipo=data['tipo'], destinatario=destinatario[:160],
                    mensagem=mensagem, recebido_em=agora(), instancia=INSTANCIA[:64]))
        except IntegrityError:
            logging.info('evento=%s duplicado: ignorado (idempotencia)', evento_id)
            return jsonify(status='duplicado', evento_id=evento_id), 200
        logging.info('evento=%s notificacao SIMULADA registrada', evento_id)
        return jsonify(status='processado', evento_id=evento_id), 201

    @app.get('/notificacoes')
    def listar():
        with engine.connect() as c:
            rows = c.execute(select(notificacoes).order_by(notificacoes.c.id.desc()).limit(200)).mappings().all()
        return jsonify([{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in r.items()} for r in rows])

    @app.get('/health/live')
    def live():
        return jsonify(status='ok', instancia=INSTANCIA)

    @app.get('/health/ready')
    def ready():
        try:
            with engine.connect() as c:
                c.execute(text('SELECT 1'))
            return jsonify(status='ok')
        except SQLAlchemyError:
            return jsonify(status='indisponivel'), 503

    @app.errorhandler(SQLAlchemyError)
    def db_error(e):
        logging.error('database_error type=%s', type(e).__name__)
        return jsonify(erro='Banco indisponível.'), 503

    return app
