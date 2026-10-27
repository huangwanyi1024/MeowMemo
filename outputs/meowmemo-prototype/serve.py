"""Local preview; use the isolated local audio backend when it is installed."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import sys
import webbrowser
import threading
import time
import urllib.request

root = Path(__file__).resolve().parent
workspace = root.parent.parent
os.chdir(root)
port = int(next((v for v in sys.argv[1:] if v.isdecimal()), '8765'))
runtime = workspace / '.venv-meowmemo' / 'bin' / 'python'
backend = workspace / 'work' / 'meowmemo-local-ai' / 'server.py'
trained = backend.parent / 'artifacts' / 'classifier.joblib'
url = f'http://127.0.0.1:{port}/meowmemo.html'

if runtime.exists() and backend.exists() and trained.exists():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
            if response.status == 200:
                print(f'MeowMemo local AI is already running: {url}')
                webbrowser.open(url)
                sys.exit(0)
    except Exception:
        pass
    def open_when_ready():
        for _ in range(90):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except Exception:
                time.sleep(.5)
    threading.Thread(target=open_when_ready, daemon=True).start()
    # Replace this process; the model and its dependencies stay inside the venv.
    os.execv(str(runtime), [str(runtime), str(backend), str(port)])

if '--ai' in sys.argv:
    raise SystemExit('Local model is not installed here. See work/meowmemo-local-ai/README.md.')
try:
    server = ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
except OSError:
    print(f"Port {port} is already in use. If MeowMemo is already running, open http://127.0.0.1:{port}/")
    print(f"Otherwise try: python3 serve.py {port + 1}")
    sys.exit(1)
print(f"MeowMemo: {url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
webbrowser.open(url)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
