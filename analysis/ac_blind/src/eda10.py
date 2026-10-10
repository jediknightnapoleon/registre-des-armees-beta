import numpy as np
from common import load_raw, boolc
raw = load_raw()
fk = raw['faction_key']; cls = raw['unit_class']; men = raw['men_display']; p = raw['base_mp_cost']
ix = np.where((cls=='cavalry_lancers') & (men=='60') & np.isin(p, ['752','764']))[0]
print(ix)
for c in raw:
    vals = [raw[c][i] for i in ix]
    if len(set(vals))>1: print(c, vals)
