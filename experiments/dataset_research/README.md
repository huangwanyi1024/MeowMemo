# Emma Yue's dataset research module

This independent research audit supports H2: whether preprocessing improves situation classification under simulated household noise. It does not train a second classifier or claim H2 is established.

## Setup and structure

Run all commands from the repository root. Use Python 3.9+ for this module; the full application separately requires Python 3.12. Runtime dependencies numpy, scipy and soundfile are already used by the backend. Matplotlib is an optional plotting dependency. No TensorFlow, running server or model weights are needed for these tests.

```sh
python3 -m venv .venv-research
.venv-research/bin/python -m pip install -r experiments/dataset_research/requirements.txt
.venv-research/bin/python -m unittest experiments.dataset_research.test_research -v
```

- `research.py`: parser, audio inspection, aggregation, manifest validation, deterministic writers, five PNG plots and CLI.
- `test_research.py`: generated synthetic audio and metadata fixtures; tests existing backend preprocessing.
- `H2_READINESS.md`: experimental design implications and implementation gaps.
- `MANIFEST_FINDINGS.md`: audit of checked-in split metadata, explicitly not a full audio audit.
- `requirements.txt`: small research environment, independent of full application installation.

## Data requirements and commands

Download **dataset.zip** for CatMeows v1.0.2 from https://zenodo.org/records/4008297 and extract the original WAV files into `experiments/dataset_research/data/catmeows/`. Respect the scientific/non-commercial terms and attribution. Do not use extras.zip or journal recordings as formal CatMeows samples. No download is automatic. Missing or empty data produces a setup error, never invented statistics.

```sh
.venv-research/bin/python -m experiments.dataset_research.research --data experiments/dataset_research/data/catmeows --output experiments/dataset_research/outputs/audio --plots
.venv-research/bin/python -m experiments.dataset_research.research --manifest work/meowmemo-local-ai/artifacts/split.json --output experiments/dataset_research/outputs/split
.venv-research/bin/python -m experiments.dataset_research.research --manifest work/meowmemo-local-ai/artifacts/split.json --data experiments/dataset_research/data/catmeows --output experiments/dataset_research/outputs/validated-split
```

The second command checks metadata and cat overlap only; it explicitly reports `audio_checked: false`. The third also checks files. Manifest paths are relative to the supplied data directory, including any subfolders. Keep output outside the scanned data directory. Recursive discovery audits every non-hidden file, so README/non-audio files are reported for review rather than silently accepted.

Outputs: `report.json`, `recordings.csv`; with `--plots`, `situations.png`, `cats.png`, `matrix.png`, `durations.png`, `quality.png`. JSON keys and file ordering are stable; there are no timestamps or absolute dataset paths in exported records. Input data and generated outputs in this module are ignored by Git. Exit 0 means no detected validation issues, 1 means inspect the report, 2 means setup/input failure. Missing classes alone are descriptive and need not invalidate a dataset.

For future noise manifests, replace string entries with objects containing `file`, `label`, `cat`, and optional `noise_source` (original ESC source ID, shared by every derived crop/mix). Other parsed fields may be supplied and will be checked. Partition names can be development/test or train/validation/test; all must be disjoint by cat and noise source. This schema applies to original CatMeows file references, not renamed mixtures. Preserve original source references separately when preparing noisy variants. The code cannot infer absent noise IDs or verify SNR without noise/mix manifests. `validate_processed_audio` supplies a finite, real, mono, nonempty output/rate contract for future denoisers and optionally checks preserved frame count; it does not implement noise reduction.

## Scope and limitations

Metadata parses context, cat, breed, sex/neuter status, owner ID, recording session and vocalization counter. It rejects extras/SEQ names. Session 4 is preserved but flagged because checked-in filenames exceed the published 1–3 session description. Labels describe elicitation situations, not emotions.

Audio inspection checks original 8 kHz mono WAV, readability, zero/nonfinite audio, duration, and SHA-256 of both bytes and decoded float32 PCM plus sampling rate. Exact PCM duplicates are suspicious, not proof of misconduct; acoustic near-duplicates and different encodings are not exhaustively detected. Statistics with invalid metadata exclude those files from class/cat counts while retaining them in total file and quality counts. An absent class makes max/min imbalance undefined (`null`).

Plot tests generate only temporary, clearly titled **SYNTHETIC FIXTURE** images. No synthetic outputs are reported as dataset findings. Full data, selected ESC-50 files and owner data are not added. The standalone audit is available to the team on this branch; automatic training gating and H2 processing are future integration work.
