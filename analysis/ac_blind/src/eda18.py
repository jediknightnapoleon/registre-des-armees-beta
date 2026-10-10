import numpy as np
from collections import Counter
from common import regular_units
from models import Ctx
d = regular_units(); c = Ctx(d)
p = np.load('../out/pred_E07d.npy')
ok = (c.fold>0)&(c.arm=='artillery')
r = np.log(c.y/p)
def tab(name, v):
    print(name)
    for k in sorted(set(v[ok]), key=str):
        m = ok&(v==k)
        print(f'   {str(k):30s} n={m.sum():4d} mean r {r[m].mean():+.3f} MAPE {100*np.mean(np.abs(c.y[m]-p[m])/c.y[m]):5.1f}')
tab('guns', c.guns); tab('class', c.cls); tab('proj', d.s('projectile_key')); tab('train', c.train); tab('speed', c.speed)
tab('cap', c.cap)
tab('stamina', c.bools['has_stamina']); 
# men per gun
tab('menraw', c.men_raw)
