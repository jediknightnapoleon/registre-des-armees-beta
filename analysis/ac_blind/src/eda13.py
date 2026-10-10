"""Army FE (common across arms) vs log cn and roster-value aggregates."""
import numpy as np
from common import regular_units
from models import Ctx, build, ARMS
from features import gridge_fit, Design
d = regular_units(); c = Ctx(d)
# one joint model: per-arm unit features but a single army FE shared across arms
o = dict(size_mode="loglin", stat_mode="both", size_quad=True, size_by_class=True, art_feats=True, art_size_onehot=True, cn_mode="none", side=False)
n = len(c.y)
blocks = []; names=[]; groups=[]
for arm in ARMS:
    m = c.arm == arm
    D = build(c, m, arm, o)
    X = np.zeros((n, len(D.names))); X[m] = D.matrix()
    blocks.append(X); names += [f'{arm}:{x}' for x in D.names]; groups += D.groups
    A = np.zeros((n,1)); A[m,0]=1; blocks.append(A); names.append(f'{arm}:icpt'); groups.append('main')
D2 = Design(); D2.add_onehot('army', c.fk, group='army')
blocks.append(D2.matrix()); names += D2.names; groups += D2.groups
X = np.column_stack(blocks)
pen = np.array([{"main":1e-3,"cat":1.0,"inter":1.0,"army":1e-3}[g] for g in groups])
a0, b = gridge_fit(X, c.ly, pen)
isarmy = np.array([nm.startswith('army=') for nm in names])
unitpred = a0 + X[:, ~isarmy] @ b[~isarmy]
armies = [nm[5:] for nm in np.array(names)[isarmy]]
fe = b[isarmy]
r = c.ly - a0 - X@b
print('resid sd joint', r.std())
cn = np.array([c.cn[c.fk==a][0] for a in armies])
bb = np.polyfit(np.log(cn), fe, 1); res = fe - np.polyval(bb, np.log(cn))
print('fe ~ log cn slope', bb, 'resid sd', res.std())
v = np.exp(unitpred)
aggs = {}
for a in armies:
    m = c.fk==a
    aggs.setdefault('log_sum_cap_v',[]).append(np.log((c.cap*v)[m].sum()))
    aggs.setdefault('log_sum_v',[]).append(np.log(v[m].sum()))
    aggs.setdefault('log_mean_v',[]).append(np.log(v[m].mean()))
    aggs.setdefault('mean_unitpred',[]).append(unitpred[m].mean())
    aggs.setdefault('log_n',[]).append(np.log(m.sum()))
    aggs.setdefault('log_sumcap',[]).append(np.log(c.cap[m].sum()))
    aggs.setdefault('xd',[]).append(c.fk_xd[m][0])
    aggs.setdefault('era',[]).append(c.fk_era[m][0])
    aggs.setdefault('emp',[]).append(float(c.side[m][0]=='empire'))
    aggs.setdefault('r',[]).append(float(c.fk_xl[m][0]=='r'))
    aggs.setdefault('fknum',[]).append(float(a.split('_')[-1]))
    aggs.setdefault('frac_cav',[]).append((c.arm[m]=='cavalry').mean())
    aggs.setdefault('frac_art',[]).append((c.arm[m]=='artillery').mean())
for k,vv in aggs.items():
    vv = np.array(vv)
    print(f'{k:15s} corr with FE resid {np.corrcoef(vv,res)[0,1]:+.3f}   with FE {np.corrcoef(vv,fe)[0,1]:+.3f}  with log cn {np.corrcoef(vv,np.log(cn))[0,1]:+.3f}')
# multiple regression of FE on log cn + aggregates
Z = np.column_stack([np.log(cn)] + [np.array(aggs[k]) for k in ['log_sum_cap_v','log_mean_v','log_n','xd','emp','r','frac_cav','frac_art']])
Z1 = np.column_stack([np.ones(len(fe)), Z])
bz,*_ = np.linalg.lstsq(Z1, fe, rcond=None)
print('multi-reg coefs', bz.round(3), 'resid sd', (fe - Z1@bz).std())
np.savez('../out/army_fe_joint.npz', armies=np.array(armies), fe=fe, cn=cn, res=res)
