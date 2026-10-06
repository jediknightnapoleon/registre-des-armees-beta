"""Exp 02: stat-change models (deltas) vs stars."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result
from features import *

DK = DSTATS
Dm = np.column_stack([D[k] for k in DK])
for meth in ["ols", "lad"]:
    # multiplicative deltas only + constant offset
    X = np.c_[P, ONE, P[:, None] * Dm]
    p, b = cv_linear(X, meth); log_result(f"D1{meth}", f"C = P(a + sum w_k dk) + b [{meth}]", 2 + 6, metrics(p), params=b)
    X = np.c_[P, ONE, P[:, None] * Dm, Dm]
    p, b = cv_linear(X, meth); log_result(f"D2{meth}", f"C = P(a + sum w_k dk) + b + sum v_k dk [{meth}]", 2 + 12, metrics(p), params=b)
    # arm-specific intercept/slope + deltas
    X = np.c_[P * INF, P * CAV, P * ART, INF, CAV, ART, P[:, None] * Dm, Dm]
    p, b = cv_linear(X, meth); log_result(f"D3{meth}", f"arm a,b + P*w dk + v dk [{meth}]", 6 + 12, metrics(p), params=b)
    # stars + deltas
    X = np.c_[P * INF, P * CAV, P * ART, INF, CAV, ART, P * S * INF, P * S * CAV, P * S * ART, S * INF, S * CAV, S * ART, P[:, None] * Dm, Dm]
    p, b = cv_linear(X, meth); log_result(f"D4{meth}", f"per-arm star model L4 + deltas (P*dk, dk) [{meth}]", 24, metrics(p), params=b)
    # relative deltas: dk / regular_k
    rel = np.column_stack([D[k] / np.maximum(REG[k], 1) for k in DK])
    X = np.c_[P, ONE, P[:, None] * rel, S]
    p, b = cv_linear(X, meth); log_result(f"D5{meth}", f"C = P(a + sum w_k dk/reg_k) + b + c s [{meth}]", 9, metrics(p), params=b)
    X = np.c_[P * INF, P * CAV, P * ART, INF, CAV, ART, P[:, None] * rel, rel, S]
    p, b = cv_linear(X, meth); log_result(f"D6{meth}", f"arm a,b + rel deltas (P*, plain) + s [{meth}]", 6 + 12 + 1, metrics(p), params=b)
