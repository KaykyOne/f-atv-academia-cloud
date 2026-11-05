import os
import tempfile
import unittest

os.environ.setdefault('NOTIF_SCHEMA', '')  # SQLite não tem schemas

from app.main import create_app
from app.init_db import initialize
from app.models import metadata, notif_metadata, eventos
from app.notificacoes import create_notif_app
from app.publicador import processar_lote
from sqlalchemy import select

SENHAS = {'admin': 'senha-admin-teste', 'secretaria': 'senha-secretaria-teste', 'professor': 'senha-prof-teste'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.url = os.getenv('TEST_DATABASE_URL', 'sqlite:///' + self.tmp.name + '/test.db')
        self.app = create_app(self.url)
        self.engine = self.app.extensions['engine']
        metadata.drop_all(self.engine)
        notif_metadata.drop_all(self.engine)
        initialize(self.engine, SENHAS)
        self.client = self.app.test_client()

    def tearDown(self):
        metadata.drop_all(self.engine)
        notif_metadata.drop_all(self.engine)
        self.engine.dispose()
        self.tmp.cleanup()

    def login(self, usuario, client=None):
        r = (client or self.client).post('/api/login', json={'usuario': usuario, 'senha': SENHAS[usuario]})
        self.assertEqual(r.status_code, 200, r.json)
        return r


class ApiTest(Base):
    def test_full_flow_and_relations(self):
        c = self.client
        self.login('admin')
        with c.get('/') as response:
            self.assertEqual(response.status_code, 200)
        with c.get('/alunos') as response:  # rota da SPA devolve o index.html
            self.assertEqual(response.status_code, 200)
        self.assertEqual(c.get('/api/inexistente/1/x').status_code, 404)
        a = c.post('/api/alunos', json={'nome': 'Teste Aluno', 'email': 'teste@example.test'})
        self.assertEqual(a.status_code, 201)
        aid = a.json['id']
        d = c.post('/api/disciplinas', json={'nome': 'Teste Disciplina', 'carga_horaria': 60})
        self.assertEqual(d.status_code, 201)
        did = d.json['id']
        m = c.post('/api/matriculas', json={'aluno_id': aid, 'disciplina_id': did})
        self.assertEqual(m.status_code, 201)
        self.assertEqual(c.get('/api/matriculas').json[0]['aluno'], 'Teste Aluno')
        self.assertEqual(c.post('/api/matriculas', json={'aluno_id': aid, 'disciplina_id': did}).status_code, 409)
        self.assertEqual(c.delete('/api/alunos/' + str(aid), json={}).status_code, 409)
        self.assertEqual(c.delete('/api/matriculas/' + str(m.json['id']), json={}).status_code, 204)
        self.assertEqual(c.delete('/api/alunos/' + str(aid), json={}).status_code, 204)
        self.assertEqual(c.delete('/api/disciplinas/' + str(did), json={}).status_code, 204)

    def test_validation_and_duplicates(self):
        c = self.client
        self.login('admin')
        self.assertEqual(c.post('/api/alunos', json={'nome': 'A', 'email': 'a'}).status_code, 400)
        self.assertEqual(c.post('/api/alunos', json={'nome': 'Outro', 'email': 'ana@example.test'}).status_code, 409)
        self.assertEqual(c.post('/api/disciplinas', json={'nome': 'Xpto', 'carga_horaria': True}).status_code, 400)
        self.assertEqual(c.post('/api/matriculas', json={'aluno_id': 999, 'disciplina_id': 1}).status_code, 400)
        self.assertEqual(c.post('/api/alunos', json=[]).status_code, 400)
        self.assertEqual(c.get('/api/desconhecido').status_code, 404)
        self.assertEqual(c.delete('/api/alunos/9999', json={}).status_code, 404)

    def test_health_seed_and_persistence(self):
        self.assertEqual(self.client.get('/health/live').status_code, 200)
        self.assertEqual(self.client.get('/health/ready').status_code, 200)
        initialize(self.engine, SENHAS)  # seed idempotente
        self.assertEqual(self.client.get('/api/resumo').json['alunos'], 2)
        other = create_app(str(self.engine.url))
        try:
            self.assertEqual(other.test_client().get('/api/resumo').json['disciplinas'], 2)
        finally:
            other.extensions['engine'].dispose()


class SegurancaTest(Base):
    def test_login_obrigatorio_e_resumo_publico(self):
        self.assertEqual(self.client.get('/api/alunos').status_code, 401)
        self.assertEqual(self.client.get('/api/resumo').status_code, 200)
        self.assertEqual(self.client.post('/api/login', json={'usuario': 'admin', 'senha': 'errada'}).status_code, 401)

    def test_matriz_de_permissoes(self):
        prof = self.app.test_client()
        self.login('professor', prof)
        self.assertEqual(prof.post('/api/alunos', json={'nome': 'Xx', 'email': 'x@example.test'}).status_code, 403)
        self.assertEqual(prof.post('/api/disciplinas', json={'nome': 'Redes', 'carga_horaria': 20}).status_code, 201)
        self.assertEqual(prof.get('/api/auditoria').status_code, 403)
        self.assertTrue(prof.get('/api/alunos').json[0]['email'].startswith('a***@'))  # e-mail mascarado
        sec = self.app.test_client()
        self.login('secretaria', sec)
        self.assertEqual(sec.post('/api/alunos', json={'nome': 'Yy', 'email': 'y@example.test'}).status_code, 201)
        self.assertEqual(sec.post('/api/disciplinas', json={'nome': 'Outra', 'carga_horaria': 20}).status_code, 403)
        self.assertEqual(sec.get('/api/alunos').json[0]['email'], 'ana@example.test')
        adm = self.app.test_client()
        self.login('admin', adm)
        acoes = [a['acao'] for a in adm.get('/api/auditoria').json]
        self.assertIn('acesso_negado', acoes)

    def test_csrf_exige_json(self):
        self.login('admin')
        r = self.client.post('/api/alunos', data={'nome': 'Form', 'email': 'f@example.test'})
        self.assertEqual(r.status_code, 415)

    def test_bloqueio_forca_bruta(self):
        for _ in range(5):
            self.client.post('/api/login', json={'usuario': 'admin', 'senha': 'errada'})
        r = self.client.post('/api/login', json={'usuario': 'admin', 'senha': SENHAS['admin']})
        self.assertEqual(r.status_code, 429)


class EventosTest(Base):
    def setUp(self):
        super().setUp()
        self.notif = create_notif_app(self.url).test_client()

    def enviar(self, ev):
        import json
        r = self.notif.post('/events', json={'evento_id': ev['id'], 'tipo': ev['tipo'], 'dados': json.loads(ev['payload'])})
        if r.status_code >= 400:
            raise OSError('HTTP %s' % r.status_code)
        return r.json['status']

    def eventos(self):
        with self.engine.connect() as c:
            return c.execute(select(eventos)).mappings().all()

    def test_outbox_entrega_e_idempotencia(self):
        self.login('admin')
        m = self.client.post('/api/matriculas', json={'aluno_id': 1, 'disciplina_id': 1})
        self.assertEqual(m.status_code, 201)
        # Matrícula rejeitada (duplicada) não gera evento.
        self.assertEqual(self.client.post('/api/matriculas', json={'aluno_id': 1, 'disciplina_id': 1}).status_code, 409)
        self.assertEqual(len(self.eventos()), 1)
        self.assertEqual(self.eventos()[0]['status'], 'pendente')

        # Consumidor fora do ar: evento continua pendente.
        def fora_do_ar(ev):
            raise OSError('connection refused')
        self.assertEqual(processar_lote(self.engine, fora_do_ar), (0, 1))
        ev = self.eventos()[0]
        self.assertEqual((ev['status'], ev['tentativas']), ('pendente', 1))

        # Consumidor volta: evento entregue e notificação registrada.
        with self.engine.begin() as c:
            c.execute(eventos.update().values(proxima_tentativa=ev['criado_em']))
        self.assertEqual(processar_lote(self.engine, self.enviar), (1, 0))
        self.assertEqual(self.eventos()[0]['status'], 'entregue')
        self.assertEqual(len(self.notif.get('/notificacoes').json), 1)

        # Reprocessar o mesmo evento não duplica a notificação.
        self.assertEqual(self.client.post(f"/api/eventos/{ev['id']}/reprocessar", json={}).status_code, 202)
        with self.engine.begin() as c:
            c.execute(eventos.update().values(proxima_tentativa=ev['criado_em']))
        processar_lote(self.engine, self.enviar)
        self.assertEqual(len(self.notif.get('/notificacoes').json), 1)
        self.assertEqual(self.notif.post('/events', json={'evento_id': 'x'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
