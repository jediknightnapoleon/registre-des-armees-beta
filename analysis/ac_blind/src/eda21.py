import numpy as np
from collections import Counter, defaultdict
from common import load_raw, boolc, num
raw = load_raw()
isg = boolc(raw['is_general']); cv = boolc(raw['is_commander_variant'])
st = np.where(isg&~cv)[0]
y = num(raw['base_mp_cost'])[st]; s = num(raw['command_stars'],0)[st]; cn = num(raw['corps_number'])[st]
print('price<=10:', (y<=10).sum(), Counter(zip(s[y<=10], raw['speed_code'][st][y<=10])))
for k in range(10):
    m = (s==k)&(y>10)
    if m.sum(): print(k, m.sum(), 'median price', np.median(y[m]), 'median price*cn/8', np.median(y[m]*cn[m]/8), np.percentile(y[m]*cn[m]/8,[10,90]).round(0))
# per army: how many staff generals
c = Counter(raw['faction_key'][st]); print(Counter(c.values()))
# show a few armies fully
for a in list(c)[:6]:
    m = raw['faction_key'][st]==a
    print(a, raw['corps_number'][st][m][0], sorted(zip(s[m], y[m], raw['speed_code'][st][m], raw['fold'][st][m])))
# other columns varying among staff
for col in raw:
    v = set(raw[col][st])
    if 1 < len(v) < 15: print(col, Counter(raw[col][st]).most_common(6))
