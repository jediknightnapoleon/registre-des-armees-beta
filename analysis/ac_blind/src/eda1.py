from common import *
from collections import Counter
raw = load_raw()
print(len(raw['unit_key']))
d = regular_units(raw)
print('regular', len(d))
y = d.f('base_mp_cost')
for c in ['unit_class','unit_training_level','speed_code','corps_side','corps_number','fold','corps_holdout','unit_drill_set','rank_depth','unit_cap','division_id','placement_source','range_selection_method','guns']:
    print(c, Counter(d.s(c)).most_common(40))
print('price', np.percentile(y,[0,1,5,25,50,75,95,99,100]))
for c in ['men_display','accuracy','reload_skill','ammo','morale','melee_attack','melee_defense','charge_bonus','range','projectile_damage','projectile_reload_time','base_density']:
    v = d.f(c)
    print(c, np.sum(np.isnan(v)), np.nanpercentile(v,[0,5,50,95,100]))
