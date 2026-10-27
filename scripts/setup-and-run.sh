#!/bin/bash
# macOS one-command installer and loopback-only launcher.
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_PORT=8765
TASK_CHECK=0
TASK_BROWSER=1
TASK_OLLAMA_PID=""
TASK_SERVER_PID=""
usage() {
  cat <<'HELP'
MeowMemo full local demo (macOS)
  bash scripts/setup-and-run.sh [--port 8765] [--no-browser]
  bash scripts/setup-and-run.sh --check

Installs missing Homebrew/Python 3.12/FFmpeg/Ollama, creates an isolated
Python environment, downloads qwen3.5:4b if absent, then opens the app.
First run needs internet and several GB of disk. No paid API key needed.
--check only reports prerequisites; it installs and starts nothing.
Ctrl+C stops only processes started by this script. Existing Ollama is kept.
HELP
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --check) TASK_CHECK=1; shift ;;
    --no-browser) TASK_BROWSER=0; shift ;;
    --port) [ "$#" -ge 2 ] || { echo 'Missing --port value.' >&2; exit 2; }; TASK_PORT="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
case "$TASK_PORT" in ''|*[!0-9]*) echo 'Port must be an integer.' >&2; exit 2 ;; esac
[ "${#TASK_PORT}" -le 5 ] && [ "$TASK_PORT" -ge 1024 ] && [ "$TASK_PORT" -le 65535 ] || { echo 'Use a port between 1024 and 65535.' >&2; exit 2; }
[ "$(uname -s)" = Darwin ] || { echo 'This installer supports macOS. See README for manual setup on other systems.' >&2; exit 1; }
cd "$TASK_ROOT"
find_brew() {
  command -v brew 2>/dev/null || { [ ! -x /opt/homebrew/bin/brew ] || echo /opt/homebrew/bin/brew; } || true
}
TASK_BREW="$(find_brew)"
if [ -z "$TASK_BREW" ] && [ -x /usr/local/bin/brew ]; then TASK_BREW=/usr/local/bin/brew; fi
if [ -n "$TASK_BREW" ]; then
  TASK_PREFIX="$("$TASK_BREW" --prefix)"
  export PATH="$TASK_PREFIX/bin:$TASK_PREFIX/sbin:$PATH"
fi
find_python() {
  command -v python3.12 2>/dev/null || {
    if [ -n "$TASK_BREW" ]; then
      TASK_PY_PREFIX="$("$TASK_BREW" --prefix python@3.12 2>/dev/null || true)"
      if [ -x "$TASK_PY_PREFIX/bin/python3.12" ]; then echo "$TASK_PY_PREFIX/bin/python3.12"; fi
    fi
  }
}
TASK_PYTHON="$(find_python)"
TASK_OLLAMA="$(command -v ollama 2>/dev/null || true)"
if [ -z "$TASK_OLLAMA" ] && [ -x /Applications/Ollama.app/Contents/Resources/ollama ]; then TASK_OLLAMA=/Applications/Ollama.app/Contents/Resources/ollama; fi
if [ "$TASK_CHECK" -eq 1 ]; then
  printf 'Repository: %s\nPython 3.12: %s\nFFmpeg: %s\nOllama: %s\nHomebrew: %s\n' "$TASK_ROOT" "${TASK_PYTHON:-missing}" "$(command -v ffmpeg || echo missing)" "${TASK_OLLAMA:-missing}" "${TASK_BREW:-missing}"
  [ ! -x "$TASK_ROOT/.venv-meowmemo/bin/python" ] || echo 'Repository Python environment: present'
  echo 'Check only. Nothing installed or started. Model availability is checked on launch.'
  exit 0
