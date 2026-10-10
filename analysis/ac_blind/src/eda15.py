import numpy as np
from collections import Counter
from common import regular_units
from features import STATS, BOOLS
d = regular_units()
fk = d.s('faction_key'); cls = d.s('unit_class')
c = Counter(zip(fk, cls))
for (a, k), n in c.most_common(4):
    m = (fk==a)&(cls==k)
    print('====', a, k, n, 'cn', d.s('corps_number')[m][0])
    cols = ['men_raw','base_mp_cost','unit_training_level','speed_code'] + STATS + ['range','unit_cap','division_id']
    rows = sorted(zip(*[d.s(cc)[m] for cc in cols]), key=lambda r: float(r[1]))
    bl = [b for b in BOOLS if d.b(b)[m].any()]
    B = {b: d.b(b)[m] for b in bl}
    print(cols, bl)
    for r in rows: print(' '.join(f'{x:>6s}' for x in r))
