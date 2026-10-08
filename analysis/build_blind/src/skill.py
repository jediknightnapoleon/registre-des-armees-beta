"""Player skill as a confounder: how do the build effects change once skill is controlled?

Training data only (rated, decisive).  For the composition features we fit:

  none      logit p = a + b*F + sum_k c_k x_k
  elo       + e * logit(E)          E = pre-game Elo expected score of this game
  player    + v_player              ridge "random effect" per player (lam_p)
  elo+player  both

and report the coefficients of the main build features under each control.
Then: does the effect of a feature depend on the player's skill?  Skill is the
player's average logit(E) over his OTHER matches (cross-fitted; a rating proxy:
how strong he usually is relative to his opponents).  Players are split into the
weaker and stronger half (among those with other games) plus "unknown" (no other
rated training game), and the `small` model is refitted per group with the Elo
control.

Writes out/skill_controls.csv and out/skill_groups.csv.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import numpy as np
import scipy.sparse as sp
from scipy.optimize import minimize

from common import OUT, faction_feature, fit_logistic, sigmoid
from models import COMP_FEATURES, SMALL_FEATURES as SMALL, Data


def sparse_ridge(Xd, S, y, lam_d, lam_s):
    """Logistic: dense Xd (first col intercept) with per-column lam_d, sparse S with lam_s."""
    d = Xd.shape[1]
    lam = np.concatenate([lam_d, np.full(S.shape[1], lam_s)])

    def f(w):
        eta = Xd @ w[:d] + S @ w[d:]
        g_eta = y - sigmoid(eta)
        ll = np.sum(y * eta - np.logaddexp(0, eta))
        return -ll + 0.5 * np.sum(lam * w * w), -np.concatenate([Xd.T @ g_eta, S.T @ g_eta]) + lam * w

    r = minimize(f, np.zeros(d + S.shape[1]), jac=True, method="L-BFGS-B",
                 options={"maxiter": 5000, "gtol": 1e-8})
    return r.x[:d], r.x[d:]


def main():
    D = Data()
    m = D.train & D.dec & D.rated
    idx = np.flatnonzero(m)
    F = faction_feature(D.armies, np.flatnonzero(D.dec), m, 100.0)
    y = D.y[idx]
    names = COMP_FEATURES
    X = np.column_stack([np.ones(len(idx)), F[idx], D.cols(names)[idx]])
    players = sorted(set(D.player[idx]))
    pi = {p: j for j, p in enumerate(players)}
    P = sp.csr_matrix((np.ones(len(idx)), (np.arange(len(idx)), [pi[p] for p in D.player[idx]])),
                      shape=(len(idx), len(players)))
    lam_p = 5.0   # ~ prior sd 0.45 logit per player; see RESULTS.md
    small_pen = 1e-3
    out = {}
    for lab in ["none", "elo", "player", "elo+player"]:
        Xx = X if "elo" not in lab else np.column_stack([X, D.le[idx]])
        pen = np.r_[0, 0, np.full(len(names), small_pen), [0] * ("elo" in lab)]
        if "player" in lab:
            b, v = sparse_ridge(Xx, P, y, pen, lam_p)
            se = None
        else:
            b, C = fit_logistic(Xx, y, pen)
            se = np.sqrt(np.diag(C))
        out[lab] = (b, se)
        print(lab, "elo coef", b[-1] if "elo" in lab else "-")

    rows = []
    for j, n in enumerate(["const", "F"] + names):
        row = [n] + [round(float(out[l][0][j]), 4) for l in out] + \
              [round(float(out[l][0][j] / out[l][1][j]), 2) if out[l][1] is not None else "" for l in ("none", "elo")]
        rows.append(row)
        print(f"{n:24s}", " ".join(f"{x:>8}" for x in row[1:]))
    with open(os.path.join(OUT, "skill_controls.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["feature", "coef_none", "coef_elo", "coef_player", "coef_elo_player", "z_none", "z_elo"])
        w.writerows(rows)

    # ---- skill groups: player's mean logit(E) over his other matches (cross-fitted)
    by_p = defaultdict(list)
    for i in np.flatnonzero(D.dec & D.rated & D.train):
        by_p[D.player[i]].append((D.armies[i].match, D.le[i]))
    skill = np.full(len(D.armies), np.nan)
    ngames = np.zeros(len(D.armies))
    for i in idx:
        oth = [e for mt, e in by_p[D.player[i]] if mt != D.armies[i].match]
        ngames[i] = len(oth)
        # shrink toward 0 (an average player) with 3 pseudo-games
        skill[i] = np.sum(oth) / (len(oth) + 3.0)
    s = skill[idx]
    known = ngames[idx] > 0
    med = np.median(s[known])
    # group 0: weaker half of players with other games, 1: stronger half,
    # 2: no other rated training game (skill unknown)
    terc = np.where(~known, 2, np.where(s <= med, 0, 1))
    trows = []
    print("\nskill groups: 0 weaker half, 1 stronger half (median", round(float(med), 3), "), 2 unknown")
    for t in range(3):
        sel = terc == t
        Xs = np.column_stack([np.ones(sel.sum()), F[idx][sel], D.cols(SMALL)[idx][sel], D.le[idx][sel]])
        b, C = fit_logistic(Xs, y[sel], np.r_[0, 0, np.full(len(SMALL), small_pen), 0])
        se = np.sqrt(np.diag(C))
        wr = y[sel].mean()
        cm = D.cols(["commander"])[idx][sel].mean()
        print(f"group {t}: n={sel.sum()} win {wr:.3f} share-with-commander {cm:.3f} median games {np.median(ngames[idx][sel])}")
        for j, n in enumerate(SMALL):
            print(f"   {n:20s} {b[2+j]:7.3f}  z {b[2+j]/se[2+j]:5.2f}")
            trows.append([t, int(sel.sum()), round(float(wr), 4), n, round(float(b[2 + j]), 4), round(float(se[2 + j]), 4)])
    with open(os.path.join(OUT, "skill_groups.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["skill_group(0 weak,1 strong,2 unknown)", "n", "win_rate", "feature", "coef_elo_controlled", "se"])
        w.writerows(trows)

    # ---- who uses what: correlation of build features with skill
    print("\ncorrelation of build features with player skill (training rows)")
    for n in ["commander", "stars", "surplus_k", "n_infantry_light", "n_cavalry_lancers", "cost_k_artillery"]:
        x = D.cols([n])[idx].ravel()
        print(f"   {n:20s} r={np.corrcoef(x, s)[0,1]:6.3f}")


if __name__ == "__main__":
    main()
