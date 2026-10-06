"""Exp 01: baselines and star/arm structures."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y, FOLDS
from features import *

print("fold sizes", np.bincount(FOLDS))
# B0: C = P
m = metrics(np.maximum(P, 1)); log_result("B0", "C = P (no change)", 0, m)
m = metrics(np.full(len(Y), np.median(Y))); log_result("B00", "C = global median", 1, m)
for meth in ["ols", "lad"]:
    X = np.c_[P, ONE]; p, b = cv_linear(X, meth); log_result(f"L1{meth}", f"C = a P + b [{meth}]", 2, metrics(p), params=b)
    X = np.c_[P, ONE, S, P * S]; p, b = cv_linear(X, meth)
    log_result(f"L2{meth}", f"C = P(a + c s) + b + d s [{meth}]", 4, metrics(p), params=b)
    X = np.c_[P, ONE, S, P * S, S**2, P*S**2]; p, b = cv_linear(X, meth)
    log_result(f"L3{meth}", f"C = P(a + c s + e s^2) + b + d s + f s^2 [{meth}]", 6, metrics(p), params=b)
    # per arm linear in stars
    X = np.column_stack([a * f for a in (INF, CAV, ART) for f in (P, ONE, S, P * S)])
    p, b = cv_linear(X, meth); log_result(f"L4{meth}", f"per arm: C = P(a + c s) + b + d s [{meth}]", 12, metrics(p), params=b)
    # star lookup (pool 6,7) global
    Sl = np.minimum(S, 6)
    X = np.column_stack([(Sl == k) * f for k in range(7) for f in (P, ONE)])
    p, b = cv_linear(X, meth); log_result(f"L5{meth}", f"star lookup: C = a_s P + b_s (s<=6) [{meth}]", 14, metrics(p), params=b)
    # star lookup x arm (pool >=5)
    Sl = np.minimum(S, 5)
    X = np.column_stack([(Sl == k) * a * f for a in (INF, CAV, ART) for k in range(6) for f in (P, ONE)])
    keep = X.any(0); X = X[:, keep]
    p, b = cv_linear(X, meth); log_result(f"L6{meth}", f"arm x star lookup (s<=5): C = a P + b [{meth}]", int(keep.sum()), metrics(p), params=b)
