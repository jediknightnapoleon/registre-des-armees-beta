"""Cavalry 0-star: offset vs men; infantry 0-star likewise."""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y
for nm, A, a in [("cav", CAV, 0.90), ("inf", INF, 0.96), ("art", ART, 0.92)]:
    m = (A == 1) & (S == 0) & (SIZE == 1)
    off = Y[m] - a * P[m]
    men = MEN_R[m]
    qs = np.unique(np.percentile(men, np.linspace(0, 100, 11)))
    print(nm, "C - a P by men decile (a=%.2f)" % a)
    for lo, hi in zip(qs[:-1], qs[1:]):
        mm = (men >= lo) & (men < hi if hi < qs[-1] else men <= hi)
        print(f"   men {lo:5.0f}-{hi:5.0f} n={mm.sum():4d} median off {np.median(off[mm]):7.1f}  IQR {np.percentile(off[mm],25):7.1f}..{np.percentile(off[mm],75):7.1f}  medP {np.median(P[m][mm]):6.0f}")
