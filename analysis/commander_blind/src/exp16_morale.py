"""Exp 16: is the morale bonus valued on a convex morale scale (men * delta(morale^2))?"""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
mr, mc = REG["morale"], COM["morale"]
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
Pd5 = [P * dmo, P * dmd, P * dcb, P * dac, P * drl]
size2 = [P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART]
rest = [S, CORPS * S] + size2
def run(eid, nm, cols, meth="lad", notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth)
    log_result(eid, nm + f" [{meth}]", X.shape[1], metrics(p), notes=notes, params=b)
    return p, b
run("U1", "J8 with men*d(morale^2)", armab + Pd5 + [MEN_R * (mc**2 - mr**2)] + rest)
run("U2", "J8 + men*d(morale^2)", armab + Pd5 + [MEN_R * dmo, MEN_R * (mc**2 - mr**2)] + rest)
run("U3", "J8 + P*d(morale^2)", armab + Pd5 + [MEN_R * dmo, P * (mc**2 - mr**2)] + rest)
run("U4", "J8 + men*dmo*reg_morale", armab + Pd5 + [MEN_R * dmo, MEN_R * dmo * mr] + rest)
# general convex: Δ(stat^2) for all P-terms
Pd5sq = [P * (COM[k]**2 - REG[k]**2) for k in ["morale", "melee_defense", "charge_bonus", "accuracy", "reload_skill"]]
run("U5", "J8 + P*d(stat^2) x5", armab + Pd5 + Pd5sq + [MEN_R * dmo] + rest)
run("U6", "J8 + P*d(morale^2) + men*d(morale^2)", armab + Pd5 + [MEN_R * dmo, P * (mc**2 - mr**2), MEN_R * (mc**2 - mr**2)] + rest)
