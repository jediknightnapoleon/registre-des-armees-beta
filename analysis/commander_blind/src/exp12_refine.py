"""Exp 12: refinements around J8."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
Pd5 = [P * dmo, P * dmd, P * dcb, P * dac, P * drl]
size2 = [P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART]
J8 = armab + Pd5 + [MEN_R * dmo, S, CORPS * S] + size2
def run(eid, nm, cols, meth="lad", notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth)
    log_result(eid, nm + f" [{meth}]", X.shape[1], metrics(p), notes=notes, params=b)
run("K0", "J8", J8, "ols")
run("K1", "J8 + corps*men*dmo", J8 + [CORPS * MEN_R * dmo])
run("K2", "J8 + per-arm s, corps*s", armab + Pd5 + [MEN_R * dmo] + [S * A for A in (INF, CAV, ART)] + [CORPS * S * A for A in (INF, CAV, ART)] + size2)
run("K3", "J8 + s^2", J8 + [S**2])
run("K4", "J8 + P*s^2", J8 + [P * S**2])
run("K5", "J8 + corps (main)", J8 + [CORPS])
run("K6", "J8 + P*corps", J8 + [P * CORPS])
run("K7", "J8 + corps*P*dmo", J8 + [CORPS * P * dmo])
run("K8", "J8 with men_c instead of men_r", armab + Pd5 + [MEN_C * dmo, S, CORPS * S] + size2)
run("K9", "J8 + P*s^2 + s^2", J8 + [P * S**2, S**2])
run("K10", "J8 + reg stats(8)", J8 + [np.column_stack([REG[k] for k in STATS])])
