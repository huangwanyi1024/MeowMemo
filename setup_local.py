"""Create the local AI environment. Run with Python 3.12; downloads dependencies."""
from pathlib import Path
import os,subprocess,sys,venv
ROOT=Path(__file__).resolve().parent
if sys.version_info[:2] != (3,12):
    raise SystemExit('Use Python 3.12: python3.12 setup_local.py')
env=ROOT/'.venv-meowmemo'
venv.EnvBuilder(with_pip=True).create(env)
python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
print('Ready. Run python3 start.py --ai. For captions/room vision, follow README Ollama setup.')
