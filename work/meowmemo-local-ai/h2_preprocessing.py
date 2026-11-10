"""H2 audio preprocessing and noise simulation. Pure NumPy/SciPy; no TensorFlow import.

All functions take and return mono float32 audio at 16 kHz, the format `model.read_audio`
produces. Noise reduction uses the optional `noisereduce` package.
"""
from pathlib import Path
import math
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 16000
PARAMS_VERSION = 'h2-preprocessing-v1'  # bump when any default below changes (invalidates caches)


def band_limit(audio):
    """Keep only content below 4 kHz, matching CatMeows' 8 kHz recordings."""
    audio = np.asarray(audio, dtype=np.float32)
    return resample_poly(resample_poly(audio, 1, 2), 2, 1)[:len(audio)].astype(np.float32)


def normalize_loudness(audio, target_dbfs=-20.0):
    """Scale to a fixed RMS level, then prevent clipping. Silent input is returned unchanged."""
    audio = np.asarray(audio, dtype=np.float32)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-8:
        return audio
    out = audio * (10 ** (target_dbfs / 20) / rms)
    return (out / max(1.0, float(np.abs(out).max()))).astype(np.float32)


def trim_silence(audio, rel_db=-35.0, frame=400, hop=160, min_len=SR):
    """Cut leading/trailing frames quieter than `rel_db` below the loudest frame.

    Keeps the original when trimming would leave less than `min_len` samples (1 s), so
    YAMNet always receives at least one full analysis window.
    """
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) < frame:
        return audio
    frames = np.lib.stride_tricks.sliding_window_view(audio, frame)[::hop]
    db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-10)
    keep = db > db.max() + rel_db
    first = int(np.argmax(keep))
    last = len(keep) - 1 - int(np.argmax(keep[::-1]))
    out = audio[first * hop:last * hop + frame]
    return out if len(out) >= min_len else audio


def reduce_noise(audio):
    """Spectral-gating noise reduction (optional dependency: pip install noisereduce)."""
    import noisereduce as nr
    out = nr.reduce_noise(y=np.asarray(audio, dtype=np.float32), sr=SR)
    return np.asarray(out, dtype=np.float32)


def noise_reduction_available():
    try:
        import noisereduce  # noqa: F401
        return True
    except ImportError:
        return False


def compose(*steps):
    def run(audio):
        audio = np.asarray(audio, dtype=np.float32)
        for step in steps:
            audio = step(audio)
        return np.asarray(audio, dtype=np.float32)
    return run


# Order matters: denoise before trimming so the silence detector sees the cleaned signal.
VARIANTS = {
    'baseline': compose(),
    'trim': compose(trim_silence),
    'normalize': compose(normalize_loudness),
    'denoise': compose(reduce_noise),
    'trim+normalize': compose(trim_silence, normalize_loudness),
    'denoise+trim+normalize': compose(reduce_noise, trim_silence, normalize_loudness),
}
NEEDS_NOISEREDUCE = {'denoise', 'denoise+trim+normalize'}


def mix_at_snr(clean, noise, snr_db, rng):
    """Add a random stretch of `noise` to `clean` at the given signal-to-noise ratio (dB)."""
    clean = np.asarray(clean, dtype=np.float32)
    noise = np.asarray(noise, dtype=np.float32)
    if len(noise) < len(clean):
        noise = np.tile(noise, math.ceil(len(clean) / len(noise)))
    start = int(rng.integers(0, len(noise) - len(clean) + 1))
    noise = noise[start:start + len(clean)]
    p_clean = float(np.mean(clean ** 2))
    p_noise = float(np.mean(noise ** 2))
    if p_clean < 1e-12 or p_noise < 1e-12:
        return clean.copy()
    mixed = clean + noise * math.sqrt(p_clean / (p_noise * 10 ** (snr_db / 10)))
    return (mixed / max(1.0, float(np.abs(mixed).max()))).astype(np.float32)


def load_noise_bank(directory, max_files=200, max_seconds=60.0):
    """Load WAV/FLAC/OGG noise files as band-limited 16 kHz mono arrays.

    Uses soundfile directly (not `model.read_audio`, which rejects files over 15.5 s).
    Files are sorted for reproducibility; near-silent files are skipped.
    """
    paths = sorted(p for p in Path(directory).rglob('*')
                   if p.suffix.lower() in {'.wav', '.flac', '.ogg'})[:max_files]
    bank = []
    for path in paths:
        with sf.SoundFile(str(path)) as f:
            frames = min(len(f), int(max_seconds * f.samplerate))
            audio = f.read(frames, dtype='float32', always_2d=True).mean(axis=1)
            sr = f.samplerate
        if sr != SR:
            g = math.gcd(sr, SR)
            audio = resample_poly(audio, SR // g, sr // g)
        audio = band_limit(audio)
        if len(audio) >= SR // 4 and float(np.sqrt(np.mean(audio ** 2))) > 1e-5:
            bank.append(audio)
    if not bank:
        raise ValueError(f'No usable noise audio found in {directory}')
    return bank


def noisy_version(clean, bank, snr_db, seed, index):
    """Deterministic noisy copy of clip `index`: every variant gets the same noise segment."""
    rng = np.random.default_rng([seed, index, int(round(snr_db * 10)) + 1000])
    noise = bank[int(rng.integers(len(bank)))]
    return mix_at_snr(clean, noise, snr_db, rng)
