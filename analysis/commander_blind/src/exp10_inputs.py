"""Exp 10: does each candidate input add anything on top of the G2 core? (LAD, grouped CV)

Each test adds (or removes) one block and reports the CV change.
"""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *
from load import FLAGS, col

Dm = np.column_stack([D[k] for k in DSTATS])
size = [P * (SIZE - 1) * A for A in (INF, CAV, ART)]
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
core = armab + [MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S] + size
def run(eid, nm, cols, notes=""):
    X = np.column_stack(cols)
    X = X[:, X.std(0) > 0] if X.shape[1] > 1 else X
    p, b = cv_linear(X, "lad")
    log_result(eid, nm + " [lad]", X.shape[1], metrics(p), notes=notes)
FD, flv = dummies(FAC, drop_first=False)
CD, clv = dummies(CLASS)
TD, tlv = dummies(TRAIN)
run("I0", "G2 core (reference)", core)
# removals
run("I1", "core minus stars terms (S, corps*S)", armab + [MEN_R[:, None] * Dm, P[:, None] * Dm] + size)
run("I2", "core minus corps*S", armab + [MEN_R[:, None] * Dm, P[:, None] * Dm, S] + size)
run("I3", "core minus men*dk", armab + [P[:, None] * Dm, CORPS * S, S] + size)
run("I4", "core minus size terms", armab + [MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S])
run("I5", "core minus all stat deltas (stars only: P*s, men*s, s, corps*s per arm)",
    armab + [P * S * A for A in (INF, CAV, ART)] + [MEN_R * S * A for A in (INF, CAV, ART)] + [S * A for A in (INF, CAV, ART)] + [CORPS * S] + size)
# additions
run("I6", "core + corps, P*corps", core + [CORPS, P * CORPS])
run("I7", "core + side", core + [(SIDE == "imperial").astype(float)])
run("I8", "core + men", core + [MEN_R])
run("I9", "core + class dummies (12)", core + [CD])
run("I10", "core + training dummies (5)", core + [TD])
run("I11", "core + army intercepts (55, lookup)", [c for c in core if not (c is INF or c is CAV or c is ART)] + [FD, CAV, ART], notes="army lookup")
run("I12", "core + army P-multipliers (55, lookup)", [c for c in core] + [P[:, None] * FD[:, 1:]], notes="army lookup")
FL = np.column_stack([col(ROWS, "regular_" + f).astype(float) for f in FLAGS])
run("I13", "core + regular flags (13)", core + [FL])
run("I14", "core + P*flags (13)", core + [P[:, None] * FL])
gained_scare = (col(ROWS, "commander_scares_enemies").astype(float) - col(ROWS, "regular_scares_enemies").astype(float))
run("I15", "core + scare gained", core + [gained_scare])
run("I16", "core + regular stats (8)", core + [np.column_stack([REG[k] for k in STATS])])
run("I17", "core + P*regular stats (8)", core + [P[:, None] * np.column_stack([REG[k] for k in STATS])])
