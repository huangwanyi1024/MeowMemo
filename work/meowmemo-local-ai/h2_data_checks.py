"""H2 data checks: run these before trusting H2 results. No TensorFlow import.

  python h2_data_checks.py shortcut            # can clip length alone predict the situation?
  python h2_data_checks.py noise data/noise    # is the noise folder free of animal sounds?

`shortcut`: silence trimming changes clip length. If length alone already predicts the
situation, a gain from the `trim` variant could come from length rather than cleaner audio.
This scores a length-only classifier with the same leave-one-cat-out test as the H2
experiment, before and after trimming, compares it with shuffled lengths (a permutation
test), and reports how much trimming removes from each situation. Writes artifacts/h2-shortcut-check.json.

`noise`: the noise pool must not contain animal sounds. ESC-50 has cat, dog and other
animal classes; mixing a cat clip into a meow would add a second cat. ESC-50 files are
recognised by their name (fold-source-take-class.wav). Exits with code 1 if any are found.
"""
import argparse
import json
import re
import sys
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / 'artifacts'
CATMEOWS = ROOT / 'data' / 'catmeows'
LABELS = ['brushing', 'food', 'isolation']
CONTEXT = {'B': 'brushing', 'F': 'food', 'I': 'isolation'}
AUDIO_SUFFIXES = {'.wav', '.flac', '.ogg'}

# ESC-50 class numbers 0-9 are the "Animals" category (meta/esc50.csv in the ESC-50 repository).
ESC50_ANIMALS = {0: 'dog', 1: 'rooster', 2: 'pig', 3: 'cow', 4: 'frog',
                 5: 'cat', 6: 'hen', 7: 'insects', 8: 'sheep', 9: 'crow'}
ESC50_NAME = re.compile(r'^(\d)-(\d+)-([A-Z])-(\d{1,2})\.(wav|flac|ogg)$', re.IGNORECASE)


# ---------- noise pool ----------

def esc50_class(filename):
    """ESC-50 class number from a filename such as 5-259169-A-5.wav, or None if not ESC-50."""
    match = ESC50_NAME.match(Path(filename).name)
    return int(match.group(4)) if match else None


def check_noise_folder(directory):
    paths = sorted(p for p in Path(directory).rglob('*') if p.suffix.lower() in AUDIO_SUFFIXES)
    if not paths:
        raise SystemExit(f'No WAV/FLAC/OGG files found in {directory}')
    animals, unknown, rates = [], [], {}
    for path in paths:
        rel = str(path.relative_to(directory))
        target = esc50_class(path.name)
        if target is None:
            unknown.append(rel)
        elif target in ESC50_ANIMALS:
            animals.append({'file': rel, 'class': ESC50_ANIMALS[target]})
        info = sf.info(str(path))
        rates[info.samplerate] = rates.get(info.samplerate, 0) + 1
    return {'files': len(paths), 'animal_files': animals, 'not_esc50': unknown,
            'sample_rates': {str(k): v for k, v in sorted(rates.items())}}


def print_noise_report(report):
    print(f'{report["files"]} noise files. Sample rates: {report["sample_rates"]} '
          '(all are band-limited to 4 kHz when loaded, so this is for information only).')
    if report['not_esc50']:
        print(f'{len(report["not_esc50"])} files are not named like ESC-50 '
              '(e.g. DEMAND/MUSAN); check by ear that they contain no animals.')
    if report['animal_files']:
        print(f'FAIL: {len(report["animal_files"])} ESC-50 animal clips must be removed:')
        for item in report['animal_files']:
            print(f'  {item["file"]} ({item["class"]})')
    else:
        print('PASS: no ESC-50 animal clips in the noise pool.')


# ---------- clip-length shortcut ----------

def duration_features(audios, sr):
    """Clip length in seconds, the only feature a length shortcut could use."""
    return np.array([[len(a) / sr] for a in audios], dtype=np.float64)


def removed_by_trim(before, after, y):
    """Mean seconds removed by trimming, per situation."""
    removed = before[:, 0] - after[:, 0]
    return {label: round(float(removed[y == label].mean()), 3) for label in LABELS if (y == label).any()}


def median_by_class(x, y):
    return {label: round(float(np.median(x[y == label, 0])), 3) for label in LABELS if (y == label).any()}


