"""Manage only a project-owned loopback Ollama child process, if needed."""
from pathlib import Path
import os
import subprocess
import time
import requests

ROOT = Path(__file__).resolve().parent


def ensure_local_runtime():
    if os.getenv('MEOWMEMO_CAPTION_PROVIDER') != 'ollama':
        return None
    try:
        requests.get('http://127.0.0.1:11434/api/version', timeout=.5).raise_for_status()
        return None
    except requests.RequestException:
        pass
    binary = ROOT / 'runtime/ollama/ollama'
    if not binary.exists():
        print('Local caption runtime is missing. Audio analysis remains available.', flush=True)
        return None
    env = {**os.environ, 'OLLAMA_HOST': '127.0.0.1:11434', 'OLLAMA_MODELS': str(ROOT / 'local-models'),
           'OLLAMA_NO_CLOUD': '1', 'OLLAMA_CONTEXT_LENGTH': '4096', 'OLLAMA_NUM_PARALLEL': '1'}
    log_path = ROOT / 'artifacts/ollama-runtime.log'
    with log_path.open('a') as log:
        process = subprocess.Popen([str(binary), 'serve'], env=env, stdout=log, stderr=log)
    for _ in range(40):
        if process.poll() is not None:
            break
        try:
            requests.get('http://127.0.0.1:11434/api/version', timeout=.5).raise_for_status()
            print('Local caption runtime ready; cloud features disabled.', flush=True)
            return process
        except requests.RequestException:
            time.sleep(.25)
    print('Local caption runtime is not ready; see artifacts/ollama-runtime.log.', flush=True)
    return process


def stop_owned_runtime(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
