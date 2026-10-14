"""Independent real loopback HTTP tests; temporary files only under project/work."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
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
