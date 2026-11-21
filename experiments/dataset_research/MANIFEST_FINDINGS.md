# Checked-in CatMeows split: metadata findings

Audit date: 2026-11-10. Input: `work/meowmemo-local-ai/artifacts/split.json` at base commit `c9cd3f8`.
Input SHA-256: `33fb98bc8ee21e066ab74b0ad3a152578f03a1117c097f51254de8f825e31d71`.

Reproduce with the manifest-only command in README.md. These statistics are computed from actual checked-in filename references, not from downloaded audio. `audio_checked` is false. Duration, actual sample rate/channels, file readability, audio duplication and completeness against the original archive remain unverified. No ESC-50 source IDs are present, so noise partition independence is unknown.

## Findings

- 440 metadata-valid references: development 320 from 15 cats, test 120 from 6 cats; 21 cats total.
- Brushing 127 (28.86%), food 92 (20.91%), isolation 221 (50.23%); largest/smallest class ratio 2.402.
- No repeated file references or cross-partition cat overlap detected.
- Eleven cats lack at least one situation. Counts range from 5 to 54 clips per cat.
- Five BLE01 isolation references use session 4, outside the published session range 1–3. They are retained and flagged pending archive verification.
- `I_BAC01_MC_MN_SIM10_102.wav` has owner SIM10 while other BAC01 references use SIM01. This is a consistency flag, not proof that the file is wrong; do not rename or remove it without checking the source archive.
- The audit deliberately exits 1 for these six review issues. This is a successful detection of existing metadata concerns, not a test failure.

## Per-cat counts and missing contexts

- ANI01: 10; brushing=6, food=0, isolation=4; missing: food.
- BAC01: 25; brushing=6, food=12, isolation=7; missing: none.
- BLE01: 48; brushing=0, food=3, isolation=45; missing: brushing.
- BRA01: 19; brushing=7, food=2, isolation=10; missing: none.
- BRI01: 15; brushing=7, food=8, isolation=0; missing: isolation.
- CAN01: 54; brushing=26, food=2, isolation=26; missing: none.
- CLE01: 20; brushing=0, food=0, isolation=20; missing: brushing, food.
- DAK01: 40; brushing=4, food=4, isolation=32; missing: none.
- IND01: 21; brushing=11, food=10, isolation=0; missing: isolation.
- JJX01: 7; brushing=7, food=0, isolation=0; missing: food, isolation.
- LEO01: 5; brushing=0, food=5, isolation=0; missing: brushing, isolation.
- MAG01: 27; brushing=10, food=14, isolation=3; missing: none.
- MAT01: 26; brushing=10, food=6, isolation=10; missing: none.
- MEG01: 14; brushing=0, food=4, isolation=10; missing: brushing.
- MIN01: 14; brushing=4, food=4, isolation=6; missing: none.
- NIG01: 5; brushing=4, food=0, isolation=1; missing: food.
- NUL01: 14; brushing=4, food=0, isolation=10; missing: food.
- REG01: 5; brushing=3, food=1, isolation=1; missing: none.
- SPI01: 27; brushing=4, food=8, isolation=15; missing: none.
- TIG01: 5; brushing=2, food=0, isolation=3; missing: food.
- WHO01: 39; brushing=12, food=9, isolation=18; missing: none.

## Validation performed

20 focused unittest cases passed, 0 failed, using Python 3.9.6, numpy 2.0.2, scipy 1.13.1, soundfile 0.13.1 and matplotlib 3.9.4 in an isolated temporary environment. All five plot types were generated from temporary synthetic fixtures titled SYNTHETIC FIXTURE. Repeated JSON/CSV exports were byte-identical. The existing shell launcher integration script also passed.

Existing MFCC code emitted numerical matmul warnings in this environment while tested outputs remained finite; matplotlib/pyparsing emitted dependency deprecation warnings. These are recorded rather than modifying unrelated backend code. Live TensorFlow/HTTP model smoke tests were not run: the full application environment/services are not installed. No pre-existing failing test has been established by these checks.
