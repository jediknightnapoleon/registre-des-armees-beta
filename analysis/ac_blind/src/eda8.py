"""Diagnostics: in-sample residuals of E02-like model (army FE) by size band per class etc."""
import numpy as np
from common import regular_units
from harness import arm_vec, ARMS
from features import Design, gridge_fit, STATS, BOOLS
d = regular_units(); y = d.f("base_mp_cost"); ly = np.log(y); arm = arm_vec(d)
size = np.where(arm == "artillery", d.f("guns", 0), d.f("men_display"))
cls = d.s('unit_class')
for a in ARMS:
    m = arm == a
    D = Design()
    D.add("log_size", np.log(size[m]))
    for s in STATS: D.add(s, d.f(s, 0)[m])
    for b in BOOLS:
        v = d.b(b)[m]
        if 0 < v.sum() < m.sum(): D.add(b, v)
    D.add_onehot("class", cls[m]); D.add_onehot("train", d.s("unit_training_level")[m])
    D.add_onehot("speed", d.s("speed_code")[m], group="cat")
    D.add_onehot("army", d.s("faction_key")[m], group="army")
    pen = np.array([{"main": 1e-3, "cat": 1.0, "army": 1.0}[g] for g in D.groups])
    X = D.matrix(); a0, b = gridge_fit(X, ly[m], pen)
    r = ly[m] - a0 - X @ b
    print(a, 'resid sd', r.std())
    for nm, bb in zip(D.names, b):
        if not nm.startswith('army'): print(f'   {nm:30s} {bb:+.4f}')
    s = size[m]; c = cls[m]
    bands = [1,2,3,4,5,99] if a=='artillery' else [0,40,60,80,100,140,180,240,999]
    for cl in sorted(set(c)):
        line = f'  {cl:22s}'
        for lo, hi in zip(bands[:-1], bands[1:]):
            mm = (c==cl)&(s>=lo)&(s<hi)
            line += f' [{lo}-{hi}) n={mm.sum():4d} r={r[mm].mean() if mm.sum() else 0:+.3f} |'
        print(line)
