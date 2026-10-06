"""Exp 03: add unit size (men) and corps number to the per-arm star models."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result
from features import *

MEN = MEN_C  # commander unit size
LS = np.log(SIZE)
def per_arm(*fs):
    return np.column_stack([a * f for a in (INF, CAV, ART) for f in fs])
for meth in ["lad"]:
    X = per_arm(P, ONE, S, P * S, MEN, MEN * S)
    p, b = cv_linear(X, meth); log_result(f"M1{meth}", f"per arm: P(a+cs) + men(g+hs) + b + ds [{meth}]", 18, metrics(p), params=b)
    X = per_arm(P, ONE, S, P * S, MEN)
    p, b = cv_linear(X, meth); log_result(f"M2{meth}", f"per arm: P(a+cs) + g men + b + ds [{meth}]", 15, metrics(p), params=b)
    X = per_arm(P, ONE, S, P * S, MEN, MEN * S, P * (SIZE - 1))
    p, b = cv_linear(X, meth); log_result(f"M3{meth}", f"M1 + per-arm P*(size ratio-1) [{meth}]", 21, metrics(p), params=b)
    X = per_arm(P, ONE, S, P * S, P * (SIZE - 1))
    p, b = cv_linear(X, meth); log_result(f"M4{meth}", f"L4 + per-arm P*(size ratio-1) [{meth}]", 15, metrics(p), params=b)
    X = per_arm(P, ONE, S, P * S, MEN, MEN * S, P * (SIZE - 1), CORPS, P * CORPS)
    p, b = cv_linear(X, meth); log_result(f"M5{meth}", f"M3 + per-arm corps, P*corps [{meth}]", 27, metrics(p), params=b)
    X = per_arm(P, ONE, S, P * S, MEN, MEN * S, P * (SIZE - 1), S * CORPS)
    p, b = cv_linear(X, meth); log_result(f"M6{meth}", f"M3 + per-arm s*corps [{meth}]", 24, metrics(p), params=b)
