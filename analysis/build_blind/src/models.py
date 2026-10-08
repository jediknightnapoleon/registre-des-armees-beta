"""Model definitions, fitting and the fixed evaluation protocol.

Models (all logistic, all linear in the copies of each card):

  faction      logit p = a + b*F                       F = logit(faction training win rate)
  paper        faction + c*S                           S = sum over cards of (value - cost)/1000
  comp         faction + ridge on the army sums of every per-card feature (features.py)
  cardEB       faction + c*R                           R = sum of copies x shrunk card residual
                                                       (cross-fitted, empirical Bayes)
  hybrid       comp + ridge card-specific bonus u_c per copy (shrunk to 0)
  small        comp restricted to SMALL_FEATURES (7 build features)
  hybsmall     small + ridge card-specific bonus u_c per copy

Each can be fitted with the skill control "+elo": logit of the pre-game Elo
expected score enters the TRAINING fit as an unpenalised covariate and is set
to its training mean when predicting, so predictions use the build and the
faction only (TASK.md).

Leakage: F is leave-one-match-out on fitted rows; R is 5-fold cross-fitted by
match on fitted rows.  Evaluation rows only ever see statistics from fitted rows.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.optimize import minimize

from common import (SEED, auc, faction_feature, fit_logistic, load_armies, load_cards,
                    logit, logloss, match_folds, sigmoid)
from features import CARD_FEATURES, CardIndex

# features the comp model uses (army sums); 'unit' + per-class counts is collinear
# with the class counts, so 'unit' is left out; per-arm cost is kept.
COMP_FEATURES = [f for f in CARD_FEATURES if f not in ("unit",)]

# the 7 composition features with the clearest training signal (explore.py / coefs_comp.py):
# a combat general, the staff general's stars, artillery (count and gold), lancers, light infantry
SMALL_FEATURES = ["commander", "stars", "cost_k_artillery", "n_artillery_foot", "n_artillery_horse",
                  "n_cavalry_lancers", "n_infantry_light"]


class Data:
    def __init__(self):
        self.cards = load_cards()
        self.armies = load_armies(self.cards)
        self.ci = CardIndex(self.cards)
        self.C = self.ci.count_matrix(self.armies)               # armies x cards (copies)
        self.A = np.asarray(self.C @ self.ci.F)                   # armies x card-features
        self.y = np.array([a.y if a.y is not None else -1 for a in self.armies], float)
        self.dec = np.array([a.y is not None for a in self.armies])
        self.train = np.array([a.train for a in self.armies])
        self.t = np.array([a.played_at for a in self.armies])
        e = np.array([a.elo_e if a.elo_e is not None else 0.5 for a in self.armies])
        self.le = logit(e)
        self.folds = match_folds(self.armies, 5, SEED)
        self.faction = np.array([a.faction for a in self.armies])
        self.player = np.array([a.player for a in self.armies])
        # Unrated "wins" (no rating change; 58 wins, 3 draws, 0 losses, often 1-5 cards)
        # are games outside the ladder (e.g. against the AI).  They are excluded from
        # every FIT, never from evaluation.
        self.rated = np.array([a.rating_change is not None for a in self.armies])

    def cols(self, names):
        return self.A[:, [CARD_FEATURES.index(n) for n in names]]


@dataclass
class Fit:
    name: str
    coef: np.ndarray            # dense coefficients in natural units (incl. intercept first)
    names: list
    card_bonus: np.ndarray | None = None   # per global card index, per copy
    elo_coef: float = 0.0
    extra: dict | None = None


# ---------------------------------------------------------------- helpers

def standardise(X, idx):
    mu = X[idx].mean(0)
    sd = X[idx].std(0)
    sd[sd == 0] = 1
    return mu, sd


def ridge_logit(Xd, y, fit_idx, lam, unpen=(), elo=None):
    """Ridge logistic on standardised dense columns; returns natural-unit coefs.

    Xd: n x d (no intercept).  `unpen`: column indices left unpenalised.
    Returns (intercept, coef[d], elo_coef).
    """
    mu, sd = standardise(Xd, fit_idx)
    Z = (Xd[fit_idx] - mu) / sd
    cols = [np.ones(len(fit_idx)), *Z.T]
    pen = [0.0] + [0.0 if j in unpen else lam for j in range(Xd.shape[1])]
    if elo is not None:
        cols.append(elo[fit_idx])
        pen.append(0.0)
    X = np.column_stack(cols)
    b, _ = fit_logistic(X, y[fit_idx], np.array(pen))
    beta = b[1:1 + Xd.shape[1]] / sd
    a = b[0] - np.sum(beta * mu)
    return a, beta, (b[-1] if elo is not None else 0.0)


def eb_scores(D: Data, fit_idx, eval_idx, p0, k):
    """Empirical-Bayes card residual score R, leakage-free.

    For card c: r_c = sum_i copies_ic (y_i - p0_i) / (sum_i copies_ic + k) over
    the rows used to estimate it.  R_i = sum_c copies_ic r_c.
    Fitted rows get R from the other 4 match-folds; eval rows from all fitted rows.
    """
    R = np.zeros(len(D.armies))
    res = D.y - p0

    def rates(rows):
        Cs = D.C[rows]
        num = Cs.T @ res[rows]
        den = np.asarray(Cs.sum(0)).ravel()
        return num / (den + k)

    f_folds = D.folds[fit_idx]
    for fo in range(5):
        r = rates(fit_idx[f_folds != fo])
        rows = fit_idx[f_folds == fo]
        R[rows] = D.C[rows] @ r
    r_all = rates(fit_idx)
    R[eval_idx] = D.C[eval_idx] @ r_all
    return R, r_all


def card_ridge(D: Data, Xd, fit_idx, lam_dense, lam_card, unpen=(), elo=None, center=True):
    """Joint ridge logistic: dense standardised features + per-card copy counts.

    Objective: -loglik + 0.5*lam_dense*|b_dense|^2 + 0.5*lam_card*|u|^2.
    With `center`, card counts are centred WITHIN FACTION (copies minus the
    army's average copies of that card over the fitted rows), so the card bonuses
    u_c only describe how a build differs from the usual build of its own army
    and cannot soak up the army's overall strength (that stays with F).  The
    centring is a per-army constant in the linear predictor, so it changes
    neither the ranking of builds within an army nor the optimiser.
    Solved with L-BFGS (cards are sparse).  Returns (a, beta_natural, u_global, elo, shift)
    where shift[faction] is the constant to subtract when predicting.
    """
    mu, sd = standardise(Xd, fit_idx)
    Z = (Xd[fit_idx] - mu) / sd
    cols = [np.ones(len(fit_idx)), *Z.T]
    pen = [0.0] + [0.0 if j in unpen else lam_dense for j in range(Xd.shape[1])]
    if elo is not None:
        cols.append(elo[fit_idx])
        pen.append(0.0)
    Xn = np.column_stack(cols)
    Cf = D.C[fit_idx]
    used = np.flatnonzero(np.asarray(Cf.sum(0)).ravel() > 0)
    Cu = Cf[:, used].tocsr()
    facs = sorted(set(D.faction[fit_idx]))
    fpos = {f: j for j, f in enumerate(facs)}
    R = sp.csr_matrix((np.ones(len(fit_idx)), (np.arange(len(fit_idx)), [fpos[f] for f in D.faction[fit_idx]])),
                      shape=(len(fit_idx), len(facs)))
    nf = np.asarray(R.sum(0)).ravel()
    Cbar = sp.diags(1.0 / nf) @ (R.T @ Cu)                       # faction x used-cards mean copies
    if not center:
        Cbar = Cbar * 0.0
    Cbar = sp.csr_matrix(Cbar)
    yf = D.y[fit_idx]
    d = Xn.shape[1]
    lam = np.concatenate([np.array(pen), np.full(len(used), lam_card)])

    def f(w):
        uu = w[d:]
        eta = Xn @ w[:d] + Cu @ uu - R @ (Cbar @ uu)
        ll = np.sum(yf * eta - np.logaddexp(0, eta))
        g_eta = yf - sigmoid(eta)
        g = np.concatenate([Xn.T @ g_eta, Cu.T @ g_eta - Cbar.T @ (R.T @ g_eta)])
        return -ll + 0.5 * np.sum(lam * w * w), -g + lam * w

    w0 = np.zeros(d + len(used))
    r = minimize(f, w0, jac=True, method="L-BFGS-B", options={"maxiter": 5000, "gtol": 1e-7})
    w = r.x
    b = w[:d]
    beta = b[1:1 + Xd.shape[1]] / sd
    a = b[0] - np.sum(beta * mu)
    u = np.zeros(D.C.shape[1])
    u[used] = w[d:]
    shift_f = Cbar @ w[d:]
    shift = {f: float(shift_f[fpos[f]]) for f in facs}
    return a, beta, u, (b[-1] if elo is not None else 0.0), shift


# ---------------------------------------------------------------- one model run

def run(D: Data, model: str, fit_mask, eval_mask, hp: dict, skill: bool):
    """Fit `model` on decisive rows of fit_mask, predict decisive rows of eval_mask.

    Returns (pred on eval rows, eval index, Fit).
    """
    if model in ("small", "hybsmall"):
        hp = dict(hp, features=SMALL_FEATURES)
        model = {"small": "comp", "hybsmall": "hybrid"}[model]
    fit_m = fit_mask & D.dec & (D.rated if hp.get("rated_only", True) else True)
    fit_idx = np.flatnonzero(fit_m)
    eval_idx = np.flatnonzero(eval_mask & D.dec)
    dec_idx = np.flatnonzero(D.dec)
    F = faction_feature(D.armies, dec_idx, fit_m, prior_n=hp.get("prior_n", 20.0))
    elo = D.le if skill else None
    elo_mean = float(D.le[fit_idx].mean())

    if model == "faction":
        a, beta, ec = ridge_logit(F[:, None], D.y, fit_idx, 0.0, elo=elo)
        eta = a + beta[0] * F + ec * elo_mean
        return sigmoid(eta[eval_idx]), eval_idx, Fit(model, np.r_[a, beta], ["F"], elo_coef=ec)

    if model == "paper":
        X = np.column_stack([F, D.cols(["surplus_k"])])
        a, beta, ec = ridge_logit(X, D.y, fit_idx, 0.0, elo=elo)
        eta = a + X @ beta + ec * elo_mean
        return sigmoid(eta[eval_idx]), eval_idx, Fit(model, np.r_[a, beta], ["F", "surplus_k"], elo_coef=ec)

    if model == "comp":
        names = hp.get("features", COMP_FEATURES)
        X = np.column_stack([F, D.cols(names)])
        a, beta, ec = ridge_logit(X, D.y, fit_idx, hp["lam"], unpen=(0,), elo=elo)
        eta = a + X @ beta + ec * elo_mean
        return sigmoid(eta[eval_idx]), eval_idx, Fit(model, np.r_[a, beta], ["F"] + list(names), elo_coef=ec)

    if model == "cardEB":
        # p0: faction-only model fitted on the fitted rows (with skill control if asked)
        a0, b0, e0 = ridge_logit(F[:, None], D.y, fit_idx, 0.0, elo=elo)
        p0 = sigmoid(a0 + b0[0] * F + (e0 * D.le if skill else 0.0))
        R, r_all = eb_scores(D, fit_idx, eval_idx, p0, hp["k"])
        X = np.column_stack([F, R])
        a, beta, ec = ridge_logit(X, D.y, fit_idx, 0.0, elo=elo)
        eta = a + X @ beta + ec * elo_mean
        return (sigmoid(eta[eval_idx]), eval_idx,
                Fit(model, np.r_[a, beta], ["F", "R"], card_bonus=beta[1] * r_all, elo_coef=ec))

    if model == "hybrid":
        names = hp.get("features", COMP_FEATURES)
        X = np.column_stack([F, D.cols(names)])
        a, beta, u, ec, shift = card_ridge(D, X, fit_idx, hp["lam"], hp["lam_card"], unpen=(0,), elo=elo,
                                           center=hp.get("center", True))
        sh = np.array([shift.get(f, 0.0) for f in D.faction])
        eta = a + X @ beta + D.C @ u - sh + ec * elo_mean
        return (sigmoid(eta[eval_idx]), eval_idx,
                Fit(model, np.r_[a, beta], ["F"] + list(names), card_bonus=u, elo_coef=ec,
                    extra={"shift": shift}))

    raise ValueError(model)


def score(D: Data, p, idx, rated_only=False):
    if rated_only:
        keep = D.rated[idx]
        p, idx = p[keep], idx[keep]
    y = D.y[idx]
    return auc(y, p), logloss(y, p), len(idx)
