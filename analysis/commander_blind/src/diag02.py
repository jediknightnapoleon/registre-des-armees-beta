"""Per-army fits on the cleanest slice (0-star, same size) for each arm."""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y
C = Y
for a, A in ARMS.items():
    print("==", a)
    for star in [0, 1]:
        out = []
        for f in sorted(set(FAC.tolist())):
            m = (FAC == f) & (A == 1) & (S == star) & (SIZE == 1)
            if a == "infantry":
                m &= (CLASS == "infantry_line")
            if m.sum() < 8: continue
            X = np.c_[P[m], np.ones(m.sum())]
            b = np.linalg.lstsq(X, C[m], rcond=None)[0]
            mae = np.mean(np.abs(C[m] - X @ b))
            out.append((CORPS[m][0], f, m.sum(), b[0], b[1], mae))
        for o in sorted(out):
            print(f"  star{star} corps {int(o[0]):2d} {o[1]:22s} n={o[2]:3d} a={o[3]:.3f} b={o[4]:7.1f} mae={o[5]:.1f}")
