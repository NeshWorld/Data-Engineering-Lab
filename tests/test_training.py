"""Adversarial practice checks using disposable project-local workspaces."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from lab.engine import Lab
from lab import training_validators as checks

ROOT=Path(__file__).resolve().parents[1]
ATELIER="""CREATE TABLE apprenants(id INTEGER PRIMARY KEY,nom TEXT NOT NULL,email TEXT NOT NULL UNIQUE);
CREATE TABLE inscriptions(id INTEGER PRIMARY KEY,apprenant_id INTEGER NOT NULL REFERENCES apprenants(id) ON DELETE CASCADE,atelier TEXT NOT NULL,inscrit_le TEXT NOT NULL,UNIQUE(apprenant_id,atelier));"""
STOCKS="""CREATE TABLE produits(id INTEGER PRIMARY KEY,sku TEXT NOT NULL UNIQUE);
CREATE TABLE stocks(produit_id INTEGER NOT NULL REFERENCES produits(id),depot TEXT NOT NULL,quantite INTEGER NOT NULL CHECK(quantite>=0),PRIMARY KEY(produit_id,depot));"""

class TrainingCase(unittest.TestCase):
 def setUp(self):
  (ROOT/'work').mkdir(exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(prefix='test-training-',dir=ROOT/'work')
  self.root=Path(self.temp.name);self.lab=Lab(self.root,bootstrap=False)
  self.service=self.lab.training
 def tearDown(self):
  self.lab.shutdown();self.temp.cleanup()
 def submit(self,eid,code,ack=True):
  if ack:self.lab.acknowledge(True)
  aid=self.service.validate(dict(exercise_id=eid,code=code))['attempt_id']
  self.lab.jobs[aid]['thread'].join(15)
  self.assertFalse(self.lab.jobs[aid]['thread'].is_alive())
  result=self.service.attempt(aid)
  self.assertNotEqual(result['status'],'running')
  return result
 def test_public_catalog_has_no_solution_or_unrevealed_hints(self):
  data=self.service.catalog();self.assertEqual(len(data['exercises']),10)
  self.assertEqual(len(data['skills']),55)
  for e in data['exercises']:
   self.assertFalse(set(e)&{'hints','solution','tests','validator_id'})
  self.assertEqual(self.service.exercise('py-normaliser-evenements')['hints'],[])
 def test_start_save_hints_and_restart_preserve_local_progress(self):
  eid='py-normaliser-evenements';self.service.start(dict(exercise_id=eid))
  self.service.save(dict(exercise_id=eid,code='my draft',notes='Une difficulté',needs_review=True))
  for _ in range(5):self.service.hint(dict(exercise_id=eid))
  self.service.start(dict(exercise_id=eid))
  self.lab.shutdown();self.lab=Lab(self.root,bootstrap=False);self.service=self.lab.training
  data=self.service.exercise(eid)
  self.assertEqual(data['progress']['code'],'my draft');self.assertEqual(data['progress']['notes'],'Une difficulté')
  self.assertTrue(data['progress']['needs_review']);self.assertEqual(len(data['hints']),3)
 def test_python_requires_explicit_existing_consent(self):
  with self.assertRaises(PermissionError):self.service.validate(dict(exercise_id='py-bilan-qualite',code='pass'))
 def test_bad_arguments_and_notes_are_rejected(self):
  for args in ({'exercise_id':'unknown','code':'x'},{'exercise_id':'py-bilan-qualite','code':'x','notes':'a'*5001},{'exercise_id':'py-bilan-qualite','code':'x','needs_review':'yes'},{'exercise_id':'py-bilan-qualite','code':'x','path':'outside'}):
   with self.assertRaises(ValueError):self.service.save(args)
 def test_starters_never_pass(self):
  for e in self.service.exercises.values():
   with self.subTest(eid=e['id']):
    a=self.submit(e['id'],e['starter']);self.assertEqual(a['status'],'failed');self.assertLess(a['passed'],3)
 def test_input_mutation_is_a_real_failure(self):
  code="""def normaliser_evenements(lignes):
    result=[]
    for item in lignes:
        value=item.get('id')
        key='' if value is None else str(value).strip()
        if key and key not in [row['id'] for row in result]:
            city=item.get('ville')
            result.append({'id':key,'ville':'' if city is None else str(city).strip().title()})
        item['mutated']=True
    return result
