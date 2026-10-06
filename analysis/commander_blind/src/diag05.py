"""How do the 70 size-change rows deviate from a no-size model?"""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y, fit_linear
Dm = np.column_stack([D[k] for k in DSTATS])
MEN = MEN_R
X = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, MEN[:, None] * Dm, P[:, None] * Dm, CORPS * S, S])
ok = SIZE == 1
b = fit_linear(X[ok], Y[ok], "lad")
base = X @ b
print("in-sample MAE on same-size rows", np.mean(abs(Y[ok] - base[ok])))
sz = ~ok
for i in np.where(sz)[0]:
    print(f"{ROWS[i]['pair_id']:>5} {ARM[i][:3]} {CLASS[i]:22s} s={int(S[i])} P={int(P[i]):5d} base={base[i]:7.1f} C={int(Y[i]):5d} ratio={SIZE[i]:.2f} C/base={Y[i]/base[i]:.2f} (C-base)/P={(Y[i]-base[i])/P[i]:.2f} log(C/base)/log(ratio)={np.log(max(Y[i],1)/max(base[i],1))/np.log(SIZE[i]):.2f}")
