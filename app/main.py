"""AcademiaCloud - aplicação web/API (núcleo acadêmico).

Mantém todas as funções da base (alunos, disciplinas, matrículas, resumo, health)
e acrescenta:
  * login com sessão assinada e autorização por perfil (Grupo 3);
  * auditoria de ações e bloqueio de força bruta no login (Grupos 3 e 6);
  * evento MatriculaCriada gravado na outbox na MESMA transação da matrícula (Grupo 2);
  * consulta de eventos, notificações e auditoria para o administrador.
A instância é stateless: a sessão fica em cookie assinado e todo estado
persistente está no PostgreSQL, permitindo várias réplicas (Grupo 4).
"""
import json
import logging
import os
import secrets as pysecrets
import socket
import time
import urllib.request
import uuid
from datetime import timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, g
from sqlalchemy import select, func, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

from app.config import secret, database_url
from app.models import (alunos, disciplinas, matriculas, usuarios, auditoria, eventos,
                        TABELAS_ACADEMICAS, agora, make_engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
INSTANCIA = socket.gethostname()

# Matriz de autorização (Grupo 3). Leitura: qualquer usuário autenticado.
PODE_ESCREVER = {
    'alunos': {'administrador', 'secretaria'},
    'disciplinas': {'administrador', 'professor'},
    'matriculas': {'administrador', 'secretaria'},
}
SO_ADMIN = {'administrador'}
MAX_FALHAS_LOGIN, JANELA_LOGIN = 5, timedelta(minutes=5)


def mascarar_email(email):
    usuario, _, dominio = email.partition('@')
    return (usuario[:1] + '***@' + dominio) if dominio else '***'


def valid_name(value):
    if not isinstance(value, str) or not 2 <= len(value.strip()) <= 100:
        raise ValueError('Nome deve ter de 2 a 100 caracteres.')
    return value.strip()


def valid_int(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f'Valor inteiro esperado entre {minimum} e {maximum}.')
    return value


def valid_email(value):
    if (not isinstance(value, str) or len(value) > 160 or '@' not in value
            or '.' not in value.split('@')[-1] or any(c.isspace() for c in value)):
        raise ValueError('Informe um e-mail válido (até 160 caracteres).')
    return value.strip().lower()


def create_app(url=None, secret_key=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # atrás do Nginx (Grupo 4)
    key = secret_key or secret('SECRET_KEY')
    if not key:
        if url is None:
            raise RuntimeError('SECRET_KEY não configurada.')
        key = pysecrets.token_hex(32)  # apenas testes
    app.config.update(
        SECRET_KEY=key,
        MAX_CONTENT_LENGTH=16384,
        SESSION_COOKIE_NAME='academia_sessao',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    engine = make_engine(url or database_url())
    app.extensions['engine'] = engine
    notif_url = os.getenv('NOTIF_URL', 'http://notificacoes:8001')

    # ------------------------------------------------------------ utilidades
    def usuario_atual():
        return session.get('usuario')

    def audit(acao, recurso=None, resultado='sucesso', detalhe=None, usuario=None):
        u = usuario or usuario_atual() or {}
        try:
            with engine.begin() as c:
                c.execute(auditoria.insert().values(
                    quando=agora(), usuario=(u.get('login') or '')[:40] or None, perfil=u.get('perfil'),
                    acao=acao, recurso=recurso, resultado=resultado,
                    detalhe=(detalhe or '')[:200] or None, ip=(request.remote_addr or '')[:45],
                    instancia=INSTANCIA[:64]))
        except SQLAlchemyError as e:
            logging.error('auditoria_falhou type=%s', type(e).__name__)

    def exige_login(perfis=None):
        def deco(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                u = usuario_atual()
                if not u:
                    return jsonify(erro='Faça login para continuar.'), 401
                if perfis is not None and u['perfil'] not in perfis:
                    audit('acesso_negado', request.path, 'negado', request.method)
                    return jsonify(erro='Seu perfil não tem permissão para esta ação.'), 403
                return fn(*args, **kwargs)
            return wrapper
        return deco

    # ------------------------------------------------------------ middlewares
    @app.before_request
    def before():
        g.started = time.monotonic()
        # Proteção CSRF: alterações só via JSON (formulário de outro site não consegue
        # enviar application/json sem preflight CORS, que não é liberado).
        if request.method in ('POST', 'DELETE', 'PUT', 'PATCH') and request.path.startswith('/api/'):
            if request.mimetype != 'application/json':
                return jsonify(erro='Envie Content-Type: application/json.'), 415

    @app.after_request
    def after(response):
        u = usuario_atual() or {}
        logging.info('method=%s path=%s status=%s duration_ms=%.1f instance=%s user=%s',
                     request.method, request.path, response.status_code,
                     (time.monotonic() - g.get('started', time.monotonic())) * 1000,
                     INSTANCIA, u.get('login', '-'))
        h = response.headers
        h['X-Content-Type-Options'] = 'nosniff'
        h['X-Frame-Options'] = 'DENY'
        h['Referrer-Policy'] = 'no-referrer'
        h['X-Instancia'] = INSTANCIA
        # Scripts só da própria origem. Estilos inline são necessários porque os
        # componentes Radix/Sonner (shadcn/ui) injetam <style> em tempo de execução.
        h['Content-Security-Policy'] = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                        "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        if request.path.startswith('/api/'):
            h['Cache-Control'] = 'no-store'
        return response

    # ------------------------------------------------------------ páginas e saúde
    # Frontend React (SPA): qualquer rota que não seja da API devolve o index.html
    # e o React Router decide a página (/alunos, /admin/eventos...).
    @app.get('/')
    @app.get('/<path:rota>')
    def spa(rota=''):
        if rota.startswith(('api/', 'health/', 'static/')):
            return jsonify(erro='Recurso não encontrado.'), 404
        return app.send_static_file('index.html')

    @app.get('/health/live')
    def live():
        return jsonify(status='ok', instancia=INSTANCIA)

    @app.get('/health/ready')
    def ready():
        try:
            with engine.connect() as c:
                c.execute(text('SELECT 1'))
            return jsonify(status='ok', banco='conectado', instancia=INSTANCIA)
        except SQLAlchemyError:
            return jsonify(status='indisponivel', banco='desconectado', instancia=INSTANCIA), 503

    @app.get('/api/resumo')
    def resumo():  # público: só contadores, sem dados pessoais (usado na demo do balanceador)
        with engine.connect() as c:
            counts = {n: c.scalar(select(func.count()).select_from(t)) for n, t in TABELAS_ACADEMICAS.items()}
        return jsonify(**counts, instancia=INSTANCIA)

    # ------------------------------------------------------------ autenticação
    @app.post('/api/login')
    def login():
        data = request.get_json(silent=True) or {}
        login_ = str(data.get('usuario', '')).strip().lower()[:40]
        senha = str(data.get('senha', ''))
        if not login_ or not senha:
            return jsonify(erro='Informe usuário e senha.'), 400
        with engine.connect() as c:
            falhas = c.scalar(select(func.count()).select_from(auditoria).where(
                auditoria.c.acao == 'login', auditoria.c.usuario == login_,
                auditoria.c.resultado == 'falha', auditoria.c.quando >= agora() - JANELA_LOGIN))
            u = c.execute(select(usuarios).where(usuarios.c.login == login_)).mappings().first()
        if falhas >= MAX_FALHAS_LOGIN:
            audit('login', 'sessao', 'bloqueado', 'muitas tentativas', {'login': login_})
            return jsonify(erro='Muitas tentativas. Aguarde alguns minutos.'), 429
        if not u or not u['ativo'] or not check_password_hash(u['senha_hash'], senha):
            audit('login', 'sessao', 'falha', None, {'login': login_})
            return jsonify(erro='Usuário ou senha inválidos.'), 401
        session.clear()
        session.permanent = True
        session['usuario'] = {'id': u['id'], 'login': u['login'], 'nome': u['nome'], 'perfil': u['perfil']}
        audit('login', 'sessao')
        return me()

    @app.post('/api/logout')
    def logout():
        if usuario_atual():
            audit('logout', 'sessao')
        session.clear()
        return '', 204

    @app.get('/api/me')
    @exige_login()
    def me():
        u = usuario_atual()
        return jsonify(**u, permissoes={k: u['perfil'] in v for k, v in PODE_ESCREVER.items()},
                       administrador=u['perfil'] in SO_ADMIN)

    # ------------------------------------------------------------ CRUD acadêmico
    def listar(entity):
        with engine.connect() as c:
            if entity == 'matriculas':
                q = (select(matriculas.c.id, matriculas.c.aluno_id, matriculas.c.disciplina_id,
                            alunos.c.nome.label('aluno'), disciplinas.c.nome.label('disciplina'))
                     .join(alunos, matriculas.c.aluno_id == alunos.c.id)
                     .join(disciplinas, matriculas.c.disciplina_id == disciplinas.c.id)
                     .order_by(matriculas.c.id))
            else:
                t = TABELAS_ACADEMICAS[entity]
                q = select(t).order_by(t.c.id)
            rows = [dict(r) for r in c.execute(q).mappings()]
        # Minimização de dados (LGPD): professor não precisa do e-mail completo.
        if entity == 'alunos' and usuario_atual()['perfil'] == 'professor':
            for r in rows:
                r['email'] = mascarar_email(r['email'])
        return jsonify(rows)

    def criar_matricula(values):
        with engine.begin() as c:
            aluno = c.execute(select(alunos).where(alunos.c.id == values['aluno_id'])).mappings().first()
            disc = c.execute(select(disciplinas).where(disciplinas.c.id == values['disciplina_id'])).mappings().first()
            if not aluno or not disc:
                return jsonify(erro='Aluno ou disciplina inexistente.'), 400
            mid = c.execute(matriculas.insert().values(**values)).inserted_primary_key[0]
            # Outbox transacional: se a matrícula for confirmada, o evento também é;
            # se falhar (ex.: duplicidade), o rollback descarta os dois.
            evento_id, momento = str(uuid.uuid4()), agora()
            payload = {'evento_id': evento_id, 'tipo': 'MatriculaCriada', 'ocorrido_em': momento.isoformat(),
                       'matricula_id': mid, 'aluno_id': aluno['id'], 'aluno': aluno['nome'],
                       'aluno_email': aluno['email'], 'disciplina_id': disc['id'], 'disciplina': disc['nome']}
            c.execute(eventos.insert().values(id=evento_id, tipo='MatriculaCriada', payload=json.dumps(payload),
                                              status='pendente', tentativas=0, criado_em=momento,
                                              proxima_tentativa=momento))
        return jsonify(id=mid, evento_id=evento_id, **values), 201

    @app.route('/api/<entity>', methods=['GET', 'POST'])
    @exige_login()
    def collection(entity):
        if entity not in TABELAS_ACADEMICAS:
            return jsonify(erro='Recurso não encontrado.'), 404
        if request.method == 'GET':
            return listar(entity)
        if usuario_atual()['perfil'] not in PODE_ESCREVER[entity]:
            audit('acesso_negado', entity, 'negado', 'POST')
            return jsonify(erro='Seu perfil não tem permissão para esta ação.'), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(erro='Envie um objeto JSON válido.'), 400
        try:
            if entity == 'alunos':
                values = {'nome': valid_name(data.get('nome')), 'email': valid_email(data.get('email', ''))}
            elif entity == 'disciplinas':
                values = {'nome': valid_name(data.get('nome')),
                          'carga_horaria': valid_int(data.get('carga_horaria'), 1, 1000)}
            else:
                values = {k: valid_int(data.get(k), 1, 2147483647) for k in ('aluno_id', 'disciplina_id')}
        except ValueError as e:
            return jsonify(erro=str(e)), 400
        try:
            if entity == 'matriculas':
                resp, status = criar_matricula(values)
            else:
                with engine.begin() as c:
                    new_id = c.execute(TABELAS_ACADEMICAS[entity].insert().values(**values)).inserted_primary_key[0]
                resp, status = jsonify(id=new_id, **values), 201
        except IntegrityError:
            audit('criar', entity, 'conflito')
            return jsonify(erro='Registro duplicado.'), 409
        if status == 201:
            audit('criar', entity, 'sucesso', f'id={resp.json["id"]}')
        return resp, status

    @app.delete('/api/<entity>/<int:identifier>')
    @exige_login()
    def delete(entity, identifier):
        if entity not in TABELAS_ACADEMICAS:
            return jsonify(erro='Recurso não encontrado.'), 404
        if usuario_atual()['perfil'] not in PODE_ESCREVER[entity]:
            audit('acesso_negado', entity, 'negado', f'DELETE id={identifier}')
            return jsonify(erro='Seu perfil não tem permissão para esta ação.'), 403
        t = TABELAS_ACADEMICAS[entity]
        try:
            with engine.begin() as c:
                result = c.execute(t.delete().where(t.c.id == identifier))
        except IntegrityError:
            audit('excluir', entity, 'conflito', f'id={identifier}')
            return jsonify(erro='Registro vinculado a uma matrícula. Remova a matrícula antes de excluir.'), 409
        if not result.rowcount:
            return jsonify(erro='Registro não encontrado.'), 404
        audit('excluir', entity, 'sucesso', f'id={identifier}')
        return '', 204

    # ------------------------------------------------------------ administração
    @app.get('/api/eventos')
    @exige_login(SO_ADMIN)
    def listar_eventos():
        with engine.connect() as c:
            rows = c.execute(select(eventos.c.id, eventos.c.tipo, eventos.c.status, eventos.c.tentativas,
                                    eventos.c.ultimo_erro, eventos.c.criado_em, eventos.c.entregue_em)
                             .order_by(eventos.c.criado_em.desc()).limit(200)).mappings().all()
        return jsonify([{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in r.items()} for r in rows])

    @app.post('/api/eventos/<evento_id>/reprocessar')
    @exige_login(SO_ADMIN)
    def reprocessar(evento_id):
        """Reenvia um evento (inclusive já entregue) para demonstrar a idempotência do consumidor."""
        with engine.begin() as c:
            r = c.execute(update(eventos).where(eventos.c.id == evento_id)
                          .values(status='pendente', proxima_tentativa=agora(), ultimo_erro=None))
        if not r.rowcount:
            return jsonify(erro='Evento não encontrado.'), 404
        audit('reprocessar', 'eventos', 'sucesso', evento_id)
        return jsonify(id=evento_id, status='pendente'), 202

    @app.get('/api/notificacoes')
    @exige_login(SO_ADMIN)
    def listar_notificacoes():
        # Consulta por contrato HTTP: a web não acessa as tabelas do serviço de notificações.
        try:
            with urllib.request.urlopen(notif_url + '/notificacoes', timeout=3) as r:
                return jsonify(json.load(r))
        except OSError:
            return jsonify(erro='Serviço de notificações indisponível.'), 503

    @app.get('/api/auditoria')
    @exige_login(SO_ADMIN)
    def listar_auditoria():
        with engine.connect() as c:
            rows = c.execute(select(auditoria).order_by(auditoria.c.id.desc()).limit(200)).mappings().all()
        return jsonify([{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in r.items()} for r in rows])

    # ------------------------------------------------------------ erros
    @app.errorhandler(SQLAlchemyError)
    def database_error(e):
        logging.error('database_error type=%s', type(e).__name__)
        return jsonify(erro='Banco indisponível. Consulte os logs e tente novamente.'), 503

    return app


if __name__ == '__main__':  # compatibilidade com a base: `python -m app.main` inicializa o banco
    from app.init_db import main
    main()
