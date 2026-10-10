"""Find groups of units identical except for size within the same army -> exact size curve."""
import numpy as np
from collections import defaultdict
from common import regular_units
from features import STATS, BOOLS
d = regular_units(); y = d.f("base_mp_cost")
keycols = ['faction_key','unit_class','speed_code','unit_training_level','weapon_key','unit_drill_set'] + STATS + BOOLS
K = list(zip(*[d.s(c) for c in keycols]))
men = d.f('men_display'); g = d.f('guns',0)
grp = defaultdict(list)
for i,k in enumerate(K): grp[k].append(i)
pairs = []
for k, ix in grp.items():
    if len(ix) < 2: continue
    sizes = set(men[ix])
    if len(sizes) < 2: 
        # identical units, same price?
        pr = set(y[ix])
        if len(pr)>1: pairs.append(('SAMESIZE', k[1], [(men[i], y[i]) for i in ix]))
        continue
    pairs.append((k[0], k[1], sorted([(men[i], g[i], y[i]) for i in ix])))
print(len(pairs))
for p in pairs[:80]: print(p)
