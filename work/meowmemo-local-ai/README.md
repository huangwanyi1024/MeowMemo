# Local AI backend

Start with the repository root README for installation, local Ollama setup, data migration and reviewer walkthrough.

From repository root, run `python3.12 setup_local.py`, then `python3 start.py --ai`. Audio encoder/classifier are included. Python 3.12 and FFmpeg are required; optional Qwen3.5:4b weights must be downloaded separately with Ollama. Copy `.env.example` to `.env.local` only for the local caption/room provider setup.

Endpoints: `/api/health`, `/api/model`, `/api/analyze`, `/api/captions/status`, `/api/captions`, `/api/rooms/status`, `/api/rooms/analyze`, `/api/samples`; audio lab at `/ai-lab`.

See MODEL_CARD.md for honest acoustic limitations (all deployed context suggestions are withheld), artifacts/ for evaluation evidence and root THIRD_PARTY_NOTICES.md for research-data/model attribution. The service binds only to 127.0.0.1; it is not a public hosted API. No paid API or secret is required for the local setup.
