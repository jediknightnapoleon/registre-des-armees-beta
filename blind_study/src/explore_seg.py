"""Exploration helper: CV a single-segment LogLinear (with army dummies) for feature sets."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, TARGET  # noqa
from features import add_features, is_excluded  # noqa
from linmodels import LogLinear  # noqa

DEV = None


def get_dev():
    global DEV
    if DEV is None:
        d = add_features(load_dev())
        DEV = d[~is_excluded(d)].reset_index(drop=True)
    return DEV


def cv_seg(seg, spec, cvflag=None, alpha=1e-4, lowcut=50, army=True, verbose=False, d=None):
    d = get_dev() if d is None else d
    d = d[d["seg"] == seg]
    if cvflag is not None:
        d = d[d["is_commander_variant"] == cvflag]
    full = spec + ([("cat", "faction_key")] if army else [])
    maes, lsds = [], []
    oof = pd.Series(np.nan, index=d.index)
    for k in range(5):
        tr, te = d[(d.fold != k) & (d[TARGET] >= lowcut)], d[d.fold == k]
        m = LogLinear(full, alpha=alpha)
        # offset by N/10 is absorbed by army dummies
        p = m.fit(tr).predict(te)
        oof[te.index] = p
    ae = (oof - d[TARGET]).abs()
    lr = np.log(oof / d[TARGET])
    return ae.mean(), lr[d[TARGET] >= lowcut].std(), oof
