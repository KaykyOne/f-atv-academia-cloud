import os, tempfile, unittest
from app.main import create_app, initialize, metadata

class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        url=os.getenv('TEST_DATABASE_URL','sqlite:///'+self.tmp.name+'/test.db')
        self.app=create_app(url)
        self.engine=self.app.extensions['engine']
        metadata.drop_all(self.engine)
        initialize(self.engine)
        self.client=self.app.test_client()
    def tearDown(self):
        metadata.drop_all(self.engine)
        self.engine.dispose()
        self.tmp.cleanup()
    def test_full_flow_and_relations(self):
        c=self.client
        with c.get('/') as response: self.assertEqual(response.status_code,200)
        with c.get('/static/app.js') as response: self.assertEqual(response.status_code,200)
        a=c.post('/api/alunos',json={'nome':'Teste Aluno','email':'teste@example.test'})
        self.assertEqual(a.status_code,201)
        aid=a.json['id']
        d=c.post('/api/disciplinas',json={'nome':'Teste Disciplina','carga_horaria':60})
        self.assertEqual(d.status_code,201)
        did=d.json['id']
        m=c.post('/api/matriculas',json={'aluno_id':aid,'disciplina_id':did})
        self.assertEqual(m.status_code,201)
        self.assertEqual(c.get('/api/matriculas').json[0]['aluno'],'Teste Aluno')
        self.assertEqual(c.post('/api/matriculas',json={'aluno_id':aid,'disciplina_id':did}).status_code,409)
        self.assertEqual(c.delete('/api/alunos/'+str(aid)).status_code,409)
        self.assertEqual(c.delete('/api/matriculas/'+str(m.json['id'])).status_code,204)
        self.assertEqual(c.delete('/api/alunos/'+str(aid)).status_code,204)
        self.assertEqual(c.delete('/api/disciplinas/'+str(did)).status_code,204)
    def test_validation_and_duplicates(self):
        c=self.client
        self.assertEqual(c.post('/api/alunos',json={'nome':'A','email':'a'}).status_code,400)
        self.assertEqual(c.post('/api/alunos',json={'nome':'Outro','email':'ana@example.test'}).status_code,409)
        self.assertEqual(c.post('/api/disciplinas',json={'nome':'Xpto','carga_horaria':True}).status_code,400)
        self.assertEqual(c.post('/api/matriculas',json={'aluno_id':999,'disciplina_id':1}).status_code,400)
        self.assertEqual(c.post('/api/alunos',json=[]).status_code,400)
        self.assertEqual(c.get('/api/desconhecido').status_code,404)
        self.assertEqual(c.delete('/api/alunos/9999').status_code,404)
    def test_health_seed_and_persistence(self):
        self.assertEqual(self.client.get('/health/live').status_code,200)
        self.assertEqual(self.client.get('/health/ready').status_code,200)
        initialize(self.engine)
        self.assertEqual(self.client.get('/api/resumo').json['alunos'],2)
        other=create_app(str(self.engine.url))
        try: self.assertEqual(other.test_client().get('/api/resumo').json['disciplinas'],2)
        finally: other.extensions['engine'].dispose()

if __name__=='__main__': unittest.main()
