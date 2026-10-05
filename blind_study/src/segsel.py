"""Per-segment stage-1 evaluation and greedy feature selection (regular units)."""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import TARGET  # noqa
from linmodels import JointLogLinear  # noqa


def fit_seg(tr, spec, lam=1e-5, lam_f=1e-4, weight="price", irls=10):
    return JointLogLinear(lambda d: np.full(len(d), "s", dtype=object), {"s": spec},
                          use_n=True, lam_f=lam_f, lam=lam, faction_col="army_seg",
                          weight=weight, irls=irls).fit(tr)


def seg_cv_mae(d, spec, folds, **kw):
    """d: regular rows of one segment (with 'fold'); MAE over rows in `folds` (out of fold)."""
    err = []
    for k in folds:
        tr, te = d[(d.fold != k) & (d.fold.isin(folds))], d[d.fold == k]
        tr = tr[tr[TARGET] >= 50]
        p = fit_seg(tr, spec, **kw).predict(te)
        err.append(np.abs(p - te[TARGET].values))
    return np.concatenate(err).mean()


def name_of(t):
    return t if isinstance(t, str) else (t[0] + ":" + t[1] if t[0] == "cat" else t[0])


def forward_select(d, core, pool, folds, max_terms=40, min_gain=0.002, log=None, **kw):
    """Greedy forward selection starting from `core`, adding terms from `pool` while the
    relative MAE gain >= min_gain and the coefficient count stays <= max_terms."""
    sel = list(core)
    best = seg_cv_mae(d, sel, folds, **kw)
    remaining = list(pool)
    while remaining:
        scores = []
        for t in remaining:
            scores.append((seg_cv_mae(d, sel + [t], folds, **kw), t))
        scores.sort(key=lambda x: x[0])
        s, t = scores[0]
        if s > best * (1 - min_gain):
            break
        cand = sel + [t]
        if n_coef(d, cand) > max_terms:
            remaining.remove(t)
            continue
        sel, best = cand, s
        remaining.remove(t)
        if log:
            log(f"  + {name_of(t):28s} MAE {best:.2f}  coefs {n_coef(d, sel)}")
    return sel, best


def n_coef(d, spec):
    m = fit_seg(d[d[TARGET] >= 50], spec, irls=0)
    nz = [c for c in m.cols if not c.startswith("fac:")]
    X_sd = m.sd  # columns with zero variance get coefficient ~0; count only varying ones
    return sum(1 for j, c in enumerate(m.cols) if not c.startswith("fac:")
               and (c.endswith(":const") or abs(m.coef[c]) > 1e-12))


def backward_prune(d, spec, folds, tol=0.001, protect=(), log=None, **kw):
    """Greedy backward elimination: repeatedly drop the term whose removal gives the lowest
    MAE, as long as that MAE <= current * (1 + tol)."""
    sel = list(spec)
    best = seg_cv_mae(d, sel, folds, **kw)
    while True:
        cands = [t for t in sel if name_of(t) not in protect]
        if not cands:
            break
        scores = [(seg_cv_mae(d, [u for u in sel if u is not t], folds, **kw), t) for t in cands]
        scores.sort(key=lambda x: x[0])
        s, t = scores[0]
        if s > best * (1 + tol):
            break
        sel = [u for u in sel if u is not t]
        best = min(best, s) if s <= best else s
        if log:
            log(f"  - {name_of(t):28s} MAE {s:.2f}")
    return sel, best


def select_segment(d, base, pool, folds, max_terms=40, log=None, **kw):
    """Prune `base` (drops constant/useless terms), then forward-add from `pool`."""
    # drop terms that are constant in this segment first (no information, cheap)
    tr = d[d[TARGET] >= 50]
    base = [t for t in base if _varies(tr, t)]
    pool = [t for t in pool if _varies(tr, t)]
    sel, m1 = backward_prune(d, base, folds, log=log, **kw)
    sel, m2 = forward_select(d, sel, pool, folds, max_terms=max_terms, min_gain=0.005,
                             log=log, **kw)
    return sel, m2


def _varies(df, t):
    from linmodels import design
    X = design(df, [t])
    return X.shape[1] > 0 and (X.std() > 0).any()
