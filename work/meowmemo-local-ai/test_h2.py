"""H2 unit tests. No TensorFlow, CatMeows download or network needed: python test_h2.py"""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
import h2_preprocessing as pre
from h2_evaluation import evaluate_unseen_cats, bootstrap_gain
from download_catmeows import NAME

SR = pre.SR


def tone(freq, seconds, amp=0.3):
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def power(x):
    return float(np.mean(np.asarray(x, dtype=np.float64) ** 2))


class PreprocessingTests(unittest.TestCase):
    def test_trim_removes_leading_and_trailing_silence(self):
        audio = np.concatenate([np.zeros(SR), tone(500, 2), np.zeros(SR)])
        out = pre.trim_silence(audio)
        self.assertLess(abs(len(out) - 2 * SR), 0.05 * SR)
        self.assertGreater(power(out), power(audio))

    def test_trim_keeps_original_when_result_would_be_too_short(self):
        audio = np.concatenate([np.zeros(SR), tone(500, 0.3), np.zeros(SR)])
        np.testing.assert_array_equal(pre.trim_silence(audio), audio)

    def test_normalize_hits_target_and_never_clips(self):
        out = pre.normalize_loudness(tone(440, 1, amp=0.01), target_dbfs=-20)
        self.assertAlmostEqual(10 * np.log10(power(out)), -20, delta=0.1)
        loud = pre.normalize_loudness(np.r_[np.zeros(SR), [1.0], np.zeros(SR)].astype(np.float32), -3)
        self.assertLessEqual(float(np.abs(loud).max()), 1.0)
        silent = np.zeros(SR, dtype=np.float32)
        np.testing.assert_array_equal(pre.normalize_loudness(silent), silent)

    def test_band_limit_removes_content_above_4khz(self):
        self.assertLess(power(pre.band_limit(tone(6000, 1))) / power(tone(6000, 1)), 0.05)
        self.assertGreater(power(pre.band_limit(tone(1000, 1))) / power(tone(1000, 1)), 0.9)
        self.assertEqual(len(pre.band_limit(tone(1000, 1.0001))), len(tone(1000, 1.0001)))

    def test_variants_without_optional_dependency_return_mono_float32(self):
        audio = np.concatenate([np.zeros(SR // 2), tone(700, 1.5), np.zeros(SR // 2)])
        for name, step in pre.VARIANTS.items():
            if name in pre.NEEDS_NOISEREDUCE:
                continue
            out = step(audio)
            self.assertEqual(out.ndim, 1, name)
            self.assertEqual(out.dtype, np.float32, name)


class NoiseTests(unittest.TestCase):
    def test_mix_reaches_requested_snr(self):
        rng = np.random.default_rng(0)
        clean = tone(500, 2, amp=0.1)
        noise = np.random.default_rng(1).normal(0, 0.05, 3 * SR).astype(np.float32)
        for snr in (20, 10, 5):
            mixed = pre.mix_at_snr(clean, noise, snr, rng)
            achieved = 10 * np.log10(power(clean) / power(mixed - clean))
            self.assertAlmostEqual(achieved, snr, delta=0.2)

    def test_short_noise_is_tiled(self):
        mixed = pre.mix_at_snr(tone(500, 2), tone(3000, 0.3), 10, np.random.default_rng(0))
        self.assertEqual(len(mixed), 2 * SR)

    def test_noisy_version_is_deterministic_per_clip(self):
        bank = [np.random.default_rng(i).normal(0, 0.1, 5 * SR).astype(np.float32) for i in range(3)]
        clean = tone(500, 1)
        a = pre.noisy_version(clean, bank, 10, seed=42, index=7)
        np.testing.assert_array_equal(a, pre.noisy_version(clean, bank, 10, seed=42, index=7))
        self.assertFalse(np.array_equal(a, pre.noisy_version(clean, bank, 10, seed=42, index=8)))

    def test_noise_bank_resamples_and_skips_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = np.arange(3 * 44100) / 44100
            sf.write(Path(tmp) / 'hum.wav', 0.2 * np.sin(2 * np.pi * 300 * t), 44100)
            sf.write(Path(tmp) / 'silent.wav', np.zeros(44100), 44100)
            bank = pre.load_noise_bank(tmp)
            self.assertEqual(len(bank), 1)
            self.assertLess(abs(len(bank[0]) - 3 * SR), 10)
            with self.assertRaises(ValueError):
                pre.load_noise_bank(Path(tmp) / 'missing')


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.groups = np.repeat([f'C{i:02d}' for i in range(8)], 15)
        self.y = np.tile(np.repeat(['brushing', 'food', 'isolation'], 5), 8)
        signal = (self.y[:, None] == np.array(['brushing', 'food', 'isolation'])).astype(float)
        self.x = np.hstack([signal * 3, rng.normal(0, 1, (len(self.y), 5))])

    def test_unseen_cat_evaluation_learns_separable_labels(self):
        result, pred = evaluate_unseen_cats(self.x, self.x, self.y, self.groups)
        self.assertEqual(len(pred), len(self.y))
        self.assertGreater(result['macro_f1'], 0.95)
        self.assertEqual(len(result['per_cat_accuracy']['by_cat']), 8)

    def test_noisy_test_features_lower_the_score(self):
        noisy = self.x + np.random.default_rng(1).normal(0, 6, self.x.shape)
        clean_score = evaluate_unseen_cats(self.x, self.x, self.y, self.groups)[0]['macro_f1']
        noisy_score = evaluate_unseen_cats(self.x, noisy, self.y, self.groups)[0]['macro_f1']
        self.assertLess(noisy_score, clean_score)

    def test_bootstrap_identical_predictions_is_not_supported(self):
        out = bootstrap_gain(self.y, self.y, self.y, self.groups, n=200)
        self.assertEqual(out['gain'], 0)
        self.assertFalse(out['supported'])

    def test_bootstrap_clear_improvement_is_supported(self):
        worse = np.where(np.arange(len(self.y)) % 2 == 0, 'isolation', self.y)
        out = bootstrap_gain(self.y, worse, self.y, self.groups, n=200)
        self.assertGreater(out['gain'], 0)
        self.assertTrue(out['supported'])


class DatasetTests(unittest.TestCase):
    def test_filename_pattern_matches_every_catmeows_clip_in_the_split(self):
        split = json.loads((Path(__file__).parent / 'artifacts' / 'split.json').read_text())
        names = split['development'] + split['test']
        self.assertEqual(len(names), 440)
        self.assertTrue(all(NAME.match(n) for n in names))
        extras = [p.name for p in (Path(__file__).parent / 'data' / 'extras').glob('*.wav')]
        self.assertFalse(any(NAME.match(n) for n in extras))


if __name__ == '__main__':
    unittest.main()
