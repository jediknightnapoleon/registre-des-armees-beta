"""Print comp-model coefficients with standard errors (training fit), +/- skill controls."""
from __future__ import annotations
import sys
import numpy as np
from common import faction_feature, fit_logistic
from models import Data, COMP_FEATURES

D = Data()
m = D.train & D.dec & D.rated
idx = np.flatnonzero(m)
F = faction_feature(D.armies, np.flatnonzero(D.dec), m, 100.0)
names = sys.argv[1].split(",") if len(sys.argv) > 1 else COMP_FEATURES
X = np.column_stack([np.ones(len(idx)), F[idx], D.cols(names)[idx]])
res = {}
for lab, extra in [("none", None), ("elo", D.le[idx])]:
    Xx = X if extra is None else np.column_stack([X, extra])
    b, C = fit_logistic(Xx, D.y[idx], np.r_[0, 0, np.full(len(names), 1e-3), [0] * (extra is not None)])
    res[lab] = (b, np.sqrt(np.diag(C)))
print(f"{'feature':24s} {'sd':>6s} | {'coef':>7s} {'z':>6s} | {'coef|elo':>8s} {'z':>6s}")
for j, n in enumerate(["const", "F"] + list(names)):
    sd = X[:, j].std()
    b0, s0 = res["none"][0][j], res["none"][1][j]
    b1, s1 = res["elo"][0][j], res["elo"][1][j]
    print(f"{n:24s} {sd:6.2f} | {b0:7.3f} {b0/s0:6.2f} | {b1:8.3f} {b1/s1:6.2f}")
print("elo coef", res["elo"][0][-1])
