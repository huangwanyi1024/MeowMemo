"""H2 evaluation: leave-one-cat-out testing and a cat-level bootstrap. No TensorFlow import."""
import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import LeaveOneGroupOut
from train import pipeline, metrics, LABELS

# Fixed for every variant so differences come from preprocessing alone (deployed settings).
CLASSIFIER_C = 1.0
CLASSIFIER_KIND = 'logistic'


def evaluate_unseen_cats(x_train, x_test, y, groups):
    """Each cat takes one turn as the unseen test cat.

    `x_train` holds the features the model learns from (clean audio) and `x_test` the
    features it is scored on (clean or noisy). Row i of both must be the same clip.
    Returns (metrics dict, out-of-fold predictions).
    """
    x_train, x_test = np.asarray(x_train), np.asarray(x_test)
    y, groups = np.asarray(y), np.asarray(groups)
    assert x_train.shape == x_test.shape and len(x_train) == len(y) == len(groups)
    pred = np.empty(len(y), dtype=object)
    for tr, te in LeaveOneGroupOut().split(x_train, y, groups):
        assert not set(groups[tr]) & set(groups[te])
        clf = pipeline(CLASSIFIER_C, CLASSIFIER_KIND).fit(x_train[tr], y[tr])
        pred[te] = clf.predict(x_test[te])
    pred = pred.astype(str)
    result = metrics(y, pred)
    result['per_cat_accuracy'] = per_cat_accuracy(y, pred, groups)
    return result, pred


def per_cat_accuracy(y, pred, groups):
    cats = np.unique(groups)
    acc = {str(c): float(np.mean(pred[groups == c] == y[groups == c])) for c in cats}
    values = np.array(list(acc.values()))
    return {'min': float(values.min()), 'median': float(np.median(values)),
            'max': float(values.max()), 'by_cat': acc}


def macro_f1(y, pred):
    return float(f1_score(y, pred, labels=LABELS, average='macro', zero_division=0))


def bootstrap_gain(y, pred_base, pred_new, groups, n=1000, seed=42):
    """95% interval for macro-F1(new) minus macro-F1(base), resampling whole cats.

    Cats, not clips, are resampled because clips from one cat are not independent.
    """
    y, groups = np.asarray(y), np.asarray(groups)
    pred_base, pred_new = np.asarray(pred_base), np.asarray(pred_new)
    rng = np.random.default_rng(seed)
    cats = np.unique(groups)
    index = {c: np.flatnonzero(groups == c) for c in cats}
    gains = np.empty(n)
    for i in range(n):
        idx = np.concatenate([index[c] for c in rng.choice(cats, len(cats))])
        gains[i] = macro_f1(y[idx], pred_new[idx]) - macro_f1(y[idx], pred_base[idx])
    low, high = np.percentile(gains, [2.5, 97.5])
    return {'gain': macro_f1(y, pred_new) - macro_f1(y, pred_base),
            'ci95': [float(low), float(high)], 'supported': bool(low > 0), 'resamples': n}
