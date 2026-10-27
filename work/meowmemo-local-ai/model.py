"""Offline YAMNet embeddings and a CatMeows context classifier. No network calls."""
from pathlib import Path
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '4')
os.environ.setdefault('TF_NUM_INTEROP_THREADS', '2')
import sys
import csv
import math
import time
import subprocess
import tempfile
import threading
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from scipy.fft import dct

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / 'vendor' / 'yamnet'
ARTIFACTS = ROOT / 'artifacts'
LABELS = ['brushing', 'food', 'isolation']
LABEL_NAMES = {'brushing': '梳毛时 / Brushing', 'food': '等待食物 / Waiting for food',
               'isolation': '陌生环境独处 / Isolation in an unfamiliar environment'}
MODEL_VERSION = 'catmeows-local-v2'


def mfcc_features(samples):
    """Compact 100-D spectral statistics, independent of cat ID and context."""
    samples = samples / max(float(np.max(np.abs(samples))), 1e-6)
    if len(samples) < 400:
        samples = np.pad(samples, (0, 400 - len(samples)))
    frames = np.lib.stride_tricks.sliding_window_view(samples, 400)[::160]
    power = np.abs(np.fft.rfft(frames * np.hanning(400), n=512)) ** 2
    hz_to_mel = lambda hz: 2595 * np.log10(1 + hz / 700)
    mel_to_hz = lambda mel: 700 * (10 ** (mel / 2595) - 1)
    centers = mel_to_hz(np.linspace(hz_to_mel(80), hz_to_mel(7600), 42))
    bins = np.fft.rfftfreq(512, 1 / 16000)
    bank = np.array([np.maximum(0, np.minimum((bins - a) / (b - a), (c - bins) / (c - b)))
                     for a, b, c in zip(centers[:-2], centers[1:-1], centers[2:])])
    mfcc = dct(np.log(np.maximum(power @ bank.T, 1e-10)), axis=1, norm='ortho')[:, 1:21]
    delta = np.diff(mfcc, axis=0) if len(mfcc) > 1 else np.zeros_like(mfcc)
    return np.concatenate([mfcc.mean(0), mfcc.std(0), np.percentile(mfcc, 10, axis=0),
                           np.percentile(mfcc, 90, axis=0), delta.std(0)]).astype(np.float32)


def read_audio(path):
    """Decode original media locally, bounded to 16 s, returning 16k mono."""
    try:
        with sf.SoundFile(str(path)) as f:
            if len(f) / f.samplerate > 16:
                raise ValueError('Please choose a recording no longer than 15 seconds.')
            samples = f.read(dtype='float32', always_2d=True).mean(axis=1)
            sr = f.samplerate
    except (sf.LibsndfileError, RuntimeError):
        # Browser WebM/M4A/MP4: ffmpeg decodes a temporary copy, never edits original.
        proc = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
                               '-t', '16', '-vn', '-ac', '1', '-ar', '16000',
                               '-f', 'f32le', 'pipe:1'], capture_output=True, timeout=30)
        if proc.returncode:
            raise ValueError('This file has no supported audio track.')
        samples = np.frombuffer(proc.stdout, dtype='<f4').copy()
        sr = 16000
    if not len(samples) or not np.isfinite(samples).all():
        raise ValueError('No valid audio found.')
    if len(samples) / sr > 15.5:
        raise ValueError('Please choose a recording no longer than 15 seconds.')
    if sr != 16000:
        divisor = math.gcd(sr, 16000)
        samples = resample_poly(samples, 16000 // divisor, sr // divisor)
    return np.asarray(samples, dtype=np.float32)


class AudioModel:
    def __init__(self, classifier=True):
        sys.path.insert(0, str(VENDOR))
        import tensorflow as tf
        import params
        import yamnet
        self.tf = tf
        # Deliberately use CPU: no Metal/CUDA dependency or GPU memory reservation.
        tf.config.set_visible_devices([], 'GPU')
        self.net = yamnet.yamnet_frames_model(params.Params())
        self.net.load_weights(str(VENDOR / 'yamnet.h5'))
        self.forward = tf.function(lambda x: self.net(x, training=False),
                                   input_signature=[tf.TensorSpec([None], tf.float32)])
        with open(VENDOR / 'yamnet_class_map.csv') as f:
            self.names = [row['display_name'] for row in csv.DictReader(f)]
        self.cat_indices = [i for i, n in enumerate(self.names)
                            if n in ('Cat', 'Meow', 'Purr', 'Hiss', 'Caterwaul')]
        self.lock = threading.Lock()
        self.bundle = None
        if classifier:
            import joblib
            self.bundle = joblib.load(ARTIFACTS / 'classifier.joblib')
            self.evaluation = __import__('json').loads((ARTIFACTS / 'evaluation.json').read_text())
        self.extract(np.zeros(16000, dtype=np.float32))

    def extract(self, samples):
        with self.lock:
            scores, embeddings, _ = self.forward(samples)
        scores, embeddings = scores.numpy(), embeddings.numpy()
        # Mean pooling also used during training. No names/tags/photos enter model.
        features = embeddings.mean(axis=0)
        cat_score = float(scores[:, self.cat_indices].max())
        mean_scores = scores.mean(axis=0)
        top = [{'label': self.names[int(i)], 'score': float(mean_scores[i])}
               for i in np.argsort(mean_scores)[-3:][::-1]]
        return features, cat_score, top

    def predict_samples(self, samples):
        start = time.perf_counter()
        duration = len(samples) / 16000
        rms = float(np.sqrt(np.mean(samples ** 2)))
        base = {'modelVersion': MODEL_VERSION, 'source': 'local-acoustic-model',
                'analyzedAt': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                'duration': round(duration, 3), 'runtime': 'CPU · offline',
                'thresholds': self.bundle['thresholds'], 'notATranslation': True}
        if duration < .25 or rms < 0.0001:
            return {**base, 'status': 'uncertain', 'suggestion': None,
                    'reason': 'too-short-or-quiet', 'scores': {},
                    'elapsedMs': round((time.perf_counter() - start) * 1000)}
        features, cat_score, top = self.extract(samples)
        clf = self.bundle['classifier']
        if self.bundle.get('feature_mode') == 'mfcc':
            features = mfcc_features(samples)
        elif self.bundle.get('feature_mode') == 'combined':
            features = np.concatenate([features, mfcc_features(samples)])
        probs = clf.predict_proba(features[None, :])[0]
        winner = int(probs.argmax())
        top_two = sorted(probs, reverse=True)[:2]
        threshold = self.bundle['thresholds']
        if cat_score < threshold['cat_event']:
            reason = 'cat-sound-not-clear'
        elif float(probs[winner]) < threshold['context'] or top_two[0] - top_two[1] < threshold['margin']:
            reason = 'context-not-clear'
        elif self.evaluation['heldout_test_before_abstention']['macro_f1'] < .65:
            reason = 'model-validation-limited'
        else:
            reason = None
        return {**base, 'status': 'uncertain' if reason else 'suggested',
                'suggestion': None if reason else str(clf.classes_[winner]),
                'experimentalTopCandidate': str(clf.classes_[winner]),
                'reason': reason, 'scores': {str(c): float(p) for c, p in zip(clf.classes_, probs)},
                'catEventScore': cat_score, 'audioEvents': top,
                'elapsedMs': round((time.perf_counter() - start) * 1000)}

    def predict_file(self, path):
        return self.predict_samples(read_audio(path))


if __name__ == '__main__':
    import json
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python model.py your-recording.wav')
    print(json.dumps(AudioModel().predict_file(sys.argv[1]), ensure_ascii=False, indent=2))
