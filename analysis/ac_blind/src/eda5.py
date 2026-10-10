from common import *
from collections import Counter
raw = load_raw()
d = regular_units(raw)
f = d.s('fold')
for i in np.where(f=='')[0]:
    print(d.s('unit_key')[i], d.s('unit_class')[i], d.s('speed_code')[i], d.s('unit_training_level')[i], d.s('corps_number')[i], d.s('base_mp_cost')[i])
# holdout armies
h = d.s('corps_holdout')=='1'
print(Counter(zip(d.s('faction_key')[h], d.s('corps_number')[h], d.s('corps_side')[h])))
# all rows
isg = boolc(raw['is_general']); cv = boolc(raw['is_commander_variant'])
print('general', isg.sum(), 'cmdvar', cv.sum(), 'staff', (isg&~cv).sum())
print(Counter(raw['fold'][isg&~cv]), Counter(raw['fold'][cv]))
print(Counter(raw['men_raw'][isg&~cv]))
# armies: names
names = sorted(set(zip(raw['corps_number'], raw['faction_key'], raw['army_corps_name'], raw['corps_side'])), key=lambda t:(int(t[0]),t[1]))
for t in names[:400]: print(t)
