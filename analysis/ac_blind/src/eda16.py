import numpy as np
from common import load_raw
raw = load_raw()
ix = np.where((raw['faction_key']=='ntw3_ac_b11_r5_189')&(raw['unit_class']=='cavalry_lancers'))[0]
skip = {'icon_name','icon_filename','icon_path','command_star_icon_path','command_star_strip_path','command_star_layout','guerrilla_badge_path','guerrilla_badge_layout'}
varying = [c for c in raw if c not in skip and len(set(raw[c][ix]))>1]
print(varying)
rows = sorted(ix, key=lambda i: float(raw['base_mp_cost'][i]))
for i in rows:
    print(' | '.join(raw[c][i] for c in varying))
