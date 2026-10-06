"""Exp 11: simplify the G2 core."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
size3 = [P * (SIZE - 1) * A for A in (INF, CAV, ART)]
armab = [P * INF, P * CAV, P * ART, INF, CAV, ART]
def run(eid, nm, cols, notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, "lad")
    log_result(eid, nm + " [lad]", X.shape[1], metrics(p), notes=notes, params=b)
Pd5 = [P * dmo, P * dmd, P * dcb, P * dac, P * drl]
run("J1", "arm a,b + P*(mo,md,cb,ac,rl) + men*dmo + s + corps*s + size3", armab + Pd5 + [MEN_R * dmo, S, CORPS * S] + size3)
run("J2", "J1 with men*s instead of men*dmo", armab + Pd5 + [MEN_R * S, S, CORPS * S] + size3)
run("J3", "J1 with men (const) instead of men*dmo", armab + Pd5 + [MEN_R, S, CORPS * S] + size3)
run("J4", "J1 + men*dmd + men*dac", armab + Pd5 + [MEN_R * dmo, MEN_R * dmd, MEN_R * dac, S, CORPS * S] + size3)
run("J5", "J1 with single a (P) + arm b", [P, INF, CAV, ART] + Pd5 + [MEN_R * dmo, S, CORPS * S] + size3)
run("J6", "J1 with single b + arm a", [P * INF, P * CAV, P * ART, ONE] + Pd5 + [MEN_R * dmo, S, CORPS * S] + size3)
run("J7", "J1 with single size term", armab + Pd5 + [MEN_R * dmo, S, CORPS * S, P * (SIZE - 1)])
run("J8", "J1 with size: inf/cav shared, art own", armab + Pd5 + [MEN_R * dmo, S, CORPS * S, P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART])
run("J9", "J1 minus P*drl", armab + [P * dmo, P * dmd, P * dcb, P * dac] + [MEN_R * dmo, S, CORPS * S] + size3)
run("J10", "J1 minus P*dac", armab + [P * dmo, P * dmd, P * dcb, P * drl] + [MEN_R * dmo, S, CORPS * S] + size3)
run("J11", "J1 minus P*dcb", armab + [P * dmo, P * dmd, P * dac, P * drl] + [MEN_R * dmo, S, CORPS * S] + size3)
run("J12", "J1 minus P*dmd", armab + [P * dmo, P * dcb, P * dac, P * drl] + [MEN_R * dmo, S, CORPS * S] + size3)
run("J13", "J1 minus P*dmo", armab + [P * dmd, P * dcb, P * dac, P * drl] + [MEN_R * dmo, S, CORPS * S] + size3)
run("J14", "J1 + P*dma", armab + Pd5 + [P * dma, MEN_R * dmo, S, CORPS * S] + size3)
run("J15", "J1 minus s, corps*s", armab + Pd5 + [MEN_R * dmo] + size3)
run("J16", "J1 minus corps*s", armab + Pd5 + [MEN_R * dmo, S] + size3)
