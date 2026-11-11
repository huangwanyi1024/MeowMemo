"""Tests for h2_data_checks.py. No TensorFlow, CatMeows download or network needed:
python test_h2_data_checks.py
"""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
import h2_preprocessing as pre
import h2_data_checks as checks

SR = pre.SR


def tone(seconds, freq=600, amp=0.3):
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def padded(meow_seconds, silence_seconds):
    pad = np.zeros(int(silence_seconds * SR), dtype=np.float32)
    return np.concatenate([pad, tone(meow_seconds), pad])


def synthetic_set(length_for, n_cats=8, per_class=4):
    """Clips from several cats; `length_for(label, rng)` returns (meow s, silence s)."""
    rng = np.random.default_rng(0)
    audios, y, groups = [], [], []
    for cat in range(n_cats):
        for label in checks.LABELS:
            for _ in range(per_class):
                meow, silence = length_for(label, rng)
                audios.append(padded(meow, silence))
                y.append(label)
                groups.append(f'CAT{cat:02d}')
    return audios, np.array(y), np.array(groups)


class NoiseFolderTests(unittest.TestCase):
    def test_reads_esc50_class_from_filename(self):
        self.assertEqual(checks.esc50_class('5-259169-A-5.wav'), 5)
        self.assertEqual(checks.esc50_class('1-100038-A-14.wav'), 14)
        self.assertIsNone(checks.esc50_class('kitchen_noise.wav'))
        self.assertIsNone(checks.esc50_class('B_ANI01_MC_FN_SIM01_101.wav'))

    def test_flags_animal_clips_and_unknown_files(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ['5-259169-A-5.wav', '1-30226-A-0.wav', '1-115545-A-35.wav', 'kitchen.wav']:
                sf.write(Path(d) / name, tone(0.5), SR)
            report = checks.check_noise_folder(d)
        self.assertEqual(report['files'], 4)
        self.assertEqual(sorted(a['class'] for a in report['animal_files']), ['cat', 'dog'])
        self.assertEqual(report['not_esc50'], ['kitchen.wav'])
        self.assertEqual(report['sample_rates'], {str(SR): 4})

    def test_clean_household_pool_passes(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ['1-115545-A-35.wav', '2-109505-A-36.wav']:  # washing machine, vacuum
                sf.write(Path(d) / name, tone(0.5), SR)
            self.assertEqual(checks.check_noise_folder(d)['animal_files'], [])


class ShortcutTests(unittest.TestCase):
    def test_detects_length_that_differs_by_situation(self):
        # Isolation meows are much longer: length alone should predict it on unseen cats.
        def lengths(label, rng):
            return (3.0 if label == 'isolation' else 1.0) + rng.uniform(0, 0.2), 0.5
        audios, y, groups = synthetic_set(lengths)
        r = checks.shortcut_check(audios, y, groups, SR, pre.trim_silence, n_permutations=100)
        self.assertTrue(r['original_length']['length_predicts_situation'])
        self.assertTrue(r['warning'])

    def test_no_warning_when_length_is_unrelated(self):
        def lengths(label, rng):
            return 1.5 + rng.uniform(0, 1.0), 0.5
        audios, y, groups = synthetic_set(lengths)
        r = checks.shortcut_check(audios, y, groups, SR, pre.trim_silence, n_permutations=100)
        self.assertFalse(r['original_length']['length_predicts_situation'])
        self.assertFalse(r['trimmed_length']['length_predicts_situation'])
        self.assertFalse(r['warning'])

    def test_detects_shortcut_created_by_trimming(self):
        # Same total length, but food clips are mostly silence: only trimming exposes it.
        def lengths(label, rng):
            meow = (1.0 if label == 'food' else 3.0) + rng.uniform(0, 0.2)
            return meow, (4.0 - meow) / 2
        audios, y, groups = synthetic_set(lengths)
        r = checks.shortcut_check(audios, y, groups, SR, pre.trim_silence, n_permutations=100)
        self.assertFalse(r['original_length']['length_predicts_situation'])
        self.assertTrue(r['trimmed_length']['length_predicts_situation'])
        self.assertGreater(r['removed_by_trim_seconds']['food'], r['removed_by_trim_seconds']['brushing'])
        self.assertTrue(r['warning'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
