import numpy as np, re
from collections import Counter
from common import regular_units
d = regular_units()
fn = d.s('icon_filename'); uk = d.s('unit_key'); fk = d.s('faction_key')
pref = []
for f in fn:
    m = re.match(r'(.*?)_(inf|cav|art)_', f)
    pref.append(m.group(1) if m else 'NONE:'+f[:30])
pref = np.array(pref, dtype=object)
c = Counter(pref); print(len(c)); print(c.most_common(80))
# armies per prefix and prefixes per army
from collections import defaultdict
pa = defaultdict(set)
for p, a in zip(pref, fk): pa[a].add(p)
print(Counter(len(v) for v in pa.values()))
# icon numeric code vs faction code
same = 0; tot=0
for f, u, a in zip(fn, uk, fk):
    m = re.search(r'_(\d{3})_(\d{3})_(\d+)_icon', f)
    if m:
        tot += 1; same += (m.group(1) == a.split('_')[-1])
print('icon code == faction code', same, tot)
print(Counter(d.s('icon_match_method')))
