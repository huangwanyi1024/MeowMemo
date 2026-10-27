from pathlib import Path
import tempfile,shutil,subprocess,os,shlex
import sys
REAL=Path(sys.executable)
source=Path(__file__).resolve().parents[1]/'scripts/setup-and-run.sh'
with tempfile.TemporaryDirectory(prefix='meowmemo shell test ') as tmp:
 root=Path(tmp)/'Repo With Spaces'; (root/'scripts').mkdir(parents=True); bindir=Path(tmp)/'bin';bindir.mkdir()
 shutil.copy2(source,root/'scripts/setup-and-run.sh');(root/'requirements.txt').write_text('mock-only\n');(root/'setup_local.py').write_text('');(root/'work/meowmemo-local-ai').mkdir(parents=True);(root/'work/meowmemo-local-ai/server.py').write_text('')
 def put(name,text):
  p=bindir/name;p.write_text('#!/bin/bash\nset -e\n'+text);p.chmod(0o755)
 put('uname','echo Darwin\n')
 put('brew',f'echo {shlex.quote(str(Path(tmp)))}\n')
 put('ffmpeg','exit 0\n')
 put('ollama',f'echo "$*" >> {shlex.quote(str(root/"ollama-calls"))}\nif [ "$1" = pull ]; then touch {shlex.quote(str(root/"model-downloaded"))}; fi\n')
 venv_template=Path(tmp)/'venv-wrapper';venv_template.write_text('#!/bin/bash\nif [ "$1" = -m ]; then echo "No broken requirements found."; exit 0; fi\nif [ "$1" = work/meowmemo-local-ai/server.py ]; then sleep 0.1; exit 0; fi\nexec '+shlex.quote(str(REAL))+' "$@"\n');venv_template.chmod(0o755)
 put('python3.12',f'''if [[ "$*" == *"Python 3.12 required"* ]]; then exit 0; fi
if [ "${{1:-}}" = setup_local.py ]; then
 mkdir -p .venv-meowmemo/bin
 cp {shlex.quote(str(venv_template))} .venv-meowmemo/bin/python
 echo setup >> setup-calls
 exit 0
fi
exec {shlex.quote(str(REAL))} "$@"
''')
 put('curl',f'''case "$*" in
 *api/version*) echo '{{"version":"mock"}}' ;;
 *api/tags*) if [ -f {shlex.quote(str(root/'model-downloaded'))} ]; then echo '{{"models":[{{"name":"qwen3.5:4b"}}]}}'; else echo '{{"models":[]}}'; fi ;;
 *api/health*) echo '{{"ready":true,"modelVersion":"catmeows-local-v2"}}' ;;
 *api/captions/status*) echo '{{"available":true,"localOnly":true,"message":"local mock ready"}}' ;;
 *api/rooms/status*) echo '{{"available":true,"localOnly":true}}' ;;
 *) echo 'unexpected network request' >&2; exit 1 ;;
esac
''')
 env={**os.environ,'PATH':str(bindir)+':/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
 def run(*args): return subprocess.run(['/bin/bash',str(root/'scripts/setup-and-run.sh'),*args],env=env,capture_output=True,text=True,timeout=15)
 x=run('--check');assert x.returncode==0,x.stderr;assert not (root/'.venv-meowmemo').exists()
 for _ in range(2):
  x=run('--no-browser');assert x.returncode==0,(x.stdout,x.stderr);assert 'Ready /' in x.stdout
 assert (root/'setup-calls').read_text().count('setup')==1
 assert (root/'ollama-calls').read_text().count('pull')==1
 for port in ['abc','80','9999999999999999999999999']:
  x=run('--port',port);assert x.returncode==2,(port,x.stderr)
 # Failures stop the run and do not claim readiness.
 put('curl','exit 7\n');put('ollama','exit 9\n')
 x=run('--no-browser');assert x.returncode!=0;assert 'Ready /' not in x.stdout;assert 'Ollama failed to start' in x.stderr
 print('PASS: mock-only shell integration: paths with spaces; check-only no mutations; first setup/download; repeat skip; invalid ports; failed Ollama startup; no real installation/download/process service changes.')
