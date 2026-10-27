# MeowMemo 🐾

A little home for the sounds you love. 给舍不得忘记的声音，一个小小的家。

A local coursework demo for real cat recordings, photos and memories. **Six saved memories, three original recordings, both cat profiles, birthdays and room/shop settings are included.** They load automatically in a new browser journal; no import is needed.

## 1. Start the demo / 启动

Download the whole repository (GitHub **Code → Download ZIP**, then unzip), or clone it. Keep its folder structure. Open Terminal, type `cd `, drag the unzipped project folder into Terminal, and press Return. Run the commands below from that folder.

### Full local AI — macOS / 完整 AI

```sh
bash start-local-ai.sh
```

The script installs missing Homebrew, Python 3.12, FFmpeg and Ollama; creates an isolated Python environment; downloads `qwen3.5:4b` if missing; checks the services; and opens the demo.

- First run needs internet, several GB of free space and an approximately 4 GB model download. macOS may request a password or Command Line Tools installation. Complete those prompts, then rerun if needed.
- Later runs reuse completed installations and downloads. No API key or paid credit is required.
- Keep Terminal open. **Ctrl+C** stops processes this launch started; an existing Ollama service stays running.
- The installer supports macOS; the original demo was tested on Apple M5 / 16 GB. A clean-machine installation has not been verified.

Optional commands:

```sh
bash start-local-ai.sh --check       # Check prerequisites without installing
bash start-local-ai.sh --no-browser  # Start without opening a browser tab
bash start-local-ai.sh --port 8766   # Use another port if 8765 is occupied
```

### Frontend only / 仅体验界面与已有内容

Requires Python 3, without AI installation:

```sh
bash start-meowmemo.sh
```

Open **http://127.0.0.1:8765/meowmemo.html**. Existing recordings, photos, captions and normal journal interactions work. New AI analysis, AI caption generation and photo recognition require the full AI launcher. Browser recording needs microphone/camera permission.

For a quick preview without a server, open `outputs/meowmemo-prototype/meowmemo.html` directly. Localhost is recommended for recording and saving. On systems without Bash, use `python3 start.py --web`; the automatic AI installer is macOS-only.

## 2. Try the features / 演示流程

1. **Home:** tap a cat; use Edit cats to change appearance/waiting spots. Customize room accepts a room photo, optional AI furniture suggestions and manual adjustment.
2. **Memory:** browse the six existing memories, search/filter or favorite one. Open a memory to play its original audio, edit details, add photos/videos or export a share card.
3. **Listen in the room:** opens Home and plays the recording with cat animation; afterward cats return to their saved spots.
4. **Record:** record/upload 2–15 seconds, optionally analyze locally, confirm the situation yourself, add a note/tag and save.
5. **Generate AI caption:** uses the note, tags, situation, cat personality and selected tone. Each click shows one creative version. Manual editing is available.
6. **My Cat:** edit names, birthdays and personality. Choose a saved recording as the cat's tap sound; Familiar Sounds provides quick access to a familiar real recording.
7. **Shop:** saving a new memory earns +2 treats; first share/export per memory earns +5. Redeem and place supported decorations/toys. Together is a future-development preview.

## 3. Save or move your data / 保存与迁移

**My Cat → Keep the originals, too. → Export backup** downloads the journal, original media and settings. On another browser, choose **Restore** in the same place and select the JSON file. Matching memory IDs are updated; other memories remain.

After first loading, edits live in that browser's IndexedDB. The bundled snapshot does not overwrite existing journals or sync later changes from the owner's browser. Clearing browser data removes local edits. Keep a private backup. Different browsers, ports, `localhost`, `127.0.0.1` and file URLs have separate storage.

**The repository intentionally includes the approved photos, three recordings, notes and profile details. Anyone with repo access can read them.** API keys, `.env.local`, private raw backup files and downloaded language-model weights are excluded. Do not add them when uploading.

## 4. Troubleshooting / 常见问题

- **Port busy:** stop the previous server, or add `--port 8766`. A different port opens a separate journal.
- **Install/download fails:** fix the displayed error and rerun the same command; completed steps are reused. Check internet access and free disk space.
- **Ollama cannot start:** inspect `.meowmemo-runtime/ollama.log`. The launcher does not stop a previously running Ollama.
- **AI unavailable in frontend mode:** stop the frontend server with Ctrl+C, then run `bash start-local-ai.sh`.
- **Names or memories appear different:** check browser and URL first. Use Restore for a newer backup. The bundled demo is a fixed snapshot.

## 5. AI limits / AI 限制

The audio experiment uses YAMNet + MFCC features and a small classifier. Exploratory held-out-cat results: **40.0% accuracy, macro-F1 0.372**. Context suggestions are currently withheld as **Uncertain**; the owner confirms the situation. Raw scores are not confidence probabilities. See [MODEL_CARD.md](MODEL_CARD.md).

Local Qwen3.5:4b generates **For fun** fictional captions and optional room-photo suggestions. It does not translate cat language or diagnose emotions. Room suggestions use editable furniture templates, not faithful 3D reconstruction. Existing audio and photos remain original. User feedback does not retrain the model automatically.

## 6. Files, editing and checks / 文件与开发

- `start-local-ai.sh` / `scripts/setup-and-run.sh`: full macOS setup and launch.
- `start-meowmemo.sh` / `start.py`: frontend preview.
- `outputs/meowmemo-prototype/`: editable HTML/CSS/JS, original example photos, `demo-data.js` snapshot and portable `meowmemo.html`.
- `work/meowmemo-local-ai/`: backend, included acoustic weights/classifier, three public lab listening examples and evaluation evidence. Lab examples are separate from the owner's three journal recordings.
- `requirements.txt`, `setup_local.py`: manual Python environment setup.
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): model/data/media attribution and reuse terms.
- [PACKAGE_VALIDATION.md](PACKAGE_VALIDATION.md): performed checks and their limits.

After editing frontend source, regenerate the portable HTML:

```sh
python3 outputs/meowmemo-prototype/build_standalone.py
```

Run existing checks as needed (Python tests require AI setup; JavaScript tests require Node.js):

```sh
python3 tests/test_shell_launcher.py
.venv-meowmemo/bin/python work/meowmemo-local-ai/test_captions.py
.venv-meowmemo/bin/python work/meowmemo-local-ai/test_rooms.py
node work/meowmemo-local-ai/test_demo_seed.cjs
```

Manual AI setup remains available: install Python 3.12 / FFmpeg / Ollama, run `python3.12 setup_local.py`, `ollama pull qwen3.5:4b`, start `ollama serve` if not running, copy the backend `.env.example` to `.env.local`, then run `python3 start.py --ai`.

#