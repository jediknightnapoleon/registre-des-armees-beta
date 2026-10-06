"""Worst CV residuals of J8 (non-size rows), with context."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, Y
from features import *
dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
X = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART])
p, b = cv_linear(X, "lad")
r = Y - p; ae = abs(r)
print("median AE", np.median(ae), "MAE", ae.mean())
idx = np.argsort(-ae)
k = 0
for i in idx:
    if SIZE[i] != 1: continue
    rr = ROWS[i]
    print(f"{rr['pair_id']:>5} {FAC[i][-6:]} c{int(CORPS[i]):2d} {CLASS[i][:18]:18s} {TRAIN[i][:6]:6s} s={int(S[i])} P={int(P[i]):5d} C={int(Y[i]):5d} pred={p[i]:7.1f} res={r[i]:+6.0f} men={int(MEN_R[i])} d=({int(dmo[i])},{int(dma[i])},{int(dmd[i])},{int(dcb[i])},{int(dac[i])},{int(drl[i])}) {rr['commander_name'][:45]}")
    k += 1
    if k >= 45: break
