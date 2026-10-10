"""Army fixed effects (no cn/side) vs army-level aggregates."""
import numpy as np
from common import regular_units
from models import Ctx, build, ARMS
from features import gridge_fit
d = regular_units(); c = Ctx(d)
o = dict(size_mode="loglin", stat_mode="both", size_quad=True, size_by_class=True, art_feats=True, art_size_onehot=True, cn_mode="none", side=False, army=True)
FE = {}
for arm in ARMS:
    m = c.arm == arm
    D = build(c, m, arm, o); X = D.matrix()
    pen = np.array([{"main":1e-3,"cat":1.0,"inter":1.0,"army":1e-3}[g] for g in D.groups])
    a0, b = gridge_fit(X, c.ly[m], pen)
    for nm, bb in zip(D.names, b):
        if nm.startswith('army='):
            FE.setdefault(nm[5:], {})[arm] = bb
armies = sorted(FE)
# army aggregates
agg = {}
for a in armies:
    m = c.fk == a
    agg[a] = dict(cn=c.cn[m][0], emp=float(c.side[m][0]=='empire'), era=c.fk_era[m][0], xd=c.fk_xd[m][0],
                  n=m.sum(), sumcap=c.cap[m].sum(), summen=(c.cap*c.men)[m].sum(),
                  frac_inf=(c.arm[m]=='infantry').mean(), frac_cav=(c.arm[m]=='cavalry').mean(),
                  mor=c.stats['morale'][m].mean(), ma=c.stats['melee_attack'][m].mean(),
                  elite=np.isin(c.train[m], ['elite','well_trained']).mean())
keys = list(agg[armies[0]].keys())
for arm in ARMS:
    fe = np.array([FE[a].get(arm, np.nan) for a in armies]); ok = np.isfinite(fe)
    fe = fe - np.nanmean(fe)
    print(arm, 'FE sd', np.nanstd(fe))
    for k in keys:
        v = np.array([agg[a][k] for a in armies])
        print(f'   {k:10s} corr {np.corrcoef(v[ok], fe[ok])[0,1]:+.3f}')
# correlation of FE across arms
F = np.array([[FE[a].get(arm, np.nan) for arm in ARMS] for a in armies])
ok = np.all(np.isfinite(F),1)
print('FE corr across arms\n', np.corrcoef(F[ok].T).round(3))
# FE vs cn: fit log(cn+k)
for arm_i, arm in enumerate(ARMS):
    fe = F[:,arm_i]; ok = np.isfinite(fe)
    cn = np.array([agg[a]['cn'] for a in armies])
    for k in [-2, -1, 0, 1, 2, 3, 5]:
        x = np.log(cn[ok]+k) if k>-3 else None
        bb = np.polyfit(x, fe[ok], 1); r = fe[ok] - np.polyval(bb, x)
        print(arm, 'log(cn+%d) slope %.3f resid sd %.4f' % (k, bb[0], r.std()))
    x = cn[ok]; bb = np.polyfit(x, fe[ok], 1); print(arm, 'linear resid sd %.4f' % (fe[ok]-np.polyval(bb,x)).std())
    x = 1/cn[ok]; bb = np.polyfit(x, fe[ok], 1); print(arm, '1/cn resid sd %.4f' % (fe[ok]-np.polyval(bb,x)).std())
np.save('../out/army_fe.npy', np.array([[agg[a]['cn']] + [FE[a].get(arm, np.nan) for arm in ARMS] for a in armies]))
with open('../out/army_fe_keys.txt','w') as fh: fh.write('\n'.join(armies))
