"""Loopback-only HTTP adapter. No project directory is exposed as a file server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit, parse_qs

from .engine import Lab, strict_json_loads

class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port, lab):
        super().__init__(('127.0.0.1',port), Handler)
        self.lab=lab

class Handler(BaseHTTPRequestHandler):
    server_version='DataEngineeringLab/1.0'
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self,*args):
        pass

    def respond(self,status,data,content_type='application/json; charset=utf-8'):
        content=json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8') if not isinstance(data,bytes) else data
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError,ConnectionResetError):
            pass

    def check_request(self):
        port=self.server.server_address[1]
        hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
        if len(self.headers.get_all('Host',[]))!=1 or self.headers.get('Host') not in hosts:
            raise PermissionError('Hôte refusé : application locale uniquement.')
        origins=self.headers.get_all('Origin',[])
        if len(origins)>1 or origins and origins[0] not in {'http://'+h for h in hosts}:
            raise PermissionError('Origine refusée.')
        if self.headers.get('Sec-Fetch-Site')=='cross-site':
            raise PermissionError('Requête intersite refusée.')

    def do_OPTIONS(self):
        self.respond(403,dict(ok=False,error='Accès intersite désactivé.'))

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def dispatch(self,method):
        try:
            self.check_request()
            parsed=urlsplit(self.path)
            path=parsed.path
            query={k:v[0] for k,v in parse_qs(parsed.query).items()}
            lab=self.server.lab
            if method=='GET' and path in ('/','/index.html','/style.css','/app.js'):
                filename='index.html' if path in ('/','/index.html') else path[1:]
                content=(lab.root/'web'/filename).read_bytes()
                self.respond(200,content,{'index.html':'text/html; charset=utf-8','style.css':'text/css; charset=utf-8','app.js':'text/javascript; charset=utf-8'}[filename])
                return
            if method=='GET':
                if path=='/api/state':
                    data=lab.state()
                elif path=='/api/schema':
                    data=lab.schema(query.get('env_id'))
                elif path=='/api/profile':
                    data=lab.profile(query.get('env_id'),query.get('table'))
                elif path=='/api/artifacts':
                    data=lab.list_items('artifacts')
                elif path=='/api/runs':
                    data=lab.get('runs',query['id']) if query.get('id') else lab.list_items('runs')[:100]
                elif path=='/api/snapshots':
                    data=[s for s in lab.list_items('snapshots') if s['env_id']==query.get('env_id')]
                else:
                    self.respond(404,dict(ok=False,error='Ressource introuvable.'))
                    return
            else:
                if self.headers.get_content_type()!='application/json' or self.headers.get('Transfer-Encoding'):
                    raise ValueError('Corps JSON avec taille explicite requis.')
                lengths=self.headers.get_all('Content-Length',[])
                if len(lengths)!=1:
                    raise ValueError('Taille de requête invalide.')
                length=int(lengths[0])
                if not 0<length<=1_000_000:
                    raise ValueError('Requête vide ou supérieure à 1 Mo.')
                args=strict_json_loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(args,dict):
                    raise ValueError('Objet JSON attendu.')
                eid=args.get('env_id')
                if path=='/api/environment':
                    data=lab.create_environment(args)
                elif path=='/api/reset':
                    data=lab.regenerate(eid,False)
                elif path=='/api/anomalies':
                    if type(args.get('enabled')) is not bool:
                        raise ValueError('enabled doit être booléen.')
                    data=lab.regenerate(eid,args['enabled'])
                elif path=='/api/snapshot':
                    data=lab.snapshot(eid)
                elif path=='/api/restore':
                    data=lab.restore(eid,args.get('snapshot_id'))
                elif path=='/api/sql':
                    data=lab.sql(eid,args.get('code',''),read_only=args.get('read_only') is True)
                elif path=='/api/artifact':
                    data=lab.save_artifact(args)
                elif path=='/api/python_ack':
                    data=lab.acknowledge(args.get('accepted'))
                elif path in ('/api/python','/api/pipeline'):
                    data=lab.launch(path.split('/')[-1],args)
                elif path=='/api/cancel':
                    data=lab.cancel(args.get('run_id'))
                else:
                    self.respond(404,dict(ok=False,error='Action introuvable.'))
                    return
            self.respond(200,dict(ok=True,data=data))
        except PermissionError as exc:
            self.respond(403,dict(ok=False,error=str(exc)))
        except (ValueError,TypeError,KeyError,sqlite3.Error,TimeoutError) as exc:
            self.respond(400,dict(ok=False,error=str(exc)))
        except Exception as exc:
            self.respond(500,dict(ok=False,error='Échec de l’opération : '+str(exc)))

