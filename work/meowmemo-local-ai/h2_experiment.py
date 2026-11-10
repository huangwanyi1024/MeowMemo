"""H2 experiment: does audio preprocessing improve context classification on unseen cats?

  python h2_experiment.py run [--noise-dir data/noise] [--snr 20 10 5] [--variants ...]
  python h2_experiment.py predict --variant trim recording1.m4a recording2.wav

`run` trains on clean CatMeows audio and scores every variant with leave-one-cat-out testing,
on clean clips and (with --noise-dir) on clips mixed with household noise. Results are written
to artifacts/h2-results.json. See H2_EXPERIMENT.md for setup and the pass/fail rule.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
from model import AudioModel, read_audio, mfcc_features, ROOT, ARTIFACTS, MODEL_VERSION, LABELS
import h2_preprocessing as pre
from h2_evaluation import evaluate_unseen_cats, bootstrap_gain, CLASSIFIER_C, CLASSIFIER_KIND
from train import pipeline

CATMEOWS = ROOT / 'data' / 'catmeows'
CACHE = ARTIFACTS / 'h2-cache'
CONTEXT = {'B': 'brushing', 'F': 'food', 'I': 'isolation'}
CAT_GATE = 0.10  # same provisional cat-sound threshold the deployed service uses


def load_catmeows():
    files = sorted(CATMEOWS.glob('*.wav'))
    if len(files) != 440:
        raise SystemExit(f'Expected 440 CatMeows WAV files in {CATMEOWS}, found {len(files)}. '
                         'Run: python download_catmeows.py')
    y = np.array([CONTEXT[p.name.split('_')[0]] for p in files])
    groups = np.array([p.name.split('_')[1] for p in files])
    return files, y, groups


def clip_features(encoder, audio):
    """The deployed 1124-D feature vector: mean YAMNet embedding + 100 MFCC statistics."""
    embedding, cat_score, _ = encoder.extract(np.asarray(audio, dtype=np.float32))
    return np.concatenate([embedding, mfcc_features(audio)]).astype(np.float32), cat_score


def cache_key(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


def feature_set(encoder, audios, variant, condition, key_parts):
    """Features for one variant applied to one condition's audio, cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f'{variant}__{condition}__{cache_key(pre.PARAMS_VERSION, variant, condition, *key_parts)}.npz'
    if path.exists():
        saved = np.load(path)
        return saved['x'], saved['cat_scores']
    step = pre.VARIANTS[variant]
    rows, scores = [], []
    for i, audio in enumerate(audios):
        x, score = clip_features(encoder, step(audio))
        rows.append(x)
        scores.append(score)
        if i % 100 == 0:
            print(f'  {variant} / {condition}: {i + 1}/{len(audios)}', flush=True)
    x, scores = np.array(rows), np.array(scores)
    np.savez_compressed(path, x=x, cat_scores=scores)
    return x, scores


def usable_variants(requested):
    unknown = set(requested) - set(pre.VARIANTS)
    if unknown:
        raise SystemExit(f'Unknown variants: {sorted(unknown)}. Choose from {list(pre.VARIANTS)}')
    if not pre.noise_reduction_available():
        skipped = [v for v in requested if v in pre.NEEDS_NOISEREDUCE]
        if skipped:
            print(f'Skipping {skipped}: install noisereduce to include noise reduction.')
        requested = [v for v in requested if v not in pre.NEEDS_NOISEREDUCE]
    if 'baseline' not in requested:
        requested = ['baseline'] + list(requested)
    return list(dict.fromkeys(requested))


