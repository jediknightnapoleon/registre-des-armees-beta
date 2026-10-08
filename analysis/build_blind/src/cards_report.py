"""How good is each card, and which kinds of cards win more than their price suggests?

All fits on rated decisive TRAINING armies, with the Elo skill control.

out/card_scores.csv   one row per card: price, paper value, training usage, and
                      w_small   its worth (logit per copy) under the recommended small+elo model,
                      w_comp    its worth under the full composition model comp+elo,
                      bonus     its shrunk card-specific bonus (hybsmall+elo, within-army centred).
out/class_effects.csv per unit class x kind: usage-weighted mean cost, paper value / cost,
                      worth per card under comp+elo and small+elo, and the "excess over
                      price": worth - k * cost, with k the usage-weighted average worth per
                      gold of all fielded cards (so a kind with positive excess wins more per
                      gold than the average card).  Logit x 25 ~ percentage points near 50%.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import numpy as np

from common import OUT
from features import CARD_FEATURES
from models import Data, run


def worth(D, model, hp):
    _, _, fit = run(D, model, D.train, ~D.train, hp, True)
    w = np.zeros(len(D.ci.card))
    for n, b in zip(fit.names, fit.coef[1:]):
        if n != "F":
            w += b * D.ci.F[:, CARD_FEATURES.index(n)]
    return w, fit


def main():
    D = Data()
    w_small, f_small = worth(D, "small", {"lam": 0.1, "prior_n": 100.0})
    w_comp, f_comp = worth(D, "comp", {"lam": 0.1, "prior_n": 100.0})
    _, _, f_h = run(D, "hybsmall", D.train, ~D.train,
                    {"lam": 1.0, "lam_card": 100.0, "prior_n": 100.0, "center": True}, True)
    bonus = f_h.card_bonus
    m = D.train & D.rated & D.dec
    use = np.asarray(D.C[np.flatnonzero(m)].sum(0)).ravel()
    cost = np.array([c.cost for c in D.ci.card])
    val = np.array([c.value_adj for c in D.ci.card])

    with open(os.path.join(OUT, "card_scores.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["faction_key", "card_key", "name", "kind", "unit_class", "cost", "value_adj",
                     "value_per_cost", "train_copies", "w_small", "w_comp", "bonus"])
        for j, c in enumerate(D.ci.card):
            wr.writerow([c.faction, c.key, c.name, c.kind, c.cls, int(c.cost), round(val[j], 1),
                         round(val[j] / c.cost, 3) if c.cost else "", int(use[j]),
                         round(w_small[j], 4), round(w_comp[j], 4), round(bonus[j], 4)])

    units = np.array([c.kind != "staff" for c in D.ci.card])
    k_comp = (use * w_comp)[units].sum() / (use * cost)[units].sum()
    k_small = (use * w_small)[units].sum() / (use * cost)[units].sum()
    g = defaultdict(list)
    for j, c in enumerate(D.ci.card):
        if c.kind != "staff" and use[j] > 0:
            g[(c.cls, c.kind)].append(j)
    rows = []
    for (cls, kind), js in sorted(g.items()):
        js = np.array(js)
        u = use[js]
        mean = lambda x: float(np.average(x[js], weights=u))
        rows.append([cls, kind, int(u.sum()), round(mean(cost)), round(mean(val / np.maximum(cost, 1)), 3),
                     round(mean(w_comp), 4), round(mean(w_comp - k_comp * cost), 4),
                     round(mean(w_small), 4), round(mean(w_small - k_small * cost), 4),
                     round(mean(bonus), 4)])
    rows.sort(key=lambda r: -r[6])
    with open(os.path.join(OUT, "class_effects.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["unit_class", "kind", "train_copies", "mean_cost", "paper_value_per_cost",
                     "worth_comp", "excess_comp", "worth_small", "excess_small", "mean_card_bonus"])
        wr.writerows(rows)
    print(f"average worth per 1000 gold: comp {1000*k_comp:.4f}, small {1000*k_small:.4f}")
    print(f"{'class':22s} {'kind':9s} {'copies':>6s} {'cost':>5s} {'v/c':>5s} {'w_comp':>7s} {'excess':>7s} {'w_small':>7s} {'excess':>7s}")
    for r in rows:
        print(f"{r[0]:22s} {r[1]:9s} {r[2]:6d} {r[3]:5d} {r[4]:5.2f} {r[5]:7.3f} {r[6]:7.3f} {r[7]:7.3f} {r[8]:7.3f}")
    # paper value vs model worth across cards (does good value on paper go with a high worth?)
    sel = units & (use > 0)
    surplus = (val - cost)[sel]
    print("corr(paper surplus, w_comp) over fielded unit cards:",
          round(float(np.corrcoef(surplus, w_comp[sel])[0, 1]), 3),
          "| corr(paper surplus, card bonus):", round(float(np.corrcoef(surplus, bonus[sel])[0, 1]), 3))
    # top / bottom card bonuses with enough usage
    order = np.argsort(bonus)
    print("\nlargest positive card bonuses (>= 30 training copies):")
    for j in [j for j in order[::-1] if use[j] >= 30][:10]:
        c = D.ci.card[j]
        print(f"   {bonus[j]:+.3f} copies {int(use[j]):4d} {c.faction} {c.cls} {int(c.cost)} {c.name}")
    print("largest negative card bonuses (>= 30 training copies):")
    for j in [j for j in order if use[j] >= 30][:10]:
        c = D.ci.card[j]
        print(f"   {bonus[j]:+.3f} copies {int(use[j]):4d} {c.faction} {c.cls} {int(c.cost)} {c.name}")


if __name__ == "__main__":
    main()
