"""What explains residuals inside a clean slice (0-star line+all infantry, cavalry)?"""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y
C = Y
for name, m in [("inf star0", (INF == 1) & (S == 0) & (SIZE == 1)),
                ("inf star1", (INF == 1) & (S == 1) & (SIZE == 1)),
                ("cav star0", (CAV == 1) & (S == 0) & (SIZE == 1)),
                ("cav star2", (CAV == 1) & (S == 2) & (SIZE == 1))]:
    X = np.c_[P[m], np.ones(m.sum())]
    b = np.linalg.lstsq(X, C[m], rcond=None)[0]
    r = C[m] - X @ b
    print(f"== {name} n={m.sum()} a={b[0]:.3f} b={b[1]:.1f} MAE={np.mean(abs(r)):.2f}")
    cands = {"P": P, "men": MEN_R, **{"reg_" + k: REG[k] for k in STATS}, **{"d_" + k: D[k] for k in DSTATS},
             "corps": CORPS}
    for k, v in cands.items():
        vv = v[m]
        if np.std(vv) == 0: continue
        c1 = np.corrcoef(vv, r)[0, 1]
        # also correlation of residual/P with v (multiplicative)
        c2 = np.corrcoef(vv, r / P[m])[0, 1]
        print(f"   {k:18s} corr(res) {c1:+.3f}  corr(res/P) {c2:+.3f}")
