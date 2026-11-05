import os, time, logging, socket
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey, UniqueConstraint, select, func, text, event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
metadata = MetaData()
alunos = Table('alunos', metadata, Column('id',Integer,primary_key=True), Column('nome',String(100),nullable=False), Column('email',String(160),unique=True,nullable=False))
disciplinas = Table('disciplinas',metadata,Column('id',Integer,primary_key=True),Column('nome',String(100),unique=True,nullable=False),Column('carga_horaria',Integer,nullable=False))
matriculas = Table('matriculas',metadata,Column('id',Integer,primary_key=True),Column('aluno_id',Integer,ForeignKey('alunos.id'),nullable=False),Column('disciplina_id',Integer,ForeignKey('disciplinas.id'),nullable=False),UniqueConstraint('aluno_id','disciplina_id'))
tables={'alunos':alunos,'disciplinas':disciplinas,'matriculas':matriculas}
def make_engine(url):
    engine=create_engine(url,pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def foreign_keys(dbapi_conn, _): dbapi_conn.execute('PRAGMA foreign_keys=ON')
    return engine

def initialize(engine):
    metadata.create_all(engine)
    with engine.begin() as c:
        if c.scalar(select(func.count()).select_from(alunos)) == 0:
            c.execute(alunos.insert(), [{'nome':'Ana Exemplo','email':'ana@example.test'},{'nome':'Bruno Exemplo','email':'bruno@example.test'}])
        if c.scalar(select(func.count()).select_from(disciplinas)) == 0:
            c.execute(disciplinas.insert(), [{'nome':'Docker','carga_horaria':40},{'nome':'Computação em Nuvem','carga_horaria':40}])

def create_app(url=None):
    app=Flask(__name__,static_folder='static',static_url_path='/static')
    app.config['MAX_CONTENT_LENGTH']=16384
    engine=make_engine(url or os.environ['DATABASE_URL'])
    app.extensions['engine']=engine
    @app.before_request
    def before(): request.started=time.monotonic()
    @app.after_request
    def after(response):
        logging.info('method=%s path=%s status=%s duration_ms=%.1f instance=%s', request.method,request.path,response.status_code,(time.monotonic()-request.started)*1000,socket.gethostname())
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'"
        return response
    @app.get('/')
    def home(): return app.send_static_file('index.html')
    @app.get('/health/live')
    def live(): return jsonify(status='ok',instancia=socket.gethostname())
    @app.get('/health/ready')
    def ready():
        try:
            with engine.connect() as c: c.execute(text('SELECT 1'))
            return jsonify(status='ok',banco='conectado')
        except SQLAlchemyError: return jsonify(status='indisponivel',banco='desconectado'),503
    @app.get('/api/resumo')
    def resumo():
        with engine.connect() as c: counts={name:c.scalar(select(func.count()).select_from(t)) for name,t in tables.items()}
        return jsonify(**counts,instancia=socket.gethostname())
    @app.route('/api/<entity>',methods=['GET','POST'])
    def collection(entity):
        if entity not in tables: return jsonify(erro='Recurso não encontrado.'),404
        t=tables[entity]
        if request.method=='GET':
            with engine.connect() as c:
                if entity=='matriculas':
                    q=select(matriculas.c.id,matriculas.c.aluno_id,matriculas.c.disciplina_id,alunos.c.nome.label('aluno'),disciplinas.c.nome.label('disciplina')).join(alunos,matriculas.c.aluno_id==alunos.c.id).join(disciplinas,matriculas.c.disciplina_id==disciplinas.c.id).order_by(matriculas.c.id)
                else: q=select(t).order_by(t.c.id)
                return jsonify([dict(r) for r in c.execute(q).mappings()])
        data=request.get_json(silent=True)
        if not isinstance(data,dict): return jsonify(erro='Envie um objeto JSON válido.'),400
        try:
            if entity=='alunos':
                nome=valid_name(data.get('nome'))
                email=data.get('email','')
                if not isinstance(email,str) or len(email)>160 or '@' not in email or '.' not in email.split('@')[-1] or any(c.isspace() for c in email): raise ValueError('Informe um e-mail válido (até 160 caracteres).')
                values={'nome':nome,'email':email.strip().lower()}
            elif entity=='disciplinas':
                values={'nome':valid_name(data.get('nome')),'carga_horaria':valid_int(data.get('carga_horaria'),1,1000)}
            else: values={k:valid_int(data.get(k),1,2147483647) for k in ('aluno_id','disciplina_id')}
        except ValueError as e: return jsonify(erro=str(e)),400
        with engine.begin() as c:
            if entity=='matriculas':
                if not c.scalar(select(alunos.c.id).where(alunos.c.id==values['aluno_id'])) or not c.scalar(select(disciplinas.c.id).where(disciplinas.c.id==values['disciplina_id'])):
                    return jsonify(erro='Aluno ou disciplina inexistente.'),400
            result=c.execute(t.insert().values(**values))
            return jsonify(id=result.inserted_primary_key[0],**values),201
    @app.delete('/api/<entity>/<int:identifier>')
    def delete(entity,identifier):
        if entity not in tables: return jsonify(erro='Recurso não encontrado.'),404
        with engine.begin() as c: result=c.execute(tables[entity].delete().where(tables[entity].c.id==identifier))
        if not result.rowcount: return jsonify(erro='Registro não encontrado.'),404
        return '',204
    @app.errorhandler(IntegrityError)
    def conflict(e): return jsonify(erro='Registro duplicado ou vinculado a uma matrícula. Remova a matrícula antes de excluir aluno ou disciplina.'),409
    @app.errorhandler(SQLAlchemyError)
    def database_error(e):
        logging.error('database_error type=%s',type(e).__name__)
        return jsonify(erro='Banco indisponível. Consulte os logs e tente novamente.'),503
    return app

def valid_name(value):
    if not isinstance(value,str) or not 2<=len(value.strip())<=100: raise ValueError('Nome deve ter de 2 a 100 caracteres.')
    return value.strip()
def valid_int(value,minimum,maximum):
    if isinstance(value,bool) or not isinstance(value,int) or not minimum<=value<=maximum: raise ValueError(f'Valor inteiro esperado entre {minimum} e {maximum}.')
    return value
if __name__=='__main__':
    import sys
    engine=make_engine(os.environ['DATABASE_URL'])
    initialize(engine)
    print('Banco inicializado com dados fictícios.')
