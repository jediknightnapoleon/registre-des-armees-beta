from __future__ import annotations
import collections
import numpy as np
from load import load, col, STATS
rows = load()
s = col(rows, "command_stars"); arm = col(rows,"arm")
D = {k: col(rows,"commander_"+k)-col(rows,"regular_"+k) for k in STATS}
for a in ["infantry","cavalry","artillery"]:
  print("==",a)
  for st in range(8):
    m=(s==st)&(arm==a)
    if m.sum()==0: continue
    print(f" star {st} n={m.sum()}", {k: dict(collections.Counter(D[k][m].astype(int).tolist()).most_common(4)) for k in ["morale","melee_attack","melee_defense","charge_bonus","accuracy","reload_skill"]})
