from __future__ import annotations
import collections
import numpy as np
from load import load, col
rows = load()
fac=col(rows,"faction_key"); s=col(rows,"command_stars"); arm=col(rows,"arm")
kind=np.array(["tow" if f.startswith("ntw3_tow_") else ("ac" if "_ac_" in f else "custom") for f in fac])
print(collections.Counter(kind.tolist()))
print("armies", len(set(fac.tolist())))
for k in ["tow","ac","custom"]:
    m=kind==k; print(k, collections.Counter(s[m].tolist()), collections.Counter(col(rows,"corps_number")[m].tolist()))
print(collections.Counter(zip(fac.tolist(), col(rows,'army_corps_name').tolist())).most_common(60))
