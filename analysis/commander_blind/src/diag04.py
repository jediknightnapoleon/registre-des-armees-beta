"""Slice fits with men and regular stats to see the local structure."""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y, fit_linear
C = Y
def show(name, m, cols):
    X = np.column_stack([v[m] for _, v in cols])
    b = fit_linear(X, C[m], "ols")
    r = C[m] - X @ b
    print(f"{name:10s} n={m.sum()} MAE {np.mean(abs(r)):.2f} | " + ", ".join(f"{n}={x:.4g}" for (n, _), x in zip(cols, b)))
    return r
for nm, m in [("inf s0", (INF == 1) & (S == 0) & (SIZE == 1)), ("inf s1", (INF == 1) & (S == 1) & (SIZE == 1)),
              ("inf s2", (INF == 1) & (S == 2) & (SIZE == 1)), ("inf s3", (INF == 1) & (S == 3) & (SIZE == 1)),
              ("cav s0", (CAV == 1) & (S == 0) & (SIZE == 1)), ("cav s1", (CAV == 1) & (S == 1) & (SIZE == 1)),
              ("cav s2", (CAV == 1) & (S == 2) & (SIZE == 1)), ("cav s3", (CAV == 1) & (S == 3) & (SIZE == 1)),
              ("art s0", (ART == 1) & (S == 0) & (SIZE == 1)), ("art s1", (ART == 1) & (S == 1) & (SIZE == 1)),
              ("art s2", (ART == 1) & (S == 2) & (SIZE == 1))]:
    show(nm, m, [("P", P), ("1", ONE)])
    show(nm, m, [("P", P), ("1", ONE), ("men", MEN_R)])
    show(nm, m, [("P", P), ("1", ONE), ("men", MEN_R), ("corps", CORPS)])
    show(nm, m, [("P", P), ("1", ONE), ("men", MEN_R), ("P*corps", P * CORPS), ("corps", CORPS)])
