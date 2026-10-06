"""Residual diagnostics for the arm x star lookup model (L6, LAD)."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, metrics, Y
from features import *

Sl = np.minimum(S, 5)
X = np.column_stack([(Sl == k) * a * f for a in (INF, CAV, ART) for k in range(6) for f in (P, ONE)])
X = X[:, X.any(0)]
pred, b = cv_linear(X, "lad")
r = Y - pred
ae = np.abs(r)
print("overall MAE", ae.mean(), "median AE", np.median(ae))
sz = SIZE != 1
print("size-change rows: n", sz.sum(), "MAE", ae[sz].mean(), "share of total AE", ae[sz].sum() / ae.sum())
print("MAE w/o size rows", ae[~sz].mean())
def by(name, v):
    print("--", name)
    for k in sorted(set(v.tolist())):
        m = (v == k) & ~sz
        if m.sum() >= 5:
            print(f"   {str(k):28s} n={m.sum():5d} medres {np.median(r[m]):7.1f} MAE {ae[m].mean():6.1f}")
by("class", CLASS); by("training", TRAIN); by("corps", CORPS); by("side", SIDE)
by("speed", SPEED)
# vs P bins per arm
for a, A in ARMS.items():
    print("--", a, "by P bin")
    for lo, hi in [(0, 150), (150, 300), (300, 500), (500, 800), (800, 1200), (1200, 4000)]:
        m = (A == 1) & (P >= lo) & (P < hi) & ~sz
        if m.sum(): print(f"   {lo}-{hi} n={m.sum()} medres {np.median(r[m]):.1f} MAE {ae[m].mean():.1f}")
# army-level residual spread
fs = sorted(set(FAC.tolist()))
meds = np.array([np.median(r[(FAC == f) & ~sz]) for f in fs])
print("army median residual quantiles", np.percentile(meds, [0, 10, 50, 90, 100]).round(1))
for f, mm in sorted(zip(fs, meds), key=lambda t: t[1])[:5] + sorted(zip(fs, meds), key=lambda t: t[1])[-5:]:
    print("  ", f, round(mm, 1), (FAC == f).sum())
