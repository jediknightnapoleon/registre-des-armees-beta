"""CV harness: given folds, out-of-fold predictions, per-arm metric reporting.

``run_cv(fit_predict, d)`` calls ``fit_predict(train_idx, test_idx)`` for each
outer fold k = 1..5 where train = rows with fold != k (including the
always-train rows with an empty fold) and test = rows with fold == k.
It returns the out-of-fold prediction vector (NaN for never-scored rows).
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from common import ARM_OF_CLASS, Data, fold_metrics, fmt_fm, append_results

ARMS = ["infantry", "cavalry", "artillery"]


def fold_vec(d: Data) -> np.ndarray:
    return np.array([int(v) if v != "" else 0 for v in d.s("fold")])


def arm_vec(d: Data) -> np.ndarray:
    return np.array([ARM_OF_CLASS[c] for c in d.s("unit_class")])


def run_cv(fit_predict: Callable[[np.ndarray, np.ndarray], np.ndarray], d: Data,
           rows: np.ndarray | None = None) -> np.ndarray:
    """rows: optional boolean mask restricting which rows take part at all."""
    fold = fold_vec(d)
    n = len(d)
    if rows is None:
        rows = np.ones(n, dtype=bool)
    pred = np.full(n, np.nan)
    for k in range(1, 6):
        tr = np.where(rows & (fold != k))[0]
        te = np.where(rows & (fold == k))[0]
        if len(te) == 0:
            continue
        pred[te] = fit_predict(tr, te)
    return pred


def report(name: str, d: Data, y: np.ndarray, pred: np.ndarray, desc: str = "",
           params: str = "", note: str = "", log: bool = True,
           segments: list[str] | None = None) -> dict[str, dict]:
    fold = fold_vec(d)
    arm = arm_vec(d)
    segs = segments if segments is not None else ARMS + ["overall"]
    out = {}
    for seg in segs:
        mask = (arm == seg) if seg in ARMS else np.ones(len(d), dtype=bool)
        mask = mask & (fold > 0) & np.isfinite(pred)
        if mask.sum() == 0:
            continue
        fm = fold_metrics(y, pred, fold, mask)
        out[seg] = fm
        print(f"  {name:10s} {seg:10s} {fmt_fm(fm)}")
        if log:
            append_results([name, desc, seg, f"{fm['mae'][0]:.1f} ± {fm['mae'][1]:.1f}",
                            f"{fm['mape'][0]:.2f}", f"{fm['r2'][0]:.4f}", params, note])
    return out
