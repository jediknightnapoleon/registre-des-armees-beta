"""Best legal build for every army under the recommended model (exact MILP).

Model: `small+elo` (models.py), fitted on rated decisive TRAINING armies with
the Elo skill control.  Its linear predictor is a sum over copies of a per-card
worth

    w_c = beta . f_c

(f_c: the card's SMALL_FEATURES: combat general, staff stars, artillery count
and gold, lancers, light infantry).  Card-specific bonuses (`hybsmall`) are NOT
used for builds: they improve prediction slightly but their build advantage
does not replicate on an independent half of the data (optimism.py).  The faction term,
the intercept and the within-army centring are constants for a given army, and
the skill term is fixed at its training mean, so the best build of an army is the
one that maximises sum_c w_c x_c -- it does not depend on who plays it.

Two stages per army and variant:
  1. maximise W = sum_c w_c x_c subject to RULES.md                (the data's choice)
  2. among builds with W >= W* - DELTA, maximise the total adjusted normative
     value sum_c value_adj_c x_c                                    (paper value as tie-break)
DELTA = 0.02 logit (about 0.5 percentage points of win probability) is far
below what the data can resolve, so stage 2 only decides between builds the data
cannot tell apart; there the game's own pricing rule (most stats for the gold)
decides.

RULES.md constraints (all enforced as linear constraints):
  one staff general; <= 31 cards; cost <= 10 000; <= 1 commander card;
  per base_unit_key: copies <= unit_cap (0 = uncapped) and <= 1 commander version;
  foot artillery <= 2; horse artillery <= 1 (2 if the army has no infantry cards);
  heavy cavalry <= 10; commander / staff at most one copy each;
  4corps: <= 4 distinct non-empty source_corps (staff included), via binary corps
  switches.

Composition guardrails (not game rules; a modelling choice): the model is linear
and was only fitted on builds players actually field, so the optimiser is kept
inside that region.  For every army the number of infantry and cavalry cards, the
number of cards of each unit class, and the copies of any single card must lie
within the middle 95% (2.5th-97.5th percentile) of that army's own rated
training builds when it has >= 40 of them, else of all rated training builds
pooled, widened to cover every build that army was actually seen to field.  If an army is infeasible under the guardrails they are dropped for it
(logged).

Token cards: cards whose adjusted normative value is below half their price
(110 cards: depleted batteries, one-model "commanders", negative-value units;
almost never fielded) are excluded.  The data cannot rate them and on paper they
are useless, but the count effects of the model (commander, foot artillery)
would otherwise reward them as cheap slot fillers.  `--noguard` writes the unguarded optimum to out/builds_noguard.csv for
comparison.

Writes out/builds.csv (faction_key, variant, card_key, copies) and
out/builds_summary.csv.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from common import OUT, sigmoid
from features import CARD_FEATURES
from models import SMALL_FEATURES, Data, run

DELTA = 0.02
TIME_LIMIT = 60.0
MIN_OWN_GAMES = 40
TOKEN_RATIO = 0.5
HP = {"lam": 0.1, "prior_n": 100.0}
MODEL = "small"
SKILL = True


def card_worths(D: Data):
    """Fit the recommended model on training data; return per-global-card worth w_c."""
    _, _, fit = run(D, MODEL, D.train, ~D.train, HP, SKILL)
    beta = dict(zip(fit.names, fit.coef[1:]))
    dense = np.zeros(len(D.ci.card))
    for n in SMALL_FEATURES:
        dense += beta[n] * D.ci.F[:, CARD_FEATURES.index(n)]
    bonus = fit.card_bonus if fit.card_bonus is not None else np.zeros(len(D.ci.card))
    return dense + bonus, dense, bonus, fit


def guardrails(D: Data):
    """Observed composition ranges of rated training builds, pooled and per army."""
    from features import CLASSES
    m = np.flatnonzero(D.train & D.rated & D.dec)

    def counts(i):
        a = D.armies[i]
        fc = D.cards[a.faction]
        arm = defaultdict(int)
        cls = defaultdict(int)
        for k, n in a.counts.items():
            c = fc[k]
            if c.kind == "staff":
                continue
            arm[c.arm] += n
            cls[c.cls] += n
        return arm, cls, max((n for k, n in a.counts.items() if fc[k].kind != "staff"), default=0)

    def ranges(per):
        arm = {}
        for a in ("infantry", "cavalry"):
            x = np.array([p[0][a] for p in per])
            arm[a] = (int(np.floor(np.percentile(x, 2.5))), int(np.ceil(np.percentile(x, 97.5))))
        cls = {c: max(1, int(np.ceil(np.percentile([p[1][c] for p in per], 97.5)))) for c in CLASSES}
        copies = int(np.ceil(np.percentile([p[2] for p in per], 97.5)))
        return {"arm": arm, "cls": cls, "copies": copies}

    per = [counts(i) for i in m]
    g = {"pooled": ranges(per), "army": {}}
    by = defaultdict(list)
    for i, p in zip(m, per):
        by[D.armies[i].faction].append(p)
    P = g["pooled"]
    for fac, ps in by.items():
        if len(ps) >= MIN_OWN_GAMES:
            g["army"][fac] = ranges(ps)
        else:   # pooled range, widened to everything this army was actually seen to field
            arm = {a: (min(lo, min(p[0][a] for p in ps)), max(hi, max(p[0][a] for p in ps)))
                   for a, (lo, hi) in P["arm"].items()}
            cls = {c: max(hi, max(p[1][c] for p in ps)) for c, hi in P["cls"].items()}
            g["army"][fac] = {"arm": arm, "cls": cls, "copies": max(P["copies"], max(p[2] for p in ps))}
    return g


def army_guard(g, fac):
    """Own middle-95% ranges (>= MIN_OWN_GAMES games) / pooled widened to own observations / pooled."""
    return g["army"].get(fac, g["pooled"])


def solve_army(cards, w, val, variant: str, time_limit=TIME_LIMIT, guard=None):
    """MILP for one army.  `cards`: list of Card; w, val: arrays aligned with cards."""
    n = len(cards)
    has_inf = any(c.arm == "infantry" for c in cards)
    corps = sorted({c.corps for c in cards if c.corps}) if variant == "4corps" else []
    nz = len(corps)
    nv = n + nz
    ub = np.zeros(nv)
    for j, c in enumerate(cards):
        if c.kind in ("staff", "commander"):
            ub[j] = 1
        else:
            ub[j] = c.cap if c.cap > 0 else 31
        if c.kind != "staff" and c.value_adj < TOKEN_RATIO * c.cost:
            ub[j] = 0                                                 # token card
    ub[n:] = 1
    A, lo, hi = [], [], []

    def add(row, l, h):
        A.append(row)
        lo.append(l)
        hi.append(h)

    def ind(pred):
        r = np.zeros(nv)
        for j, c in enumerate(cards):
            if pred(c):
                r[j] = 1
        return r

    add(ind(lambda c: c.kind == "staff"), 1, 1)                      # rule 1
    add(ind(lambda c: True), 0, 31)                                   # rule 2
    r = np.zeros(nv)
    r[:n] = [c.cost for c in cards]
    add(r, 0, 10000)                                                  # rule 3
    add(ind(lambda c: c.kind == "commander"), 0, 1)                   # rule 4
    groups = defaultdict(list)
    for j, c in enumerate(cards):
        if c.kind != "staff":
            groups[c.base].append(j)
    capof = {c.key: c.cap for c in cards}
    for b, js in groups.items():                                      # rule 5
        cap = capof.get(b, max(cards[j].cap for j in js))
        if cap > 0:
            r = np.zeros(nv)
            r[js] = 1
            add(r, 0, cap)
        cm = [j for j in js if cards[j].kind == "commander"]
        if len(cm) > 1:
            r = np.zeros(nv)
            r[cm] = 1
            add(r, 0, 1)
    add(ind(lambda c: c.cls == "artillery_foot"), 0, 2)               # rule 6
    add(ind(lambda c: c.cls == "artillery_horse"), 0, 1 if has_inf else 2)
    add(ind(lambda c: c.cls == "cavalry_heavy"), 0, 10)
    if guard is not None:                                             # guardrails
        for arm, (glo, ghi) in guard["arm"].items():
            if any(c.arm == arm for c in cards):
                add(ind(lambda c, a=arm: c.arm == a and c.kind != "staff"), glo, ghi)
        for cl, ghi in guard["cls"].items():
            if any(c.cls == cl for c in cards):
                add(ind(lambda c, k=cl: c.cls == k), 0, ghi)
        for j, c in enumerate(cards):
            if c.kind == "unit":
                ub[j] = min(ub[j], guard["copies"])
    if nz:                                                            # rule 7
        zi = {s: n + k for k, s in enumerate(corps)}
        for j, c in enumerate(cards):
            if c.corps:
                r = np.zeros(nv)
                r[j] = 1
                r[zi[c.corps]] = -ub[j]
                add(r, -np.inf, 0)
        r = np.zeros(nv)
        r[n:] = 1
        add(r, 0, 4)
    A = np.array(A)
    cons = [LinearConstraint(A, lo, hi)]
    integrality = np.ones(nv)
    bounds = Bounds(np.zeros(nv), ub)

    obj = np.zeros(nv)
    obj[:n] = -w
    r1 = milp(obj, constraints=cons, integrality=integrality, bounds=bounds,
              options={"time_limit": time_limit, "disp": False})
    if r1.x is None:
        if guard is not None:
            print("   guardrails infeasible -> dropped for this army")
            return solve_army(cards, w, val, variant, time_limit, None)
        raise RuntimeError(f"stage 1 failed: {r1.message}")
    W1 = float(w @ np.round(r1.x[:n]))
    # stage 2: paper-value tie-break within DELTA of the best worth
    r = np.zeros(nv)
    r[:n] = w
    cons2 = cons + [LinearConstraint(r[None, :], W1 - DELTA, np.inf)]
    obj2 = np.zeros(nv)
    obj2[:n] = -val / 1000.0
    r2 = milp(obj2, constraints=cons2, integrality=integrality, bounds=bounds,
              options={"time_limit": time_limit, "disp": False})
    x = np.round(r2.x[:n] if r2.x is not None else r1.x[:n]).astype(int)
    if r1.status != 0 or (r2.x is not None and r2.status != 0):
        print("   warning: MILP not proven optimal", r1.status, r2.status)
    status = f"s1:{r1.status} s2:{r2.status}"
    return x, W1, status


def main():
    noguard = "--noguard" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    D = Data()
    G = guardrails(D)
    print("pooled guardrails:", G["pooled"], "| armies with own ranges:", len(G["army"]))
    w_all, dense, bonus, fit = card_worths(D)
    print("model", MODEL, "skill-controlled", SKILL, "coefs", dict(zip(fit.names, np.round(fit.coef[1:], 4))))
    # average observed build worth per army (training, rated) for comparison
    W_obs = np.asarray(D.C @ w_all).ravel()
    rows, summ = [], []
    for fac in sorted(D.cards):
        if only and fac not in only:
            continue
        keys = sorted(D.cards[fac])
        cards = [D.cards[fac][k] for k in keys]
        gi = np.array([D.ci.pos[(fac, k)] for k in keys])
        w = w_all[gi]
        val = np.array([c.value_adj for c in cards])
        obs = (D.faction == fac) & D.train & D.rated
        w_mean_obs = float(W_obs[obs].mean()) if obs.any() else float("nan")
        w_best_obs = float(W_obs[obs].max()) if obs.any() else float("nan")
        for variant in ("free", "4corps"):
            guard = None if noguard else army_guard(G, fac)
            x, W1, status = solve_army(cards, w, val, variant, guard=guard)
            Wx = float(w @ x)
            sel = np.flatnonzero(x)
            for j in sel:
                rows.append([fac, variant, cards[j].key, int(x[j])])
            summ.append([fac, variant, int(x.sum()), int(sum(cards[j].cost * x[j] for j in sel)),
                         round(float(val @ x)), round(Wx, 4), round(W1, 4), round(w_mean_obs, 4),
                         round(w_best_obs, 4), round(Wx - w_mean_obs, 4),
                         round(float(sigmoid(Wx - w_mean_obs) - 0.5), 4),
                         len({cards[j].corps for j in sel if cards[j].corps}), int(obs.sum()), status])
            print(f"{fac:24s} {variant:6s} cards {x.sum():2d} cost {summ[-1][3]:5d} W {Wx:.3f} "
                  f"(obs mean {w_mean_obs:.3f}) corps {summ[-1][11]} {status}")
    os.makedirs(OUT, exist_ok=True)
    suffix = ("_noguard" if noguard else "") + ("" if not only else "_partial")
    with open(os.path.join(OUT, f"builds{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["faction_key", "variant", "card_key", "copies"])
        wr.writerows(rows)
    with open(os.path.join(OUT, f"builds_summary{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["faction_key", "variant", "n_cards", "cost", "normative_value", "worth_W",
                     "worth_stage1_best", "obs_mean_W", "obs_best_W", "gain_vs_avg_build_logit",
                     "gain_vs_avg_build_prob_at_50pct", "n_source_corps", "n_train_games", "milp_status"])
        wr.writerows(summ)


if __name__ == "__main__":
    main()
