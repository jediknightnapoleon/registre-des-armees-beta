"""Exp 06 (diagnostic): is the premium tied to P or to an army-free stat value V?

V = exp(per-arm OLS of log P on regular stats, log men, flags) -- uses only regular
columns, never commander_price; fitted inside each training fold.
"""
from __future__ import annotations
import numpy as np
from harness import cv_custom, metrics, log_result, Y, fit_linear
from features import *
from load import FLAGS, col

FL = np.column_stack([col(ROWS, "regular_" + f).astype(float) for f in FLAGS])
Zr = np.column_stack([REG[k] for k in STATS] + [np.log(MEN_R), np.log(np.maximum(GUN_R, 1)), FL, ONE])
Dm = np.column_stack([D[k] for k in DSTATS])

def value(tr):
    V = np.empty(len(Y))
    for A in (INF, CAV, ART):
        m = A == 1
        b = np.linalg.lstsq(Zr[tr & m], np.log(P[tr & m]), rcond=None)[0]
        V[m] = np.exp(Zr[m] @ b)
    return V

def make(cols_fn):
    def fit_fn(tr):
        V = value(tr)
        X = cols_fn(V)
        b = fit_linear(X[tr], Y[tr], "lad")
        return (lambda m: X[m] @ b), {"coef": b}
    return fit_fn

base = lambda: [P, P * (SIZE - 1)]
armc = lambda: [INF, CAV, ART]
tests = {
  "V1": ("C = P + arm consts + V*dk", lambda V: np.column_stack([P, *armc(), V[:, None] * Dm, P * (SIZE - 1)])),
  "V2": ("C = P + arm consts + P*dk (compare)", lambda V: np.column_stack([P, *armc(), P[:, None] * Dm, P * (SIZE - 1)])),
  "V3": ("C = P + arm consts + V*dk + men*dk", lambda V: np.column_stack([P, *armc(), V[:, None] * Dm, MEN_C[:, None] * Dm, P * (SIZE - 1)])),
  "V4": ("C = aP + arm consts + V*arm + V*dk + men*dk", lambda V: np.column_stack([P, *armc(), V * INF, V * CAV, V * ART, V[:, None] * Dm, MEN_C[:, None] * Dm, P * (SIZE - 1)])),
  "V5": ("C = a_arm P + arm consts + V*arm + V*dk + men*dk + dk", lambda V: np.column_stack([P * INF, P * CAV, P * ART, *armc(), V * INF, V * CAV, V * ART, V[:, None] * Dm, MEN_C[:, None] * Dm, Dm, P * (SIZE - 1)])),
}
for eid, (nm, fn) in tests.items():
    p, prm = cv_custom(make(fn))
    log_result(eid, nm + " [lad]", len(prm["coef"]), metrics(p), notes="V=army-free stat value (diagnostic)")
