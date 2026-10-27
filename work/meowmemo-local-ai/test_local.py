"""Smoke checks for the running local service. Uses public audio, never personal media."""
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import numpy as np
import soundfile as sf
import requests

base = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765'
root = Path(__file__).resolve().parent
assert requests.get(base + '/api/health').json()['offline'] is True
assert requests.get(base + '/api/model').json()['status'] == 'experimental'
samples = requests.get(base + '/api/samples').json()
for sample in samples:
    response = requests.post(base + '/api/samples/' + sample['id'] + '/analyze')
    response.raise_for_status()
    analysis = response.json()['analysis']
    assert analysis['source'] == 'local-acoustic-model'
    assert analysis['status'] == 'uncertain' and analysis['suggestion'] is None
    assert abs(sum(analysis['scores'].values()) - 1) < 1e-5
for label, waveform in [('silence', np.zeros(48000)),
                          ('tone', .25 * np.sin(2 * np.pi * 440 * np.arange(48000) / 16000)),
                          ('noise', np.random.default_rng(42).normal(0, .08, 48000))]:
    buf = io.BytesIO(); sf.write(buf, waveform, 16000, format='WAV')
    response = requests.post(base + '/api/analyze', files={'file': (label + '.wav', buf.getvalue())})
    response.raise_for_status()
    assert response.json()['status'] == 'uncertain', label
bad = {'file': ('broken.wav', b'not audio')}
assert requests.post(base + '/api/analyze', files=bad).status_code == 400
assert requests.post(base + '/api/analyze', files=bad, headers={'Origin': 'https://example.com'}).status_code == 403
assert requests.get(base + '/api/samples/not-a-sample/audio').status_code == 404
with tempfile.TemporaryDirectory() as temp:
    for suffix, codec in [('webm', 'libopus'), ('m4a', 'aac')]:
        output = Path(temp) / ('public-sample.' + suffix)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(root / 'data' / samples[0]['directory'] / samples[0]['name']),
                        '-af', 'apad=whole_dur=3', '-t', '3', '-c:a', codec, str(output)], check=True)
        with output.open('rb') as f:
            response = requests.post(base + '/api/analyze', files={'file': (output.name, f)})
        response.raise_for_status()
        assert 2.8 < response.json()['duration'] < 3.2
print('PASS: real public samples, uncertainty policy, silence/tone/noise, corrupt audio, foreign origin, WebM and M4A decoding.')
