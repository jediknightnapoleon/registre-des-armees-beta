"""Exp 17: fully per-arm J8 (all premium coefficients per arm)."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *
dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
cols = []
for A in (INF, CAV, ART):
    for f in (P, ONE, P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, P * (SIZE - 1)):
        cols.append(A * f)
X = np.column_stack(cols); X = X[:, np.abs(X).sum(0) > 0]
p, b = cv_linear(X, "lad"); log_result("W1", "J8 fully per arm [lad]", X.shape[1], metrics(p), params=b)
# per-arm with star lookups (stars capped at 5) instead of deltas, plus men*dmo and corps*s and size
cols = []
for A in (INF, CAV, ART):
    for k in range(6):
        Sk = (np.minimum(S, 5) == k).astype(float)
        cols += [A * Sk * P, A * Sk]
    cols += [A * MEN_R * dmo, A * CORPS * S, A * P * (SIZE - 1)]
X = np.column_stack(cols); X = X[:, np.abs(X).sum(0) > 0]
p, b = cv_linear(X, "lad"); log_result("W2", "arm x star lookup (a,b) + men*dmo + corps*s + size, per arm [lad]", X.shape[1], metrics(p), params=b)
