"""Disposable v1.1 browser QA, never targets the user's catalogue or databases."""
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.engine import Lab
from lab.server import Server, Handler
from lab.storage import database

fixture=ROOT/'work/v1.1-ui-validation'
fixture.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'web',fixture/'web',dirs_exist_ok=True)
lab=Lab(fixture)
if not any(e['name']=='QA — Clés composites' for e in lab.list_items('environments')):
    env=lab.create_environment(dict(name='QA — Clés composites',kind='events',size=0))
    with database(env['db_path']) as c:
        c.executescript("""CREATE TABLE qa_parent(b INTEGER,a INTEGER,label TEXT,PRIMARY KEY(a,b));
        CREATE TABLE qa_child(x INTEGER,y INTEGER,z INTEGER,calc INTEGER GENERATED ALWAYS AS (x+y),
          FOREIGN KEY(x,y) REFERENCES qa_parent ON DELETE CASCADE,
          FOREIGN KEY(z,y) REFERENCES qa_parent(a,b));
        CREATE TABLE qa_self(id INTEGER PRIMARY KEY,parent INTEGER REFERENCES qa_self(id));
        CREATE TABLE qa_orphan(x REFERENCES absent(id));
        CREATE TABLE qa_lookalike(qa_parent_id INTEGER);
        CREATE TABLE "__proto__"(id INTEGER PRIMARY KEY);
        CREATE TABLE qa_proto_link(p INTEGER REFERENCES "__proto__"(id));""")
if not any(e['name']=='QA — Grand schéma' for e in lab.list_items('environments')):
    env=lab.create_environment(dict(name='QA — Grand schéma',kind='events',size=0))
    with database(env['db_path']) as c:
        for i in range(50):
            cols=', '.join(f'value_{j} TEXT' for j in range(8))
            fk=f', parent_id INTEGER REFERENCES qa_table_{i-1:02d}(id)' if i else ''
            c.execute(f'CREATE TABLE qa_table_{i:02d}(id INTEGER PRIMARY KEY,{cols}{fk})')
class FixtureHandler(Handler):
    def dispatch(self,method):
        flag=fixture/'fail-preferences-once'
        if method=='GET' and self.path=='/api/preferences' and flag.exists():
            self.check_request()
            try:flag.unlink()
            except FileNotFoundError:pass
            else:
                self.respond(503,dict(ok=False,error='Indisponibilité simulée pour le contrôle de reprise.'))
                return
        super().dispatch(method)
server=Server(8768,lab)
server.RequestHandlerClass=FixtureHandler
print('QA v1.1 : http://127.0.0.1:8768',flush=True)
try:server.serve_forever(poll_interval=.1)
except KeyboardInterrupt:pass
finally:server.server_close();lab.shutdown()
