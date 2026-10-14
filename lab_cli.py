"""CLI for the same loopback API used by the interface; no remote services."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Data Engineering Lab — terminal')
    parser.add_argument('--port', type=int, default=8765)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    for name in ('schema', 'sql', 'python', 'pipeline'):
        item = sub.add_parser(name)
        item.add_argument('env_id')
        if name != 'schema':
            item.add_argument('file', type=Path)
    item = sub.add_parser('run')
    item.add_argument('run_id')
    args = parser.parse_args()
    def call(path, data=None):
        req = Request(f'http://127.0.0.1:{args.port}/api/{path}',
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=20) as response:
                result = json.load(response)
        except HTTPError as error:
            raise ValueError(json.load(error).get('error', str(error))) from error
        if not result['ok']:
            raise ValueError(result['error'])
        return result['data']
    try:
        if args.command == 'list':
            state = call('state')
            result = dict(environments=state['environments'], artifacts=state['artifacts'], python=state['python'], root=state['root'])
        elif args.command == 'schema':
            result = call('schema?env_id=' + args.env_id)
        elif args.command == 'run':
            result = call('runs?id=' + args.run_id)
        else:
            code = args.file.read_text(encoding='utf-8-sig')
            payload = dict(env_id=args.env_id)
            if args.command == 'pipeline':
                payload.update(json.loads(code))
                payload['env_id'] = args.env_id
            else:
                payload['code'] = code
            result = call(args.command, payload)
            if 'run_id' in result and args.command != 'sql':
                while True:
                    run = call('runs?id=' + result['run_id'])
                    if run['status'] != 'running':
                        result = run
                        break
                    time.sleep(.2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(isinstance(result, dict) and result.get('status') in ('error', 'cancelled'))
    except (ValueError, OSError, URLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
