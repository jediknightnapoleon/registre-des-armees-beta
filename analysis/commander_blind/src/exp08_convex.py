"""Exp 08: convexity in stars / deltas on top of G2."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

Dm = np.column_stack([D[k] for k in DSTATS])
size = [P * (SIZE - 1) * A for A in (INF, CAV, ART)]
core = [P * INF, P * CAV, P * ART, INF, CAV, ART, MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S] + size
def run(eid, nm, cols):
    X = np.column_stack(cols)
    p, b = cv_linear(X, "lad")
    log_result(eid, nm + " [lad]", X.shape[1], metrics(p), params=b)
    return p, b
run("H1", "G2 + P*s^2", core + [P * S**2])
run("H2", "G2 + per-arm P*s^2", core + [P * S**2 * A for A in (INF, CAV, ART)])
run("H3", "G2 + per-arm P*s^2 + s^2", core + [P * S**2 * A for A in (INF, CAV, ART)] + [S**2])
run("H4", "G2 + per-arm P*s^2 + men*s^2", core + [P * S**2 * A for A in (INF, CAV, ART)] + [MEN_R * S**2])
# star-only formulation, no stat deltas: per arm P*(a + c s + e s^2) + men*(g s) + b + d s + corps*s
run("H5", "per arm P(a+cs+es^2) + b + ds + men*s(arm) + corps*s + size",
    [P * A for A in (INF, CAV, ART)] + [A for A in (INF, CAV, ART)] + [P * S * A for A in (INF, CAV, ART)] + [P * S**2 * A for A in (INF, CAV, ART)]
    + [S * A for A in (INF, CAV, ART)] + [MEN_R * S * A for A in (INF, CAV, ART)] + [CORPS * S] + size)
run("H6", "H5 + men*s^2(arm)",
    [P * A for A in (INF, CAV, ART)] + [A for A in (INF, CAV, ART)] + [P * S * A for A in (INF, CAV, ART)] + [P * S**2 * A for A in (INF, CAV, ART)]
    + [S * A for A in (INF, CAV, ART)] + [MEN_R * S * A for A in (INF, CAV, ART)] + [MEN_R * S**2 * A for A in (INF, CAV, ART)] + [CORPS * S] + size)
