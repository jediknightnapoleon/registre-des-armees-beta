"""Exp 19: lean fallback models (<= ~10 parameters)."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, log_result, Y
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
def run(eid, nm, cols, meth="lad", notes=""):
    X = np.column_stack(cols)
    p, b = cv_linear(X, meth)
    log_result(eid, nm + f" [{meth}]", X.shape[1], metrics(p), notes=notes, params=b)
    return p, b
sz = P * (SIZE - 1)
run("Z1", "aP + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps) + g P(r-1)", [P, ONE, P * dmo, P * dmd, P * drl, MEN_R * dmo, S, CORPS * S, sz])
run("Z2", "aP + b + P(w.dmo,dmd,dac,drl) + v men dmo + s(k - c corps) + g P(r-1)", [P, ONE, P * dmo, P * dmd, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, sz])
run("Z3", "aP + b + P(w.dmo,dmd,dcb,dac,drl) + v men dmo + s(k - c corps) + g P(r-1)", [P, ONE, P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, sz])
run("Z4", "aP + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps)", [P, ONE, P * dmo, P * dmd, P * drl, MEN_R * dmo, S, CORPS * S])
run("Z5", "aP + b + P(w.dmo,dmd) + v men dmo + s(k - c corps) + g P(r-1)", [P, ONE, P * dmo, P * dmd, MEN_R * dmo, S, CORPS * S, sz])
run("Z6", "a_arm P + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps) + g P(r-1)", [P * INF, P * CAV, P * ART, ONE, P * dmo, P * dmd, P * drl, MEN_R * dmo, S, CORPS * S, sz])
run("Z7", "stars only: P(a + c s) + b + v men (1+floor(s/2)) + s(k - c corps) + g P(r-1)", [P, P * S, ONE, MEN_R * dmo, S, CORPS * S, sz])
run("Z8", "stars+arm: P(a_arm + c_arm s) + b + v men dmo + s(k - c corps) + g P(r-1)", [P * INF, P * CAV, P * ART, P * S * INF, P * S * CAV, P * S * ART, ONE, MEN_R * dmo, S, CORPS * S, sz])
run("Z9", "Z1 with art size separate", [P, ONE, P * dmo, P * dmd, P * drl, MEN_R * dmo, S, CORPS * S, sz * (1 - ART), sz * ART])
run("Z10", "Z2 with art size separate", [P, ONE, P * dmo, P * dmd, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, sz * (1 - ART), sz * ART])
