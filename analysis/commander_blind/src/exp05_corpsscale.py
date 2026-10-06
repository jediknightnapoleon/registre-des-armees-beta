"""Exp 05: premium terms scaled by a corps factor (1 + lam*(corps-9)), lam chosen on train folds."""
from __future__ import annotations
import numpy as np
from harness import cv_custom, metrics, log_result, Y, fit_linear
from features import *

Dm = np.column_stack([D[k] for k in DSTATS])
LSZ = SIZE - 1
LAMS = np.round(np.arange(-0.16, 0.021, 0.02), 3)

def make(build):
    def fit_fn(tr):
        best = None
        for lam in LAMS:
            X = build(lam)
            b = fit_linear(X[tr], Y[tr], "lad")
            err = np.mean(np.abs(Y[tr] - X[tr] @ b))
            if best is None or err < best[0]:
                best = (err, lam, b)
        _, lam, b = best
        X = build(lam)
        return (lambda m: X[m] @ b), {"lam": lam, "coef": b}
    return fit_fn

def b1(lam):
    F = 1 + lam * (CORPS - 9)
    return np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * LSZ,
                            F[:, None] * MEN_C[:, None] * Dm, P[:, None] * Dm])
def b2(lam):
    F = 1 + lam * (CORPS - 9)
    return np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * LSZ,
                            F[:, None] * MEN_C[:, None] * Dm, F[:, None] * Dm, P[:, None] * Dm])
def b3(lam):
    F = 1 + lam * (CORPS - 9)
    return np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * LSZ,
                            F[:, None] * MEN_C[:, None] * Dm, F[:, None] * Dm])
for eid, nm, bld, k in [("F1", "arm a,b + P(size-1) + F*men*dk + P*dk", b1, 20),
                        ("F2", "arm a,b + P(size-1) + F*men*dk + F*dk + P*dk", b2, 26),
                        ("F3", "arm a,b + P(size-1) + F*men*dk + F*dk", b3, 20)]:
    p, prm = cv_custom(make(bld))
    log_result(eid, nm + ", F=1+lam(corps-9) [lad]", k, metrics(p), notes=f"lam={prm['lam']}", params=prm)
