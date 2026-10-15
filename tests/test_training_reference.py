"""All ten exercises must accept independently written implementations."""
from pathlib import Path
import tempfile
import unittest
from lab.engine import Lab
from reference_training import SOLUTIONS
ROOT=Path(__file__).resolve().parents[1]
class ReferenceTrainingCase(unittest.TestCase):
 def test_all_ten_correct_submissions_run_three_real_cases_each(self):
  with tempfile.TemporaryDirectory(prefix='test-training-reference-',dir=ROOT/'work') as folder:
   lab=Lab(Path(folder),bootstrap=False)
   try:
    lab.acknowledge(True)
    self.assertEqual(set(SOLUTIONS),set(lab.training.exercises))
    for eid,code in SOLUTIONS.items():
     with self.subTest(exercise=eid):
      aid=lab.training.validate(dict(exercise_id=eid,code=code))['attempt_id']
      lab.jobs[aid]['thread'].join(15)
      self.assertFalse(lab.jobs[aid]['thread'].is_alive())
      attempt=lab.training.attempt(aid)
      self.assertEqual((attempt['status'],attempt['passed'],attempt['total']),('success',3,3),attempt)
      self.assertTrue(all(case['status']=='success' for case in attempt['cases']))
      self.assertEqual(lab.training.exercise(eid)['progress']['success_count'],1)
   finally:lab.shutdown()
   reloaded=Lab(Path(folder),bootstrap=False)
   try:
    self.assertEqual(sum(p['status']=='completed' for p in reloaded.training.catalog()['progress'].values()),10)
   finally:reloaded.shutdown()
if __name__=='__main__':unittest.main()
