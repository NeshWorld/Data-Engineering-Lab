"""Independent adversarial checks; all temporary data stays in the project."""
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from lab.engine import Lab, execute_sql
ROOT=Path(__file__).resolve().parents[1]

class EngineCase(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='test-engine-',dir=ROOT/'work')
        self.root=Path(self.temp.name)
        self.lab=Lab(self.root,bootstrap=False)
        self.env=self.lab.create_environment(dict(name='QA fictif',kind='commerce',seed=91,size=12))
        self.eid=self.env['id']; self.db=Path(self.env['db_path'])
    def tearDown(self):
        self.lab.shutdown(); self.temp.cleanup()
    def wait(self,rid):
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            run=self.lab.get('runs',rid)
            if run['status']!='running':
                self.lab.jobs[rid]['thread'].join(timeout=2)
                return run
            time.sleep(.03)
        self.fail('Execution did not finish within test deadline')
    def python(self,code,**extra):
        self.lab.acknowledge(True)
        return self.wait(self.lab.launch('python',dict(env_id=self.eid,code=code,**extra))['run_id'])
    def pipeline(self,steps,consent=False):
        if consent:self.lab.acknowledge(True)
        return self.wait(self.lab.launch('pipeline',dict(env_id=self.eid,steps=steps))['run_id'])
    def test_real_sql_join_cte_views_indexes(self):
        r=self.lab.sql(self.eid,"CREATE TABLE qa_p(id INTEGER PRIMARY KEY,name TEXT); CREATE TABLE qa_c(pid INTEGER REFERENCES qa_p(id),amount REAL); INSERT INTO qa_p VALUES(1,'alpha'),(2,'beta'); INSERT INTO qa_c VALUES(1,3.5),(1,4.5),(2,2); CREATE INDEX qa_c_pid ON qa_c(pid); CREATE VIEW qa_v AS SELECT p.name,SUM(c.amount) amount FROM qa_p p JOIN qa_c c ON p.id=c.pid GROUP BY p.id; WITH f AS (SELECT * FROM qa_v WHERE amount>3) SELECT name AS value,amount AS value FROM f;")
        self.assertEqual(r['columns'],['value','value']); self.assertEqual(r['rows'],[['alpha',8.0]])
        schema={t['name']:t for t in self.lab.schema(self.eid)['tables']}
        self.assertEqual(schema['qa_v']['type'],'view'); self.assertEqual(schema['qa_c']['foreign_keys'][0]['table'],'qa_p')
        self.assertIn('qa_c_pid',[i['name'] for i in schema['qa_c']['indexes']])
    def test_trigger_and_literal_statement_boundaries(self):
        r=self.lab.sql(self.eid,"CREATE TABLE qa_i(value TEXT); CREATE TABLE qa_a(value TEXT); CREATE TRIGGER qa_after AFTER INSERT ON qa_i BEGIN INSERT INTO qa_a VALUES('quoted;semicolon'); INSERT INTO qa_a VALUES(NEW.value); END; INSERT INTO qa_i VALUES('source;value'); SELECT value FROM qa_a ORDER BY rowid;")
        self.assertEqual(r['rows'],[['quoted;semicolon'],['source;value']])
    def test_atomic_rollback_implicit_explicit_and_committed_batches(self):
        batches=['CREATE TABLE qa_r(x); INSERT INTO qa_r VALUES(4); SELECT * FROM absent_qa;','CREATE TABLE qa_r(x); BEGIN; INSERT INTO qa_r VALUES(4); SELECT * FROM absent_qa;','BEGIN; CREATE TABLE qa_r(x); INSERT INTO qa_r VALUES(4); COMMIT; SELECT * FROM absent_qa;']
        for code in batches:
            with self.subTest(code=code):
                with self.assertRaises(sqlite3.Error):self.lab.sql(self.eid,code)
                self.assertEqual(self.lab.sql(self.eid,"SELECT name FROM sqlite_master WHERE name='qa_r'")['rows'],[])
        self.assertTrue(any(r['status']=='error' for r in self.lab.list_items('runs')))
    def test_constraints_commit_and_rollback(self):
        with self.assertRaises(sqlite3.IntegrityError):self.lab.sql(self.eid,'CREATE TABLE qa_p(id PRIMARY KEY); CREATE TABLE qa_c(id REFERENCES qa_p(id)); INSERT INTO qa_c VALUES(999);')
        self.assertEqual(self.lab.sql(self.eid,"SELECT name FROM sqlite_master WHERE name='qa_p'")['rows'],[])
        self.lab.sql(self.eid,'BEGIN; CREATE TABLE qa_t(x); INSERT INTO qa_t VALUES(8); COMMIT;')
        self.lab.sql(self.eid,'BEGIN; INSERT INTO qa_t VALUES(9); ROLLBACK;')
        self.assertEqual(self.lab.sql(self.eid,'SELECT * FROM qa_t')['rows'],[[8]])
    def test_sql_external_io_forbidden(self):
        target=self.root/'forbidden.sqlite'; quoted=str(target).replace("'","''")
        for sql in [f"ATTACH DATABASE '{quoted}' AS external;",f"VACUUM INTO '{quoted}';",'DETACH DATABASE main;',"SELECT load_extension('nonexistent.dll');"]:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.Error):self.lab.sql(self.eid,sql)
            self.assertFalse(target.exists())
        for pragma in ['writable_schema=ON',"temp_store_directory='.'","data_store_directory='.'",'journal_mode=OFF','trusted_schema=ON']:
            with self.subTest(pragma=pragma),self.assertRaises(sqlite3.Error):self.lab.sql(self.eid,'PRAGMA '+pragma)
        self.assertEqual(self.lab.sql(self.eid,'PRAGMA integrity_check')['rows'],[['ok']])
    def test_sql_limits_count_cells_and_deadline(self):
        r=self.lab.sql(self.eid,'WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<1234) SELECT x FROM n;')
        self.assertEqual(r['row_count'],1234); self.assertEqual(len(r['rows']),1000); self.assertTrue(r['truncated'])
        r=self.lab.sql(self.eid,"SELECT zeroblob(8),printf('%.*c',21000,'z'),1e999;")
        self.assertEqual(r['rows'][0][0],'[BLOB 8 octets]'); self.assertLess(len(r['rows'][0][1]),21000); json.dumps(r,allow_nan=False)
        start=time.monotonic()
        with self.assertRaises((sqlite3.Error,TimeoutError)):execute_sql(self.db,'WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n;',deadline=.05)
        self.assertLess(time.monotonic()-start,2)
    def test_invalid_sql_configs_identifiers(self):
        for code in ['', ' ',None,'x'*200001]:
            with self.subTest(type=type(code)),self.assertRaises(ValueError):self.lab.sql(self.eid,code)
        for args in [dict(seed=True),dict(size=-1),dict(size=10001),dict(seed=-1),dict(anomalies='yes')]:
            with self.subTest(args=args),self.assertRaises(ValueError):self.lab.create_environment(dict(name='bad',kind='commerce',**args))
        with self.assertRaises(ValueError):self.lab.get('environments','../outside')
    def test_artifacts_survive_reset_and_restart(self):
        saved=[self.lab.save_artifact(dict(kind=k,name='Personnel',code=code,env_id=self.eid)) for k,code in [('sql','SELECT 99;'),('python',"print('perso')")]]
        self.lab.sql(self.eid,'CREATE TABLE qa_disposable(x);'); self.lab.regenerate(self.eid)
        self.assertEqual(self.lab.sql(self.eid,"SELECT name FROM sqlite_master WHERE name='qa_disposable'")['rows'],[])
        restarted=Lab(self.root,bootstrap=False)
        try:
            for a in saved:
                self.assertEqual(Path(a['path']).read_text(encoding='utf-8'),a['code']); self.assertEqual(restarted.get('artifacts',a['id'])['code'],a['code'])
            self.assertEqual(len(restarted.state()['environments']),1); self.assertTrue(restarted.list_items('runs'))
        finally:restarted.shutdown()
    def test_snapshot_restores_database_sources_rejects_other_env(self):
        source=self.db.parent/'source.csv'; before=source.read_bytes()
        self.lab.sql(self.eid,'CREATE TABLE qa_snapshot(x); INSERT INTO qa_snapshot VALUES(7);'); snap=self.lab.snapshot(self.eid)
        self.lab.sql(self.eid,'DELETE FROM qa_snapshot;'); source.write_text('bad\nchanged\n',encoding='utf-8'); self.lab.restore(self.eid,snap['id'])
        self.assertEqual(self.lab.sql(self.eid,'SELECT * FROM qa_snapshot')['rows'],[[7]]); self.assertEqual(source.read_bytes(),before)
        other=self.lab.create_environment(dict(name='Other',kind='events',size=1,seed=1))
        with self.assertRaises(ValueError):self.lab.restore(other['id'],snap['id'])
    def test_python_consent(self):
        with self.assertRaises(PermissionError):self.lab.launch('python',dict(env_id=self.eid,code='print(1)'))
        with self.assertRaises(PermissionError):self.lab.launch('pipeline',dict(env_id=self.eid,steps=[dict(id='p',type='python',code='print(1)')]))
        for wrong in [False,1,'true',None]:
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):self.lab.acknowledge(wrong)
        self.lab.acknowledge(True); restarted=Lab(self.root,bootstrap=False)
        try:self.assertTrue(restarted.state()['python_ack'])
        finally:restarted.shutdown()
    def test_python_output_exception_database_copy(self):
        self.lab.sql(self.eid,'CREATE TABLE qa_original(x); INSERT INTO qa_original VALUES(42);')
        code="import os,sqlite3,json\nfrom pathlib import Path\nprint('bonjour été')\nwith sqlite3.connect(os.environ['LAB_DB']) as c:c.execute('DELETE FROM qa_original')\nPath('result.json').write_text(json.dumps({'value':17}),encoding='utf-8')\nprint(Path.cwd()==Path(os.environ['LAB_WORKSPACE']))"
        run=self.python(code); self.assertEqual(run['status'],'success',run); self.assertIn('bonjour été',run['stdout']); self.assertIn('True',run['stdout']); self.assertEqual(run['result'],{'value':17})
        self.assertEqual(self.lab.sql(self.eid,'SELECT * FROM qa_original')['rows'],[[42]]); self.assertTrue(Path(run['workspace']).is_relative_to(self.root))
        run=self.python("raise RuntimeError('QA deliberate')"); self.assertEqual(run['status'],'error'); self.assertIn('QA deliberate',run['stderr'])
    def test_python_large_outputs_are_bounded(self):
        run=self.python("import sys\nsys.stdout.write('a'*300000)\nsys.stderr.write('b'*300000)"); self.assertEqual(run['status'],'success',run)
        for key in ['stdout','stderr']:self.assertLess(len(run[key]),66000); self.assertIn('tronquée',run[key])
    def test_python_timeout_cancel_invalid_limits(self):
        run=self.python('while True:pass',timeout=1); self.assertEqual(run['status'],'error',run); self.assertIn('Délai',run['error']); self.assertLess(run['duration_ms'],8000)
        rid=self.lab.launch('python',dict(env_id=self.eid,code='import time\ntime.sleep(20)'))['run_id']; self.assertTrue(self.lab.cancel(rid)['cancelled']); self.assertEqual(self.wait(rid)['status'],'cancelled'); self.assertFalse(self.lab.cancel(rid)['cancelled'])
        for timeout in [0,121,True,float('nan'),'2']:
            with self.subTest(timeout=timeout),self.assertRaises(ValueError):self.lab.launch('python',dict(env_id=self.eid,code='pass',timeout=timeout))
    def test_pipeline_csv_python_validate_load_query_export(self):
        code="import csv\nwith open('source.csv',newline='',encoding='utf-8-sig') as src:data=list(csv.DictReader(src))\nwith open('result.csv','w',newline='',encoding='utf-8') as dst:\n w=csv.writer(dst);w.writerow(['qa_id','flag'])\n for i,row in enumerate(data):w.writerow([i,'processed'])"
        steps=[dict(id='source',type='csv'),dict(id='transform',type='python',code=code),dict(id='check',type='validate',min_rows=1,required_columns=['qa_id','flag']),dict(id='load',type='load'),dict(id='query',type='sql',code='SELECT COUNT(*) AS n FROM pipeline_output;'),dict(id='export',type='export',path='exports/count.csv')]
        run=self.pipeline(steps,consent=True); self.assertEqual(run['status'],'success',run); self.assertEqual([s['status'] for s in run['steps']],['success']*6); self.assertGreater(run['result']['rows'][0][0],0)
        self.assertTrue((Path(run['workspace'])/'exports/count.csv').is_file()); self.assertEqual(self.lab.sql(self.eid,"SELECT name FROM sqlite_master WHERE name='pipeline_output'")['rows'],[])
    def test_dag_order_cycles_duplicate_missing_dependencies(self):
        run=self.pipeline([dict(id='query',type='sql',depends_on=['load'],code='SELECT COUNT(*) FROM qa_dag;'),dict(id='load',type='load',depends_on=['source'],table='qa_dag'),dict(id='source',type='csv')]); self.assertEqual(run['status'],'success',run); self.assertEqual([s['id'] for s in run['steps']],['source','load','query'])
        invalid=[[],[dict(id='a',type='csv'),dict(id='a',type='load')],[dict(id='a',type='csv',depends_on=['missing'])],[dict(id='a',type='csv',depends_on=['b']),dict(id='b',type='load',depends_on=['a'])]]
        for steps in invalid:
            with self.subTest(steps=steps),self.assertRaises(ValueError):self.lab.validate_pipeline(steps)
    def test_pipeline_failure_stops_and_paths_rejected(self):
        run=self.pipeline([dict(id='bad',type='validate',min_rows=999999),dict(id='unreached',type='sql',code='SELECT 1;')]); self.assertEqual(run['status'],'error'); self.assertEqual(len(run['steps']),1)
        for path in ['../../outside.csv',str(self.root/'outside.csv')]:
            with self.subTest(path=path):
                run=self.pipeline([dict(id='bad',type='csv',path=path)]); self.assertEqual(run['status'],'error',run); self.assertIn('répertoire',run['error'])
    def test_csv_malformed_headers_width_quotes(self):
        for content in ['a,a\n1,2\n',',b\n1,2\n','a,b\n1,2,3\n','a,b\n1\n','a,b\n1,"unterminated\n']:
            with self.subTest(content=content):
                (self.db.parent/'source.csv').write_text(content,encoding='utf-8'); run=self.pipeline([dict(id='read',type='csv')]); self.assertEqual(run['status'],'error',run)
    def test_export_refuses_truncated_results(self):
        run=self.pipeline([dict(id='q',type='sql',code='WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<1100) SELECT x FROM n;'),dict(id='e',type='export')]); self.assertEqual(run['status'],'error',run); self.assertIn('tronqué',run['error'])
    def test_profile_unusual_identifiers_and_nulls(self):
        self.lab.sql(self.eid,'CREATE TABLE "qa strange"("a""b" TEXT); INSERT INTO "qa strange" VALUES(NULL),(\'x\'),(\'x\');'); p=self.lab.profile(self.eid,'qa strange'); self.assertEqual(p['count'],3); self.assertEqual(p['columns'][0]['nulls'],1); self.assertEqual(p['columns'][0]['distinct'],1)
        with self.assertRaises(ValueError):self.lab.profile(self.eid,'qa strange; DROP TABLE anything')

    def test_transaction_comments_and_unclosed_transaction(self):
        for code in ['/* txn */ BEGIN; SELECT 1;', '/* txn */ BEGIN; SELECT 1; /* end */ COMMIT;']:
            self.assertEqual(self.lab.sql(self.eid,code)['rows'],[[1]])
    def test_nonfinite_python_json_does_not_poison_history(self):
        run=self.python("from pathlib import Path\nPath('result.json').write_text('{\"nested\":[NaN,Infinity]}')")
        self.assertEqual(run['status'],'error',run)
        self.assertIn('JSON non fini',run['error'])
        json.dumps(self.lab.state(),allow_nan=False)

    def test_infinite_view_has_deadline_and_reset_recovers(self):
        self.lab.sql(self.eid,'CREATE VIEW qa_infinite AS WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT x FROM n;')
        start=time.monotonic()
        with self.assertRaises(sqlite3.Error):self.lab.schema(self.eid)
        self.assertLess(time.monotonic()-start,8)
        self.lab.regenerate(self.eid)
        self.assertTrue(self.lab.schema(self.eid)['tables'])
    def test_stores_stocks_and_foreign_key_inspection(self):
        result=self.lab.sql(self.eid,'SELECT COUNT(DISTINCT store_id) FROM orders;')
        self.assertEqual(result['rows'],[[2]])
        self.assertEqual(self.lab.sql(self.eid,'PRAGMA foreign_key_check;')['rows'],[])
        self.assertTrue(self.lab.sql(self.eid,'SELECT s.name,p.name,st.quantity FROM stocks st JOIN stores s ON s.id=st.store_id JOIN products p ON p.id=st.product_id;')['rows'])

    def test_explorer_read_only_query_rejects_injected_mutation(self):
        self.assertTrue(self.lab.sql(self.eid,'SELECT * FROM orders LIMIT 2;',read_only=True)['rows'])
        with self.assertRaises(sqlite3.Error):self.lab.sql(self.eid,'SELECT * FROM orders WHERE 1; DROP TABLE orders;',read_only=True)
        self.assertEqual(self.lab.sql(self.eid,'SELECT COUNT(*) FROM orders;')['rows'],[[12]])

    def test_arbitrary_json_cannot_inject_run_metrics(self):
        run=self.python("from pathlib import Path\nPath('result.json').write_text('{\"columns\":\"record field\",\"row_count\":\"<img src=x>\"}')")
        self.assertEqual(run['status'],'success',run)
        self.assertEqual(run['row_count'],0)
        self.assertEqual(run['result']['columns'],'record field')

    def test_overflow_json_numbers_rejected_without_poison(self):
        run=self.python("from pathlib import Path\nPath('result.json').write_text('{\"nested\":[1e999]}')")
        self.assertEqual(run['status'],'error',run)
        self.assertIn('hors limites',run['error'])
        json.dumps(self.lab.state(),allow_nan=False)
        with self.assertRaises(ValueError):
            self.lab.save_artifact(dict(env_id=self.eid,kind='pipeline',name='overflow',code='{"steps":[{"id":"q","type":"sql","code":"SELECT 1","extra":1e999}]}'))
    def test_partial_bundle_failures_roll_back_generate_and_restore(self):
        import os
        from unittest.mock import patch
        from lab.datasets import generate
        initial={name:(self.db.parent/name).read_bytes() for name in ('lab.sqlite','source.csv','source.json')}
        real_replace=os.replace
        def fail_csv(source,target):
            if Path(target).name=='source.csv' and not Path(source).name.startswith('.rollback-'):
                raise PermissionError('QA locked CSV')
            return real_replace(source,target)
        with patch('os.replace',side_effect=fail_csv):
            with self.assertRaises(PermissionError):generate(self.db,'commerce',999,23)
        for name,content in initial.items():self.assertEqual((self.db.parent/name).read_bytes(),content)
        snap=self.lab.snapshot(self.eid)
        self.lab.sql(self.eid,'CREATE TABLE qa_keep(x); INSERT INTO qa_keep VALUES(99);')
        before=self.db.read_bytes()
        with patch('os.replace',side_effect=fail_csv):
            with self.assertRaises(PermissionError):self.lab.restore(self.eid,snap['id'])
        self.assertEqual(self.db.read_bytes(),before)
        self.assertEqual(self.lab.sql(self.eid,'SELECT * FROM qa_keep')['rows'],[[99]])
        self.assertFalse(list(self.db.parent.glob('.rollback-*')))
    def test_external_database_lock_has_bounded_backup(self):
        with sqlite3.connect(self.db) as external:
            external.execute('BEGIN EXCLUSIVE')
            start=time.monotonic()
            with self.assertRaises(TimeoutError):execute_sql(self.db,'SELECT 1;',deadline=.05)
            self.assertLess(time.monotonic()-start,4)
            external.rollback()
        external.close()
    def test_python_can_use_json_sources_and_optional_pandas(self):
        import importlib.util
        if not importlib.util.find_spec('pandas'):self.skipTest('pandas facultatif absent')
        run=self.python("import pandas as pd,os,sqlite3,json\nfrom pathlib import Path\nrows=json.loads(Path('source.json').read_text(encoding='utf-8'))\ndf=pd.DataFrame(rows)\nprint('pandas_rows',len(df))\nwith sqlite3.connect(os.environ['LAB_DB']) as c: print('sqlite_rows',pd.read_sql_query('SELECT COUNT(*) n FROM orders',c).iloc[0,0])")
        self.assertEqual(run['status'],'success',run)
        self.assertIn('pandas_rows 12',run['stdout'])
        self.assertIn('sqlite_rows 12',run['stdout'])

if __name__=='__main__':unittest.main()