fi
cleanup() {
  TASK_STATUS=$?
  trap - EXIT INT TERM
  if [ -n "$TASK_SERVER_PID" ] && kill -0 "$TASK_SERVER_PID" 2>/dev/null; then kill "$TASK_SERVER_PID" 2>/dev/null || true; wait "$TASK_SERVER_PID" 2>/dev/null || true; fi
  if [ -n "$TASK_OLLAMA_PID" ] && kill -0 "$TASK_OLLAMA_PID" 2>/dev/null; then kill "$TASK_OLLAMA_PID" 2>/dev/null || true; wait "$TASK_OLLAMA_PID" 2>/dev/null || true; fi
  if [ "$TASK_STATUS" -ne 0 ] && [ "$TASK_STATUS" -ne 130 ]; then echo 'Setup/start did not finish. Read the error above, fix it and rerun; completed downloads/installations are reused.' >&2; fi
  exit "$TASK_STATUS"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf '\nMeowMemo · Full local AI setup / 完整本地 AI\nFirst run downloads Python dependencies and about 4 GB of model weights.\n'
if [ -z "$TASK_PYTHON" ] || ! command -v ffmpeg >/dev/null 2>&1 || [ -z "$TASK_OLLAMA" ]; then
  if [ -z "$TASK_BREW" ]; then
    echo 'Installing Homebrew from its official installer. macOS may ask for your password or Command Line Tools.'
    TASK_INSTALLER="$(mktemp -t meowmemo-brew)"
    curl --fail --location --show-error https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$TASK_INSTALLER"
    /bin/bash "$TASK_INSTALLER"
    rm -f "$TASK_INSTALLER"
    TASK_BREW="$(find_brew)"
    if [ -z "$TASK_BREW" ] && [ -x /usr/local/bin/brew ]; then TASK_BREW=/usr/local/bin/brew; fi
    [ -n "$TASK_BREW" ] || { echo 'Homebrew installation did not finish. Complete it, then rerun.' >&2; exit 1; }
    TASK_PREFIX="$("$TASK_BREW" --prefix)"
    export PATH="$TASK_PREFIX/bin:$TASK_PREFIX/sbin:$PATH"
  fi
  [ -n "$TASK_PYTHON" ] || "$TASK_BREW" install python@3.12
  command -v ffmpeg >/dev/null 2>&1 || "$TASK_BREW" install ffmpeg
  [ -n "$TASK_OLLAMA" ] || "$TASK_BREW" install ollama
  TASK_PYTHON="$(find_python)"
  if [ -z "$TASK_OLLAMA" ]; then TASK_OLLAMA="$(command -v ollama)"; fi
fi
[ -n "$TASK_PYTHON" ] || { echo 'Python 3.12 not found after installation.' >&2; exit 1; }
"$TASK_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 required"'
TASK_VENV="$TASK_ROOT/.venv-meowmemo/bin/python"
TASK_REQUIREMENTS_SHA="$(shasum -a 256 requirements.txt | awk '{print $1}')"
TASK_STAMP="$TASK_ROOT/.venv-meowmemo/.requirements-sha256"
if [ ! -x "$TASK_VENV" ] || [ ! -f "$TASK_STAMP" ] || [ "$(cat "$TASK_STAMP")" != "$TASK_REQUIREMENTS_SHA" ]; then
  "$TASK_PYTHON" setup_local.py
  printf '%s\n' "$TASK_REQUIREMENTS_SHA" > "$TASK_STAMP"
fi
"$TASK_VENV" -m pip check
# Explicitly choose local AI without modifying .env.local or exposing any key.
export MEOWMEMO_CAPTION_PROVIDER=ollama
export MEOWMEMO_LOCAL_MODEL=qwen3.5:4b
export MEOWMEMO_CLOUD_CAPTIONS=0
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
mkdir -p "$TASK_ROOT/.meowmemo-runtime"
if ! curl --fail --silent --max-time 2 http://127.0.0.1:11434/api/version >/dev/null; then
  "$TASK_OLLAMA" serve > "$TASK_ROOT/.meowmemo-runtime/ollama.log" 2>&1 &
  TASK_OLLAMA_PID=$!
  TASK_READY=0
  for ((TASK_TRY=0;TASK_TRY<60;TASK_TRY++)); do
    if curl --fail --silent --max-time 2 http://127.0.0.1:11434/api/version >/dev/null; then TASK_READY=1; break; fi
    kill -0 "$TASK_OLLAMA_PID" 2>/dev/null || break
    sleep 1
  done
  [ "$TASK_READY" -eq 1 ] || { echo 'Ollama failed to start; see .meowmemo-runtime/ollama.log.' >&2; exit 1; }
fi
if ! curl --fail --silent --max-time 5 http://127.0.0.1:11434/api/tags | "$TASK_VENV" -c 'import json,sys; sys.exit(0 if any(x.get("name")=="qwen3.5:4b" for x in json.load(sys.stdin).get("models",[])) else 1)'; then
  echo 'Downloading qwen3.5:4b. Keep this terminal open; rerunning resumes completed layers.'
  "$TASK_OLLAMA" pull qwen3.5:4b
fi
TASK_URL="http://127.0.0.1:$TASK_PORT/meowmemo.html"
# Do not interrupt or silently switch an existing server using the chosen port.
if "$TASK_VENV" - "$TASK_PORT" <<'PY'
import socket,sys
with socket.socket() as sock:
    sys.exit(0 if sock.connect_ex(('127.0.0.1',int(sys.argv[1])))==0 else 1)
PY
then
  echo "Port $TASK_PORT is already in use. Stop that server or rerun with --port 8766. Existing server was left unchanged." >&2
  exit 1
fi
"$TASK_VENV" work/meowmemo-local-ai/server.py "$TASK_PORT" &
TASK_SERVER_PID=$!
TASK_READY=0
for ((TASK_TRY=0;TASK_TRY<180;TASK_TRY++)); do
  if curl --fail --silent --max-time 2 "http://127.0.0.1:$TASK_PORT/api/health" | "$TASK_VENV" -c 'import json,sys; x=json.load(sys.stdin); sys.exit(0 if x.get("ready") and x.get("modelVersion")=="catmeows-local-v2" else 1)' 2>/dev/null; then TASK_READY=1; break; fi
  kill -0 "$TASK_SERVER_PID" 2>/dev/null || break
  sleep 1
done
[ "$TASK_READY" -eq 1 ] || { echo 'MeowMemo backend failed to become ready. Read the server error above.' >&2; exit 1; }
# Check model availability via the same caption service used by the UI.
curl --fail --silent --max-time 10 "http://127.0.0.1:$TASK_PORT/api/captions/status" | "$TASK_VENV" -c 'import json,sys; x=json.load(sys.stdin); print("Caption status:",x.get("message",x.get("provider","unknown"))); sys.exit(0 if x.get("available") and x.get("localOnly") else 1)'
curl --fail --silent --max-time 10 "http://127.0.0.1:$TASK_PORT/api/rooms/status" | "$TASK_VENV" -c 'import json,sys; x=json.load(sys.stdin); print("Room photo status:",x.get("message","unknown")); sys.exit(0 if x.get("available") and x.get("localOnly") else 1)'
printf '\nReady / 已就绪: %s\nThe bundled memories and original recordings load automatically in a new browser.\nKeep this terminal open. Ctrl+C stops this launch.\n' "$TASK_URL"
[ "$TASK_BROWSER" -ne 1 ] || open "$TASK_URL"
wait "$TASK_SERVER_PID"
