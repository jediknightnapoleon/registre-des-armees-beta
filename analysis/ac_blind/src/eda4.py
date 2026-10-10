from common import *
from collections import Counter, defaultdict
raw = load_raw()
d = regular_units(raw)
y = d.f('base_mp_cost'); men = d.f('men_display'); cls = d.s('unit_class')
arm = np.array([ARM_OF_CLASS[c] for c in cls])
fk = d.s('faction_key'); cn = d.f('corps_number')
stats = ['accuracy','reload_skill','ammo','morale','melee_attack','melee_defense','charge_bonus']
bools = ['can_form_square','has_stamina','is_shock_resistant','can_inspire','has_guerrilla_deployment','can_place_stakes','can_place_mines','scares_enemies','can_build_barricades','skirmish','guard_mode','can_snipe','pike_square']
def onehot(v):
    u = sorted(set(v)); return np.column_stack([(v==x).astype(float) for x in u]), u
for a in ['infantry','cavalry','artillery']:
    m = arm==a
    size = d.f('guns')[m] if a=='artillery' else men[m]
    parts = [np.log(size)[:,None]]
    parts.append(np.column_stack([d.f(s,0)[m] for s in stats]))
    parts.append(np.column_stack([d.b(b)[m].astype(float) for b in bools]))
    C,_ = onehot(cls[m]); parts.append(C)
    T,_ = onehot(d.s('unit_training_level')[m]); parts.append(T[:,1:])
    S,_ = onehot(d.s('speed_code')[m]); parts.append(S[:,1:])
    X0 = np.column_stack(parts)
    lp = np.log(y[m])
    def fit(X):
        b,*_ = np.linalg.lstsq(X, lp, rcond=None); r = lp - X@b
        return r, b
    r0,_ = fit(X0)
    F,fu = onehot(fk[m]); 
    r1,b1 = fit(np.column_stack([X0, F[:,1:]]))
    # corps number only
    N,_ = onehot(cn[m].astype(int).astype(str)); 
    r2,_ = fit(np.column_stack([X0, N[:,1:]]))
    print(a, m.sum(), 'resid sd no army', r0.std(), 'with corps_number', r2.std(), 'with army FE', r1.std())
    # army effects relation to corps number
    eff = defaultdict(list)
    for f_, rr in zip(fk[m], r0): eff[f_].append(rr)
    cnmap = dict(zip(fk, cn))
    ev = np.array([np.mean(v) for v in eff.values()]); en = np.array([cnmap[k] for k in eff])
    print('   corr(army mean resid, corps_number)', np.corrcoef(ev,en)[0,1])
    for k in sorted(set(en)):
        print('     cn', int(k), 'n armies', (en==k).sum(), 'mean resid %.3f sd %.3f' % (ev[en==k].mean(), ev[en==k].std()))
