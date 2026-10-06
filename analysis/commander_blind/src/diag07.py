"""Same commander card name across several armies: how do C and P co-move?"""
from __future__ import annotations
import collections
import numpy as np
from features import *
from harness import Y
names = col_names = [r["commander_name"] for r in ROWS]
g = collections.defaultdict(list)
for i, n in enumerate(names):
    g[n].append(i)
multi = {n: ix for n, ix in g.items() if len(ix) >= 2 and all(SIZE[ix] == 1)}
print("names with >=2 occurrences:", len(multi))
cnt = 0
for n, ix in sorted(multi.items(), key=lambda t: -len(t[1]))[:25]:
    ix = sorted(ix, key=lambda i: CORPS[i])
    print(n[:70], "stars", int(S[ix[0]]), "men", int(MEN_R[ix[0]]))
    for i in ix:
        same_stats = all(REG[k][i] == REG[k][ix[0]] for k in ["morale", "melee_attack", "accuracy", "reload_skill"])
        print(f"    corps {int(CORPS[i]):2d} {FAC[i][-6:]} P={int(P[i]):5d} C={int(Y[i]):5d} C-P={int(Y[i]-P[i]):5d} C/P={Y[i]/P[i]:.3f} same_reg_stats={same_stats} mor={REG['morale'][i]:.0f} acc={REG['accuracy'][i]:.0f} rel={REG['reload_skill'][i]:.0f} ma={REG['melee_attack'][i]:.0f}")
