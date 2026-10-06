"""Exp 04: per-man value of stat changes; corps scaling of the general's premium."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result
from features import *

Dm = np.column_stack([D[k] for k in DSTATS])
MEN = MEN_C
LSZ = (SIZE - 1)
base = [P * INF, P * CAV, P * ART, INF, CAV, ART, P * LSZ]
def run(eid, name, cols, meth="lad"):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth); log_result(eid, name + f" [{meth}]", X.shape[1], metrics(p), params=b)
    return p, b
run("E1", "arm a,b + P*(size-1) + men*dk", base + [MEN[:, None] * Dm])
run("E2", "arm a,b + P*(size-1) + men*dk + P*dk", base + [MEN[:, None] * Dm, P[:, None] * Dm])
run("E3", "arm a,b + P*(size-1) + men*dk + P*dk + dk", base + [MEN[:, None] * Dm, P[:, None] * Dm, Dm])
run("E4", "E2 + corps*dk", base + [MEN[:, None] * Dm, P[:, None] * Dm, CORPS[:, None] * Dm])
run("E5", "E2 + corps*s + s", base + [MEN[:, None] * Dm, P[:, None] * Dm, CORPS * S, S])
run("E6", "arm a,b + P*(size-1) + men*s*arm + P*s*arm + s*arm + corps*s", base + [MEN * S * INF, MEN * S * CAV, MEN * S * ART, P * S * INF, P * S * CAV, P * S * ART, S * INF, S * CAV, S * ART, CORPS * S])
