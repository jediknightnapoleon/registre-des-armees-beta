"""Within-card slope: for the same commander card in several armies, does C-P move with P?"""
from __future__ import annotations
import collections
import numpy as np
from features import *
from harness import Y
g = collections.defaultdict(list)
for i, r in enumerate(ROWS):
    g[r["commander_name"]].append(i)
dP, dD, arm, same = [], [], [], []
for n, ix in g.items():
    if len(ix) < 2 or not all(SIZE[ix] == 1): continue
    i0 = ix[0]
    for i in ix[1:]:
        dP.append(P[i] - P[i0]); dD.append((Y[i] - P[i]) - (Y[i0] - P[i0])); arm.append(ARM[i])
        same.append(all(REG[k][i] == REG[k][i0] for k in STATS) and MEN_R[i] == MEN_R[i0])
dP, dD, arm, same = map(np.array, (dP, dD, arm, same))
print("pairs", len(dP), "same stats", same.sum())
for nm, m in [("all", np.ones(len(dP), bool)), ("same stats", same), ("diff stats", ~same)]:
    if m.sum() < 3: continue
    slope = np.sum(dP[m] * dD[m]) / np.sum(dP[m] ** 2)
    print(f"{nm:10s} n={m.sum()} within-card slope of (C-P) on P: {slope:.4f}; corr {np.corrcoef(dP[m], dD[m])[0,1]:.3f}; mean|dD| {np.mean(abs(dD[m])):.1f}; mean|dP| {np.mean(abs(dP[m])):.1f}")
    for a in ["infantry", "cavalry", "artillery"]:
        mm = m & (arm == a)
        if mm.sum() >= 3:
            print(f"     {a:9s} n={mm.sum()} slope {np.sum(dP[mm]*dD[mm])/np.sum(dP[mm]**2):.4f}")
