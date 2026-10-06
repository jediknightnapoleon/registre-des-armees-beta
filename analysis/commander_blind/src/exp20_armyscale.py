"""Exp 20: is the commander premium scaled per army?  C = a_arm P + b_arm + size + lam_army * premium.

premium = P*(w.d) + men*(v.d) + s*(k)   (the J8 premium block, without corps*s)
lam_army fitted by alternating LAD (army lookup, 55 values), then a parametric
lam = 1 + c*(corps-9) + e*imperial is tried.
"""
from __future__ import annotations
import numpy as np
from harness import cv_custom, metrics, log_result, Y, fit_linear
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
BASE = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART])
PREM = np.column_stack([P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S])
armies = sorted(set(FAC.tolist())); aid = np.array([armies.index(f) for f in FAC])

def wmedian(x, w):
    o = np.argsort(x); x, w = x[o], w[o]; c = np.cumsum(w)
    return x[np.searchsorted(c, c[-1] / 2)]

def fit_army(tr, iters=8):
    lam = np.ones(len(armies))
    for _ in range(iters):
        L = lam[aid]
        X = np.column_stack([BASE, L[:, None] * PREM])
        b = fit_linear(X[tr], Y[tr], "lad")
        rest = BASE @ b[:BASE.shape[1]]; prem = PREM @ b[BASE.shape[1]:]
        for j in range(len(armies)):
            m = tr & (aid == j) & (np.abs(prem) > 1)
            if m.sum() >= 3:
                # minimise sum |Y - rest - lam*prem| -> weighted median of (Y-rest)/prem with weights |prem|
                lam[j] = wmedian((Y[m] - rest[m]) / prem[m], np.abs(prem[m]))
        lam /= np.median(lam)
    L = lam[aid]
    X = np.column_stack([BASE, L[:, None] * PREM])
    b = fit_linear(X[tr], Y[tr], "lad")
    return (lambda m: X[m] @ b), {"lam": dict(zip(armies, lam.round(3))), "coef": b}

p, prm = cv_custom(fit_army)
log_result("X1", "a_arm P + b_arm + size + lam_army*(P w.d + men v dmo + k s) (55 army scales)", 8 + 7 + 54, metrics(p), notes="army lookup on premium", params=prm)
lam = prm["lam"]
corps_of = {f: CORPS[FAC == f][0] for f in armies}; imp_of = {f: SIDE[FAC == f][0] == "imperial" for f in armies}
la = np.array([lam[f] for f in armies]); co = np.array([corps_of[f] for f in armies]); im = np.array([imp_of[f] for f in armies], float)
n = np.array([(FAC == f).sum() for f in armies])
Xl = np.column_stack([np.ones(len(armies)), co - 9, im])
bl = np.linalg.lstsq(Xl * np.sqrt(n)[:, None], la * np.sqrt(n), rcond=None)[0]
print("lam ~ 1 + c(corps-9) + e*imperial (weighted OLS over armies):", bl.round(4), " R2:",
      1 - np.sum(n * (la - Xl @ bl) ** 2) / np.sum(n * (la - np.average(la, weights=n)) ** 2))
for f in sorted(armies, key=lambda f: lam[f]):
    print(f"   {f:22s} corps {int(corps_of[f]):2d} {'imp' if imp_of[f] else 'coa'} n={(FAC==f).sum():4d} lam {lam[f]:.3f}")
