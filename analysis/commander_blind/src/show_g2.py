from __future__ import annotations
import numpy as np
from harness import fit_linear, Y
from features import *
Dm = np.column_stack([D[k] for k in DSTATS])
names = ["P*inf", "P*cav", "P*art", "inf", "cav", "art"] + [f"men*d_{k}" for k in DSTATS] + [f"P*d_{k}" for k in DSTATS] + ["corps*s", "s", "P(r-1)inf", "P(r-1)cav", "P(r-1)art"]
X = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, MEN_R[:, None] * Dm, P[:, None] * Dm, CORPS * S, S] + [P * (SIZE - 1) * A for A in (INF, CAV, ART)])
for meth in ["lad", "ols"]:
    b = fit_linear(X, Y, meth)
    print(meth, "in-sample MAE", np.mean(abs(Y - X @ b)).round(2))
    for n, v in zip(names, b): print(f"   {n:14s} {v: .5f}")