"""
  a=self.submit('py-normaliser-evenements',code)
  self.assertEqual(a['status'],'failed');self.assertEqual(a['passed'],1)
  self.assertIn('modifier',a['stderr'])
 def test_integer_counters_are_strict_but_sql_numbers_are_tolerant(self):
  self.assertFalse(checks.compare_values({'total':1.0},{'total':1})[0])
  self.assertFalse(checks.compare_values(True,1)[0])
  self.assertFalse(checks.compare_values(10**1000,1.0)[0])
  self.assertTrue(checks.compare_sql({'columns':['x'],'rows':[[1.0]]},{'columns':['x'],'rows':[[1]]})[0])
 def test_fixture_failure_is_technical_not_student_failure(self):
  with patch('lab.training.checks.sql_fixture',side_effect=sqlite3.OperationalError('fixture QA indisponible')):
   a=self.submit('sql-filtrer-alertes','SELECT 1')
  self.assertEqual(a['status'],'error');self.assertEqual(a['passed'],0)
  self.assertTrue(all(c['status']=='skipped' for c in a['cases']))
 def test_schemas_accept_real_declared_constraints(self):
  for eid,code in [('schema-atelier',ATELIER),('schema-stocks',STOCKS)]:
   with self.subTest(eid=eid):
    a=self.submit(eid,code);self.assertEqual(a['status'],'success',a)
 def test_composite_identifier_does_not_masquerade_as_simple_pk(self):
  code=STOCKS.replace('id INTEGER PRIMARY KEY,sku TEXT NOT NULL UNIQUE','id INTEGER,extra TEXT,sku TEXT NOT NULL UNIQUE,PRIMARY KEY(id,extra),UNIQUE(id)')
  a=self.submit('schema-stocks',code);self.assertEqual(a['status'],'failed');self.assertIn('primaire',a['cases'][0]['message'])
 def test_permanent_rows_and_update_blocking_trigger_are_refused(self):
  for suffix in ("INSERT INTO produits VALUES(1,'demo');", "CREATE TRIGGER block_update BEFORE UPDATE ON stocks BEGIN SELECT RAISE(ABORT,'blocked'); END;"):
   with self.subTest(suffix=suffix):
    a=self.submit('schema-stocks',STOCKS+suffix);self.assertEqual(a['status'],'failed')
 def test_success_survives_later_failure_and_finalization_is_idempotent(self):
  good=self.submit('schema-stocks',STOCKS)
  bad=self.submit('schema-stocks','CREATE TABLE wrong(x);')
  self.service._finalize(copy.deepcopy(good))
  p=self.service.exercise('schema-stocks')['progress']
  self.assertEqual((p['attempt_count'],p['success_count'],p['status'],p['last_status']),(2,1,'completed','failed'))
  self.assertEqual(p['code'],'CREATE TABLE wrong(x);')
 def test_terminal_result_and_progress_rollback_together(self):
  a=self.submit('schema-stocks',STOCKS)
  with self.lab.connect() as db:
   db.execute("CREATE TRIGGER qa_fail_progress BEFORE INSERT ON training_progress BEGIN SELECT RAISE(ABORT,'QA write failure'); END;")
  modified=copy.deepcopy(a);modified['status']='failed'
  with self.assertRaises(sqlite3.IntegrityError):self.service._finalize(modified)
  self.assertEqual(self.service.attempt(a['id'])['status'],'success')
  self.assertEqual(self.service.exercise('schema-stocks')['progress']['success_count'],1)
 def test_cancel_and_interrupted_restart_are_distinct(self):
  self.lab.acknowledge(True)
  aid=self.service.validate(dict(exercise_id='py-bilan-qualite',code='def bilan_qualite(lignes):\n    while True: pass'))['attempt_id']
  self.service.cancel(dict(attempt_id=aid));self.lab.jobs[aid]['thread'].join(8)
  self.assertEqual(self.service.attempt(aid)['status'],'cancelled')
  a=self.service.attempt(aid);a['status']='running';a['cases'][0]['status']='running';self.service._put('training_attempts',a)
  self.lab.shutdown();self.lab=Lab(self.root,bootstrap=False);self.service=self.lab.training
  recovered=self.service.attempt(aid)
  self.assertEqual(recovered['status'],'error');self.assertTrue(recovered['interrupted'])
  self.assertEqual(self.service.exercise('py-bilan-qualite')['progress']['last_status'],'error')
 def test_python_timeout_does_not_declare_success(self):
  a=self.submit('py-bilan-qualite','def bilan_qualite(lignes):\n    while True: pass')
  self.assertEqual(a['status'],'failed');self.assertEqual(a['passed'],0);self.assertIsNotNone(a['error'])
 def test_false_constant_output_does_not_pass_other_populations(self):
  a=self.submit('py-bilan-qualite','def bilan_qualite(lignes):\n    return {"total":0,"manquantes":0,"doublons":0,"negatives":0}')
  self.assertEqual(a['status'],'failed');self.assertEqual(a['passed'],1)

if __name__=='__main__':unittest.main()
