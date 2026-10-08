"""How much of an optimised build's predicted advantage is real?  (split-half check)

The optimiser picks the cards with the highest estimated worth, so the in-sample
predicted gain over the army's average build is inflated by noise in those
estimates (winner's curse).  Check: split the training MATCHES into two halves
A and B; fit a candidate model on A, optimise every army (free variant,
guardrails on, paper-value tie-break), then score that build on half B with

  * the same model type refitted on B           ("self" yardstick), and
  * the richest skill-controlled model (hybrid+elo) refitted on B ("common" yardstick).

  gain = W(build) - W(average observed build of that army), in logit units,
averaged over armies with >= 5 rated training games (weighted by games), both
directions A->B and B->A.  A model whose builds keep their advantage on the
other half is the better DECISION model.  Writes out/optimism.csv.
"""
from __future__ import annotations

import csv
import os

import numpy as np

from common import OUT
from features import CARD_FEATURES
from models import Data, run
from optimise import army_guard, guardrails, solve_army

CANDIDATES = {
    "small+elo": ("small", {"lam": 0.1, "prior_n": 100.0}),
    "hybsmall+elo": ("hybsmall", {"lam": 1.0, "lam_card": 300.0, "prior_n": 100.0, "center": True}),
    "comp+elo": ("comp", {"lam": 0.1, "prior_n": 100.0}),
    "hybrid+elo": ("hybrid", {"lam": 1.0, "lam_card": 300.0, "prior_n": 100.0, "center": True}),
}


def worths(D, model, hp, mask):
    _, _, fit = run(D, model, mask, ~mask, hp, True)
    w = np.zeros(len(D.ci.card))
    for n, b in zip(fit.names, fit.coef[1:]):
        if n != "F":
            w += b * D.ci.F[:, CARD_FEATURES.index(n)]
    if fit.card_bonus is not None:
        w = w + fit.card_bonus
    return w


def main():
    D = Data()
    G = guardrails(D)
    half = (D.folds % 2 == 0)
    halves = {"A": D.train & half, "B": D.train & ~half}
    W = {(m, h): worths(D, *CANDIDATES[m], halves[h]) for m in CANDIDATES for h in "AB"}
    obs = D.train & D.rated & D.dec
    rows = []
    for m in CANDIDATES:
        for h1, h2 in (("A", "B"), ("B", "A")):
            for fac in sorted(D.cards):
                om = obs & (D.faction == fac)
                if om.sum() < 5:
                    continue
                keys = sorted(D.cards[fac])
                cards = [D.cards[fac][k] for k in keys]
                gi = np.array([D.ci.pos[(fac, k)] for k in keys])
                val = np.array([c.value_adj for c in cards])
                x, _, _ = solve_army(cards, W[(m, h1)][gi], val, "free", guard=army_guard(G, fac))
                mean_obs = np.asarray(D.C[np.flatnonzero(om)][:, gi].mean(0)).ravel()
                g = lambda w: float(w[gi] @ x - w[gi] @ mean_obs)
                rows.append([m, f"{h1}->{h2}", fac, int(om.sum()), g(W[(m, h1)]), g(W[(m, h2)]),
                             g(W[("hybrid+elo", h2)])])
    print(f"{'model':14s} {'in-sample':>10s} {'other half (self)':>18s} {'other half (common)':>20s}")
    summary = []
    for m in CANDIDATES:
        R = np.array([r[4:] for r in rows if r[0] == m])
        wts = np.array([r[3] for r in rows if r[0] == m], float)
        a = [np.average(R[:, j], weights=wts) for j in range(3)]
        summary.append([m] + [round(v, 4) for v in a])
        print(f"{m:14s} {a[0]:10.3f} {a[1]:18.3f} {a[2]:20.3f}")
    with open(os.path.join(OUT, "optimism.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "direction", "faction_key", "n_games_train", "gain_insample",
                    "gain_otherhalf_self", "gain_otherhalf_common"])
        w.writerows([r[:4] + [round(v, 4) for v in r[4:]] for r in rows])
        w.writerow([])
        w.writerow(["SUMMARY model", "", "", "", "gain_insample", "gain_otherhalf_self", "gain_otherhalf_common"])
        for s in summary:
            w.writerow([s[0], "", "", ""] + s[1:])


if __name__ == "__main__":
    main()
