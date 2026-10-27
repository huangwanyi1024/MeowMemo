"""Portable repo launcher; preview needs stdlib only."""
from pathlib import Path
import argparse,os,subprocess,sys,webbrowser
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
mode=parser.add_mutually_exclusive_group()
mode.add_argument('--web',action='store_true',help='Frontend only (default)')
mode.add_argument('--ai',action='store_true',help='Python audio backend; run setup_local.py first')
parser.add_argument('--port',type=int,default=8765)
args=parser.parse_args()
if not 1024 <= args.port <= 65535: parser.error('Choose a port from 1024 to 65535.')
url=f'http://127.0.0.1:{args.port}/meowmemo.html'
if args.ai:
    runtime=ROOT/'.venv-meowmemo'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not runtime.exists():
        parser.exit(1,'AI environment missing. Run Python 3.12 setup_local.py first.\n')
    raise SystemExit(subprocess.call([str(runtime),str(ROOT/'work/meowmemo-local-ai/server.py'),str(args.port)],cwd=ROOT))
handler=partial(SimpleHTTPRequestHandler,directory=str(ROOT/'outputs/meowmemo-prototype'))
try:
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
except OSError:
    parser.exit(1,f'Port {args.port} is busy. If MeowMemo is already running, open {url}; otherwise choose --port {args.port+1}.\n')
print(f'MeowMemo frontend: {url}\nAI is disabled in preview mode. Ctrl+C stops the server.',flush=True)
webbrowser.open(url)
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
