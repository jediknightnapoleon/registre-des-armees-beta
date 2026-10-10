"""Print a term-by-term worked example of M1 for one unit (used in REPORT.md)."""
import csv, numpy as np
from common import regular_units, OUT
from features import STATS, BOOLS
from models import Ctx
d = regular_units(); c = Ctx(d)
i = [j for j in range(len(c.y)) if d.s('unit_name')[j].startswith('Infantería de Alcázar de San Juan')][0]
cf = {r['term']: float(r['coef']) for r in csv.DictReader(open(f'{OUT}/coefs_M1_infantry.csv', encoding='utf-8'))}
off = {(r['faction_key'], r['arm']): float(r['offset_log']) for r in csv.DictReader(open(f'{OUT}/army_offsets_M1.csv', encoding='utf-8'))}
offc = {(r['faction_key'], r['unit_class']): float(r['offset_log']) for r in csv.DictReader(open(f'{OUT}/army_class_offsets_M1.csv', encoding='utf-8'))}
cl = c.cls[i]; ls = np.log(c.men_raw[i])
print(d.s('unit_name')[i], cl, d.s('army_corps_name')[i], 'cn', c.cn[i], c.side[i], 'men_raw', c.men_raw[i], 'train', c.train[i], 'speed', c.speed[i], 'price', c.y[i])
print({s: c.stats[s][i] for s in STATS}, [b for b in BOOLS if c.bools[b][i]])
tot = 0
def add(name, v):
    global tot; tot += v; print(f'  {name:45s} {v:+.4f}   running {tot:+.4f}')
add('constant (line)', cf['intercept'] + cf['class=' + cl])
add(f'log size slope x log({c.men_raw[i]:.0f})', (cf['log_size'] + cf['log_size:' + cl]) * ls)
for k in [150, 200, 260, 340]:
    v = cf[f'hinge_log_size_{k}'] * max(0, ls - np.log(k))
    if v: add(f'hinge {k}', v)
st = 0
for s in STATS:
    x = c.stats[s][i]
    st += cf.get(s, 0) * x + (cf.get('log1p_' + s, 0) + cf.get(f'log1p_{s}:{cl}', 0)) * np.log1p(x)
add('stat terms (7 stats, linear + log)', st)
ab = sum(cf.get(b, 0) for b in BOOLS if c.bools[b][i]); add('abilities', ab)
add('training ' + c.train[i], cf['train=' + c.train[i]])
add('speed ' + c.speed[i], cf['speed=' + c.speed[i]])
add(f'log(cn={c.cn[i]:.0f})', cf['log_cn_k'] * np.log(c.cn[i]))
add('empire', cf['empire'] * (c.side[i] == 'empire'))
print(f'  price without army tables = exp({tot:.4f}) = {np.exp(tot):.1f}')
add('army offset', off[(c.fk[i], 'infantry')]); add('army x class offset', offc.get((c.fk[i], cl), 0))
print(f'  price = exp({tot:.4f}) = {np.exp(tot):.1f}   (true {c.y[i]:.0f})')
