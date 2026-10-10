from common import *
from collections import Counter, defaultdict
raw = load_raw()
d = regular_units(raw)
y = d.f('base_mp_cost'); men = d.f('men_display'); cls = d.s('unit_class')
stats = ['accuracy','reload_skill','ammo','morale','melee_attack','melee_defense','charge_bonus','range','projectile_damage','projectile_reload_time','rank_depth','base_density','unit_cap','corps_number']
X = np.column_stack([d.f(s, 0) for s in stats])
lp = np.log(y)
for cl in ['infantry_line','cavalry_light','artillery_foot']:
    m = cls==cl
    size = d.f('guns')[m] if cl.startswith('art') else men[m]
    print(cl)
    for j,s in enumerate(stats):
        v = X[m,j]
        if v.std()==0: continue
        print(f"  {s:25s} corr(logp)={np.corrcoef(v,lp[m])[0,1]:+.3f} corr(log p/size)={np.corrcoef(v,lp[m]-np.log(size))[0,1]:+.3f}  corr(size)={np.corrcoef(v,size)[0,1]:+.3f}")
    for b in ['can_form_square','has_stamina','is_shock_resistant','can_inspire','has_guerrilla_deployment','can_place_stakes','can_place_mines','scares_enemies','can_build_barricades','skirmish','guard_mode','can_snipe','pike_square']:
        v = d.b(b)[m]
        if v.mean() in (0,1): continue
        r = lp[m]-np.log(size)
        print(f"  {b:25s} frac={v.mean():.2f} diff log p/size = {r[v].mean()-r[~v].mean():+.3f}")
    tl = d.s('unit_training_level')[m]
    r = lp[m]-np.log(size)
    for t in ['elite','well_trained','trained','poorly_trained','mob']:
        mm = tl==t
        if mm.sum(): print(f"  train {t:15s} n={mm.sum()} mean log p/size={r[mm].mean():.3f}")
