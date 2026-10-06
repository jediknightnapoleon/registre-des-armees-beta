"""Exp 07: size-change handling on top of E5."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

Dm = np.column_stack([D[k] for k in DSTATS])
core = [P * INF, P * CAV, P * ART, INF, CAV, ART, MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S]
sz = SIZE != 1
def run(eid, nm, extra):
    X = np.column_stack(core + extra)
    p, b = cv_linear(X, "lad")
    m = metrics(p)
    ae = np.abs(p - Y)
    log_result(eid, nm + " [lad]", X.shape[1], m, notes=f"size rows MAE {ae[sz].mean():.0f}, other {ae[~sz].mean():.2f}")
    return p, b
run("G0", "E5 core, no size term (men*dk uses regular men)", [])
run("G1", "core + P*(ratio-1)", [P * (SIZE - 1)])
run("G2", "core + per-arm P*(ratio-1)", [P * (SIZE - 1) * A for A in (INF, CAV, ART)])
run("G3", "core + per-arm P*(ratio^2-1)", [P * (SIZE**2 - 1) * A for A in (INF, CAV, ART)])
run("G4", "core + inf/cav P*(ratio-1) + art P*(ratio^2-1)", [P * (SIZE - 1) * INF, P * (SIZE - 1) * CAV, P * (SIZE**2 - 1) * ART])
run("G5", "core + per-arm P*(ratio-1) + per-arm (ratio-1)", [P * (SIZE - 1) * A for A in (INF, CAV, ART)] + [(SIZE - 1) * A for A in (INF, CAV, ART)])
