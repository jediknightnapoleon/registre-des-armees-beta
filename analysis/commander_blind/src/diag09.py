"""Residual structure of G2 (CV predictions)."""
from __future__ import annotations
import numpy as np
from harness import cv_linear, Y
from features import *
from load import FLAGS, col

Dm = np.column_stack([D[k] for k in DSTATS])
X = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S] + [P * (SIZE - 1) * A for A in (INF, CAV, ART)])
p, b = cv_linear(X, "lad")
r = Y - p; ae = abs(r); ok = SIZE == 1
np.save("../out/g2_cvpred.npy", p)
def by(name, v, minn=10):
    print("--", name)
    for k in sorted(set(v.tolist())):
        m = (v == k) & ok
        if m.sum() >= minn:
            print(f"   {str(k):24s} n={m.sum():5d} medres {np.median(r[m]):7.1f} meanres {np.mean(r[m]):7.1f} MAE {ae[m].mean():6.1f}")
by("arm", ARM); by("class", CLASS); by("training", TRAIN); by("stars", S, 3); by("corps", CORPS)
for f in FLAGS:
    v = col(ROWS, "regular_" + f)
    m1 = (v == 1) & ok
    if m1.sum() >= 5:
        print(f"flag {f:26s} n={m1.sum():5d} medres {np.median(r[m1]):6.1f} MAE {ae[m1].mean():5.1f}  (off: MAE {ae[(v==0)&ok].mean():5.1f})")
# irregular deltas: rows whose dk differ from the arm x star mode
print("-- error quantiles (non-size)", np.percentile(ae[ok], [50, 75, 90, 95, 99, 100]).round(1))
print("share of AE from top 5% rows:", np.sort(ae)[::-1][:262].sum() / ae.sum())
fs = sorted(set(FAC.tolist()))
meds = [(np.median(r[(FAC == f) & ok]), np.mean(ae[(FAC == f) & ok]), f, ((FAC == f) & ok).sum()) for f in fs]
meds.sort()
print("army median residual (lowest/highest 6):")
for t in meds[:6] + meds[-6:]: print("   ", f"{t[2]:22s} n={t[3]:4d} medres {t[0]:6.1f} MAE {t[1]:5.1f}")
print("spread of army medians: sd", np.std([t[0] for t in meds]).round(2))
