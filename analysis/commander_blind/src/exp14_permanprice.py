"""Exp 14: price-per-man and 1/men terms (a commander costing a fixed number of men?)."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
Pd5 = [P * dmo, P * dmd, P * dcb, P * dac, P * drl]
size2 = [P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART]
J8 = armab + Pd5 + [MEN_R * dmo, S, CORPS * S] + size2
PPM = P / MEN_R
def run(eid, nm, cols, meth="lad", notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth)
    log_result(eid, nm + f" [{meth}]", X.shape[1], metrics(p), notes=notes, params=b)
    return p, b
run("R1", "J8 + P/men", J8 + [PPM])
run("R2", "J8 + per-arm P/men", J8 + [PPM * A for A in (INF, CAV, ART)])
run("R3", "J8 + per-arm 1/men", J8 + [A / MEN_R for A in (INF, CAV, ART)])
run("R4", "J8 - men*dmo + per-arm P/men", armab + Pd5 + [S, CORPS * S] + size2 + [PPM * A for A in (INF, CAV, ART)])
run("R5", "J8 + P/men + P/men*s", J8 + [PPM, PPM * S])
run("R6", "J8 + P/men*dmo", J8 + [PPM * dmo])
