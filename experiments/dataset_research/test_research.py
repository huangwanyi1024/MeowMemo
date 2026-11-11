"""Small generated fixtures only; no dataset downloads, model initialization or owner media."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import soundfile as sf
from experiments.dataset_research.research import (parse_metadata, summarize, analyze,
    inspect_audio, validate_manifest, write_report, plot_report, validate_processed_audio)

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('meowmemo_existing_model', ROOT / 'work/meowmemo-local-ai/model.py')
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)
NAME = 'B_BRA01_MC_MN_SIM01_101.wav'


class AudioFixtures:

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def wav(self, name=NAME, samples=None, rate=8000, subtype='FLOAT'):
        path = self.root / name
        sf.write(path, np.linspace(-.3, .3, 800) if samples is None else samples, rate, subtype=subtype)
        return path


class ResearchTests(AudioFixtures, unittest.TestCase):
    def test_metadata(self):
        row = parse_metadata(NAME)
        self.assertEqual((row['label'], row['cat'], row['breed'], row['sex'], row['session']), ('brushing', 'BRA01', 'MC', 'MN', 1))
        self.assertEqual(parse_metadata('F_BRI01_MC_FI_SIM01_201.wav')['label'], 'food')
        self.assertEqual(parse_metadata('I_BRI01_MC_FI_SIM01_401.wav')['session'], 4)

    def test_malformed(self):
        for name in ['x.wav', NAME.replace('MC', 'XX'), NAME.replace('MN', 'MX'), NAME.replace('101', '100'), NAME.replace('101', '1SEQ1')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_metadata(name)

    def test_aggregation(self):
        rows = [dict(file=NAME, **parse_metadata(NAME)), dict(file=NAME, **parse_metadata(NAME))]
        result = summarize(rows)
        self.assertEqual(result['class_counts'], dict(brushing=2, food=0, isolation=0))
        self.assertEqual(result['cat_counts'], {'BRA01': 2})
        self.assertEqual(result['missing_classes'], {'BRA01': ['food', 'isolation']})
        self.assertIsNone(result['imbalance_max_min'])

    def test_empty(self):
        with self.assertRaisesRegex(ValueError, 'Empty dataset'):
            analyze(self.root)
        with self.assertRaisesRegex(ValueError, 'missing'):
            analyze(self.root / 'missing')
        self.assertFalse(validate_manifest({})['valid'])
        self.assertEqual(summarize([])['recordings'], 0)

    def test_audio_quality(self):
        self.wav()
        (self.root / 'broken.wav').write_bytes(b'not audio')
        self.wav('F_BRA01_MC_MN_SIM01_101.wav', np.zeros((30, 2)), 16000)
        report = analyze(self.root)
        self.assertEqual(report['summary']['recordings'], 3)
        self.assertEqual(report['summary']['issue_counts']['unreadable_audio'], 1)
        self.assertEqual(report['summary']['issue_counts']['sample_rate'], 1)
        self.assertEqual(report['summary']['issue_counts']['channels'], 1)

    def test_duplicates_and_identity(self):
        self.wav()
        self.wav('F_BRA01_EU_FN_SIM01_101.wav')
        report = analyze(self.root)
        self.assertEqual(len(report['summary']['suspicious_pcm_duplicates']), 1)
        self.assertEqual(report['summary']['inconsistent_cat_metadata'], ['BRA01'])

    def test_invalid_samples(self):
        for samples, issue in [(np.array([]), 'empty_audio'), (np.array([np.nan, np.inf]), 'nonfinite_audio')]:
            path = self.wav(samples=samples)
            self.assertTrue(any(s.startswith(issue) for s in inspect_audio(path)[1]))

    def test_manifest_leakage(self):
        result = validate_manifest({'development': [{'file': NAME, 'label': 'food', 'cat': 'WRONG', 'noise_source': 'original-1'}], 'test': [{'file': NAME, 'noise_source': 'original-1'}]}, self.root)
        for message in ['cat leakage', 'noise source leakage', 'duplicate file', 'incorrect label', 'incorrect cat', 'missing label', 'unreadable_audio']:
            self.assertIn(message, '\n'.join(result['issues']))

    def test_valid_manifest(self):
        self.wav()
        result = validate_manifest({'development': [NAME]}, self.root)
        self.assertTrue(result['valid'], result['issues'])
        self.assertTrue(result['audio_checked'])
        self.assertFalse(validate_manifest({'development': [NAME]})['audio_checked'])

    def test_bad_manifest(self):
        result = validate_manifest({'test': [{}, '../escape.wav', 'invalid.mp3']})
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['issues']), 3)
        with self.assertRaises(ValueError):
            validate_manifest({'test': 'not-list'})

    def test_reproducible_reports(self):
        self.wav()
        report = analyze(self.root)
        write_report(report, self.root / 'one')
        write_report(report, self.root / 'two')
        for name in ('report.json', 'recordings.csv'):
            self.assertEqual((self.root / 'one' / name).read_bytes(), (self.root / 'two' / name).read_bytes())
        self.assertEqual(json.loads((self.root / 'one/report.json').read_text()), report)

    def test_processed_output_contract(self):
        self.assertEqual(validate_processed_audio(np.zeros(8), 16000, expected_frames=8), [])
        for samples in [[], [np.nan], [np.inf], [[0, 1]], ['bad'], [1j]]:
            with self.subTest(samples=samples):
                self.assertTrue(validate_processed_audio(samples, 16000))
        self.assertTrue(validate_processed_audio(np.zeros(8), 8000))
        self.assertTrue(validate_processed_audio(np.zeros(8), 16000, expected_frames=9))

    def test_session_documentation_discrepancy(self):
        result = validate_manifest({'test': ['I_BLE01_EU_FN_DEL01_401.wav']})
        self.assertFalse(result['valid'])
        self.assertIn('session outside published range', result['issues'][0])

    def test_unsupported_format(self):
        path = self.root / 'clip.mp3'
        path.write_bytes(b'bad')
        self.assertTrue(any(x.startswith('unsupported_format') for x in inspect_audio(path)[1]))

    def test_synthetic_plots(self):
        self.wav()
        plot_report(analyze(self.root), self.root / 'plots', synthetic=True)
        self.assertEqual(len(list((self.root / 'plots').glob('*.png'))), 5)
        self.assertTrue(all(p.stat().st_size > 1000 for p in (self.root / 'plots').glob('*.png')))


class ExistingPreprocessingTests(AudioFixtures, unittest.TestCase):
    def test_resampling_and_mono(self):
        signal = .25 * np.sin(2*np.pi*440*np.arange(8000)/8000)
        path = self.wav(samples=np.column_stack([signal, signal]))
        output = model.read_audio(path)
        self.assertEqual(output.shape, (16000,))
        self.assertEqual(output.dtype, np.float32)
        frequency = np.fft.rfftfreq(len(output), 1/16000)[np.argmax(np.abs(np.fft.rfft(output)))]
        self.assertAlmostEqual(frequency, 440, delta=1)
        self.assertTrue(np.isfinite(output).all())

    def test_empty_and_nonfinite_rejected(self):
        for samples in [np.array([]), np.array([np.nan]), np.array([np.inf])]:
            with self.subTest(samples=samples), self.assertRaisesRegex(ValueError, 'No valid audio'):
                model.read_audio(self.wav(samples=samples))

    def test_short_silence_and_normalization(self):
        for samples in [np.zeros(1), np.zeros(800), np.array([1e-20]), np.array([.5])]:
            features = model.mfcc_features(model.read_audio(self.wav(samples=samples)))
            self.assertEqual(features.shape, (100,))
            self.assertTrue(np.isfinite(features).all())
        samples = np.linspace(-.2, .2, 800)
        np.testing.assert_allclose(model.mfcc_features(samples), model.mfcc_features(samples*2), atol=1e-5)

    def test_no_implicit_trim_or_gain(self):
        samples = np.r_[np.zeros(100), np.ones(100)*.2, np.zeros(100)]
        output = model.read_audio(self.wav(samples=samples, rate=16000))
        np.testing.assert_array_equal(output, samples.astype('float32'))

    def test_training_inference_shared_reader(self):
        # Verify actual predict_file dispatch without loading TensorFlow or classifier.
        instance = object.__new__(model.AudioModel)
        path = self.wav()
        expected = model.read_audio(path)
        with patch.object(instance, 'predict_samples', side_effect=lambda x: x):
            np.testing.assert_array_equal(instance.predict_file(path), expected)
        # Training imports this same reader, rather than an independent preprocessing path.
        import ast
        tree = ast.parse((ROOT / 'work/meowmemo-local-ai/train.py').read_text())
        imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == 'model']
        self.assertTrue(any(a.name == 'read_audio' for n in imports for a in n.names))


if __name__ == '__main__':
    unittest.main()
