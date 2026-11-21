"""Deterministic CatMeows audit; never loads owner media or trains a classifier."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

LABELS = ('brushing', 'food', 'isolation')
PATTERN = re.compile(r'([BFI])_([A-Z]{3}\d{2})_(MC|EU)_(FI|FN|MI|MN)_([A-Z]{3}\d{2})_([1-9])(\d{2})\.wav', re.I)


def parse_metadata(filename):
    match = PATTERN.fullmatch(Path(filename).name)
    if not match or match[7] == '00':
        raise ValueError(f'{filename}: expected C_CAT01_BB_SS_OWN01_RXX.wav; extras/SEQ files are excluded')
    context, cat, breed, sex, owner, session, counter = (v.upper() for v in match.groups())
    return dict(label={'B': 'brushing', 'F': 'food', 'I': 'isolation'}[context],
                cat=cat, breed=breed, sex=sex, owner=owner, session=int(session), counter=int(counter))


def inspect_audio(path, expected_rate=8000):
    import numpy as np
    import soundfile as sf
    issues = []
    result = {}
    if path.suffix.lower() != '.wav':
        issues.append('unsupported_format: use original WAV')
    try:
        samples, rate = sf.read(path, always_2d=True, dtype='float32')
        result = dict(sample_rate=rate, channels=samples.shape[1], frames=len(samples), duration=len(samples)/rate)
        if rate != expected_rate:
            issues.append(f'sample_rate: expected {expected_rate}, found {rate}')
        if samples.shape[1] != 1:
            issues.append('channels: expected mono')
        if not len(samples):
            issues.append('empty_audio: no frames')
        elif not np.isfinite(samples).all():
            issues.append('nonfinite_audio: NaN or infinity')
        else:
            result['pcm_sha256'] = hashlib.sha256(samples.astype('<f4').tobytes() + str(rate).encode()).hexdigest()
            if not np.any(samples):
                issues.append('silent_audio: all samples zero')
        result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, RuntimeError, ValueError) as exc:
        issues.append(f'unreadable_audio: {type(exc).__name__}; check file exists and is valid WAV')
    return result, issues


def validate_processed_audio(samples, sample_rate, expected_rate=16000, expected_frames=None):
    """Contract for future H2 processors, including denoisers; no processing here.

    Set expected_frames only for operations declared to preserve duration.
    Trimmers should omit it and separately document their boundary policy.
    """
    import numpy as np
    samples = np.asarray(samples)
    issues = []
    if samples.ndim != 1:
        issues.append('processed audio must be one-dimensional mono')
    if not samples.size:
        issues.append('processed audio must not be empty')
    if not np.issubdtype(samples.dtype, np.number) or np.iscomplexobj(samples):
        issues.append('processed audio must contain real numeric samples')
    elif not np.isfinite(samples).all():
        issues.append('processed audio contains NaN or infinity')
    if sample_rate != expected_rate:
        issues.append(f'processed sample rate must be {expected_rate}')
    if expected_frames is not None and (samples.ndim != 1 or len(samples) != expected_frames):
        issues.append(f'processed audio must preserve {expected_frames} frames')
    return issues


def summarize(rows):
    counts = Counter(r['label'] for r in rows if r.get('label') in LABELS)
    cats = defaultdict(Counter)
    identities = defaultdict(set)
    hashes = defaultdict(list)
    for row in rows:
        if row.get('cat') and row.get('label') in LABELS:
            cats[row['cat']][row['label']] += 1
            identities[row['cat']].add((row.get('breed'), row.get('sex'), row.get('owner')))
        if row.get('pcm_sha256'):
            hashes[row['pcm_sha256']].append(row['file'])
    values = [counts[c] for c in LABELS]
    return dict(recordings=len(rows), metadata_valid=sum(values), class_counts={c: counts[c] for c in LABELS},
                class_proportions={c: counts[c]/sum(values) if sum(values) else 0 for c in LABELS},
                imbalance_max_min=max(values)/min(values) if min(values) else None,
                cat_counts={c: sum(cats[c].values()) for c in sorted(cats)},
                cat_by_situation={c: {k: cats[c][k] for k in LABELS} for c in sorted(cats)},
                missing_classes={c: [k for k in LABELS if not cats[c][k]] for c in sorted(cats) if len(cats[c]) < 3},
                inconsistent_cat_metadata=sorted(c for c, v in identities.items() if len(v) > 1),
                suspicious_pcm_duplicates=sorted(sorted(v) for v in hashes.values() if len(v) > 1),
                issue_counts=dict(sorted(Counter(issue.split(':')[0] for r in rows for issue in r.get('issues', [])).items())))


def analyze(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError('CatMeows directory missing. Extract dataset.zip from https://zenodo.org/records/4008297 (not extras.zip).')
    files = sorted(p for p in root.rglob('*') if p.is_file() and not p.name.startswith('.'))
    if not files:
        raise ValueError('Empty dataset directory; extract CatMeows dataset.zip first.')
    rows = []
    for path in files:
        row = {'file': path.relative_to(root).as_posix(), 'issues': []}
        try:
            row.update(parse_metadata(path.name))
            if row['session'] > 3:
                row['issues'].append('session_outside_documentation: retain observed session, verify source')
        except ValueError as exc:
            row['issues'].append(f'metadata: {exc}')
        info, issues = inspect_audio(path)
        row.update(info)
        row['issues'].extend(issues)
        rows.append(row)
    return dict(provenance='actual audio directory', records=rows, summary=summarize(rows))


def validate_manifest(manifest, root=None):
    """Accept existing split.json or partition -> list of metadata dictionaries.

    Dictionary rows require file/label/cat; optional noise_source is an original
    ESC source ID, never a crop/mix ID. root=None explicitly means metadata only.
    """
    issues, rows = [], []
    seen, cats, noises = defaultdict(set), defaultdict(set), defaultdict(set)
    for partition, entries in sorted(manifest.items()):
        if not isinstance(entries, list):
            raise ValueError(f'{partition}: expected a list of file references')
        for entry in entries:
            row = {'file': entry} if isinstance(entry, str) else dict(entry)
            filename = row.get('file')
            if not isinstance(filename, str) or not filename:
                issues.append(f'{partition}: missing file reference')
                continue
            path = Path(filename)
            if path.is_absolute() or '..' in path.parts:
                issues.append(f'{partition}/{filename}: use a path within dataset root')
                continue
            ref = path.as_posix()
            if seen[ref]:
                issues.append(f'{partition}/{filename}: duplicate file reference')
            seen[ref].add(partition)
            try:
                parsed = parse_metadata(filename)
                for key, value in parsed.items():
                    if key in row and row[key] != value:
                        issues.append(f'{partition}/{filename}: incorrect {key}; expected {value}')
                if not isinstance(entry, str):
                    for key in ('label', 'cat'):
                        if key not in row:
                            issues.append(f'{partition}/{filename}: missing {key}')
                row = {**row, **parsed}
                if parsed['session'] > 3:
                    issues.append(f'{partition}/{filename}: session outside published range 1–3; verify source')
                cats[row['cat']].add(partition)
            except ValueError as exc:
                issues.append(str(exc))
            if row.get('noise_source'):
                noises[str(row['noise_source'])].add(partition)
            if root is not None:
                info, errors = inspect_audio(Path(root) / path)
                row.update(info)
                issues.extend(f'{partition}/{filename}: {e}' for e in errors)
            row.update(file=ref, partition=partition)
            rows.append(row)
    for kind, groups in [('cat', cats), ('noise source', noises)]:
        for identity, partitions in sorted(groups.items()):
            if len(partitions) > 1:
                issues.append(f'{kind} leakage: {identity} in {", ".join(sorted(partitions))}; keep source in one partition')
    if not rows:
        issues.append('empty manifest: no recordings')
    summary = summarize(rows)
    for cat in summary['inconsistent_cat_metadata']:
        issues.append(f'inconsistent cat metadata: {cat}')
    return dict(provenance='manifest metadata only' if root is None else 'manifest with audio validation',
                audio_checked=root is not None, valid=not issues, issues=issues, records=rows, summary=summary)


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    fields = sorted(set().union(*(r.keys() for r in report['records']))) if report['records'] else ['file']
    with (output / 'recordings.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in report['records'])


def plot_report(report, output, synthetic=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = report['summary']
    prefix = 'SYNTHETIC FIXTURE — ' if synthetic else report['provenance'] + ' — '
    for name, data in [('situations', summary['class_counts']), ('cats', summary['cat_counts']), ('quality', summary['issue_counts'] or {'no recorded issues': 0})]:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(list(data), list(data.values()))
        ax.tick_params(axis='x', rotation=90)
        ax.set_title(prefix + name)
        ax.set_ylabel('Count')
        fig.tight_layout(); fig.savefig(output / (name + '.png')); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 7))
    cats = list(summary['cat_by_situation'])
    if cats:
        image = ax.imshow([list(summary['cat_by_situation'][c].values()) for c in cats], aspect='auto')
        ax.set_yticks(range(len(cats)), cats); ax.set_xticks(range(3), LABELS); fig.colorbar(image, ax=ax)
    ax.set_title(prefix + 'cat by situation'); fig.tight_layout(); fig.savefig(output / 'matrix.png'); plt.close(fig)
    fig, ax = plt.subplots()
    durations = [r['duration'] for r in report['records'] if 'duration' in r]
    if durations:
        ax.hist(durations, bins='auto')
    else:
        ax.text(.1, .5, 'Audio durations unavailable; metadata only', transform=ax.transAxes)
    ax.set_xlabel('Duration (seconds)'); ax.set_title(prefix + 'durations')
    fig.tight_layout(); fig.savefig(output / 'durations.png'); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plots', action='store_true')
    args = parser.parse_args()
    if not args.data and not args.manifest:
        parser.error('provide --data or --manifest; no dataset is downloaded automatically')
    try:
        report = validate_manifest(json.loads(args.manifest.read_text()), args.data) if args.manifest else analyze(args.data)
        write_report(report, args.output)
        if args.plots:
            plot_report(report, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'{exc}\n')
    if report.get('valid') is False or report['summary']['issue_counts'] or report['summary']['inconsistent_cat_metadata'] or report['summary']['suspicious_pcm_duplicates']:
        parser.exit(1, 'Audit found issues; inspect report.json before experimentation.\n')


if __name__ == '__main__':
    main()
