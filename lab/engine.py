"""Persistent experiments, bounded SQL and local asynchronous execution."""
from __future__ import annotations
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from .storage import database, backup_database, publish_files
from .sql_engine import execute_sql, identifier, safe_json, reject_constant, strict_json_loads

from .datasets import generate, GENERATOR_VERSION

def now():
    return datetime.now(timezone.utc).isoformat()

class Lab:
    def __init__(self, root: Path, bootstrap=True):
        self.root = root.resolve()
        self.lock = threading.RLock()
        self.jobs = {}
        for name in ('data/environments','data/snapshots','experiments','work/runs'):
            (self.root/name).mkdir(parents=True, exist_ok=True)
        self.catalog = self.root/'data/catalog.sqlite'
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS environments(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);''')
        for run in self.list_items('runs'):
            if run['status'] == 'running':
                run.update(status='error', error='Application fermée pendant l’exécution. Relancez cette expérience.')
                self.put('runs', run)
        if bootstrap and not self.list_items('environments'):
            for kind, name in [('commerce','Commerce & distribution'),('logistics','Logistique'),
                               ('events','Événements applicatifs'),('imperfect','Données imparfaites')]:
                self.create_environment(dict(name=name,kind=kind,seed=42,size=300,anomalies=False))

    def connect(self):
        return database(self.catalog, timeout=10)

    def list_items(self, table):
        with self.lock, self.connect() as c:
            return [json.loads(row[0]) for row in c.execute(f'SELECT payload FROM {table} ORDER BY rowid DESC')]

    def put(self, table, payload):
        with self.lock, self.connect() as c:
            c.execute(f'INSERT OR REPLACE INTO {table}(id,payload) VALUES (?,?)', (payload['id'],json.dumps(payload,ensure_ascii=False,allow_nan=False)))
        return payload

    def get(self, table, item_id):
        if not isinstance(item_id,str) or not re.fullmatch('[a-f0-9]{32}', item_id):
            raise ValueError('Identifiant invalide.')
        with self.lock, self.connect() as c:
            row = c.execute(f'SELECT payload FROM {table} WHERE id=?',(item_id,)).fetchone()
        if not row:
            raise ValueError('Élément introuvable.')
        return json.loads(row[0])

    def state(self):
        with self.lock, self.connect() as c:
            ack = c.execute("SELECT value FROM settings WHERE key='python_ack'").fetchone()
        return dict(environments=self.list_items('environments'),artifacts=self.list_items('artifacts'),
                    runs=self.list_items('runs')[:100],python_ack=bool(ack),root=str(self.root),
                    python=sys.executable,pandas=importlib.util.find_spec('pandas') is not None)

    def acknowledge(self, accepted):
        if accepted is not True:
            raise ValueError('Le consentement explicite est requis.')
        with self.lock, self.connect() as c:
            c.execute("INSERT OR REPLACE INTO settings VALUES ('python_ack','true')")
        return dict(accepted=True)

    def create_environment(self, args):
        kind = args.get('kind','commerce')
        name = str(args.get('name',kind)).strip()[:120]
        if not name:
            raise ValueError('Nom requis.')
        seed, size = args.get('seed',42), args.get('size',300)
        if type(seed) is not int or not 0 <= seed <= 2147483647 or type(size) is not int or not 0 <= size <= 10000:
            raise ValueError('Graine : 0 à 2147483647 ; volume : 0 à 10000 entiers.')
        anomaly = args.get('anomalies',False)
        if type(anomaly) is not bool:
            raise ValueError('Le choix anomalies doit être booléen.')
        eid = uuid.uuid4().hex
        path = self.root/'data/environments'/eid/'lab.sqlite'
        with self.lock:
            stats = generate(path,kind,seed,size,anomaly)
            return self.put('environments',dict(id=eid,name=name,kind=kind,seed=seed,size=size,
                            anomalies=anomaly,generator_version=GENERATOR_VERSION,db_path=str(path),stats=stats,created=now()))

    def regenerate(self, eid, anomalies=False):
        with self.lock:
            env = self.get('environments',eid)
            stats = generate(Path(env['db_path']),env['kind'],env['seed'],env['size'],anomalies)
            env.update(anomalies=anomalies,stats=stats,generator_version=GENERATOR_VERSION)
            return self.put('environments',env)

    def snapshot(self, eid):
        with self.lock:
            env = self.get('environments',eid)
            sid = uuid.uuid4().hex
            folder = self.root/'data/snapshots'/sid
            folder.mkdir()
            with database(env['db_path']) as src, database(folder/'lab.sqlite') as dst:
                backup_database(src,dst)
            for f in ('source.csv','source.json'):
                shutil.copy2(Path(env['db_path']).parent/f,folder/f)
            return self.put('snapshots',dict(id=sid,env_id=eid,name='Sauvegarde '+now(),created=now(),environment=env))

    def restore(self,eid,sid):
        with self.lock:
            snap = self.get('snapshots',sid)
            if snap['env_id'] != eid:
                raise ValueError('Sauvegarde d’un autre environnement.')
            env = self.get('environments',eid)
            folder = self.root/'data/snapshots'/sid
            target=Path(env['db_path'])
            if any(Path(str(target)+suffix).exists() for suffix in ('-wal','-shm','-journal')):
                raise ValueError('Fermez les connexions SQLite externes avant la restauration.')
            staging=target.parent/('.restore-'+uuid.uuid4().hex)
            staging.mkdir()
            try:
                with database(folder/'lab.sqlite') as src, database(staging/'lab.sqlite') as dst:
                    backup_database(src,dst)
                for f in ('source.csv','source.json'):
                    shutil.copy2(folder/f,staging/f)
                publish_files([(staging/f,target.parent/f) for f in ('lab.sqlite','source.csv','source.json')])
            finally:
                shutil.rmtree(staging)
            restored = dict(snap['environment'])
            restored['db_path'] = env['db_path']
            return self.put('environments',restored)

    def schema(self,eid):
        with self.lock:
            env = self.get('environments',eid)
            with database(env['db_path']) as c:
                started = time.monotonic()
                c.execute('PRAGMA trusted_schema=OFF')
                c.set_progress_handler(lambda: int(time.monotonic()-started > 5), 1000)
                result = []
                for name, kind in c.execute("SELECT name,type FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
                    columns = [dict(name=x[1],type=x[2],notnull=bool(x[3]),pk=bool(x[5])) for x in c.execute('PRAGMA table_info('+identifier(name)+')')]
                    fks = [dict(table=x[2],**{'from':x[3],'to':x[4]}) for x in c.execute('PRAGMA foreign_key_list('+identifier(name)+')')]
                    indexes = [dict(name=x[1],unique=bool(x[2])) for x in c.execute('PRAGMA index_list('+identifier(name)+')')]
                    result.append(dict(name=name,type=kind,count=c.execute('SELECT COUNT(*) FROM '+identifier(name)).fetchone()[0],columns=columns,foreign_keys=fks,indexes=indexes))
                return dict(tables=result)

    def profile(self,eid,table):
        with self.lock:
            schema = self.schema(eid)
            spec = next((t for t in schema['tables'] if t['name']==table),None)
            if spec is None:
                raise ValueError('Table introuvable.')
            env = self.get('environments',eid)
            started = time.monotonic()
            with database(env['db_path']) as c:
                c.set_progress_handler(lambda:int(time.monotonic()-started > 5),1000)
                c.execute('PRAGMA trusted_schema=OFF')
                cols = []
                for col in spec['columns']:
                    n, t = identifier(col['name']), identifier(table)
                    values = c.execute(f'SELECT SUM({n} IS NULL), COUNT(DISTINCT {n}), MIN({n}), MAX({n}) FROM {t}').fetchone()
                    top = [dict(value=safe_json(r[0]),count=r[1]) for r in c.execute(f'SELECT {n},COUNT(*) AS frequency FROM {t} GROUP BY {n} ORDER BY frequency DESC LIMIT 5')]
                    cols.append(dict(name=col['name'],type=col['type'],nulls=values[0] or 0,distinct=values[1],min=safe_json(values[2]),max=safe_json(values[3]),top=top))
                return dict(count=spec['count'],columns=cols)

    def save_artifact(self,args):
        kind = args.get('kind')
        if kind not in ('sql','python','pipeline'):
            raise ValueError('Type d’expérience invalide.')
        code = args.get('code','')
        if not isinstance(code,str) or len(code) > 200000:
            raise ValueError('Code trop volumineux.')
        self.get('environments',args.get('env_id'))
        aid = args.get('id') or uuid.uuid4().hex
        if args.get('id'):
            old = self.get('artifacts',aid)
            if old['kind'] != kind:
                raise ValueError('Type de fichier existant incompatible.')
        if kind == 'pipeline':
            definition=strict_json_loads(code)
            if not isinstance(definition,dict):
                raise ValueError('Un pipeline enregistré doit être un objet JSON avec steps.')
            self.validate_pipeline(definition.get('steps',[]))
        name = str(args.get('name','Expérience')).strip()[:120]
        if not name:
            raise ValueError('Nom requis.')
        path = self.root/'experiments'/(aid+dict(sql='.sql',python='.py',pipeline='.json')[kind])
        with self.lock:
            temp = path.with_suffix(path.suffix+'.tmp')
            temp.write_text(code,encoding='utf-8')
            temp.replace(path)
            return self.put('artifacts',dict(id=aid,name=name,kind=kind,code=code,env_id=args['env_id'],path=str(path),updated=now()))

    def sql(self,eid,code,read_only=False):
        started = time.monotonic()
        run = dict(id=uuid.uuid4().hex,kind='sql',env_id=eid,status='running',started=now(),
                   duration_ms=0,row_count=0,stdout='',stderr='',error=None,result=None,steps=[],workspace='',code=code)
        try:
            with self.lock:
                env = self.get('environments',eid)
                result = execute_sql(env['db_path'],code,read_only=read_only)
            run.update(status='success',result=result,row_count=result['row_count'],duration_ms=result['duration_ms'])
            result['run_id'] = run['id']
            return result
        except Exception as exc:
            run.update(status='error',error=str(exc),duration_ms=round((time.monotonic()-started)*1000,2))
            raise
        finally:
            self.put('runs',run)

    @staticmethod
    def validate_pipeline(steps):
        if not isinstance(steps,list) or not 1 <= len(steps) <= 30:
            raise ValueError('Un pipeline doit comporter de 1 à 30 étapes.')
        ids = []
        for step in steps:
            if not isinstance(step,dict) or not isinstance(step.get('id'),str) or not step['id'] or step['id'] in ids:
                raise ValueError('Les identifiants d’étapes doivent être uniques et non vides.')
            if step.get('type') not in ('csv','python','validate','load','sql','export'):
                raise ValueError('Type d’étape inconnu.')
            ids.append(step['id'])
        pending, ordered = list(steps), []
        while pending:
            progressed = False
            for step in list(pending):
                deps = step.get('depends_on',[])
                if not isinstance(deps,list) or any(d not in ids for d in deps):
                    raise ValueError('Dépendance introuvable.')
                if all(d in [s['id'] for s in ordered] for d in deps):
                    ordered.append(step)
                    pending.remove(step)
                    progressed = True
            if not progressed:
                raise ValueError('Cycle détecté dans les dépendances.')
        return ordered

    def launch(self,kind,args):
        code = args.get('code','')
        if not isinstance(code,str) or len(code)>200000:
            raise ValueError('Code invalide ou trop volumineux.')
        steps = self.validate_pipeline(args.get('steps')) if kind=='pipeline' else []
        if kind == 'python' or any(s['type']=='python' for s in steps):
            if not self.state()['python_ack']:
                raise PermissionError('Confirmez les risques avant la première exécution Python : un sous-processus n’est pas une sandbox.')
        timeout = args.get('timeout',30)
        if type(timeout) not in (int,float) or not 1 <= timeout <= 120:
            raise ValueError('Délai : 1 à 120 secondes.')
        with self.lock:
            env = self.get('environments',args.get('env_id'))
            if sum(1 for job in self.jobs.values() if job['thread'].is_alive()) >= 3:
                raise ValueError('Trois exécutions actives : arrêtez-en une avant de continuer.')
            rid = uuid.uuid4().hex
            workspace = self.root/'work/runs'/rid
            workspace.mkdir()
            with database(env['db_path']) as src, database(workspace/'lab.sqlite') as dst:
                backup_database(src,dst)
            for f in ('source.csv','source.json'):
                shutil.copy2(Path(env['db_path']).parent/f,workspace/f)
            run = dict(id=rid,name=str(args.get('name',kind))[:120],kind=kind,env_id=env['id'],status='running',
                       started=now(),duration_ms=0,row_count=0,stdout='',stderr='',error=None,result=None,steps=[],
                       workspace=str(workspace),code=code,configuration=args,environment=env)
            self.put('runs',run)
            event = threading.Event()
            worker = threading.Thread(target=self._worker,args=(run,steps,event,timeout),daemon=True)
            self.jobs[rid] = dict(event=event,thread=worker,process=None)
            worker.start()
            return dict(run_id=rid)

    def cancel(self,rid):
        with self.lock:
            self.get('runs',rid)
            job = self.jobs.get(rid)
            if job and job['thread'].is_alive():
                job['event'].set()
                return dict(cancelled=True)
            return dict(cancelled=False)

    def shutdown(self):
        for job in list(self.jobs.values()):
            job['event'].set()
        for job in list(self.jobs.values()):
            job['thread'].join(timeout=4)

    @staticmethod
    def _local_file(workspace,path):
        target = (workspace/str(path)).resolve()
        if not target.is_relative_to(workspace.resolve()) or target == workspace.resolve():
            raise ValueError('Le fichier doit rester dans le répertoire de cette exécution.')
        return target

    @staticmethod
    def _read_csv(path):
        if not path.is_file() or path.stat().st_size > 20_000_000:
            raise ValueError('CSV absent ou supérieur à 20 Mo.')
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader = csv.DictReader(f, strict=True)
            columns = reader.fieldnames
            if not columns or any(not x for x in columns) or len(set(columns))!=len(columns):
                raise ValueError('En-têtes CSV vides ou dupliqués.')
            rows = []
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('CSV malformé : nombre de champs incorrect.')
                rows.append(row)
                if len(rows)>100000:
                    raise ValueError('CSV supérieur à 100 000 lignes.')
            return columns,rows

    def _python(self,run,code,event,timeout,filename='script.py'):
        workspace = Path(run['workspace'])
        (workspace/filename).write_text(code,encoding='utf-8')
        process_env = {k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','PATH','TEMP','TMP','COMSPEC','PATHEXT')}
        (workspace/'tmp').mkdir(exist_ok=True)
        process_env.update(LAB_DB=str(workspace/'lab.sqlite'),LAB_WORKSPACE=str(workspace),
                           PYTHONIOENCODING='utf-8',TEMP=str(workspace/'tmp'),TMP=str(workspace/'tmp'))
        proc = subprocess.Popen([sys.executable,'-I','-X','utf8',str(workspace/filename)],cwd=workspace,env=process_env,
                                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.jobs[run['id']]['process'] = proc
        buffers = {'stdout':bytearray(),'stderr':bytearray()}
        truncated = set()
        def drain(pipe,key):
            try:
                while True:
                    chunk=pipe.read(4096)
                    if not chunk:
                        break
                    room=65536-len(buffers[key])
                    if room>0:
                        buffers[key].extend(chunk[:room])
                    if len(chunk)>room:
                        truncated.add(key)
            finally:
                pipe.close()
        readers = [threading.Thread(target=drain,args=(pipe,key),daemon=True) for pipe,key in ((proc.stdout,'stdout'),(proc.stderr,'stderr'))]
        for thread in readers:
            thread.start()
        started=time.monotonic()
        reason=None
        while proc.poll() is None:
            if event.is_set() or time.monotonic()-started>timeout:
                reason='Exécution annulée.' if event.is_set() else f'Délai dépassé ({timeout} s).'
                try:
                    if os.name=='nt':
                        subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'),'/PID',str(proc.pid),'/T','/F'],
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3,
                                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                except (OSError, subprocess.TimeoutExpired):
                    pass
                finally:
                    if proc.poll() is None:
                        proc.kill()
                break
            time.sleep(.05)
        proc.wait(timeout=5)
        for thread in readers:
            thread.join(timeout=2)
        for key in buffers:
            run[key] += buffers[key].decode('utf-8',errors='replace') + ('\n[Sortie tronquée à 64 Kio]\n' if key in truncated else '')
            run[key] = run[key][-131072:]
        self.jobs[run['id']]['process']=None
        if reason:
            raise TimeoutError(reason)
        if proc.returncode:
            raise RuntimeError(f'Python terminé avec le code {proc.returncode}. Consultez stderr.')

    def _worker(self,run,steps,event,timeout):
        started=time.monotonic()
        workspace=Path(run['workspace'])
        current_csv=workspace/'source.csv'
        last_result=None
        try:
            if run['kind']=='python':
                self._python(run,run['code'],event,timeout)
                result_file=workspace/'result.csv'
                if result_file.exists():
                    cols,rows=self._read_csv(result_file)
                    last_result=dict(columns=cols,rows=[[r[c] for c in cols] for r in rows[:1000]],row_count=len(rows),truncated=len(rows)>1000)
                else:
                    result_file=workspace/'result.json'
                    if result_file.exists():
                        if result_file.stat().st_size>1_000_000:
                            raise ValueError('result.json dépasse 1 Mo.')
                        last_result=strict_json_loads(result_file.read_text(encoding='utf-8'))
            else:
                for spec in steps:
                    if event.is_set():
                        raise TimeoutError('Exécution annulée.')
                    step=dict(id=spec['id'],name=spec.get('name',spec['id']),type=spec['type'],status='running',
                              duration_ms=0,input_rows=0,output_rows=0,error=None,result=None)
                    run['steps'].append(step)
                    self.put('runs',run)
                    tick=time.monotonic()
                    try:
                        kind=spec['type']
                        if kind=='csv':
                            current_csv=self._local_file(workspace,spec.get('path','source.csv'))
                            cols,rows=self._read_csv(current_csv)
                            step.update(output_rows=len(rows),result=dict(columns=cols,rows=[[r[c] for c in cols] for r in rows[:20]]))
                        elif kind=='python':
                            if current_csv.exists():
                                step['input_rows']=len(self._read_csv(current_csv)[1])
                            self._python(run,spec.get('code',''),event,timeout,filename='step_'+str(len(run['steps']))+'.py')
                            current_csv=self._local_file(workspace,spec.get('path','result.csv'))
                            cols,rows=self._read_csv(current_csv)
                            step['output_rows']=len(rows)
                        elif kind=='validate':
                            cols,rows=self._read_csv(current_csv)
                            minimum=spec.get('min_rows',1)
                            if type(minimum) is not int or minimum<0:
                                raise ValueError('min_rows doit être un entier positif ou nul.')
                            if len(rows)<minimum:
                                raise ValueError(f'Validation : {len(rows)} lignes, minimum {minimum}.')
                            required=spec.get('required_columns',[])
                            if not isinstance(required,list) or any(x not in cols for x in required):
                                raise ValueError('Validation : colonne requise absente.')
                            step.update(input_rows=len(rows),output_rows=len(rows),result={'valid':True})
                        elif kind=='load':
                            cols,rows=self._read_csv(current_csv)
                            table=spec.get('table','pipeline_output')
                            if not isinstance(table,str) or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',table) or table.startswith('sqlite_'):
                                raise ValueError('Nom de table destination invalide.')
                            with database(workspace/'lab.sqlite') as c:
                                c.execute('DROP TABLE IF EXISTS '+identifier(table))
                                c.execute('CREATE TABLE '+identifier(table)+' ('+','.join(identifier(col)+' TEXT' for col in cols)+')')
                                c.executemany('INSERT INTO '+identifier(table)+' VALUES ('+','.join('?' for _ in cols)+')',[[r[col] for col in cols] for r in rows])
                            step.update(input_rows=len(rows),output_rows=len(rows),result={'table':table})
                        elif kind=='sql':
                            last_result=execute_sql(workspace/'lab.sqlite',spec.get('code',''))
                            step.update(output_rows=last_result['row_count'],result=last_result)
                        elif kind=='export':
                            if not last_result or not isinstance(last_result,dict) or 'columns' not in last_result:
                                raise ValueError('Aucun résultat SQL à exporter.')
                            if last_result.get('truncated'):
                                raise ValueError('Export refusé : résultat SQL tronqué. Réduisez le résultat à 1000 lignes.')
                            current_csv=self._local_file(workspace,spec.get('path','result.csv'))
                            current_csv.parent.mkdir(parents=True,exist_ok=True)
                            with current_csv.open('w',encoding='utf-8',newline='') as f:
                                writer=csv.writer(f)
                                writer.writerow(last_result['columns'])
                                writer.writerows(last_result['rows'])
                            step.update(input_rows=len(last_result['rows']),output_rows=len(last_result['rows']))
                        step['status']='success'
                    except Exception as exc:
                        step.update(status='cancelled' if event.is_set() else 'error',error=str(exc))
                        raise
                    finally:
                        step['duration_ms']=round((time.monotonic()-tick)*1000,2)
                        self.put('runs',run)
            run.update(status='cancelled' if event.is_set() else 'success',result=last_result,
                       row_count=last_result.get('row_count',0) if isinstance(last_result,dict) and type(last_result.get('row_count',0)) is int else 0)
        except Exception as exc:
            run.update(status='cancelled' if event.is_set() else 'error',error=str(exc))
        finally:
            run['duration_ms']=round((time.monotonic()-started)*1000,2)
            self.put('runs',run)
