"""Isolated browser QA for training and sandbox. Never uses personal data."""
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.engine import Lab
from lab.server import Server

fixture=ROOT/'work/training-lot1/ui-validation'
fixture.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'web',fixture/'web',dirs_exist_ok=True)
lab=Lab(fixture)
if not any(e['name']=='Atelier libre QA' for e in lab.list_items('environments')):
    lab.sandbox.create(dict(name='Atelier libre QA',table_count=2,row_count=8,seed=19))
server=Server(8769,lab)
print('QA Entraînement : http://127.0.0.1:8769',flush=True)
try:server.serve_forever(poll_interval=.1)
except KeyboardInterrupt:pass
finally:server.server_close();lab.shutdown()
