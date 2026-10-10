"""Shape of stat effects: one-hot each stat (binned) in a log model with army FE, infantry & cavalry."""
import numpy as np
from common import regular_units
from harness import arm_vec
from features import Design, gridge_fit, STATS, BOOLS
d = regular_units(); y = d.f("base_mp_cost"); ly = np.log(y); arm = arm_vec(d)
size = np.where(arm == "artillery", d.f("guns", 0), d.f("men_raw"))
cls = d.s('unit_class')
for a in ['infantry','cavalry']:
    m = arm == a
    for target in ['morale','melee_attack','melee_defense','charge_bonus','accuracy','reload_skill']:
        D = Design()
        D.add("log_size", np.log(size[m])); D.add("log_size2", np.log(size[m])**2)
        for s in STATS:
            if s != target: D.add(s, d.f(s, 0)[m])
        v = d.f(target,0)[m]
        qs = np.unique(np.percentile(v, np.linspace(0,100,9)))
        bins = np.digitize(v, qs[1:-1])
        D.add_onehot('bin', bins.astype(str), drop='0')
        for b in BOOLS:
            vv = d.b(b)[m]
            if 0 < vv.sum() < m.sum(): D.add(b, vv)
        D.add_onehot("class", cls[m]); 
        D.add_onehot("speed", d.s("speed_code")[m], group="cat")
        D.add_onehot("army", d.s("faction_key")[m], group="army")
        pen = np.array([{"main": 1e-3, "cat": 1.0, "army": 1.0}[g] for g in D.groups])
        X = D.matrix(); a0, b = gridge_fit(X, ly[m], pen)
        coefs = [0.0] + [bb for nm, bb in zip(D.names, b) if nm.startswith('bin=')]
        centers = [v[bins==k].mean() for k in range(len(coefs))]
        print(a, target, ' '.join(f'{c:.0f}:{e:+.2f}' for c, e in zip(centers, coefs)))
