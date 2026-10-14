"""Start the offline lab from this directory only."""
import argparse
import sys
from pathlib import Path
import threading
import webbrowser
from lab.engine import Lab
from lab.server import Server

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Data Engineering Lab — application locale hors ligne')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    lab=Lab(root)
    try:
        server=Server(args.port,lab)
    except OSError as exc:
        print(f'Impossible d’ouvrir le port {args.port} : {exc}. Essayez --port 8766.')
        return 1
    url=f'http://127.0.0.1:{server.server_address[1]}'
    print(f'Data Engineering Lab : {url}\nProjet : {root}\nArrêt : Ctrl+C',flush=True)
    if args.open:
        threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        lab.shutdown()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
