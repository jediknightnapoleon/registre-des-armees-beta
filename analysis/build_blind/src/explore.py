"""Exploration: univariate within-faction signal of build features (training only).

For each candidate build feature x we fit  logit P(win) = a + b*faction_logit + c*z(x)
on training decisive armies and print c with its z-score, with and without the
Elo control (logit of the pre-game expected score implied by the rating change).
Nothing here touches the test rows.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from common import (fit_logistic, load_armies, load_cards, logit, faction_feature)

cards = load_cards()
armies = load_armies(cards)
dec = np.array([i for i, a in enumerate(armies) if a.y is not None])
trm = np.array([a.train for a in armies])
F = faction_feature(armies, dec, trm)
tr = np.array([i for i in dec if trm[i]])
y = np.array([armies[i].y for i in tr], float)
f = F[tr]

feat = defaultdict(list)
for i in tr:
    a = armies[i]
    fc = cards[a.faction]
    cs = [(fc[k], n) for k, n in a.counts.items()]
    units = [(c, n) for c, n in cs if c.kind != "staff"]
    staff = [c for c, n in cs if c.kind == "staff"]
    P = sum(c.cost * n for c, n in cs)
    V = sum(c.value_adj * n for c, n in units)
    Pu = sum(c.cost * n for c, n in units)
    N = sum(n for c, n in cs)
    feat["n_cards"].append(N)
    feat["cost_k"].append(P / 1000)
    feat["unspent_k"].append(max(0, 10000 - P) / 1000)
    feat["surplus_k"].append((V - Pu) / 1000)
    feat["value_ratio"].append(V / Pu if Pu else 1)
    feat["surplus_raw_k"].append((sum(c.value * n for c, n in units) - Pu) / 1000)
    for arm in ["infantry", "cavalry", "artillery"]:
        feat[f"cost_{arm}_k"].append(sum(c.cost * n for c, n in units if c.arm == arm) / 1000)
        feat[f"n_{arm}"].append(sum(n for c, n in units if c.arm == arm))
        feat[f"surplus_{arm}_k"].append(sum((c.value_adj - c.cost) * n for c, n in units if c.arm == arm) / 1000)
    for cl in ["infantry_line", "infantry_light", "infantry_grenadiers", "infantry_militia",
               "infantry_skirmishers", "cavalry_heavy", "cavalry_light", "cavalry_standard",
               "cavalry_lancers", "artillery_foot", "artillery_horse"]:
        feat[f"n_{cl}"].append(sum(n for c, n in units if c.cls == cl))
    feat["stars"].append(staff[0].stars if staff else 0)
    feat["staff_cost_k"].append(staff[0].cost / 1000 if staff else 0)
    feat["n_commander"].append(sum(n for c, n in units if c.kind == "commander"))
    feat["models_k"].append(sum(c.models * n for c, n in units) / 1000)
    feat["mean_tier_inf"].append(np.mean([c.tier for c, n in units for _ in range(n) if c.arm == "infantry"] or [3]))
    feat["mean_tier_cav"].append(np.mean([c.tier for c, n in units for _ in range(n) if c.arm == "cavalry"] or [3]))
    feat["n_corps"].append(len({c.corps for c, n in cs}))
    feat["mean_unit_cost"].append(Pu / max(1, N - 1) / 1000)

elo = np.array([armies[i].elo_e if armies[i].elo_e is not None else 0.5 for i in tr])
le = logit(elo)
print("train decisive", len(tr), "elo missing", sum(armies[i].elo_e is None for i in tr))
X = np.column_stack([np.ones(len(tr)), f, le])
b, C = fit_logistic(X, y)
print("faction + elo coefs", b, np.sqrt(np.diag(C)))
print(f"{'feature':24s} {'mean':>8s} {'sd':>7s} {'coef':>7s} {'z':>6s} | {'coef|elo':>8s} {'z':>6s}")
for k, v in feat.items():
    x = np.array(v, float)
    sd = x.std() or 1
    z = (x - x.mean()) / sd
    b1, C1 = fit_logistic(np.column_stack([np.ones(len(tr)), f, z]), y)
    b2, C2 = fit_logistic(np.column_stack([np.ones(len(tr)), f, z, le]), y)
    print(f"{k:24s} {x.mean():8.3f} {sd:7.3f} {b1[2]:7.3f} {b1[2]/np.sqrt(C1[2,2]):6.2f} | {b2[2]:8.3f} {b2[2]/np.sqrt(C2[2,2]):6.2f}")
