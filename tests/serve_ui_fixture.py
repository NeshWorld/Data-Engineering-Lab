"""Disposable loopback fixture for the independent browser QA workflow.
All fixtures and captures stay within this project. Never used by run.py.
"""
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.engine import Lab
from lab.server import Server

lab_root=ROOT/'work/ui-validation'
lab_root.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'web',lab_root/'web',dirs_exist_ok=True)
lab=Lab(lab_root)
server=Server(8767,lab)
print('Browser QA: http://127.0.0.1:8767',flush=True)
try:
    server.serve_forever(poll_interval=.1)
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    lab.shutdown()
