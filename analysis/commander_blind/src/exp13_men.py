"""Exp 13: per-arm men terms."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
Pd5 = [P * dmo, P * dmd, P * dcb, P * dac, P * drl]
size2 = [P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART]
base = armab + Pd5 + [S, CORPS * S] + size2
def run(eid, nm, cols, meth="lad", notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth)
    log_result(eid, nm + f" [{meth}]", X.shape[1], metrics(p), notes=notes, params=b)
    return p
run("Q1", "J8 with per-arm men*dmo", base + [MEN_R * dmo * A for A in (INF, CAV, ART)])
run("Q2", "J8 + per-arm men", base + [MEN_R * dmo] + [MEN_R * A for A in (INF, CAV, ART)])
run("Q3", "J8 + men*s", base + [MEN_R * dmo, MEN_R * S])
run("Q4", "J8 + per-arm men + men*s", base + [MEN_R * dmo, MEN_R * S] + [MEN_R * A for A in (INF, CAV, ART)])
run("Q5", "J8 with per-arm men*dmo + men*s", base + [MEN_R * dmo * A for A in (INF, CAV, ART)] + [MEN_R * S])
run("Q6", "J8 with per-arm men*dmo + men*dmd + men*drl", base + [MEN_R * dmo * A for A in (INF, CAV, ART)] + [MEN_R * dmd, MEN_R * drl])
