from common import *
from collections import defaultdict
raw = load_raw(); d = regular_units(raw)
y = d.f('base_mp_cost'); fk = d.s('faction_key'); cap = d.f('unit_cap'); men = d.f('men_display'); cn = d.f('corps_number')
cls = d.s('unit_class')
armies = sorted(set(fk))
rows = []
for a in armies:
    m = fk==a
    rows.append((a, cn[m][0], m.sum(), cap[m].sum(), (cap*y)[m].sum(), y[m].sum(), (cap*men)[m].sum(), y[m].mean()))
R = np.array([r[1:] for r in rows], dtype=float)
names = ['cn','n_units','sum_cap','sum_cap_price','sum_price','sum_cap_men','mean_price']
print(np.corrcoef(R.T).round(2))
for k in sorted(set(R[:,0])):
    mm = R[:,0]==k
    print(int(k), mm.sum(), 'n_units %.1f sumcap %.1f sum_cap_price %.0f (sd %.0f) sum_price %.0f (sd %.0f) cap*men %.0f' % (R[mm,1].mean(), R[mm,2].mean(), R[mm,3].mean(), R[mm,3].std(), R[mm,4].mean(), R[mm,4].std(), R[mm,5].mean()))
