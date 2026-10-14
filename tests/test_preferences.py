"""UI preference persistence and faithful SQLite schema tests. Disposable project fixtures."""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from lab.engine import Lab
from lab.storage import database
ROOT=Path(__file__).resolve().parents[1]

class PreferencesCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='test-preferences-',dir=ROOT/'work')
        self.root=Path(self.temp.name)
        self.lab=Lab(self.root,bootstrap=False)
        self.env=self.lab.create_environment(dict(name='Preferences QA',kind='commerce',size=0))
        self.eid=self.env['id']
    def tearDown(self):
        self.lab.shutdown();self.temp.cleanup()
    def test_default_and_restart_preserves_consent(self):
        self.assertEqual(self.lab.preferences(),dict(theme='emerald',diagrams={}))
        self.lab.acknowledge(True)
        self.lab.preferences({'theme':'copper','diagram':{'env_id':self.eid,'positions':{'orders':{'x':1.5,'y':-2}},'viewport':{'x':10,'y':20,'scale':.7}}})
        self.lab.shutdown();self.lab=Lab(self.root,bootstrap=False)
        self.assertEqual(self.lab.preferences()['theme'],'copper')
        self.assertEqual(self.lab.preferences()['diagrams'][self.eid]['positions']['orders']['x'],1.5)
        self.assertTrue(self.lab.state()['python_ack'])
    def test_partial_merge_and_explicit_reorganization(self):
        self.lab.preferences({'diagram':{'env_id':self.eid,'positions':{'a':{'x':1,'y':2}}}})
        self.lab.preferences({'theme':'amethyst'})
        self.lab.preferences({'diagram':{'env_id':self.eid,'positions':{'b':{'x':3,'y':4}}}})
        self.assertEqual(len(self.lab.preferences()['diagrams'][self.eid]['positions']),2)
        self.lab.preferences({'diagram':{'env_id':self.eid,'positions':{'b':{'x':5,'y':6}},'replace_positions':True}})
        self.assertEqual(self.lab.preferences()['diagrams'][self.eid]['positions'],{'b':{'x':5,'y':6}})
    def test_validation_is_atomic(self):
        bad=[{'diagram':{'env_id':self.eid,'positions':{'huge':{'x':10**400,'y':0}}}}, {}, {'theme':'unknown'}, {'python_ack':True}, {'diagram':[]}, {'diagram':{'env_id':'../x'}},
             {'diagram':{'env_id':self.eid,'positions':{'a':{'x':float('nan'),'y':0}}}},
             {'diagram':{'env_id':self.eid,'positions':{'a':{'x':True,'y':0}}}},
             {'diagram':{'env_id':self.eid,'viewport':{'x':0,'y':0,'scale':0}}},
             {'diagram':{'env_id':self.eid,'viewport':{'x':0,'y':float('inf'),'scale':1}}},
             {'diagram':{'env_id':self.eid,'positions':{'a':{'x':0,'y':0,'z':0}}}},
             {'diagram':{'env_id':self.eid,'replace_positions':True}},
             {'diagram':{'env_id':self.eid,'positions':{'a'*513:{'x':0,'y':0}}}},
             {'diagram':{'env_id':self.eid,'positions':{str(i):{'x':0,'y':0} for i in range(1001)}}}]
        for patch in bad:
            with self.subTest(patch=str(patch)[:120]):
                before=self.lab.preferences()
                with self.assertRaises((ValueError,TypeError)):self.lab.preferences(patch)
                self.assertEqual(self.lab.preferences(),before)
        with self.assertRaises(ValueError):self.lab.preferences({'theme':'copper','diagram':{'env_id':'bad'}})
        self.assertEqual(self.lab.preferences()['theme'],'emerald')
    def test_parallel_theme_and_layout_updates_do_not_clobber(self):
        def write(i):
            return self.lab.preferences({'theme':'arctic'} if i%2 else {'diagram':{'env_id':self.eid,'positions':{str(i):{'x':i,'y':i}}}})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(write,range(40)))
        p=self.lab.preferences();self.assertEqual(p['theme'],'arctic');self.assertEqual(len(p['diagrams'][self.eid]['positions']),20)
    def test_layout_is_scoped_by_environment(self):
        second=self.lab.create_environment(dict(name='Second',kind='events',size=0))
        for eid,x in [(self.eid,1),(second['id'],2)]:self.lab.preferences({'diagram':{'env_id':eid,'positions':{'same':{'x':x,'y':0}}}})
        self.assertEqual(self.lab.preferences()['diagrams'][self.eid]['positions']['same']['x'],1)
    def test_actual_composite_multiple_implicit_and_generated_schema(self):
        with database(self.env['db_path']) as c:
            c.executescript("""CREATE TABLE qa_parent(b INTEGER,a INTEGER,PRIMARY KEY(a,b));
            CREATE TABLE qa_child(x INTEGER,y INTEGER,z INTEGER,calc INTEGER GENERATED ALWAYS AS (x+y) VIRTUAL,
              FOREIGN KEY(x,y) REFERENCES qa_parent ON DELETE CASCADE,
              FOREIGN KEY(z,y) REFERENCES qa_parent(a,b));
            CREATE TABLE qa_orphan(x REFERENCES absent(id));
            CREATE TABLE qa_lookalike(qa_parent_id INTEGER);
            CREATE VIEW qa_view AS SELECT x,calc FROM qa_child;""")
        tables={t['name']:t for t in self.lab.schema(self.eid)['tables']}
        self.assertEqual([c['pk_ordinal'] for c in tables['qa_parent']['columns']],[2,1])
        generated=next(c for c in tables['qa_child']['columns'] if c['name']=='calc')
        self.assertEqual(generated['hidden'],2)
        fks=tables['qa_child']['foreign_keys'];self.assertEqual(len(fks),4)
        self.assertEqual(len(set(f['id'] for f in fks)),2)
        implicit=[f for f in fks if f['to'] is None];self.assertEqual(len(implicit),2)
        self.assertEqual([f['seq'] for f in implicit],[0,1]);self.assertTrue(all(f['on_delete']=='CASCADE' for f in implicit))
        self.assertEqual(tables['qa_lookalike']['foreign_keys'],[])
        self.assertEqual(tables['qa_orphan']['foreign_keys'][0]['table'],'absent')
        self.assertEqual(tables['qa_view']['type'],'view');self.assertIn('CREATE TABLE',tables['qa_child']['sql'])

if __name__=='__main__':unittest.main()
