# Emma Yue (Qin Yue) — Individual Contribution

GitHub: `emmiamia`. Assigned role: Data Researcher & Developer. Contribution branch: `emma-dataset-analysis`. Date: 2026-11-10.

## Individual codebase

- `experiments/dataset_research/research.py`: CatMeows filename parsing; original audio format/readability checks; duration and class/cat aggregation; missing-context, metadata-consistency and exact decoded-audio duplicate detection; manifest cat/noise-source leakage checks; deterministic JSON/CSV exports; five PNG visualization types; future H2 processor output validation contract.
- `experiments/dataset_research/test_research.py`: 20 unittest cases covering parser errors, aggregation, missing classes, empty datasets, invalid audio, manifest defects/leakage, report reproducibility and plots; tests reuse the existing backend reader/MFCC functions for resampling, mono conversion, silence, short input, normalization and nonfinite rejection, and exercise inference dispatch to the shared reader.
- `experiments/dataset_research/__init__.py`: importable module package.
- `experiments/dataset_research/requirements.txt`: lightweight research/test environment requirements.
- `experiments/dataset_research/README.md`: root-relative setup/run/test commands, schema, output descriptions, provenance and limitations.
- `experiments/dataset_research/H2_READINESS.md`: research synthesis about imbalance, cat generalization, LOCO, grouped bootstrap, paired noise experiments and 8/16 kHz processing parity; primary dataset references and implementation gaps.
- `experiments/dataset_research/MANIFEST_FINDINGS.md`: reproducible audit findings from the existing split, source hash, per-cat counts/missing contexts and validation evidence.
- `EMMA_INDIVIDUAL_CONTRIBUTION.md`: individual hypothesis, aims, contribution boundaries and course summary.
- `.gitignore`: excludes local research datasets and generated reports/plots. Root README links the new workflow.

No classifier, production processing path, existing evaluation artifact, owner recording or journal data was changed. The contribution extends existing team work rather than claiming its earlier model as individual work.

## Individual hypothesis

“Systematic dataset quality validation and cat-level distribution analysis can identify sources of bias, leakage, and preprocessing inconsistency, improving the reliability of the team's evaluation of audio preprocessing under household noise.”

Motivation: a small, clustered and imbalanced cat dataset can support misleading clip-level conclusions when prolific cats, missing situations or repeated noise sources cross evaluation boundaries. A shared format/processing contract also helps prevent training/inference drift. Expected value is earlier detection of invalid comparisons and more interpretable H2 evidence.

Evaluate this hypothesis by comparing pre-audit and post-audit experiment manifests, documenting confirmed/corrected issues, injecting known errors to measure validator sensitivity, and checking paired cat-held-out evaluations for consistent processing and reproducible metrics. Current synthetic tests establish detection behavior; the real manifest audit identifies reviewable concerns. These do not empirically confirm an improvement in model performance or in evaluation reliability at team scale.

## Individual project aim

Establish a reliable, reproducible dataset analysis and validation workflow supporting the team's H2 experiment, within the Data Researcher & Developer role.

## Contributions promoted to the team

Implemented on this branch: standalone audit consumes the team's existing `artifacts/split.json`; regression tests import existing `model.py` functions; research findings and setup commands are linked from the root README. These are concrete code/artifact integrations available for team review.

Proposed future adoption: enforce the audit automatically before training, supply ESC-50 source manifests, integrate/test actual trimming and denoising, run paired H2 arms, LOCO and grouped bootstrap, and verify source-archive metadata discrepancies. No shared production training gate was added. A pushed branch is not evidence of team merge, approval or completed adoption.

Verified manifest findings: 440 references, 21 cats; counts 127/92/221; no cat overlap or repeated references across development/test; 11 cats lack contexts; five session-4 entries and BAC01 owner-ID inconsistency require source verification. Full dataset audio is unavailable, so no empirical audio quality/duration findings are claimed. The existing 40.0% accuracy and 0.372 macro-F1 belong to the team; H2 remains unestablished. Owner recordings are qualitative only.

## Rubric-ready summary

Emma Yue (Qin Yue), Data Researcher & Developer, implemented a reproducible CatMeows dataset research module with filename metadata parsing, audio quality checks, cat-level distribution analysis, leakage validation, deterministic reports and exploratory plotting. Auditing the team's existing 440-reference split identified 11 cats missing situation classes and metadata discrepancies requiring source verification, while detecting no cat overlap between development and test. Twenty automated tests passed using synthetic fixtures and the team's existing preprocessing functions. Her H2 readiness report addresses imbalance, grouped evaluation, noise-source independence and training/inference consistency. Full-dataset audio validation and formal H2 evaluation remain pending; no preprocessing performance improvement is claimed.

| Individual Work | Technical Evidence | Value to Team Project |
|---|---|---|
| Metadata and distribution research | `research.py`; `MANIFEST_FINDINGS.md`; parser/aggregation tests | Makes imbalance and missing contexts visible |
| Audio and manifest validation | `inspect_audio`, `validate_manifest`; corrupt/nonfinite/overlap tests | Detects invalid inputs and partition leakage |
| Reproducible EDA | Stable JSON/CSV exports; five synthetic PNG plot tests | Provides repeatable inspection without fabricating findings |
| Preprocessing consistency validation | Existing reader/MFCC regression tests; processed-output contract | Documents current behavior and future H2 checks |
| Experimental readiness documentation | `H2_READINESS.md` with primary dataset sources | Defines reliable grouped/noise comparisons and honest claim limits |

## Validation and remaining submission steps

20 focused tests passed, 0 failed; existing shell launcher regression script passed. Numerical warnings from existing MFCC matmul code and plotting dependency deprecations occurred but outputs remained finite. Full TensorFlow/HTTP smoke checks were not run because the complete application environment/services were unavailable. No pre-existing failing tests were established.

Before formal H2 submission, obtain the original full dataset, verify flagged metadata against the source archive, provide the selected ESC-50 source inventory and run the audio audit. Team review/merge and actual H2 experiments are separate follow-up work. This branch does not create or merge a pull request automatically.
