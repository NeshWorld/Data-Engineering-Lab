"""Independent real loopback HTTP tests; temporary files only under project/work."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from lab.engine import Lab
from lab.server import Server
ROOT=Path(__file__).resolve().parents[1]

class ServerCase(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='test-server-',dir=ROOT/'work'); self.root=Path(self.temp.name)
        (self.root/'web').mkdir()
        for name,code in [('index.html','<!doctype html><title>QA local</title>'),('app.js','/* QA */'),('style.css','body {}')]:
            (self.root/'web'/name).write_text(code,encoding='utf-8')
        self.lab=Lab(self.root,bootstrap=False); self.server=Server(0,self.lab)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True); self.thread.start()
        self.port=self.server.server_address[1]; self.host='127.0.0.1:'+str(self.port)
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3); self.lab.shutdown(); self.temp.cleanup()
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        try:
            c.request(method,path,body=body,headers=headers or {}); r=c.getresponse(); content=r.read()
            data=json.loads(content) if r.getheader('Content-Type','').startswith('application/json') else content
            return r.status,dict(r.getheaders()),data
        finally:c.close()
    def post(self,path,payload,headers=None):
        return self.request('POST',path,json.dumps(payload).encode('utf-8'),{'Content-Type':'application/json',**(headers or {})})
    def test_api_create_query_save_reset_state(self):
        status,_,r=self.post('/api/environment',dict(name='Fictif API',kind='commerce',seed=3,size=4)); self.assertEqual(status,200,r); eid=r['data']['id']
        status,_,r=self.post('/api/sql',dict(env_id=eid,code='SELECT 6*7 AS answer;')); self.assertEqual(status,200,r); self.assertEqual(r['data']['rows'],[[42]])
        status,_,saved=self.post('/api/artifact',dict(env_id=eid,kind='sql',name='API saved',code='SELECT 42;')); self.assertEqual(status,200,saved)
        self.assertEqual(self.post('/api/reset',dict(env_id=eid))[0],200)
        status,_,state=self.request('GET','/api/state'); self.assertEqual(status,200); self.assertEqual(state['data']['artifacts'][0]['id'],saved['data']['id'])
        self.assertEqual(self.request('GET','/api/schema?env_id='+eid)[0],200)
    def test_preferences_http_and_new_static_modules(self):
        self.assertEqual(self.request('GET','/api/preferences')[2]['data']['theme'],'emerald')
        self.assertEqual(self.post('/api/preferences',{'theme':'amethyst'})[0],200)
        self.assertEqual(self.request('GET','/api/preferences')[2]['data']['theme'],'amethyst')
        self.assertEqual(self.post('/api/preferences',{'theme':'invalid'})[0],400)
        for filename in ['themes.js','themes.css','python-editor.js','er-diagram.js','er-diagram.css','practice.js','practice.css','sandbox.js']:
            (self.root/'web'/filename).write_text('/* fixture */',encoding='utf-8')
            status,headers,_=self.request('GET','/'+filename)
            self.assertEqual(status,200)
            self.assertIn('text/css' if filename.endswith('.css') else 'text/javascript',headers['Content-Type'])

    def test_sandbox_create_structured_crud_export_import_restore(self):
        status,_,response=self.post('/api/sandbox/create',dict(name='Libre HTTP',table_count=0))
        self.assertEqual(status,200,response);eid=response['data']['id']
        status,_,info=self.request('GET','/api/sandbox/info?env_id='+eid);self.assertEqual(status,200);self.assertTrue(info['data']['is_sandbox'])
        status,_,result=self.post('/api/sandbox/action',dict(env_id=eid,operation='create_table',table='notes',columns=[dict(name='id',type='INTEGER',primary_key=True),dict(name='value',type='TEXT')]))
        self.assertEqual(status,200,result)
        self.assertEqual(self.post('/api/sandbox/action',dict(env_id=eid,operation='insert_row',table='notes',values={'id':1,'value':'conservé'}))[0],200)
        status,_,changed=self.post('/api/sandbox/action',dict(env_id=eid,operation='delete_row',table='notes',key={'id':1}));self.assertEqual(status,200,changed)
        self.assertEqual(self.post('/api/restore',dict(env_id=eid,snapshot_id=changed['data']['snapshot_id']))[0],200)
        status,_,export=self.request('GET','/api/sandbox/export?env_id='+eid+'&table=notes&format=json')
        self.assertEqual(status,200,export);self.assertEqual(json.loads(export['data']['content']),[{'id':1,'value':'conservé'}])
        self.assertEqual(self.post('/api/sandbox/import',dict(env_id=eid,table='bad',format='csv',text='a,b\n"unclosed'))[0],400)
        self.assertEqual(self.post('/api/sandbox/duplicate',dict(env_id=eid,name='Autre copie'))[0],200)

    def test_training_http_real_validation_hints_and_durable_progress(self):
        status,_,catalog=self.request('GET','/api/training/catalog');self.assertEqual(status,200,catalog)
        self.assertEqual(len(catalog['data']['exercises']),10);self.assertEqual(len(catalog['data']['skills']),55)
        self.assertTrue(all('hints' not in e and 'validator_id' not in e and 'solution' not in e for e in catalog['data']['exercises']))
        eid='py-normaliser-evenements'
        status,_,opened=self.post('/api/training/start',{'exercise_id':eid});self.assertEqual(status,200,opened)
        self.assertEqual(opened['data']['progress']['status'],'started');self.assertEqual(opened['data']['hints'],[])
        status,_,hints=self.post('/api/training/hint',{'exercise_id':eid});self.assertEqual(status,200);self.assertEqual(hints['data']['revealed_count'],1)
        code="def normaliser_evenements(lignes):\n    vus=set()\n    resultat=[]\n    for ligne in lignes:\n        brut=ligne.get('id')\n        ident='' if brut is None else str(brut).strip()\n        if not ident or ident in vus: continue\n        ville=ligne.get('ville')\n        vus.add(ident)\n        resultat.append({'id':ident,'ville':'' if ville is None else str(ville).strip().title()})\n    return resultat\n"
        self.assertEqual(self.post('/api/training/validate',{'exercise_id':eid,'code':code})[0],403)
        self.post('/api/python_ack',{'accepted':True})
        self.assertEqual(self.post('/api/training/save',{'exercise_id':eid,'code':code,'notes':'À revoir les données vides','needs_review':True})[0],200)
        status,_,started=self.post('/api/training/validate',{'exercise_id':eid,'code':code});self.assertEqual(status,200,started)
        aid=started['data']['attempt_id'];deadline=time.monotonic()+10
        while True:
            status,_,attempt=self.request('GET','/api/training/attempt?id='+aid);self.assertEqual(status,200)
            if attempt['data']['status']!='running':break
            self.assertLess(time.monotonic(),deadline);time.sleep(.02)
        self.assertEqual(attempt['data']['status'],'success',attempt);self.assertEqual(attempt['data']['passed'],3)
        progress=self.request('GET','/api/training/exercise?id='+eid)[2]['data']['progress']
        self.assertEqual(progress['status'],'completed');self.assertTrue(progress['needs_review']);self.assertEqual(progress['attempt_count'],1)
        self.assertEqual(self.request('GET','/api/training/attempt?id=../../invalid')[0],400)
        self.assertEqual(self.post('/api/training/save',{'exercise_id':eid,'code':'x','notes':'x'*5001})[0],400)

    def test_host_origin_fetch_site_controls(self):
        for headers in [{'Host':'attacker.example'},{'Host':'127.0.0.1:1'},{'Origin':'https://attacker.example'},{'Origin':'null'},{'Sec-Fetch-Site':'cross-site'}]:
            with self.subTest(headers=headers):self.assertEqual(self.request('GET','/api/state',headers=headers)[0],403)
        self.assertEqual(self.request('GET','/api/state',headers={'Origin':'http://'+self.host})[0],200)
    def test_duplicate_host_rejected(self):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        try:
            c.putrequest('GET','/api/state',skip_host=True); c.putheader('Host',self.host); c.putheader('Host',self.host); c.endheaders()
            r=c.getresponse(); self.assertEqual(r.status,403); r.read()
        finally:c.close()
    def test_post_json_content_type_object_and_length(self):
        cases=[('accepted=true',{'Content-Type':'application/x-www-form-urlencoded'}),('{broken',{'Content-Type':'application/json'}),('[]',{'Content-Type':'application/json'}),('true',{'Content-Type':'application/json'}),('{}',{'Content-Type':'application/json','Content-Length':'0'}),('{}',{'Content-Type':'application/json','Content-Length':'1000001'})]
        for body,headers in cases:
            with self.subTest(body=body,headers=headers):self.assertEqual(self.request('POST','/api/python_ack',body,headers)[0],400)
    def test_transfer_encoding_duplicate_length_rejected(self):
        for duplicate in [False,True]:
            with self.subTest(duplicate=duplicate):
                c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
                try:
                    c.putrequest('POST','/api/python_ack'); c.putheader('Content-Type','application/json'); c.putheader('Content-Length','2')
                    c.putheader('Content-Length' if duplicate else 'Transfer-Encoding','2' if duplicate else 'chunked'); c.endheaders(b'{}')
                    r=c.getresponse(); self.assertEqual(r.status,400); r.read()
                finally:c.close()
    def test_static_allowlist_and_traversal(self):
        for path in ['/../data/catalog.sqlite','/%2e%2e/data/catalog.sqlite','/data/catalog.sqlite','/experiments/test.py','/web/index.html','/app.js/../data/catalog.sqlite']:
            with self.subTest(path=path):self.assertEqual(self.request('GET',path)[0],404)
        for path in ['/','/index.html','/style.css','/app.js']:
            with self.subTest(path=path):
                status,headers,_=self.request('GET',path); self.assertEqual(status,200); self.assertNotIn('Access-Control-Allow-Origin',headers)
                self.assertEqual(headers['X-Content-Type-Options'],'nosniff'); self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
    def test_options_unknown_routes(self):
        self.assertEqual(self.request('OPTIONS','/api/state')[0],403); self.assertEqual(self.request('GET','/api/nonexistent')[0],404); self.assertEqual(self.post('/api/nonexistent',{})[0],404)
    def test_python_consent_invalid_identifiers(self):
        env=self.post('/api/environment',dict(name='Fictif',kind='events',size=0))[2]['data']
        self.assertEqual(self.post('/api/python',dict(env_id=env['id'],code='print(1)'))[0],403)
        self.assertEqual(self.post('/api/python_ack',{'accepted':1})[0],400); self.assertEqual(self.post('/api/python_ack',{'accepted':True})[0],200)
        self.assertEqual(self.post('/api/sql',{'env_id':'../../outside','code':'SELECT 1;'})[0],400)

    def test_nonfinite_request_rejected(self):
        status,_,r=self.request('POST','/api/environment','{"size":NaN}',{'Content-Type':'application/json'})
        self.assertEqual(status,400,r)
        self.assertTrue(self.request('GET','/api/state')[2]['ok'])

    def test_overflow_json_request_rejected(self):
        status,_,r=self.request('POST','/api/environment','{"extra":[1e999]}',{'Content-Type':'application/json'})
        self.assertEqual(status,400,r)
        self.assertTrue(self.request('GET','/api/state')[2]['ok'])

if __name__=='__main__':unittest.main()