def run(args):
    started = time.time()
    files, y, groups = load_catmeows()
    names = [p.name for p in files]
    variants = usable_variants(args.variants)
    print(f'CatMeows: {len(files)} clips, {len(set(groups))} cats. Variants: {variants}')
    clean = [read_audio(p) for p in files]
    conditions = {'clean': clean}
    noise_info = None
    if args.noise_dir:
        bank = pre.load_noise_bank(args.noise_dir)
        noise_files = sorted(str(p.relative_to(args.noise_dir)) for p in Path(args.noise_dir).rglob('*')
                             if p.suffix.lower() in {'.wav', '.flac', '.ogg'})
        noise_info = {'directory': str(args.noise_dir), 'usable_files': len(bank),
                      'fingerprint': cache_key(noise_files)}
        for snr in args.snr:
            conditions[f'snr{snr:g}dB'] = [pre.noisy_version(a, bank, snr, args.seed, i)
                                           for i, a in enumerate(clean)]
    encoder = AudioModel(classifier=False)
    key_parts = (names, args.seed, noise_info and noise_info['fingerprint'])
    feats = {v: {c: feature_set(encoder, audios, v, c, key_parts) for c, audios in conditions.items()}
             for v in variants}

    results = {}
    for condition in conditions:
        results[condition] = {}
        preds = {}
        for v in variants:
            scored, pred = evaluate_unseen_cats(feats[v]['clean'][0], feats[v][condition][0], y, groups)
            preds[v] = pred
            scored['cat_gate_pass_rate'] = float(np.mean(feats[v][condition][1] >= CAT_GATE))
            results[condition][v] = scored
        for v in variants:
            if v != 'baseline':
                results[condition][v]['vs_baseline'] = bootstrap_gain(
                    y, preds['baseline'], preds[v], groups, n=args.bootstrap, seed=args.seed)

    report = {
        'hypothesis': 'H2: preprocessing raises macro-F1 on unseen cats and reduces the loss from household noise.',
        'pass_rule': 'Supported if the 95% cat-level bootstrap interval of the macro-F1 gain over baseline is above zero.',
        'evaluation': 'Leave-one-cat-out; trained on clean audio, scored on the named condition.',
        'model_version_features': MODEL_VERSION,
        'preprocessing_version': pre.PARAMS_VERSION,
        'classifier': {'kind': CLASSIFIER_KIND, 'C': CLASSIFIER_C, 'class_weight': 'balanced'},
        'dataset': {'name': 'CatMeows 1.0.2', 'clips': len(files), 'cats': int(len(set(groups))),
                    'class_counts': {l: int((y == l).sum()) for l in LABELS}},
        'noise': noise_info, 'snr_db': args.snr if args.noise_dir else [], 'seed': args.seed,
        'variants': variants, 'results': results,
        'runtime_seconds': round(time.time() - started, 1), 'python': platform.python_version(),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print_summary(results)
    print(f'\nWrote {out}')


def print_summary(results):
    print(f'\n{"condition":<12} {"variant":<24} {"acc":>6} {"macroF1":>8}  gain vs baseline [95% CI]')
    for condition, by_variant in results.items():
        for v, r in by_variant.items():
            cmp = r.get('vs_baseline')
            extra = (f'{cmp["gain"]:+.3f} [{cmp["ci95"][0]:+.3f}, {cmp["ci95"][1]:+.3f}]'
                     f'{"  supported" if cmp["supported"] else ""}') if cmp else '(reference)'
            print(f'{condition:<12} {v:<24} {r["accuracy"]:6.3f} {r["macro_f1"]:8.3f}  {extra}')


def predict(args):
    """Train on all clean CatMeows clips with one variant, then label the given recordings.

    Recordings are band-limited to 4 kHz first so phone audio matches CatMeows' bandwidth.
    For a qualitative real-home check only: a handful of files cannot measure accuracy.
    """
    files, y, groups = load_catmeows()
    variant = usable_variants([args.variant])[-1]
    encoder = AudioModel(classifier=False)
    clean = [read_audio(p) for p in files]
    x, _ = feature_set(encoder, clean, variant, 'clean', ([p.name for p in files], args.seed, None))
    clf = pipeline(CLASSIFIER_C, CLASSIFIER_KIND).fit(x, y)
    for path in args.files:
        audio = pre.VARIANTS[variant](pre.band_limit(read_audio(path)))
        features, cat_score = clip_features(encoder, audio)
        probs = dict(zip(clf.classes_, clf.predict_proba(features[None, :])[0].round(3).tolist()))
        gate = 'cat sound detected' if cat_score >= CAT_GATE else 'cat sound NOT clear'
        print(f'{path}: {max(probs, key=probs.get)} {probs} | cat score {cat_score:.2f} ({gate})')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run', help='score all variants with leave-one-cat-out testing')
    r.add_argument('--variants', nargs='+', default=list(pre.VARIANTS))
    r.add_argument('--noise-dir', type=Path, help='folder of household noise WAV/FLAC/OGG files')
    r.add_argument('--snr', type=float, nargs='+', default=[20, 10, 5])
    r.add_argument('--bootstrap', type=int, default=1000)
    r.add_argument('--seed', type=int, default=42)
    r.add_argument('--out', default=str(ARTIFACTS / 'h2-results.json'))
    p = sub.add_parser('predict', help='label real recordings with a model trained on all CatMeows clips')
    p.add_argument('--variant', default='baseline', choices=list(pre.VARIANTS))
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('files', nargs='+')
    args = parser.parse_args()
    run(args) if args.command == 'run' else predict(args)


if __name__ == '__main__':
    main()
