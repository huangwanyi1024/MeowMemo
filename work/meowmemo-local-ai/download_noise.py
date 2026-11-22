"""Download the 20 ESC-50 household noise clips used by the H2 experiment and check them.

  python download_noise.py            # download into data/noise/esc50/ (skips clips already correct)
  python download_noise.py --verify   # only check what is in data/noise/

The H2 noise conditions and the noise-augmented training are built from exactly these files, so a
rerun with any other noise gives different numbers. Every clip is checked against its SHA-256, and
the set is checked against the noise fingerprint stored in artifacts/h2-results.json.

h2_experiment.py reads every audio file under data/noise/, so keep other audio out of that folder
when reproducing the committed results; --verify warns about extra files.

Terms: ESC-50 (K. J. Piczak, "ESC: Dataset for Environmental Sound Classification", ACM Multimedia
2015) is licensed CC BY-NC 3.0: credit the author, non-commercial use only. The audio stays out of
Git (.gitignore).
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

# Pinned ESC-50 commit, so the files cannot change underneath us.
COMMIT = '33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6'
SOURCE = f'https://raw.githubusercontent.com/karolpiczak/ESC-50/{COMMIT}/audio/'
NOISE_ROOT = Path(__file__).resolve().parent / 'data' / 'noise'
TARGET = NOISE_ROOT / 'esc50'
SUBDIR = 'esc50'
FINGERPRINT = '64d13fcbce3ed30f'  # 'noise.fingerprint' in artifacts/h2-results.json
HEADERS = {'User-Agent': 'MeowMemo-coursework-downloader'}
AUDIO = {'.wav', '.flac', '.ogg'}

# ESC-50 class numbers in the file names: 17 pouring water, 18 toilet flush, 30 door knock,
# 31 mouse click, 35 washing machine, 36 vacuum cleaner, 37 clock alarm, 38 clock tick.
CLIPS = {
    '1-100210-A-36.wav': 'f97e97b0fe0afce323d858503b6fa3ffd6c8cb1162c43cf3b24461300fb9abf6',
    '1-101336-A-30.wav': 'e738266e395e378102f74e0920b05ff5937543788420d5b2a6b8d3df8bdb3910',
    '1-118206-A-31.wav': '4461fa26f119749f99a4762be421d0d64e774960be7eef9780812d48580e48fb',
    '1-21896-A-35.wav': '1b4210c50a01cabab07065a112463fad4f82de60385ef9aaf6316afe7d4b976c',
    '1-21934-A-38.wav': '8d26e40e0e382b0d2d7f6dafcb132cfe703ee3f7f32780e878fdb5a1aaffcc28',
    '2-102414-A-17.wav': '2e8840176baf5e07f8f3239fe13f4f43c1c485e05c7f5795204f86d2e60df729',
    '2-102414-D-17.wav': '754e3a3f29218b6742c6b60c26e12fe0693352da38c46015652f1bf2e7fdda05',
    '2-102435-A-37.wav': '6917ce398c3cb7cb426c65224f59e63794eeabd732ad2f399c23f5b091bbcd12',
    '2-102567-A-35.wav': 'fb6a18ab967f87466bb047e0165354e20fb1d33a8a6ea5810fa260645171b26b',
    '2-104476-A-37.wav': 'eb652724ba0a12a9665073a2b7130c685c67ac69c2d55cd8fd6c5b4593e28548',
    '3-100018-A-18.wav': 'd234d3dfce197182b5b97291a262eb59bd1da646e279ad1ae45c3f351b032b41',
    '3-108451-A-17.wav': 'b03020a9662624137b529ea76eb7f5074ca4fd906e1526b747b0ec305988cda1',
    '3-117793-A-37.wav': '403a522c137b94195bdf3d9175aa3432a76018e41fd049f74cbd6da900f38cd4',
    '4-119720-A-18.wav': '7ba566572f51a9c851f4853bc6206efa6483262af6b99f7e7f90f83dc05800f8',
    '4-146200-A-36.wav': '41db87e753f13f238ba7f8ffca60421d08f8ab3e315c4d79f0557caed80ee9d8',
    '4-151242-A-37.wav': 'c83789199d3a2794323f9151cae42fa478b7ae408a624f483399316bd44cf899',
    '5-141683-A-35.wav': 'c8ac3bafa369ff4bcfef515f00060c963f4c19d9275ada75edbc8cdb9c1ad591',
    '5-156698-A-18.wav': '276b703a87be2d4703f89ad7412332720c73062f4c5147728b931ba26273ba46',
    '5-181977-A-35.wav': 'f04401db719f20052c3c7497a5893f644473f08a05f4820200b36076079f7951',
    '5-182007-A-36.wav': '3da75e2e43452c3d1bc595b46a51e7a04bc6be977fc5b11e7adaa5e8e5877b0f',
}


def fingerprint(relative_names):
    """Same calculation as h2_experiment.py: cache_key(sorted names relative to the noise folder)."""
    return hashlib.sha256(json.dumps((sorted(relative_names),), sort_keys=True).encode()).hexdigest()[:16]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
        return r.read()


def download():
    TARGET.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for name, expected in CLIPS.items():
        path = TARGET / name
        if path.exists() and sha256(path) == expected:
            continue
        data = fetch(SOURCE + name)
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit(f'Checksum mismatch for {name}: expected {expected}, got {actual}')
        path.write_bytes(data)
        fetched += 1
    print(f'Downloaded {fetched} clip(s); {len(CLIPS) - fetched} already present in {TARGET}')
    return verify()


def verify():
    problems = []
    for name, expected in CLIPS.items():
        path = TARGET / name
        if not path.exists():
            problems.append(f'missing: {name}')
        elif sha256(path) != expected:
            problems.append(f'wrong contents: {name}')
    found = sorted(str(p.relative_to(NOISE_ROOT)) for p in NOISE_ROOT.rglob('*')
                   if p.suffix.lower() in AUDIO) if NOISE_ROOT.exists() else []
    extras = [n for n in found if n not in {f'{SUBDIR}/{c}' for c in CLIPS}]
    print(f'Noise clips: {len(CLIPS) - sum(p.startswith("missing") for p in problems)}/{len(CLIPS)} present in {TARGET}')
    for p in problems:
        print(f'  {p}')
    if extras:
        print(f'WARNING: {len(extras)} other audio file(s) in {NOISE_ROOT} will be used by h2_experiment.py '
              f'and change the results: {", ".join(extras[:5])}{" ..." if len(extras) > 5 else ""}')
    actual = fingerprint(found)
    match = actual == FINGERPRINT
    print(f'Noise fingerprint: {actual} ({"matches" if match else "does NOT match"} the committed results, {FINGERPRINT})')
    ok = not problems and match
    print('OK: identical to the noise used for the committed H2 results.' if ok else 'Not identical; see above.')
    return ok


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verify', action='store_true', help='only check the files in data/noise/')
    sys.exit(0 if (verify() if parser.parse_args().verify else download()) else 1)
