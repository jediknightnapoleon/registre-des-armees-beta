"""Grouped 5-fold CV harness shared by all experiments.

Folds group on regular_unit_key (seed 0).  A model is either
  * a linear design: X = design(rows) and the target commander_price, fitted by
    OLS or LAD (median regression), or
  * a callable fit(train_idx) -> predict(idx) for nonlinear forms.
Every row stays in the reported error.  Predictions are clipped to >= 1
(the game never prices below 1 gold).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from load import load, col, group_folds, OUT, ROOT

ROWS = load()
Y = col(ROWS, "commander_price").astype(float)
FOLDS = group_folds(ROWS, 5, seed=0)
RESULTS_MD = ROOT / "RESULTS.md"
RESULTS_CSV = OUT / "results.csv"


def lad(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Least-absolute-deviation fit via linear programming (exact)."""
    n, p = X.shape
    # variables: beta+ (p), beta- (p), u (n), v (n); minimise sum(u+v)
    c = np.r_[np.zeros(2 * p), np.ones(2 * n)]
    A_eq = np.hstack([X, -X, np.eye(n), -np.eye(n)]) if n * (2 * p + 2 * n) < 4e8 else None
    if A_eq is None:
        raise ValueError("too large for dense LAD")
    res = linprog(c, A_eq=A_eq, b_eq=y, bounds=(0, None), method="highs")
    return res.x[:p] - res.x[p:2 * p]


def lad_sparse(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    from scipy import sparse
    n, p = X.shape
    c = np.r_[np.zeros(2 * p), np.ones(2 * n)]
    I = sparse.identity(n, format="csr")
    A_eq = sparse.hstack([sparse.csr_matrix(X), sparse.csr_matrix(-X), I, -I], format="csr")
    res = linprog(c, A_eq=A_eq, b_eq=y, bounds=(0, None), method="highs")
    return res.x[:p] - res.x[p:2 * p]


def fit_linear(X, y, method="ols"):
    if method == "ols":
        return np.linalg.lstsq(X, y, rcond=None)[0]
    return lad_sparse(X, y)


def metrics(pred, y=Y):
    ae = np.abs(pred - y)
    fold_mae = np.array([ae[FOLDS == f].mean() for f in range(5)])
    ape = ae / y * 100
    return dict(mae=float(fold_mae.mean()), sd=float(fold_mae.std(ddof=1)),
                se=float(fold_mae.std(ddof=1) / np.sqrt(5)), medape=float(np.median(ape)),
                fold_mae=fold_mae.round(2).tolist())


def cv_linear(X, method="ols", clip=True):
    pred = np.empty(len(Y))
    for f in range(5):
        tr = FOLDS != f
        b = fit_linear(X[tr], Y[tr], method)
        pred[~tr] = X[~tr] @ b
    if clip:
        pred = np.maximum(pred, 1)
    full = fit_linear(X, Y, method)
    return pred, full


def cv_custom(fit_fn, clip=True):
    """fit_fn(train_mask) -> (predict_fn(mask) -> array, params)."""
    pred = np.empty(len(Y))
    for f in range(5):
        tr = FOLDS != f
        predict, _ = fit_fn(tr)
        pred[~tr] = predict(~tr)
    if clip:
        pred = np.maximum(pred, 1)
    _, params = fit_fn(np.ones(len(Y), bool))
    return pred, params


def log_result(exp_id, name, k, m, notes="", params=None):
    new = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id", "model", "params", "cv_mae", "sd", "se", "median_ape", "fold_mae", "notes"])
        w.writerow([exp_id, name, k, f"{m['mae']:.2f}", f"{m['sd']:.2f}", f"{m['se']:.2f}",
                    f"{m['medape']:.2f}", json.dumps(m["fold_mae"]), notes])
    if not RESULTS_MD.exists():
        RESULTS_MD.write_text("# Results log\n\nOne row per experiment. CV = grouped 5-fold on "
                              "`regular_unit_key`, seed 0; all 5 238 rows scored; predictions clipped at >= 1.\n\n"
                              "| id | model | params | CV MAE | sd | median APE % | notes |\n"
                              "|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with open(RESULTS_MD, "a", encoding="utf-8") as f:
        f.write(f"| {exp_id} | {name} | {k} | {m['mae']:.2f} | {m['sd']:.2f} | {m['medape']:.2f} | {notes} |\n")
    if params is not None:
        with open(OUT / f"params_{exp_id}.json", "w", encoding="utf-8") as f:
            json.dump(params, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"{exp_id:6s} {name:60s} k={k:3d} MAE {m['mae']:7.2f} ± {m['sd']:5.2f}  medAPE {m['medape']:5.2f}%  {notes}")
