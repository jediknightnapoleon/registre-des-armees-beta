"""Exp 09: multiplicative (exponential) premium forms, robust soft-L1 fits."""
from __future__ import annotations
import numpy as np
from harness import cv_custom, metrics, log_result, Y
from features import *
from nl import nl_fit_fn

Dm = np.column_stack([D[k] for k in DSTATS])
A3 = np.column_stack([INF, CAV, ART])
nk = Dm.shape[1]

def f1(th, m):
    # C = P*exp(arm + b.dk) * ratio^g_arm + men*(v.dk) + c_arm + d*s*(corps-9)
    a = A3[m] @ th[0:3]; beta = th[3:3 + nk]; v = th[3 + nk:3 + 2 * nk]; c = A3[m] @ th[3 + 2 * nk:6 + 2 * nk]
    d = th[6 + 2 * nk]; g = A3[m] @ th[7 + 2 * nk:10 + 2 * nk]
    return P[m] * np.exp(a + Dm[m] @ beta) * SIZE[m] ** g + MEN_R[m] * (Dm[m] @ v) + c + d * S[m] * (CORPS[m] - 9)
th0 = np.r_[-0.1, -0.1, -0.1, np.zeros(nk), np.zeros(nk), -100, -100, -100, 0, 1, 1, 1]
p, prm = cv_custom(nl_fit_fn(f1, th0)); log_result("N1", "P exp(a_arm + b.dk) ratio^g_arm + men v.dk + c_arm + d s(corps-9)", len(th0), metrics(p), params=prm)

def f2(th, m):
    # without the men term
    a = A3[m] @ th[0:3]; beta = th[3:3 + nk]; c = A3[m] @ th[3 + nk:6 + nk]; d = th[6 + nk]; g = A3[m] @ th[7 + nk:10 + nk]
    return P[m] * np.exp(a + Dm[m] @ beta) * SIZE[m] ** g + c + d * S[m] * (CORPS[m] - 9)
th0 = np.r_[-0.1, -0.1, -0.1, np.zeros(nk), -100, -100, -100, 0, 1, 1, 1]
p, prm = cv_custom(nl_fit_fn(f2, th0)); log_result("N2", "P exp(a_arm + b.dk) ratio^g_arm + c_arm + d s(corps-9)", len(th0), metrics(p), params=prm)

def f3(th, m):
    # premium on (P + K): C = (P+K) exp(a_arm + b.dk) ratio^g - K2_arm + men v.dk + d s(corps-9)
    K = th[0]; a = A3[m] @ th[1:4]; beta = th[4:4 + nk]; v = th[4 + nk:4 + 2 * nk]; c = A3[m] @ th[4 + 2 * nk:7 + 2 * nk]
    d = th[7 + 2 * nk]; g = A3[m] @ th[8 + 2 * nk:11 + 2 * nk]
    return (P[m] + K) * np.exp(a + Dm[m] @ beta) * SIZE[m] ** g + MEN_R[m] * (Dm[m] @ v) + c + d * S[m] * (CORPS[m] - 9)
th0 = np.r_[0, -0.1, -0.1, -0.1, np.zeros(nk), np.zeros(nk), -100, -100, -100, 0, 1, 1, 1]
p, prm = cv_custom(nl_fit_fn(f3, th0)); log_result("N3", "(P+K) exp(a_arm+b.dk) ratio^g_arm + men v.dk + c_arm + d s(corps-9)", len(th0), metrics(p), params=prm)