def permutation_test(x, y, groups, n_permutations, seed):
    """Macro-F1 of a length-only model on unseen cats, and how often shuffled lengths match it.

    Shuffling lengths across clips breaks any link between length and situation while keeping
    the class counts and cats unchanged, so the shuffled scores show what chance looks like
    for this classifier. (Comparing with "always guess the commonest class" is too easy a bar:
    any classifier that varies its guesses beats that on macro-F1.)
    """
    from h2_evaluation import evaluate_unseen_cats
    scored, _ = evaluate_unseen_cats(x, x, y, groups)
    rng = np.random.default_rng(seed)
    null = np.array([evaluate_unseen_cats(s, s, y, groups)[0]['macro_f1']
                     for s in (x[rng.permutation(len(x))] for _ in range(n_permutations))])
    p_value = (1 + int((null >= scored['macro_f1']).sum())) / (n_permutations + 1)
    return scored, {'chance_macro_f1_median': round(float(np.median(null)), 3),
                    'chance_macro_f1_95th': round(float(np.percentile(null, 95)), 3),
                    'p_value': round(p_value, 4), 'permutations': n_permutations}


def shortcut_check(audios, y, groups, sr, trim, n_permutations=200, seed=42, alpha=0.05):
    """Score a length-only classifier on unseen cats, before and after trimming.

    Uses the same leave-one-cat-out evaluation as the H2 experiment. A p-value below `alpha`
    means length alone predicts the situation better than chance.
    """
    y, groups = np.asarray(y), np.asarray(groups)
    before = duration_features(audios, sr)
    after = duration_features([trim(a) for a in audios], sr)
    result = {'removed_by_trim_seconds': removed_by_trim(before, after, y), 'alpha': alpha}
    for name, x in (('original_length', before), ('trimmed_length', after)):
        scored, chance = permutation_test(x, y, groups, n_permutations, seed)
        result[name] = {'median_seconds_by_class': median_by_class(x, y),
                        'accuracy': scored['accuracy'], 'macro_f1': scored['macro_f1'],
                        'chance': chance, 'length_predicts_situation': chance['p_value'] < alpha}
    result['warning'] = bool(result['original_length']['length_predicts_situation']
                             or result['trimmed_length']['length_predicts_situation'])
    return result


def load_catmeows(directory):
    from model import read_audio
    files = sorted(Path(directory).glob('*.wav'))
    if len(files) != 440:
        raise SystemExit(f'Expected 440 CatMeows WAV files in {directory}, found {len(files)}. '
                         'Run: python download_catmeows.py')
    y = np.array([CONTEXT[p.name.split('_')[0]] for p in files])
    groups = np.array([p.name.split('_')[1] for p in files])
    return [read_audio(p) for p in files], y, groups


def print_shortcut_report(r):
    print(f'Seconds removed by trimming, per situation: {r["removed_by_trim_seconds"]}')
    for name in ('original_length', 'trimmed_length'):
        s = r[name]
        c = s['chance']
        print(f'{name:<16} median s {s["median_seconds_by_class"]}  macro-F1 {s["macro_f1"]:.3f}  '
              f'(chance median {c["chance_macro_f1_median"]:.3f}, 95th {c["chance_macro_f1_95th"]:.3f}; '
              f'p = {c["p_value"]:.3f})')
    if r['warning']:
        print('WARNING: clip length alone predicts the situation on unseen cats. A gain from '
              'trimming may come from length, so compare it with these length-only scores.')
    else:
        print('PASS: clip length alone does not reliably predict the situation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('shortcut', help='can clip length alone predict the situation?')
    s.add_argument('--catmeows', type=Path, default=CATMEOWS)
    s.add_argument('--permutations', type=int, default=200)
    s.add_argument('--seed', type=int, default=42)
    s.add_argument('--out', default=str(ARTIFACTS / 'h2-shortcut-check.json'))
    n = sub.add_parser('noise', help='check a noise folder for animal sounds')
    n.add_argument('directory', type=Path)
    args = parser.parse_args()

    if args.command == 'noise':
        report = check_noise_folder(args.directory)
        print_noise_report(report)
        sys.exit(1 if report['animal_files'] else 0)

    import h2_preprocessing as pre
    audios, y, groups = load_catmeows(args.catmeows)
    report = shortcut_check(audios, y, groups, pre.SR, pre.trim_silence, args.permutations, args.seed)
    report['preprocessing_version'] = pre.PARAMS_VERSION
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print_shortcut_report(report)
    print(f'\nWrote {out}')


if __name__ == '__main__':
    main()
