# Package verification / 打包验证

Verified on the original Apple M5 Mac, October 26, 2026, from the staged repository copy:

- Python source syntax parsed successfully.
- Included YAMNet checkpoint matches the recorded SHA-256.
- All three original lab recordings match the provenance hashes; playback previews exist.
- Five frontend regression scripts passed: caption payload/templates, memory attachment saving/cancel, room customization, room cat proportions/playback restoration, shop rewards/redemption/placement.
- Python caption tests: 16 passed. Room service tests: 6 passed.
- Started the packaged backend on temporary loopback port 8770 using the existing Python 3.12 environment.
- API smoke checks passed: real public samples, uncertainty policy, silence/tone/noise, corrupt audio, foreign origin rejection, WebM and M4A decoding.
- Scanned packaged source for credential-like OpenAI tokens and excluded local secrets, personal backup, cache and runtime-log files.

The model download / dependency installation was not repeated in a fresh environment. Runtime tests reused the installed Python environment; reviewers must follow setup instructions. Optional Qwen/Ollama was not bundled or newly installed for this packaging check. This does not certify performance on other machines or satisfy public deployment/user-pilot/video deliverables.

The destination's existing MeowMemo_Plan.pdf is preserved separately and ignored for Git. The original browser journal remains unchanged. At the owner's request, this updated package embeds the exported snapshot for teacher review. The source backup was exported through the app's normal UI; six memories / three recordings were confirmed. Original media bytes are retained.

## First-run demo update

- Added `test_demo_seed.cjs`: verifies six memories, three original audio blobs and photo bytes, cat names/settings and shop balance; no repeat loading; no overwrite of reviewer edits or an intentionally emptied journal; transaction failure leaves no partial seed.
- Existing five frontend regression scripts still pass.
- Chrome fresh-origin check: portable HTML on 127.0.0.1:8772 auto-loaded six memories / three recordings; refresh retained six without duplicates. Source index.html on a separate new localhost:8772 origin independently loaded profiles, birthday and three recordings. No manual import or AI backend was needed.
- The original user journal on port 8765 was only exported, not overwritten. The snapshot is static and does not automatically update when the owner adds future memories.

## macOS one-command launcher update (October 27, 2026)

- `bash -n` passed for setup-and-run.sh and bash start-local-ai.sh.
- Read-only --check ran on the current Mac without installing/starting anything.
- `python3 tests/test_shell_launcher.py` passed with mock installers/endpoints: repository path with spaces, check-only behavior, initial environment/model setup, repeat skip, argument validation and startup failure. Tests do not download or install software.
- Caption and vision availability are checked before reporting full readiness. Runtime services started by the script are cleaned up; previously running Ollama is reused.
- Clean-machine Homebrew/dependency installation was not executed. User/system prompts during first-time Homebrew installation cannot be eliminated by this script.

## Launcher naming and README cleanup

Root launchers are now `start-local-ai.sh` and `start-meowmemo.sh`; legacy command wrappers were removed. README consolidates startup, data migration, reviewer steps, troubleshooting, development and submission instructions. UI/backend guidance uses the new shell command. Shell syntax, check-only mode, mocked startup/repeat/failure checks and six frontend regression scripts passed after renaming.
