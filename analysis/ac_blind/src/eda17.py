import numpy as np
from common import regular_units
from models import Ctx
d = regular_units(); c = Ctx(d)
p = np.load('../out/pred_E06a.npy')
ok = c.fold>0
e = p - c.y; ae = np.abs(e); ape = ae/c.y
print('by class')
for cl in sorted(set(c.cls)):
    m = ok&(c.cls==cl)
    print(f'  {cl:22s} n={m.sum():5d} MAE {ae[m].mean():6.1f} MAPE {100*ape[m].mean():5.2f} bias {np.median(np.log(p[m]/c.y[m])):+.3f}')
print('by training')
for t in ['elite','well_trained','trained','poorly_trained','mob']:
    m = ok&(c.train==t); print(f'  {t:15s} n={m.sum():5d} MAE {ae[m].mean():6.1f} MAPE {100*ape[m].mean():5.2f}')
print('by cn')
for k in range(3,14):
    m = ok&(c.cn==k); print(f'  {k:3d} n={m.sum():5d} MAE {ae[m].mean():6.1f} MAPE {100*ape[m].mean():5.2f}')
print('by price band')
for lo,hi in [(0,200),(200,400),(400,700),(700,1000),(1000,1500),(1500,4000)]:
    m = ok&(c.y>=lo)&(c.y<hi); print(f'  {lo}-{hi} n={m.sum():5d} MAE {ae[m].mean():6.1f} MAPE {100*ape[m].mean():5.2f}')
# worst rows
o = np.argsort(-ape*ok)[:25]
for i in o:
    print(f'{d.s("unit_key")[i]:35s} {c.cls[i]:20s} men {c.men_raw[i]:4.0f} g {c.guns[i]:.0f} y {c.y[i]:6.0f} p {p[i]:7.1f} {d.s("unit_name")[i][:50]}')
# army-level MAPE concentration
from collections import defaultdict
am = defaultdict(list)
for i in np.where(ok)[0]: am[c.fk[i]].append(ape[i])
v = sorted(((np.mean(x), len(x), k) for k,x in am.items()), reverse=True)
print('worst armies', [(round(100*a,1), n, k) for a,n,k in v[:10]])
print('best armies', [(round(100*a,1), n, k) for a,n,k in v[-5:]])
