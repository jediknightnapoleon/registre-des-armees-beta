from common import *
from collections import Counter
raw = load_raw(); d = regular_units(raw)
m = np.array([c.startswith('artillery') for c in d.s('unit_class')])
cols = ['unit_class','men_display','guns','projectile_damage','projectile_reload_time','range','range_selection_method','accuracy','reload_skill','morale','unit_training_level','speed_code','corps_number','base_mp_cost','weapon_key','projectile_key']
idx = np.where(m)[0][:60]
for i in idx:
    print(' '.join(str(d.s(c)[i]) for c in cols))
print(Counter(d.s('projectile_key')[m]).most_common(50))
men = d.f('men_display')[m]; g = d.f('guns')[m]
print('men per gun', Counter((men/g).round(1)).most_common(20))
