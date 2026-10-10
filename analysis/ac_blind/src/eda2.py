from common import *
from collections import Counter, defaultdict
raw = load_raw()
d = regular_units(raw)
y = d.f('base_mp_cost'); men = d.f('men_display'); cls = d.s('unit_class')
uk = d.s('unit_key'); fk = d.s('faction_key')
c = Counter(uk); print('unique unit keys', len(c), 'max dup', c.most_common(5))
# same unit key different prices?
g = defaultdict(set)
for k,p in zip(uk,y): g[k].add(p)
print('keys with >1 price', sum(len(v)>1 for v in g.values()))
# unit key structure
print(uk[:30])
# per class: log-log slope of price on men
for cl in sorted(set(cls)):
    m = cls==cl
    if cl.startswith('artillery'):
        x = d.f('guns')[m]
    else:
        x = men[m]
    b = np.polyfit(np.log(x), np.log(y[m]), 1)
    print(f"{cl:22s} n={m.sum():5d} slope={b[0]:.3f} price med={np.median(y[m]):.0f} size med={np.median(x):.0f} range {x.min()}-{x.max()}")
