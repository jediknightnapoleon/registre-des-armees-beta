from __future__ import annotations
import numpy as np
from load import load, col
rows = load()
P = col(rows, "regular_price"); C = col(rows, "commander_price"); s = col(rows, "command_stars")
arm = col(rows,"arm"); men_eq = col(rows,"regular_men")==col(rows,"commander_men")
print("price ranges", P.min(), P.max(), C.min(), C.max())
for st in range(8):
    m = (s==st)&men_eq
    if m.sum()<3: continue
    A = np.c_[P[m], np.ones(m.sum())]
    b,_,_,_ = np.linalg.lstsq(A, C[m], rcond=None)
    res = C[m]-A@b
    print(f"star {st} n={m.sum()} C = {b[0]:.4f} P + {b[1]:.1f}  MAE {np.mean(abs(res)):.1f} medres {np.median(res):.1f}")
    for a in ["infantry","cavalry","artillery"]:
        mm = m&(arm==a)
        if mm.sum()<5: continue
        A = np.c_[P[mm], np.ones(mm.sum())]
        b,_,_,_ = np.linalg.lstsq(A, C[mm], rcond=None)
        print(f"    {a:10s} n={mm.sum()} C = {b[0]:.4f} P + {b[1]:.1f}  MAE {np.mean(abs(C[mm]-A@b)):.1f}")
# global fit
A = np.c_[P, np.ones(len(P))] ; b=np.linalg.lstsq(A,C,rcond=None)[0]; print("all", b, np.mean(abs(C-A@b)))
# C as fn of P bins for star 0
m=(s==0)&men_eq
for lo,hi in [(0,200),(200,400),(400,700),(700,1000),(1000,1500),(1500,3000),(3000,9e9)]:
    mm=m&(P>=lo)&(P<hi)
    if mm.sum(): print(lo,hi,mm.sum(), "median C-P", np.median(C[mm]-P[mm]), "median C/P", np.median(C[mm]/P[mm]).round(3))
