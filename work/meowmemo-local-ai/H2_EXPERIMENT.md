# H2 experiment: audio preprocessing

**Hypothesis (H2):** cleaning up audio before analysis (trimming silence, normalising loudness, reducing noise) raises macro-F1 for context classification (brushing / waiting for food / isolation) on cats the model has never heard, and reduces the accuracy lost to household noise.

**Status:** prototype code and unit tests are in place. The full experiment has **not been run yet**; it needs the CatMeows download and the Python 3.12 environment. No results exist until `artifacts/h2-results.json` is produced.

## Pass/fail rule (agreed before running)

- **Supported** if a variant's macro-F1 gain over the baseline has a 95% bootstrap interval above zero, resampling whole cats (1,000 resamples).
- **Rejected** otherwise. That would point to data, not audio quality, as the limit.
- The classifier is fixed for every variant (StandardScaler + balanced logistic regression, C = 1, the deployed settings), so differences come from preprocessing alone.

## Files

| File | What it does |
| --- | --- |
| `h2_preprocessing.py` | Silence trimming, loudness normalisation, optional noise reduction, 4 kHz band-limiting, noise mixing at a set signal-to-noise ratio, noise-folder loader. NumPy/SciPy only. |
| `h2_evaluation.py` | Leave-one-cat-out evaluation and the cat-level bootstrap. Reuses `pipeline` and `metrics` from `train.py`. |
| `h2_experiment.py` | `run`: scores every variant on clean and noisy audio and writes `artifacts/h2-results.json`. `predict`: labels real recordings (for the real-home check). |
| `download_catmeows.py` | Downloads CatMeows v1.0.2 from Zenodo into `data/catmeows/`, verifies checksums, reports labels, sample rates and durations. |
| `test_h2.py` | 14 unit tests; no TensorFlow, dataset or network needed. |
| `h2_data_checks.py` | Checks to run before trusting results: `noise` (no animal sounds in the noise pool) and `shortcut` (can clip length alone predict the situation?). No TensorFlow. |
| `test_h2_data_checks.py` | 6 unit tests for the data checks; no TensorFlow, dataset or network needed. |

## Setup

From the repository root:

```sh
python3.12 setup_local.py                      # creates .venv-meowmemo (TensorFlow, scikit-learn, ...)
cd work/meowmemo-local-ai
../../.venv-meowmemo/bin/python download_catmeows.py
../../.venv-meowmemo/bin/python download_catmeows.py --verify   # expect 440 clips, 21 cats, 127/92/221
../../.venv-meowmemo/bin/pip install noisereduce               # optional: enables the denoise variants
```

Put household noise recordings (WAV/FLAC/OGG) in `work/meowmemo-local-ai/data/noise/`. Candidate public sets: DEMAND, MUSAN, ESC-50; **confirm each licence before use** (several are non-commercial). Audio data and caches are git-ignored.

## Data checks (run first)

```sh
../../.venv-meowmemo/bin/python h2_data_checks.py noise data/noise   # exit code 1 if animal clips are found
../../.venv-meowmemo/bin/python h2_data_checks.py shortcut           # writes artifacts/h2-shortcut-check.json
```

- **Noise pool:** ESC-50 classes 0-9 are animals (dog, cat, rooster, ...). Mixing a cat clip into a meow adds a second cat, so these must be removed. Files not named like ESC-50 (DEMAND, MUSAN) are listed for a manual listen.
- **Clip-length shortcut:** an early MeowMemo prototype's cat detector learned clip length instead of what a cat sounds like. Silence trimming changes clip length, so a gain from `trim` could come from length rather than cleaner audio. This check scores a length-only classifier with the same leave-one-cat-out test, before and after trimming, against shuffled lengths (a permutation test). If it prints a WARNING, report the length-only macro-F1 next to the `trim` result and treat a `trim` gain of similar size with caution.

## Run

```sh
../../.venv-meowmemo/bin/python test_h2.py                                   # quick checks
../../.venv-meowmemo/bin/python test_h2_data_checks.py                       # data-check tests
../../.venv-meowmemo/bin/python h2_experiment.py run                         # clean audio only
../../.venv-meowmemo/bin/python h2_experiment.py run --noise-dir data/noise  # adds 20/10/5 dB noise
../../.venv-meowmemo/bin/python h2_experiment.py predict --variant trim my-recording.m4a
```

Variants: `baseline`, `trim`, `normalize`, `denoise`, `trim+normalize`, `denoise+trim+normalize`. Pick a subset with `--variants trim normalize`. Features are cached in `artifacts/h2-cache/`, so reruns are fast.

## How it maps to the plan

1. **Fair baseline:** leave-one-cat-out (train on 20 cats, test on the 21st, repeat). The original 6-cat test split has already been used twice and is not reused.
2. **Noise stress test:** train on clean clips, score on clips mixed with household noise at 20, 10 and 5 dB. Every variant gets the identical noise segment per clip, so comparisons are paired. Noise is band-limited to 4 kHz to match CatMeows.
3. **One step at a time, then combinations:** each variant is applied to both training and test audio.
4. **Decide:** the `vs_baseline` block in the results gives the gain, its 95% interval and `supported`.
5. **Real-home check:** `predict` band-limits recordings to 4 kHz first, then reports the label, probabilities and whether a cat sound was detected. A handful of files is a qualitative check, not a score.

The results also include `cat_gate_pass_rate`: the share of clips passing the app's cat-sound check (YAMNet Cat/Meow/Purr score >= 0.10) under each condition.

## Things to know

- **CatMeows audio is 8 kHz** (checked on the 3 bundled clips; `--verify` checks all 440), so the model never sees sound above 4 kHz.
- **The MFCC half of the features is already peak-normalised** inside `mfcc_features`, so loudness normalisation can only affect the YAMNet half.
- **Mean pooling:** YAMNet produces one embedding per ~0.96 s window (0.48 s hop) and `model.py` averages them, so silence dilutes the meow. This is the main reason to expect trimming to help.
- **Ethics and terms:** use only public data and normal, everyday behaviour; never create distress to obtain a recording. CatMeows is for scientific, non-commercial use with acknowledgement of Ludovico et al.
