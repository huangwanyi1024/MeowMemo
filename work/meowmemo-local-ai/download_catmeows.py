"""Download CatMeows v1.0.2 from Zenodo into data/catmeows/ and check what arrived.

  python download_catmeows.py            # download (skips if all 440 clips are present)
  python download_catmeows.py --verify   # only report clip count, labels, sample rates, durations

Terms: CatMeows is published for scientific, non-commercial use with acknowledgement of
Ludovico et al. (DOI 10.5281/zenodo.4008297). The audio stays out of Git (.gitignore).
"""
import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

RECORD = 'https://zenodo.org/api/records/4008297'
TARGET = Path(__file__).resolve().parent / 'data' / 'catmeows'
NAME = re.compile(r'^[BFI]_[A-Z]{3}\d{2}_[A-Z]{2}_[A-Z]{2}_[A-Z]{3}\d{2}_\d+\.wav$')
HEADERS = {'User-Agent': 'MeowMemo-coursework-downloader'}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
        return r.read()


def checked(data, checksum):
    algo, _, expected = (checksum or '').partition(':')
    if algo in hashlib.algorithms_available and expected:
        actual = hashlib.new(algo, data).hexdigest()
        if actual != expected:
            raise SystemExit(f'Checksum mismatch ({algo}): expected {expected}, got {actual}')
    return data


def download():
    clips = [p for p in TARGET.glob('*.wav') if NAME.match(p.name)]
    if len(clips) == 440:
        print(f'All 440 clips already present in {TARGET}')
        return
    TARGET.mkdir(parents=True, exist_ok=True)
    record = json.loads(fetch(RECORD))
    entries = record.get('files') or []
    if isinstance(entries, dict):  # some API versions nest the list
        entries = entries.get('entries', [])
    written = 0
    for entry in entries:
        key = entry.get('key', '')
        links = entry.get('links', {})
        url = links.get('content') or links.get('self') or links.get('download')
        if not url or not key.lower().endswith(('.zip', '.wav')):
            continue
        print(f'Downloading {key} ({entry.get("size", "?")} bytes)...', flush=True)
        data = checked(fetch(url), entry.get('checksum'))
        if key.lower().endswith('.wav'):
            members = [(Path(key).name, data)]
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                members = [(Path(m).name, z.read(m)) for m in z.namelist()
                           if m.lower().endswith('.wav') and not Path(m).name.startswith('.')]
        for name, payload in members:
            if NAME.match(name):  # only the 440 labelled clips; skips extras/previews
                (TARGET / name).write_bytes(payload)
                written += 1
    print(f'Wrote {written} labelled clips to {TARGET}')
    verify()


def verify():
    import soundfile as sf
    clips = sorted(p for p in TARGET.glob('*.wav') if NAME.match(p.name))
    labels = Counter(p.name[0] for p in clips)
    cats = {p.name.split('_')[1] for p in clips}
    rates, durations = Counter(), []
    for p in clips:
        info = sf.info(str(p))
        rates[info.samplerate] += 1
        durations.append(info.duration)
    print(f'Clips: {len(clips)} (expected 440) | cats: {len(cats)} (expected 21)')
    print(f'Labels: brushing {labels["B"]}, food {labels["F"]}, isolation {labels["I"]} (expected 127/92/221)')
    print(f'Sample rates: {dict(rates)}')
    if durations:
        durations.sort()
        print(f'Duration (s): min {durations[0]:.2f}, median {durations[len(durations) // 2]:.2f}, max {durations[-1]:.2f}')
    if len(clips) != 440:
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verify', action='store_true', help='only check the downloaded clips')
    verify() if parser.parse_args().verify else download()
