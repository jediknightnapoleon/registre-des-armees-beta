import numpy as np, re
from collections import Counter
from common import load_raw, boolc, num
raw = load_raw()
isg = boolc(raw['is_general']); cv = boolc(raw['is_commander_variant'])
y = num(raw['base_mp_cost']); uk = raw['unit_key']; fk = raw['faction_key']
reg = {(f, k): i for i, (f, k) in enumerate(zip(fk, uk)) if not isg[i]}
ix = np.where(cv)[0]
miss = 0; rows = []
for i in ix:
    base = re.sub(r'_com_\d+$', '', uk[i])
    j = reg.get((fk[i], base))
    if j is None: miss += 1; continue
    rows.append((i, j))
print('cmd variants', len(ix), 'unmatched', miss)
I = np.array([r[0] for r in rows]); J = np.array([r[1] for r in rows])
stars = num(raw['command_stars'], 0)[I]
ratio = y[I]/y[J]; diff = y[I]-y[J]
print('stars', Counter(stars))
for s in sorted(set(stars)):
    m = stars==s
    print(f'stars {s:.0f} n={m.sum():4d} ratio med {np.median(ratio[m]):.3f} p10 {np.percentile(ratio[m],10):.3f} p90 {np.percentile(ratio[m],90):.3f}  diff med {np.median(diff[m]):.0f} p10 {np.percentile(diff[m],10):.0f} p90 {np.percentile(diff[m],90):.0f}')
# do men_raw / stats differ between variant and regular?
for col in ['men_raw','morale','melee_attack','accuracy','reload_skill','unit_class','unit_training_level','speed_code','is_shock_resistant','can_inspire']:
    same = np.mean(raw[col][I]==raw[col][J]); print(col, 'same frac', round(same,3))
print(Counter(raw['unit_class'][I]).most_common(3), Counter(raw['men_raw'][np.where(isg&~cv)[0]]))
# staff generals
st = np.where(isg&~cv)[0]
print('staff price', np.percentile(y[st],[0,10,50,90,100]), Counter(num(raw['command_stars'], 0)[st]))
for col in ['speed_code','unit_training_level','morale','melee_attack','men_raw','corps_number']:
    print(col, Counter(raw[col][st]).most_common(8))
