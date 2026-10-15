"""Local guided practice, additive progress storage, and reproducible execution.

Personal Python runs with account permissions. Neither this service nor the
existing process runner constitutes a security sandbox or anti-cheating system.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from datetime import datetime,timezone

from .sql_engine import execute_sql,strict_json_loads
from .storage import database
from . import training_validators as checks

CONTENT=Path(__file__).resolve().parents[1]/'content'
MAX_CODE=200000
MAX_NOTES=5000
MAX_OUTPUT=1000000
CASE_TIMEOUT=3
TOTAL_TIMEOUT=20

def now():
    return datetime.now(timezone.utc).isoformat()

class Training:
    def __init__(self,lab):
        self.lab=lab
        self.resources=strict_json_loads((CONTENT/'catalog.json').read_text(encoding='utf-8-sig'))
        raw=strict_json_loads((CONTENT/'exercises.json').read_text(encoding='utf-8-sig'))
        self.content_version=raw.get('version','1') if isinstance(raw,dict) else '1'
        exercises=raw.get('exercises',[]) if isinstance(raw,dict) else raw
        self.exercises={}
        for exercise in exercises:
            eid=exercise.get('id')
            if eid not in checks.ENGINES or eid in self.exercises or exercise.get('engine')!=checks.ENGINES[eid] or exercise.get('validator_id')!=eid:
                raise ValueError('Catalogue et validateur incompatibles : '+str(eid))
            self.exercises[eid]=exercise
        with lab.lock,lab.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS training_progress(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS training_attempts(id TEXT PRIMARY KEY,payload TEXT NOT NULL);''')
        for attempt in self._list('training_attempts'):
            job=lab.jobs.get(attempt['id'])
            if attempt['status']=='running' and not (job and job['thread'].is_alive()):
                attempt.update(status='error',error='Application fermée pendant la validation.',summary='Validation interrompue ; relancez votre tentative.',finished_at=now(),interrupted=True)
                for case in attempt['cases']:
                    if case['status'] in ('pending','running'):
                        case.update(status='skipped',message='Cas non terminé avant la fermeture.')
                self._finalize(attempt)

    def _list(self,table):
        with self.lab.lock,self.lab.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM '+table+' ORDER BY rowid DESC')]

    def _put(self,table,value):
        with self.lab.lock,self.lab.connect() as db:
            db.execute('INSERT OR REPLACE INTO '+table+'(id,payload) VALUES(?,?)',(value['id'],json.dumps(value,ensure_ascii=False,allow_nan=False)))
        return value

    def _known(self,eid):
        if not isinstance(eid,str) or eid not in self.exercises:
            raise ValueError('Exercice introuvable.')
        return self.exercises[eid]

    @staticmethod
    def _args(args,allowed):
        if not isinstance(args,dict) or set(args)-set(allowed):
            raise ValueError('Paramètres de l’entraînement invalides.')

    def _progress(self,eid):
        exercise=self._known(eid)
        with self.lab.lock,self.lab.connect() as db:
            row=db.execute('SELECT payload FROM training_progress WHERE id=?',(eid,)).fetchone()
        if row:return json.loads(row[0])
        return dict(id=eid,exercise_id=eid,exercise_version=exercise['version'],code=exercise.get('starter',''),notes='',needs_review=False,status='new',hints_revealed=0,attempt_count=0,success_count=0,last_attempt_id=None,last_status=None,started_at=None,updated_at=None,completed_at=None)

    @staticmethod
    def _public(exercise):
        return {key:value for key,value in exercise.items() if key not in ('hints','validator_id','solution','tests')}

    def catalog(self):
        with self.lab.lock:
            progress={p['exercise_id']:p for p in self._list('training_progress')}
            exercises=[self._public(value) for value in self.exercises.values()]
            skills=[]
            for item in self.resources['skills']:
                skill=dict(item)
                relevant=[e for e in exercises if skill['id'] in e.get('skill_ids',[])]
                skill['exercise_count']=len(relevant)
                skill['validated_exercise_count']=len(relevant)
                skill['completed_exercise_count']=sum(progress.get(e['id'],{}).get('status')=='completed' for e in relevant)
                skills.append(skill)
            return dict(version=self.content_version,sources=self.resources['sources'],domains=self.resources['domains'],skills=skills,exercises=exercises,progress=progress,validation_version=checks.VALIDATOR_VERSION,progress_notice='Une réussite locale ne signifie pas une maîtrise définitive.')

    def exercise(self,eid):
        with self.lab.lock:
            exercise=self._known(eid);progress=self._progress(eid)
            attempts=[a for a in self._list('training_attempts') if a['exercise_id']==eid][:30]
            return dict(exercise=self._public(exercise),progress=progress,attempts=attempts,hints=exercise.get('hints',[])[:progress['hints_revealed']])

    def start(self,args):
        self._args(args,('exercise_id',))
        eid=args.get('exercise_id');self._known(eid)
        with self.lab.lock:
            progress=self._progress(eid)
            if progress['status']=='new':
                progress.update(status='started',started_at=now(),updated_at=now())
                self._put('training_progress',progress)
            return self.exercise(eid)

    def save(self,args):
        self._args(args,('exercise_id','code','notes','needs_review'))
        eid=args.get('exercise_id');self._known(eid)
        code=args.get('code')
        if not isinstance(code,str) or len(code)>MAX_CODE:
            raise ValueError('Le code doit contenir au maximum 200 000 caractères.')
        if 'notes' in args and (not isinstance(args['notes'],str) or len(args['notes'])>MAX_NOTES):
            raise ValueError('Les notes doivent contenir au maximum 5 000 caractères.')
        if 'needs_review' in args and type(args['needs_review']) is not bool:
            raise ValueError('Le choix « à reprendre » doit être booléen.')
        with self.lab.lock:
            progress=self._progress(eid)
            progress.update(code=code,updated_at=now())
            if progress['status']=='new':progress.update(status='started',started_at=now())
            for key in ('notes','needs_review'):
                if key in args:progress[key]=args[key]
            return self._put('training_progress',progress)

    def hint(self,args):
        self._args(args,('exercise_id',))
        eid=args.get('exercise_id');exercise=self._known(eid)
        with self.lab.lock:
            progress=self._progress(eid)
            progress['hints_revealed']=min(len(exercise.get('hints',[])),progress['hints_revealed']+1)
            if progress['status']=='new':progress.update(status='started',started_at=now())
            progress['updated_at']=now();self._put('training_progress',progress)
            hints=exercise.get('hints',[])[:progress['hints_revealed']]
            return dict(hints=hints,revealed_count=len(hints))

    def attempt(self,aid):
        if not isinstance(aid,str) or len(aid)!=32 or any(c not in '0123456789abcdef' for c in aid):
            raise ValueError('Identifiant de tentative invalide.')
        with self.lab.lock,self.lab.connect() as db:
            row=db.execute('SELECT payload FROM training_attempts WHERE id=?',(aid,)).fetchone()
        if not row:raise ValueError('Tentative introuvable.')
        return json.loads(row[0])

    def validate(self,args):
        self._args(args,('exercise_id','code'))
        eid=args.get('exercise_id');exercise=self._known(eid)
        code=args.get('code')
        if not isinstance(code,str) or not code.strip() or len(code)>MAX_CODE:
            raise ValueError('Écrivez votre travail, dans la limite de 200 000 caractères.')
        with self.lab.lock:
            if exercise['engine']=='python' and not self.lab.state()['python_ack']:
                raise PermissionError('Confirmez les risques Python avant de valider : ce processus n’est pas une sandbox.')
            if sum(job['thread'].is_alive() for job in self.lab.jobs.values())>=3:
                raise ValueError('Trois exécutions sont déjà actives ; arrêtez-en une avant de continuer.')
            aid=uuid.uuid4().hex
            workspace=self.lab.root/'work/training'/aid
            workspace.mkdir(parents=True)
            (workspace/('submission.py' if exercise['engine']=='python' else 'submission.sql')).write_text(code,encoding='utf-8')
            titles=['Données variées et pièges courants','Autre jeu de données','Valeurs limites et contraintes']
            attempt=dict(id=aid,exercise_id=eid,exercise_version=exercise['version'],validator_version=checks.VALIDATOR_VERSION,dataset_seed=20251015,status='running',passed=0,total=3,cases=[dict(id=f'cas-{i+1}',title=titles[i],status='pending',message='',duration_ms=0) for i in range(3)],summary='Validation en cours.',stdout='',stderr='',error=None,duration_ms=0,started_at=now(),finished_at=None,workspace=str(workspace),code=code,code_sha256=hashlib.sha256(code.encode()).hexdigest())
            self._put('training_attempts',attempt)
            progress=self.save(dict(exercise_id=eid,code=code))
            progress.update(attempt_count=progress['attempt_count']+1,last_attempt_id=aid,last_status='running')
            self._put('training_progress',progress)
            event=threading.Event()
            thread=threading.Thread(target=self._worker,args=(attempt,exercise,event),daemon=True)
            self.lab.jobs[aid]=dict(event=event,thread=thread,process=None)
            thread.start()
            return dict(attempt_id=aid)

    def cancel(self,args):
        self._args(args,('attempt_id',))
        aid=args.get('attempt_id');self.attempt(aid)
        with self.lab.lock:
            job=self.lab.jobs.get(aid)
            active=bool(job and job['thread'].is_alive())
            if active:job['event'].set()
            return dict(cancelled=active)

    def _python_case(self,attempt,exercise,case,path,event):
        (path/'submission.py').write_text(attempt['code'],encoding='utf-8')
        (path/'input.json').write_text(json.dumps(case['input'],ensure_ascii=False,allow_nan=False),encoding='utf-8')
        with database(path/'lab.sqlite') as db:db.execute('CREATE TABLE training_context(id INTEGER PRIMARY KEY)')
        function=checks.PYTHON_FUNCTIONS[exercise['id']]
        wrapper=f'''import importlib.util,json,copy
from pathlib import Path
spec=importlib.util.spec_from_file_location('training_submission',str(Path('submission.py').resolve()))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
function=getattr(module,{function!r})
if not callable(function):raise TypeError('La fonction demandée doit être appelable.')
argument=json.loads(Path('input.json').read_text(encoding='utf-8'))
original=copy.deepcopy(argument)
actual=function(argument)
if argument!=original:raise ValueError('La fonction ne doit pas modifier son entrée.')
encoded=json.dumps(actual,ensure_ascii=False,allow_nan=False)
if len(encoded.encode('utf-8'))>{MAX_OUTPUT}:raise ValueError('Résultat supérieur à 1 Mo.')
Path('training-output.json').write_text(encoded,encoding='utf-8')
'''
        run=dict(id=attempt['id'],workspace=str(path),stdout='',stderr='')
        try:
            self.lab._python(run,wrapper,event,CASE_TIMEOUT,filename='runner.py')
        finally:
            for stream in ('stdout','stderr'):
                if run[stream]:attempt[stream]=(attempt[stream]+'\n['+case['id']+']\n'+run[stream])[-131072:]
        output=path/'training-output.json'
        if output.is_symlink() or not output.is_file() or output.stat().st_size>MAX_OUTPUT or not output.resolve().is_relative_to(path.resolve()):
            raise ValueError('La fonction n’a pas produit une sortie JSON exploitable dans la limite de 1 Mo.')
        try:actual=strict_json_loads(output.read_text(encoding='utf-8'))
        except (ValueError,UnicodeError,RecursionError) as exc:raise ValueError('La sortie produite n’est pas un JSON valide et fini.') from exc
        return checks.compare_values(actual,case['expected'])

    def _worker(self,attempt,exercise,event):
        start=time.monotonic();eid=exercise['id'];technical=False
        try:
            python_cases=checks.python_cases(eid) if exercise['engine']=='python' else None
            for index,case in enumerate(attempt['cases']):
                if event.is_set():break
                if time.monotonic()-start>TOTAL_TIMEOUT:
                    raise TimeoutError('Le budget total de validation est dépassé.')
                path=Path(attempt['workspace'])/f'case-{index+1}';path.mkdir()
                case.update(status='running');tick=time.monotonic()
                self._put('training_attempts',attempt)
                # Building fixtures is infrastructure work, outside student-error handling.
                if exercise['engine']=='sql':
                    spec=checks.sql_fixture(path/'lab.sqlite',eid,index);case['title']=spec['title']
                elif exercise['engine']=='schema':
                    with database(path/'lab.sqlite') as db:db.execute('PRAGMA user_version=0')
                try:
                    if exercise['engine']=='python':
                        spec=python_cases[index];case['title']=spec['title']
                        correct,message=self._python_case(attempt,exercise,spec,path,event)
                    elif exercise['engine']=='sql':
                        actual=execute_sql(path/'lab.sqlite',attempt['code'],deadline=2,read_only=True)
                        correct,message=checks.compare_sql(actual,spec['expected'])
                    else:
                        execute_sql(path/'lab.sqlite',attempt['code'],deadline=2)
                        message=checks.validate_schema(path/'lab.sqlite',eid,index);correct=True
                    if event.is_set():case.update(status='cancelled',message='Validation annulée.')
                    else:
                        case.update(status='success' if correct else 'failed',message=message)
                        attempt['passed']+=int(correct)
                except (checks.ValidationFailure,sqlite3.Error,ValueError,TypeError,RuntimeError,TimeoutError,RecursionError) as exc:
                    case.update(status='cancelled' if event.is_set() else 'failed',message=str(exc)[:1000])
                    if isinstance(exc,TimeoutError):
                        attempt['error']=str(exc);break
                finally:
                    case['duration_ms']=round((time.monotonic()-tick)*1000,2)
                    self._put('training_attempts',attempt)
            attempt['status']='cancelled' if event.is_set() else 'success' if attempt['passed']==attempt['total'] else 'failed'
            attempt['summary']=('Validation annulée.' if event.is_set() else f"{attempt['passed']} cas réussis sur {attempt['total']}.")
        except Exception as exc:
            technical=True
            attempt.update(status='cancelled' if event.is_set() else 'error',error=str(exc)[:1000],summary='Validation annulée.' if event.is_set() else 'Erreur technique pendant la validation ; aucune réussite n’est déclarée.')
        finally:
            for case in attempt['cases']:
                if case['status'] in ('pending','running'):
                    case.update(status='skipped',message='Cas non exécuté après une interruption.' if event.is_set() or technical or attempt.get('error') else 'Cas non exécuté.')
            attempt.update(duration_ms=round((time.monotonic()-start)*1000,2),finished_at=now())
            self._finalize(attempt)

    def _finalize(self,attempt):
        """Publish terminal result and derived progress in one SQLite transaction.

        Deriving counters from attempts makes restart recovery idempotent and
        handles concurrent attempts completing in a different order.
        """
        with self.lab.lock,self.lab.connect() as db:
            progress=self._progress(attempt['exercise_id'])
            db.execute('INSERT OR REPLACE INTO training_attempts(id,payload) VALUES(?,?)',
                       (attempt['id'],json.dumps(attempt,ensure_ascii=False,allow_nan=False)))
            related=[json.loads(row[0]) for row in db.execute('SELECT payload FROM training_attempts')]
            related=[item for item in related if item['exercise_id']==attempt['exercise_id']]
            success=[item for item in related if item['status']=='success']
            progress.update(attempt_count=len(related),success_count=len(success),updated_at=now())
            if success:
                progress.update(status='completed',completed_at=progress.get('completed_at') or min(item['finished_at'] for item in success))
            elif progress['status']=='new':
                progress.update(status='started',started_at=attempt['started_at'],code=attempt['code'])
            latest=max(related,key=lambda item:item['started_at'])
            progress.update(last_attempt_id=latest['id'],last_status=latest['status'])
            db.execute('INSERT OR REPLACE INTO training_progress(id,payload) VALUES(?,?)',
                       (progress['id'],json.dumps(progress,ensure_ascii=False,allow_nan=False)))
