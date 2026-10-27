# Model Card · MeowMemo local audio v2

Date: 2026-10-26. Model ID: `catmeows-local-v2`. Status: **experimental; context recognition not ready for reliable use**.

## Intended use / 使用范围

Coursework research into three recorded contexts: brushing, waiting for food, isolation in an unfamiliar environment. This is a context classification experiment, not translation, intent recognition, personality detection, veterinary advice or emotion diagnosis. Unknown/out-of-scope is expected. The owner's observations always remain separate from model predictions.

## Model / 模型

Official pretrained YAMNet on CPU supplies 1024-D mean pooled embeddings. A separate 100-D MFCC statistical extractor supplies spectral statistics (20 nonzero coefficients; mean, standard deviation, 10th/90th percentile, delta standard deviation). Concatenate 1124-D features, StandardScaler, balanced L2 logistic regression C=1.0. Model weights are loaded locally; no API requests during inference. `work/meowmemo-local-ai/vendor/yamnet/SOURCE.json` pins upstream implementation. Hashes and exact installed package versions are in `work/meowmemo-local-ai/artifacts/environment.json`.

## Data / 数据

CatMeows v1.0.2, 440 WAV clips, 21 cats, 2 breeds (Maine Coon / European Shorthair). Counts: brushing 127, waiting for food 92, unfamiliar-environment isolation 221. Context labels record the experimental setup, not verified subjective intentions. Source: https://zenodo.org/records/4008297 . Acknowledge Ludovico et al.; record terms specify scientific research/non-commercial use. No user/private cat media were included.

## Training and evaluation / 训练与评估

One GroupShuffleSplit with seed 42 and test_size=.24 holds out 6 whole cats, 120 clips. Development: 15 cats, 320 clips. Development tuning uses 4-fold StratifiedGroupKFold grouped by cat. Standardization is fitted inside each fold. Cat IDs, filenames, owner tags, photographs and profile descriptions are never model inputs. Frames are pooled per clip before splitting; no frame or same-cat train/test overlap.

Fifteen fixed candidate configurations compare YAMNet, MFCC, combined features, logistic C=.01/.1/1 and RBF SVM C=1/10. Selection uses development OOF macro-F1 only: combined logistic C=1 has 0.473. Test cats remain excluded from the deployed classifier's training data.

Exploratory limitation: the v2 comparison was added after seeing poor v1 test performance, and the same test set was reused. It is not an untouched final confirmatory evaluation. Keep the failed v1 result and obtain a new independent evaluation before any stronger claim.

Test before abstention: **accuracy 0.400; macro-F1 0.372**. Per-class F1: brushing 0.606, food 0.256, isolation 0.254. Development-majority baseline (always isolation) test accuracy 0.325; macro-F1 0.164. One small split provides no reliable population estimate or per-breed generalization claim.

Confusion matrix rows=true, columns=predicted, order brushing / food / isolation:

```text
30  18   8
 7  10   8
 6  25   8
```

Raw per-file results and all candidate scores: `work/meowmemo-local-ai/artifacts/evaluation.json`. First YAMNet-only baseline: accuracy 0.358, macro-F1 0.336 (`evaluation-yamnet-v1.json`).

## Abstention / 不确定

Initial heuristics: silence RMS <1e-4 or duration <.25 s; YAMNet cat-event maximum <.10; context score <.60 or top-two score margin <.15. None of the explored development thresholds reached 75% accuracy at >=25% coverage. Context scores are uncalibrated; do not display them as correctness probabilities.

The recorded `heldout_test_with_abstention` describes only this initial heuristic experiment: 72/120 accepted, accepted accuracy 0.306. It is **not** the deployed product policy. Since validation failed, the final service suppresses all context suggestions through a global readiness gate (test macro-F1 <.65). Actual deployed context coverage is therefore 0, abstention 100%. .65 is an engineering readiness criterion added after evaluation, not a validated confidence threshold. Experimental raw candidates remain accessible for diagnosis only.

Silence, 440 Hz sine and seeded white noise were rejected in smoke checks. Some real cat clips also fail the provisional cat-event gate. This is not a comprehensive out-of-distribution or cat-detection evaluation; raw YAMNet event candidates can be incorrect too.

## Runtime / 本机性能

Apple M5 MacBook Air, 10 CPU cores, 10 GPU cores, 16 GB shared memory. CPU-only execution (GPU unused). Warm inference median 6.36 ms for 3 s and 20.97 ms for 15 s (10 repeated synthetic-duration fixtures made from public audio). Excludes file decoding, HTTP/browser and cold interpreter/TensorFlow import. Encoder initialization after imports ~1.36 s; benchmark peak process memory ~520 MB. These are local measurements, not hosted latency promises.

## Privacy, limits, next work / 隐私与后续

Service binds only 127.0.0.1 and checks Host/Origin; original uploaded bytes are held in a local temporary directory and removed after inference. Browser journal data and optional saved analysis still live in IndexedDB; this change adds no cloud backup. Audio/video original media, profile choices, owner labels and creative captions stay unchanged by analysis. No microphone/camera recording was performed by automated testing.

Not evaluated on the owner's cats, other breeds, purring-only audio, long conversations, noisy homes or phones. Future work should start with consented natural recordings and an independent cat/session-held-out set. Collect normal behavior only; do not create isolation or distress to obtain labels. More compute alone does not resolve these data/generalization limits.
