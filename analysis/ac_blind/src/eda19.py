"""What explains army x class offsets? correlate with army-class aggregates."""
import numpy as np
from common import regular_units
from models import Ctx, build, ARMS, DEFAULT_PEN
from features import gridge_fit
d = regular_units(); c = Ctx(d)
o = dict(size_mode="loglin", stat_mode="both", size_quad=True, size_by_class=True, art_feats=True, art_size_onehot=True, art_proj=True,
         stat_by_class=True, size_spline=[60,100,150,220,320], cn_mode="log+0", side=True, army=True, army_class=True)
for arm in ARMS:
    m = c.arm==arm
    D = build(c, m, arm, o); X = D.matrix()
    pen = {**DEFAULT_PEN, "armycls": 0.3, "army": 0.3}
    p = np.array([pen[g] for g in D.groups])
    a0, b = gridge_fit(X, c.ly[m], p)
    names = D.names
    off = {nm[8:]: bb for nm, bb in zip(names, b) if nm.startswith('armycls=')}
    armyoff = {nm[5:]: bb for nm, bb in zip(names, b) if nm.startswith('army=')}
    keys = list(off)
    ov = np.array([off[k] for k in keys])
    print(arm, 'n army-class cells', len(keys), 'offset sd', ov.std(), 'army offset sd', np.std(list(armyoff.values())))
    feats = {}
    unitpred = a0 + X @ b - sum(X[:, j]*b[j] for j, nm in enumerate(names) if nm.startswith('armycls=') or nm.startswith('army='))
    for k in keys:
        a, cl = k.split('|')
        mm = (c.fk[m]==a)&(c.cls[m]==cl)
        ma = (c.fk[m]==a)
        feats.setdefault('log_n_cls', []).append(np.log(mm.sum()))
        feats.setdefault('share_cls_in_arm', []).append(mm.sum()/ma.sum())
        feats.setdefault('mean_unitpred_cls', []).append(unitpred[mm].mean())
        feats.setdefault('mean_unitpred_cls_minus_arm', []).append(unitpred[mm].mean()-unitpred[ma].mean())
        feats.setdefault('mean_logsize', []).append(np.log(c.size[m][mm]).mean())
        feats.setdefault('mean_morale', []).append(c.stats['morale'][m][mm].mean())
        feats.setdefault('cap_sum', []).append(c.cap[m][mm].sum())
    for k, v in feats.items():
        v = np.array(v); print(f'   {k:30s} corr {np.corrcoef(v, ov)[0,1]:+.3f}')
    # per-class offset sd
    for cl in sorted(set(c.cls[m])):
        sel = np.array([k.split('|')[1]==cl for k in keys])
        print(f'   {cl:22s} cells {sel.sum():4d} offset sd {ov[sel].std():.3f}')
