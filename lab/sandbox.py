"""Structured, bounded SQLite experiments in explicitly disposable environments."""
from __future__ import annotations
import csv
import io
import json
import math
import random
import re
import shutil
import sqlite3
import time
import uuid
from contextlib import closing
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

from .storage import database, backup_database
from .sql_engine import identifier, strict_json_loads, safe_json

TYPES = {'INTEGER', 'REAL', 'TEXT', 'BLOB', 'NUMERIC'}
MAX_ROWS = 10000
MAX_TEXT = 750 * 1024
_ASCII_CASE = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')
def sqlite_name(value):
    return value.translate(_ASCII_CASE)

class Sandbox:
    def __init__(self, lab):
        self.lab = lab

    @staticmethod
    def _name(value, label='Nom'):
        if not isinstance(value, str) or not value.strip() or len(value)>120 or '\x00' in value:
            raise ValueError(label+' requis, limité à 120 caractères.')
        return value.strip()

    @staticmethod
    def _number(value, low, high, integer=False):
        if type(value) not in ((int,) if integer else (int,float)) or not low<=value<=high or not math.isfinite(value):
            raise ValueError(f'Nombre attendu entre {low} et {high}.')
        return value

    def _environment(self, eid, writable=False):
        env=self.lab.get('environments',eid)
        path=Path(env['db_path']).resolve()
        if not path.is_relative_to((self.lab.root/'data/environments').resolve()) or not path.is_file():
            raise ValueError('Base extérieure au laboratoire ou introuvable.')
        if writable and env.get('sandbox') is not True:
            raise ValueError('Dupliquez cet environnement avant de le modifier dans le Bac à sable.')
        return env

    def info(self, eid):
        with self.lab.lock:
            env=self._environment(eid)
            return dict(environment=env,tables=self.lab.schema(eid)['tables'],is_sandbox=env.get('sandbox') is True,
                        limits=dict(max_rows=MAX_ROWS,max_import_bytes=MAX_TEXT,max_total_generated_rows=50000))

    def _publish_environment(self, name, build, extra=None):
        name=self._name(name,'Nom de l’environnement')
        eid=uuid.uuid4().hex
        parent=(self.lab.root/'data/environments').resolve()
        folder=parent/eid
        with self.lab.lock:
            folder.mkdir()
            try:
                stats=build(folder)
                env=dict(id=eid,name=name,kind='custom',sandbox=True,seed=0,size=0,anomalies=False,
                         generator_version='sandbox-1',db_path=str(folder/'lab.sqlite'),stats=stats,
                         created=datetime.now(timezone.utc).isoformat())
                env.update(extra or {})
                return self.lab.put('environments',env)
            except Exception:
                if folder.resolve().is_relative_to(parent):shutil.rmtree(folder)
                raise

    def create(self, args):
        count=self._number(args.get('table_count',0),0,8,True)
        rows=self._number(args.get('row_count',100),0,MAX_ROWS,True)
        seed=self._number(args.get('seed',42),0,2147483647,True)
        if count*rows>50000:raise ValueError('Génération limitée à 50 000 lignes au total.')
        null_rate=self._number(args.get('null_rate',0),0,.8)
        duplicates=self._number(args.get('duplicate_rate',0),0,.5)
        distribution=args.get('distribution','uniform')
        if distribution not in ('uniform','normal'):raise ValueError('Distribution inconnue.')
        related=args.get('related',True);anomalies=args.get('anomalies',False)
        if type(related) is not bool or type(anomalies) is not bool:raise ValueError('Options booléennes attendues.')
        try:start=date.fromisoformat(args.get('start_date','2025-01-01'));end=date.fromisoformat(args.get('end_date','2025-12-31'))
        except (ValueError,TypeError):raise ValueError('Période attendue au format AAAA-MM-JJ.')
        if not date(1900,1,1)<=start<=end<=date(2200,12,31):raise ValueError('Période invalide (1900–2200).')
        config=dict(table_count=count,row_count=rows,distribution=distribution,start_date=start.isoformat(),end_date=end.isoformat(),
                    null_rate=null_rate,duplicate_rate=duplicates,related=related,anomalies=anomalies,seed=seed)
        def build(folder):
            rng=random.Random(seed);nulls=duplicate_labels=anomaly_count=0
            with database(folder/'lab.sqlite') as c:
                c.execute('PRAGMA foreign_keys=ON')
                for i in range(count):
                    table=f'table_{i+1}';link=i>0 and related
                    fk=f',parent_id INTEGER REFERENCES table_{i}(id)' if link else ''
                    c.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY,label TEXT NOT NULL,value REAL,event_date TEXT NOT NULL,category TEXT NOT NULL{fk})')
                    labels=[]
                    for j in range(rows):
                        label=f'Objet {i+1}-{j+1}'
                        if labels and rng.random()<duplicates:label=rng.choice(labels);duplicate_labels+=1
                        labels.append(label)
                        value=round(rng.gauss(50,15) if distribution=='normal' else rng.uniform(0,100),2)
                        if rng.random()<null_rate:value=None;nulls+=1
                        if anomalies and (j==0 or rng.random()<.03):
                            if value is None:nulls-=1
                            value=-abs(value or 0)-10000;anomaly_count+=1
                        values=[j+1,label,value,(start+timedelta(days=rng.randrange((end-start).days+1))).isoformat(),rng.choice(['A','B','C'])]
                        if link:values.append(rng.randrange(1,rows+1))
                        c.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in values)})',values)
                if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Relations générées incohérentes.')
            self._sources(folder,'table_1' if count else None)
            return dict(tables=count,rows=count*rows,null_values=nulls,duplicate_labels=duplicate_labels,
                        anomalies=[f'{anomaly_count} valeurs négatives hors plage.'] if anomaly_count else [],configuration=config)
        return self._publish_environment(args.get('name'),build,dict(seed=seed,size=count*rows,anomalies=anomalies))

    def duplicate(self, args):
        with self.lab.lock:
            original=self._environment(args.get('env_id'))
            def build(folder):
                with database(original['db_path']) as src,database(folder/'lab.sqlite') as dst:backup_database(src,dst)
                for name in ('source.csv','source.json'):
                    src=Path(original['db_path']).parent/name
                    if src.is_file():shutil.copy2(src,folder/name)
                if not (folder/'source.csv').exists() or not (folder/'source.json').exists():self._sources(folder,None)
                return dict(original.get('stats',{}))
            return self._publish_environment(args.get('name') or original['name']+' — copie',build,dict(origin_id=original['id'],source_kind=original['kind']))

    @staticmethod
    def _sources(folder, table):
        columns=['id','value'];rows=[]
        if table:
            with database(folder/'lab.sqlite') as c:
                cur=c.execute('SELECT * FROM '+identifier(table));columns=[d[0] for d in cur.description];rows=cur.fetchall()
        with (folder/'source.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(columns);w.writerows(rows)
        (folder/'source.json').write_text(json.dumps([dict(zip(columns,row)) for row in rows],ensure_ascii=False,allow_nan=False),encoding='utf-8')

    def _table(self, eid, name):
        name=self._name(name,'Table')
        tables=self.lab.schema(eid)['tables']
        table=next((t for t in tables if sqlite_name(t['name'])==sqlite_name(name)),None)
        if table is None or table['type']!='table':raise ValueError('Table modifiable introuvable.')
        return table

    def _column_sql(self, spec, adding=False):
        if not isinstance(spec,dict):raise ValueError('Définition de colonne invalide.')
        name=self._name(spec.get('name'),'Colonne');kind=spec.get('type','TEXT')
        if kind not in TYPES:raise ValueError('Type de colonne non pris en charge.')
        for k in ('primary_key','not_null','unique'):
            if k in spec and type(spec[k]) is not bool:raise ValueError('Contraintes booléennes attendues.')
        if adding and (spec.get('primary_key') or spec.get('unique')):raise ValueError('SQLite ne permet pas ADD COLUMN avec PRIMARY KEY ou UNIQUE ; utilisez une nouvelle table et le SQL libre.')
        sql=identifier(name)+' '+kind
        if spec.get('not_null'):sql+=' NOT NULL'
        if spec.get('unique'):sql+=' UNIQUE'
        if 'min' in spec and spec['min'] is not None:
            minimum=self._number(spec['min'],-1e12,1e12);sql+=' CHECK ('+identifier(name)+'>='+str(minimum)+')'
        ref=spec.get('references')
        if ref:
            if not isinstance(ref,dict):raise ValueError('Référence invalide.')
            sql+=' REFERENCES '+identifier(self._name(ref.get('table')))+'('+identifier(self._name(ref.get('column')))+')'
        return name,sql

    @staticmethod
    def _value(value):
        if value is not None and type(value) not in (str,int,float,bool):raise ValueError('Valeur simple attendue.')
        if isinstance(value,str) and len(value)>20000:raise ValueError('Valeur texte trop longue.')
        if type(value) is int and not -(2**63)<=value<2**63:raise ValueError('Entier SQLite hors limites.')
        if type(value) is float and not math.isfinite(value):raise ValueError('Nombre fini attendu.')
        return value

    def _mutate(self,eid,fn,destructive=False):
        with self.lab.lock:
            env=self._environment(eid,True)
            with closing(sqlite3.connect(':memory:')) as c:
                c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA trusted_schema=OFF')
                with database(env['db_path']) as src:backup_database(src,c)
                c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2_000_000)
                started=time.monotonic();c.set_progress_handler(lambda:int(time.monotonic()-started>5),1000)
                result=fn(c) or {};c.commit()
                if c.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Une contrainte étrangère est incohérente.')
                snapshot_id=self.lab.snapshot(eid)['id'] if destructive else None
                with database(env['db_path']) as dst:backup_database(c,dst)
            return dict(**result,snapshot_id=snapshot_id)

    def action(self,args):
        eid=args.get('env_id');op=args.get('operation');name=self._name(args.get('table'),'Table')
        if op=='create_table':
            specs=args.get('columns')
            if not isinstance(specs,list) or not 1<=len(specs)<=100:raise ValueError('Définissez de 1 à 100 colonnes.')
            definitions=[self._column_sql(s) for s in specs]
            if len({sqlite_name(n) for n,_ in definitions})!=len(definitions):raise ValueError('Noms de colonnes dupliqués.')
            pk=[n for (n,_),spec in zip(definitions,specs) if spec.get('primary_key')]
            parts=[sql for _,sql in definitions]
            if pk:parts.append('PRIMARY KEY ('+','.join(map(identifier,pk))+')')
            sql='CREATE TABLE '+identifier(name)+'('+','.join(parts)+')'
            return self._mutate(eid,lambda c:self._exec(c,sql))
        with self.lab.lock:
            self._environment(eid,True);table=self._table(eid,name);name=table['name']
            columns={col['name']:col for col in table['columns']}
            def realcol(n):
                n=self._name(n,'Colonne')
                if n not in columns:raise ValueError('Colonne inconnue : '+n)
                return identifier(n)
            if op=='add_column':
                _,definition=self._column_sql(args.get('column'),adding=True);sql='ALTER TABLE '+identifier(name)+' ADD COLUMN '+definition
                return self._mutate(eid,lambda c:self._exec(c,sql))
            if op in ('rename_column','drop_column'):
                col=realcol(args.get('column'));sql='ALTER TABLE '+identifier(name)+(' RENAME COLUMN '+col+' TO '+identifier(self._name(args.get('new_name'))) if op=='rename_column' else ' DROP COLUMN '+col)
                return self._mutate(eid,lambda c:self._exec(c,sql),True)
            if op=='drop_table':return self._mutate(eid,lambda c:self._exec(c,'DROP TABLE '+identifier(name)),True)
            if op not in ('insert_row','update_row','delete_row'):raise ValueError('Opération inconnue.')
            values=args.get('values',{})
            if not isinstance(values,dict) or len(values)>100 or (op!='delete_row' and not values):raise ValueError('Valeurs de colonnes requises.')
            for key,value in values.items():realcol(key);self._value(value)
            if op=='insert_row':
                sql='INSERT INTO '+identifier(name)+'('+','.join(map(realcol,values))+') VALUES ('+','.join('?' for _ in values)+')'
                return self._mutate(eid,lambda c:self._exec(c,sql,list(values.values())))
            key=args.get('key');pk=[col['name'] for col in table['columns'] if col['pk']]
            if not pk or not isinstance(key,dict) or set(key)!=set(pk):raise ValueError('Une clé primaire complète est nécessaire ; utilisez le SQL libre pour les autres tables.')
            where=' AND '.join(realcol(k)+' IS ?' for k in pk);params=[self._value(key[k]) for k in pk]
            def edit(c):
                if c.execute('SELECT COUNT(*) FROM '+identifier(name)+' WHERE '+where,params).fetchone()[0]!=1:raise ValueError('La clé doit identifier exactement une ligne.')
                sql=('DELETE FROM '+identifier(name)+' WHERE '+where if op=='delete_row' else 'UPDATE '+identifier(name)+' SET '+','.join(realcol(k)+'=?' for k in values)+' WHERE '+where)
                return self._exec(c,sql,params if op=='delete_row' else list(values.values())+params)
            return self._mutate(eid,edit,True)

    @staticmethod
    def _exec(c,sql,params=()):
        before=c.total_changes;c.execute(sql,params);return dict(changes=c.total_changes-before,sql=sql)

    def import_data(self,args):
        text=args.get('text');fmt=args.get('format');name=self._name(args.get('table'),'Table')
        if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_TEXT:raise ValueError('Fichier limité à 750 Kio.')
        if fmt=='csv':
            reader=csv.reader(io.StringIO(text,newline=''),strict=True)
            try:columns=next(reader)
            except StopIteration:raise ValueError('CSV vide.')
            rows=[]
            for row in reader:
                if len(row)!=len(columns):raise ValueError('Nombre de colonnes CSV incohérent.')
                rows.append([self._value(value) for value in row])
                if len(rows)>MAX_ROWS:raise ValueError('Import limité à 10 000 lignes.')
        elif fmt=='json':
            try:records=strict_json_loads(text)
            except RecursionError:raise ValueError('JSON trop imbriqué.')
            if not isinstance(records,list) or not records or len(records)>MAX_ROWS or any(not isinstance(row,dict) for row in records):raise ValueError('Liste JSON non vide de 10 000 objets au plus attendue.')
            columns=list(records[0])
            if any(set(row)!=set(columns) for row in records):raise ValueError('Toutes les lignes JSON doivent posséder les mêmes clés.')
            rows=[[self._value(row[col]) for col in columns] for row in records]
        else:raise ValueError('Format CSV ou JSON attendu.')
        if not 1<=len(columns)<=100 or len({sqlite_name(self._name(col,'Colonne')) for col in columns})!=len(columns):raise ValueError('En-têtes absents ou dupliqués.')
        # CSV remains TEXT deliberately; JSON primitive types retain SQLite values.
        types=[]
        for i,col in enumerate(columns):
            kinds={type(row[i]) for row in rows if row[i] is not None}
            types.append('INTEGER' if kinds and kinds<={int,bool} else 'REAL' if kinds and kinds<={int,float,bool} else 'TEXT')
        def load(c):
            c.execute('CREATE TABLE '+identifier(name)+'('+','.join(identifier(col)+' '+kind for col,kind in zip(columns,types))+')')
            sql='INSERT INTO '+identifier(name)+' VALUES ('+','.join('?' for _ in columns)+')'
            c.executemany(sql,rows);return dict(changes=len(rows),table=name,row_count=len(rows))
        return self._mutate(args.get('env_id'),load)

    def export(self,eid,table,fmt):
        if fmt not in ('csv','json'):raise ValueError('Format CSV ou JSON attendu.')
        with self.lab.lock:
            env=self._environment(eid);spec=self._table(eid,table)
            with database(env['db_path']) as c:
                started=time.monotonic();c.execute('PRAGMA trusted_schema=OFF');c.set_progress_handler(lambda:int(time.monotonic()-started>5),1000)
                cur=c.execute('SELECT * FROM '+identifier(spec['name'])+' LIMIT 10001');columns=[d[0] for d in cur.description];rows=[];budget=0
                for row in cur:
                    if len(rows)>=MAX_ROWS:raise ValueError('Export limité à 10 000 lignes : filtrez vos données dans SQL puis exportez un sous-ensemble.')
                    if any(isinstance(v,bytes) or type(v) is float and not math.isfinite(v) for v in row):raise ValueError('Export CSV/JSON fidèle impossible pour BLOB ou nombre non fini ; convertissez explicitement dans SQL.')
                    if any(isinstance(v,str) and len(v)>20000 for v in row):raise ValueError('Cellule trop longue pour un export fidèle.')
                    budget+=len(json.dumps(list(row),ensure_ascii=False).encode('utf-8'))
                    if budget>5_000_000:raise ValueError('Export supérieur à 5 Mo.')
                    rows.append(list(row))
            converted=rows
            if fmt=='csv':
                stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(columns);writer.writerows(converted);content=stream.getvalue()
            else:content=json.dumps([dict(zip(columns,row)) for row in converted],ensure_ascii=False,allow_nan=False,indent=2)
            if len(content.encode('utf-8'))>5_000_000:raise ValueError('Export supérieur à 5 Mo.')
            safe=re.sub(r'[^\w.-]+','_',spec['name'],flags=re.UNICODE)[:80] or 'table'
            return dict(filename=safe+'.'+fmt,content=content,format=fmt,row_count=len(rows))
