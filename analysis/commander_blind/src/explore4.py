from __future__ import annotations
import collections
import numpy as np
from load import load, col
rows = load()
P = col(rows, "regular_price"); C = col(rows, "commander_price"); s = col(rows, "command_stars"); arm=col(rows,"arm")
dm = col(rows,"commander_melee_attack")-col(rows,"regular_melee_attack")
drl = col(rows,"commander_reload_skill")-col(rows,"regular_reload_skill")
men_eq = col(rows,"regular_men")==col(rows,"commander_men")
print("C==1:", (C==1).sum(), " C<=10:", (C<=10).sum())
m = (s==0)&(arm=="infantry")&(dm==0)&(drl==5)&men_eq
A=np.c_[P[m],np.ones(m.sum())]; b=np.linalg.lstsq(A,C[m],rcond=None)[0]; r=C[m]-A@b
print("inf star0 clean n",m.sum(),b, "MAE",np.mean(abs(r)), np.percentile(r,[0,5,25,50,75,95,100]))
# residual vs P, corps, side, class
fac=col(rows,"faction_key")[m]; cn=col(rows,"corps_number")[m]; uc=col(rows,"unit_class")[m]; tl=col(rows,"training_level")[m]
for name,v in [("corps",cn),("class",uc),("train",tl)]:
    print(name, {k: (int((v==k).sum()), round(float(np.median(r[v==k])),1)) for k in sorted(set(v.tolist()))})
tow = np.array([f.startswith("ntw3_tow_") for f in fac])
print("tow", tow.sum(), np.median(r[tow]), "non", np.median(r[~tow]))
# ratio C+k / P for various k
for k in [80,90,95,100,105,110,120]:
    q=(C[m]+k)/P[m]; print(k, np.std(q).round(4), np.median(q).round(4))
