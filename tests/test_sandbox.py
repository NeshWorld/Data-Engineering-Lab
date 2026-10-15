"""Real sandbox actions on disposable fixtures under project/work."""
from pathlib import Path
import csv
import hashlib
import io
import json
import random
import sqlite3
import tempfile
import unittest
from lab.engine import Lab
from lab.storage import database

ROOT=Path(__file__).resolve().parents[1]
class SandboxCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='test-sandbox-',dir=ROOT/'work')
        self.lab=Lab(Path(self.temp.name),bootstrap=False);self.service=self.lab.sandbox
        self.env=self.service.create(dict(name='Libre',table_count=0));self.eid=self.env['id']
    def tearDown(self):self.lab.shutdown();self.temp.cleanup()
    def action(self,operation,table='robots',**args):
        return self.service.action(dict(env_id=self.eid,operation=operation,table=table,**args))
    def table(self,name='robots'):
        return self.action('create_table',name,columns=[dict(name='id',type='INTEGER',primary_key=True),dict(name='name',type='TEXT',not_null=True,unique=True)])
    def query(self,sql):return self.lab.sql(self.eid,sql,True)['rows']
    def test_empty_database_sources_and_existing_tools(self):
        self.assertTrue(self.env['sandbox']);self.assertEqual(self.lab.schema(self.eid)['tables'],[])
        self.assertEqual(self.lab.sql(self.eid,'SELECT 6*7 AS answer')['rows'],[[42]])
        folder=Path(self.env['db_path']).parent
        self.assertTrue((folder/'source.csv').is_file());self.assertEqual(json.loads((folder/'source.json').read_text()),[])
        with self.assertRaises(ValueError):self.lab.regenerate(self.eid)
    def test_visual_ddl_crud_and_automatic_restore(self):
        self.table();self.action('insert_row',values={'id':1,'name':'Rhéa'})
        r=self.action('update_row',key={'id':1},values={'name':'Gaïa'})
        self.assertEqual(r['changes'],1);self.assertTrue(r['snapshot_id']);self.assertEqual(self.query('SELECT name FROM robots'),[['Gaïa']])
        self.lab.restore(self.eid,r['snapshot_id']);self.assertEqual(self.query('SELECT name FROM robots'),[['Rhéa']])
        d=self.action('delete_row',key={'id':1});self.assertEqual(self.query('SELECT * FROM robots'),[])
        self.lab.restore(self.eid,d['snapshot_id']);self.assertEqual(len(self.query('SELECT * FROM robots')),1)
    def test_composite_keys_foreign_keys_checks_and_rollback(self):
        self.table('sites');self.action('insert_row','sites',values={'id':1,'name':'Nord'})
        self.action('create_table','stocks',columns=[dict(name='site_id',type='INTEGER',primary_key=True,references={'table':'sites','column':'id'}),dict(name='sku',type='TEXT',primary_key=True),dict(name='quantity',type='INTEGER',min=0,not_null=True)])
        self.action('insert_row','stocks',values={'site_id':1,'sku':'x','quantity':2})
        for row in [{'site_id':2,'sku':'y','quantity':1},{'site_id':1,'sku':'x','quantity':4},{'site_id':1,'sku':'z','quantity':-1}]:
            with self.subTest(row=row),self.assertRaises(sqlite3.IntegrityError):self.action('insert_row','stocks',values=row)
        self.assertEqual(len(self.query('SELECT * FROM stocks')),1)
        with self.assertRaises(ValueError):self.action('delete_row','stocks',key={'sku':'x'})
        self.action('update_row','stocks',key={'site_id':1,'sku':'x'},values={'quantity':7});self.assertEqual(self.query('SELECT quantity FROM stocks'),[[7]])
    def test_quoted_names_and_values_are_bound(self):
        name='table " é';self.table(name)
        self.action('insert_row',name,values={'id':1,'name':"Robert'); DROP TABLE sites;--"})
        result=self.service.export(self.eid,name,'json');self.assertEqual(json.loads(result['content'])[0]['name'],"Robert'); DROP TABLE sites;--")
        with self.assertRaises(ValueError):self.action('insert_row',name,values={'bad"name':4})
    def test_sqlite_ascii_case_matching_never_confuses_unicode_table_names(self):
        self.table('Ä');self.table('ä')
        self.action('insert_row','Ä',values={'id':1,'name':'majuscule'})
        self.action('insert_row','ä',values={'id':1,'name':'minuscule'})
        self.assertEqual(json.loads(self.service.export(self.eid,'Ä','json')['content'])[0]['name'],'majuscule')
        self.assertEqual(json.loads(self.service.export(self.eid,'ä','json')['content'])[0]['name'],'minuscule')
        self.table('MixedCase');self.action('insert_row','mixedcase',values={'id':1,'name':'ASCII correct'})
        self.assertEqual(json.loads(self.service.export(self.eid,'MIXEDCASE','json')['content'])[0]['name'],'ASCII correct')

    def test_alter_and_drop_have_real_schema_changes(self):
        self.table();self.action('add_column',column={'name':'extra','type':'TEXT'})
        self.action('rename_column',column='extra',new_name='label')
        self.assertIn('label',[c['name'] for c in self.lab.schema(self.eid)['tables'][0]['columns']])
        r=self.action('drop_column',column='label');self.assertTrue(r['snapshot_id'])
        self.action('drop_table');self.assertEqual(self.lab.schema(self.eid)['tables'],[])
    def test_no_unsafe_visual_changes_without_unique_key(self):
        self.lab.sql(self.eid,'CREATE TABLE unkeyed(value TEXT); INSERT INTO unkeyed VALUES ("a"),("a");')
        with self.assertRaises(ValueError):self.action('delete_row','unkeyed',key={'value':'a'})
        self.assertEqual(len(self.query('SELECT * FROM unkeyed')),2)
        self.lab.sql(self.eid,'CREATE TABLE nullable(a TEXT,b TEXT,PRIMARY KEY(a,b)); INSERT INTO nullable VALUES(NULL,"b"),(NULL,"b");')
        with self.assertRaises(ValueError):self.action('delete_row','nullable',key={'a':None,'b':'b'})
        self.assertEqual(len(self.query('SELECT * FROM nullable')),2)
    def test_existing_environment_protected_and_duplicate_is_independent(self):
        old=self.lab.create_environment(dict(name='Ancien',kind='commerce',size=3))
        digest=hashlib.sha256(Path(old['db_path']).read_bytes()).hexdigest()
        with self.assertRaises(ValueError):self.service.action(dict(env_id=old['id'],operation='drop_table',table='orders'))
        dup=self.service.duplicate(dict(env_id=old['id'],name='Copie libre'))
        self.assertTrue(dup['sandbox']);self.lab.sql(dup['id'],'CREATE TABLE only_copy(x);')
        self.assertEqual(hashlib.sha256(Path(old['db_path']).read_bytes()).hexdigest(),digest)
        self.assertNotIn('only_copy',[t['name'] for t in self.lab.schema(old['id'])['tables']])
    def test_generator_is_deterministic_related_and_configurable(self):
        config=dict(name='Fictif',table_count=3,row_count=200,seed=7,distribution='normal',null_rate=.3,duplicate_rate=.4,anomalies=True,related=True,start_date='2024-01-01',end_date='2024-01-03')
        rand=random.getstate();a=self.service.create(config);b=self.service.create(config);self.assertEqual(random.getstate(),rand)
        for table in ['table_1','table_2','table_3']:
            self.assertEqual(self.service.export(a['id'],table,'json')['content'],self.service.export(b['id'],table,'json')['content'])
        self.assertGreater(a['stats']['null_values'],0);self.assertGreater(a['stats']['duplicate_labels'],0);self.assertTrue(a['stats']['anomalies'])
        with database(a['db_path']) as c:
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertTrue(c.execute('SELECT MIN(event_date),MAX(event_date) FROM table_1').fetchone()[1]<='2024-01-03')
            self.assertGreater(c.execute('SELECT COUNT(*) FROM table_1 WHERE value<0').fetchone()[0],0)
    def test_generator_limits_reject_without_partial_environment(self):
        before=len(self.lab.list_items('environments'))
        for bad in [dict(table_count=9),dict(table_count=8,row_count=10000),dict(null_rate=float('nan')),dict(seed=True),dict(start_date='2025-05-01',end_date='2024-01-01'),dict(related=1),dict(distribution='magic')]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.service.create(dict(name='Invalide',**bad))
        self.assertEqual(len(self.lab.list_items('environments')),before)
    def test_csv_json_import_export_preserve_values(self):
        self.service.import_data(dict(env_id=self.eid,table='csv_table',format='csv',text='id,texte\r\n1,"un, deux"\r\n2,"ligne\ntexte"\r\n'))
        data=self.service.export(self.eid,'csv_table','csv')
        self.assertEqual(list(csv.reader(io.StringIO(data['content']))),[['id','texte'],['1','un, deux'],['2','ligne\ntexte']])
        records=[{'id':1,'value':None,'name':'é'},{'id':2,'value':1.25,'name':'x'}]
        self.service.import_data(dict(env_id=self.eid,table='json_table',format='json',text=json.dumps(records)))
        self.assertEqual(json.loads(self.service.export(self.eid,'json_table','json')['content']),records)
    def test_bad_imports_are_atomic_and_never_overwrite(self):
        self.table();self.action('insert_row',values={'id':1,'name':'préservé'})
        cases=[('csv','a,a\n1,2'),('csv','a,b\n1'),('csv','a\n"unclosed'),('json','[{"a":1},{"b":2}]'),('json','[{"a":NaN}]'),('json','[{"a":[]} ]'),('json','[]')]
        for fmt,text in cases:
            with self.subTest(text=text),self.assertRaises((ValueError,csv.Error)):self.service.import_data(dict(env_id=self.eid,table='bad',format=fmt,text=text))
        with self.assertRaises(sqlite3.OperationalError):self.service.import_data(dict(env_id=self.eid,table='robots',format='csv',text='a\nx'))
        self.assertEqual(self.query('SELECT name FROM robots'),[['préservé']])
        self.assertNotIn('bad',[t['name'] for t in self.lab.schema(self.eid)['tables']])
    def test_export_never_silently_truncates_or_replaces_blob(self):
        self.lab.sql(self.eid,"CREATE TABLE blob_table(x); INSERT INTO blob_table VALUES(zeroblob(2));")
        with self.assertRaises(ValueError):self.service.export(self.eid,'blob_table','json')
        self.lab.sql(self.eid,'CREATE TABLE many(x); WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<10001) INSERT INTO many SELECT x FROM n;')
        with self.assertRaises(ValueError):self.service.export(self.eid,'many','csv')
    def test_invalid_values_and_operations_rejected(self):
        self.table()
        for value in [2**80,float('inf'),{'x':1},'x'*20001]:
            with self.subTest(value=str(value)[:20]),self.assertRaises(ValueError):self.action('insert_row',values={'id':1,'name':value})
        with self.assertRaises(ValueError):self.action('mystery')
        with self.assertRaises(ValueError):self.action('add_column',column=dict(name='x',type='INTEGER',primary_key=True))

if __name__=='__main__':unittest.main()
