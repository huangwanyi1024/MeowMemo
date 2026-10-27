"""Reproducible cat-held-out training. Test cats never used to select C/threshold."""
import json
import hashlib
import time
from collections import Counter
from pathlib import Path
import numpy as np
import joblib
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
from model import AudioModel, read_audio, mfcc_features, ROOT, ARTIFACTS, MODEL_VERSION, LABELS


def pipeline(c, kind='logistic'):
    estimator = (SVC(C=c, kernel='rbf', class_weight='balanced', probability=True, random_state=42)
                 if kind == 'svm' else LogisticRegression(C=c, class_weight='balanced', max_iter=2000, random_state=42))
    return make_pipeline(StandardScaler(), estimator)


def metrics(y, pred):
    return {'accuracy': float(accuracy_score(y, pred)),
            'macro_f1': float(f1_score(y, pred, labels=LABELS, average='macro', zero_division=0)),
            'confusion_matrix': confusion_matrix(y, pred, labels=LABELS).tolist(),
            'per_class': classification_report(y, pred, labels=LABELS, output_dict=True, zero_division=0)}


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    files = sorted((ROOT / 'data' / 'catmeows').glob('*.wav'))
    assert len(files) == 440, 'Download and extract CatMeows first.'
    labels = {'B': 'brushing', 'F': 'food', 'I': 'isolation'}
    y = np.array([labels[p.name.split('_')[0]] for p in files])
    groups = np.array([p.name.split('_')[1] for p in files])
    names = [p.name for p in files]
    encoder = AudioModel(classifier=False)
    cache = ARTIFACTS / 'embeddings.npz'
    if cache.exists():
        saved = np.load(cache)
        assert saved['files'].tolist() == names
        x, cat_scores = saved['features'], saved['cat_scores']
    else:
        features, cat_scores = [], []
        for i, p in enumerate(files):
            v, score, _ = encoder.extract(read_audio(p))
            features.append(v); cat_scores.append(score)
            if i % 50 == 0:
                print(f'Embedding {i + 1}/{len(files)}', flush=True)
        x = np.array(features)
        cat_scores = np.array(cat_scores)
        np.savez_compressed(cache, features=x, cat_scores=cat_scores, files=names)
    # One deterministic split chosen before inspecting test results; no random clip split.
    dev, test = next(GroupShuffleSplit(n_splits=1, test_size=.24, random_state=42).split(x, y, groups))
    assert not set(groups[dev]) & set(groups[test])
    folds = list(StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42).split(x[dev], y[dev], groups[dev]))
    mfcc = np.array([mfcc_features(read_audio(p)) for p in files])
    feature_sets = {'yamnet': x, 'mfcc': mfcc, 'combined': np.concatenate([x, mfcc], axis=1)}
    candidates = []
    configurations = [(mode, kind, c) for mode in feature_sets for kind, cs in
                      [('logistic', (.01, .1, 1.0)), ('svm', (1., 10.))] for c in cs]
    for mode, kind, c in configurations:
        feature_x = feature_sets[mode]
        oof = np.zeros((len(dev), 3))
        for tr, va in folds:
            assert not set(groups[dev][tr]) & set(groups[dev][va])
            clf = pipeline(c, kind).fit(feature_x[dev][tr], y[dev][tr])
            assert list(clf.classes_) == LABELS
            oof[va] = clf.predict_proba(feature_x[dev][va])
        score = metrics(y[dev], np.array(LABELS)[oof.argmax(axis=1)])
        candidates.append((score['macro_f1'], mode, kind, c, oof, score))
        print('Development group-CV', mode, kind, c, score['macro_f1'], flush=True)
    _, best_mode, best_kind, best_c, oof, dev_metrics = max(candidates, key=lambda row: row[0])
    x = feature_sets[best_mode]
    # Cat gate is a provisional heuristic, not an evaluated universal cat detector.
    # Context threshold selected using development OOF only, never test labels.
    threshold = .60
    threshold_search = []
    for t in (.50, .55, .60, .65, .70, .75, .80):
        ordered = np.sort(oof, axis=1)
        mask = (oof.max(axis=1) >= t) & ((ordered[:, -1] - ordered[:, -2]) >= .15) & (cat_scores[dev] >= .10)
        n = int(mask.sum())
        acc = float(accuracy_score(y[dev][mask], np.array(LABELS)[oof[mask].argmax(axis=1)])) if n else None
        threshold_search.append({'threshold': t, 'coverage': n / len(dev), 'accuracy': acc})
    eligible = [r for r in threshold_search if r['accuracy'] is not None and r['accuracy'] >= .75 and r['coverage'] >= .25]
    if eligible:
        threshold = max(eligible, key=lambda r: r['coverage'])['threshold']
    thresholds = {'context': threshold, 'margin': .15, 'cat_event': .10, 'silence_rms': .0001}
    clf = pipeline(best_c, best_kind).fit(x[dev], y[dev])
    pred_probs = clf.predict_proba(x[test])
    pred = clf.predict(x[test])
    ordered = np.sort(pred_probs, axis=1)
    accepted = (pred_probs.max(axis=1) >= threshold) & ((ordered[:, -1] - ordered[:, -2]) >= .15) & (cat_scores[test] >= .10)
    heldout = metrics(y[test], pred)
    majority = Counter(y[dev]).most_common(1)[0][0]
    report = {'model_version': MODEL_VERSION, 'dataset': 'CatMeows 1.0.2 / 10.5281/zenodo.4008297',
              'sample_count': len(files), 'cat_count': len(set(groups)), 'labels': LABELS,
              'class_counts': dict(Counter(y)), 'split_seed': 42,
              'development_cats': sorted(set(groups[dev])), 'test_cats': sorted(set(groups[test])),
              'development_samples': len(dev), 'test_samples': len(test),
              'selected_C': best_c, 'feature_mode': best_mode, 'classifier_kind': best_kind, 'development_group_cv': dev_metrics,
              'candidate_group_cv': [{'features': mode, 'classifier': kind, 'C': c, 'macro_f1': f} for f, mode, kind, c, _, _ in candidates],
              'threshold_search_development_only': threshold_search, 'thresholds': thresholds,
              'heldout_test_before_abstention': heldout,
              'majority_baseline_test': metrics(y[test], np.repeat(majority, len(test))),
              'heldout_test_with_abstention': {'accepted': int(accepted.sum()), 'total': len(test),
                  'coverage': float(accepted.mean()),
                  'accuracy_on_accepted': float(accuracy_score(y[test][accepted], pred[accepted])) if accepted.any() else None},
              'test_predictions': [{'file': files[i].name, 'cat': str(groups[i]), 'actual': str(y[i]),
                 'predicted': str(pred[j]), 'accepted': bool(accepted[j]),
                 'scores': {c: float(p) for c, p in zip(LABELS, pred_probs[j])}}
                 for j, i in enumerate(test)],
              'warning': 'Exploratory baseline comparison after seeing v1 test failure; same test partition reused, not a pristine final benchmark. Model/threshold selected by development group-CV only. Scores not calibrated. Not tested on owner cats.'}
    joblib.dump({'classifier': clf, 'feature_mode': best_mode, 'classifier_kind': best_kind,
                 'thresholds': thresholds, 'model_version': MODEL_VERSION,
                 'test_cats_excluded_from_training': report['test_cats']}, ARTIFACTS / 'classifier.joblib')
    (ARTIFACTS / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (ARTIFACTS / 'split.json').write_text(json.dumps({'development': [names[i] for i in dev], 'test': [names[i] for i in test]}, indent=2))
    print(json.dumps({k: report[k] for k in ['selected_C', 'development_samples', 'test_samples',
          'test_cats', 'heldout_test_before_abstention', 'heldout_test_with_abstention']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
