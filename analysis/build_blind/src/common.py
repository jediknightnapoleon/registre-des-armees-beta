"""Shared loading, feature and evaluation helpers for the blind build study.

Everything here is deterministic and reads only `analysis/build_blind/data/`.

Conventions
-----------
* An "army row" is one army in one game (a row of armies.csv).
* y = 1 for a win, 0 for a loss; draws / unknown results are kept for nothing
  except descriptive counts (TASK.md: evaluate on decisive games only).
* Train / test follow data/split.json exactly (string comparison of the ISO
  timestamps is exact because every timestamp has the same format).
* Cross-fitting is grouped by match_id: teammates share a result, so a
  leave-one-army-out estimate would still see the army's own result through a
  teammate of the same faction.  Grouping by match removes that path.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

SEED = 20260920
K_ELO = 24.0          # observed: win change + |loss change| ~= 24 per game
BIG_MODELS = 240.0    # TASK.md: normative value overstated above 240 models


@dataclass
class Card:
    faction: str
    key: str
    kind: str
    base: str
    name: str
    cls: str
    arm: str
    cost: float
    cap: int
    corps: str
    models: float
    stars: int
    value: float            # raw normative value
    value_adj: float        # value with the >240-model correction
    tag: str                # speed-tag letter (L, G, S, C, F, H) or '-'
    tier: int               # speed-tag digit, 0 if none


@dataclass
class Army:
    match: str
    played_at: str
    faction: str
    player: str
    team: str
    result: str
    rating_change: float | None
    staff: str
    counts: dict = field(default_factory=dict)   # card_key -> copies (staff included)
    train: bool = True

    @property
    def y(self) -> int | None:
        return {"win": 1, "loss": 0}.get(self.result)

    @property
    def elo_e(self) -> float | None:
        """Pre-game Elo expected score implied by the rating change.

        With K = 24: a win pays K(1-E), a loss costs K*E.  The magnitude of the
        change is a pre-game quantity (the rating gap to the opponents); the
        sign only tells which formula applies.  Used ONLY as a training-time
        control, never as a predictor.
        """
        if self.rating_change is None or self.y is None:
            return None
        d = self.rating_change
        e = 1.0 - d / K_ELO if self.y == 1 else -d / K_ELO
        return min(0.95, max(0.05, e))


def adjusted_value(value: float, models: float) -> float:
    """Normative value with the large-unit correction.

    TASK.md warns that values of units above 240 models are overstated.  The
    simplest readable correction: price such a unit as if it had 240 models
    (value assumed proportional to size above that point).
    """
    if models > BIG_MODELS:
        return value * BIG_MODELS / models
    return value


def load_cards() -> dict[str, dict[str, Card]]:
    out: dict[str, dict[str, Card]] = defaultdict(dict)
    with open(os.path.join(DATA, "cards.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = re.search(r"\[(\w)(\d)\]\s*$", r["name"])
            models = float(r["models"] or 0)
            value = float(r["normative_value"])
            c = Card(
                faction=r["faction_key"], key=r["card_key"], kind=r["kind"],
                base=r["base_unit_key"], name=r["name"], cls=r["unit_class"],
                arm=r["arm"], cost=float(r["cost"]), cap=int(r["unit_cap"] or 0),
                corps=r["source_corps"], models=models,
                stars=int(r["command_stars"] or 0), value=value,
                value_adj=adjusted_value(value, models),
                tag=m.group(1) if m else "-", tier=int(m.group(2)) if m else 0,
            )
            out[c.faction][c.key] = c
    return dict(out)


def load_armies(cards: dict[str, dict[str, Card]]) -> list[Army]:
    cut = json.load(open(os.path.join(DATA, "split.json")))["cut_played_at"]
    armies = []
    with open(os.path.join(DATA, "armies.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            counts: dict[str, int] = defaultdict(int)
            fc = cards.get(r["faction_key"], {})
            for k in [r["staff_key"]] + r["unit_keys"].split():
                if k in fc:              # 52 of 186k references are unknown; dropped
                    counts[k] += 1
            rc = r["player_rating_change"]
            armies.append(Army(
                match=r["match_id"], played_at=r["played_at"], faction=r["faction_key"],
                player=r["player"], team=r["team"], result=r["result"],
                rating_change=float(rc) if rc else None, staff=r["staff_key"],
                counts=dict(counts), train=r["played_at"] < cut,
            ))
    return armies


def match_folds(armies: list[Army], k: int = 5, seed: int = SEED) -> np.ndarray:
    """Deterministic fold id per army, grouped by match."""
    matches = sorted({a.match for a in armies})
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(matches))
    fold_of = {m: int(perm[i] % k) for i, m in enumerate(matches)}
    return np.array([fold_of[a.match] for a in armies])


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def auc(y: np.ndarray, p: np.ndarray) -> float:
    from scipy.stats import rankdata
    r = rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def logloss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def faction_rates(armies: list[Army], idx_fit, prior_n: float = 20.0) -> dict[str, tuple[float, float]]:
    """(wins, games) per faction over the given decisive rows."""
    w = defaultdict(float)
    n = defaultdict(float)
    for i in idx_fit:
        a = armies[i]
        w[a.faction] += a.y
        n[a.faction] += 1
    return {f: (w[f], n[f]) for f in n}


def shrunk_rate(w: float, n: float, base: float, prior_n: float) -> float:
    return (w + prior_n * base) / (n + prior_n)


def faction_feature(armies: list[Army], dec_idx: np.ndarray, train_mask: np.ndarray,
                    prior_n: float = 20.0) -> np.ndarray:
    """Logit of the faction's training win rate, leakage-free.

    Training rows: leave-one-MATCH-out (the row's own match removed).
    Test rows: all training decisive rows.
    Shrunk toward the overall training win rate with `prior_n` pseudo-games.
    """
    tr = [i for i in dec_idx if train_mask[i]]
    base = float(np.mean([armies[i].y for i in tr]))
    tot = faction_rates(armies, tr)
    # per (faction, match) contributions on training rows
    fm_w = defaultdict(float)
    fm_n = defaultdict(float)
    for i in tr:
        a = armies[i]
        fm_w[(a.faction, a.match)] += a.y
        fm_n[(a.faction, a.match)] += 1
    out = np.zeros(len(armies))
    for i in dec_idx:
        a = armies[i]
        w, n = tot.get(a.faction, (0.0, 0.0))
        if train_mask[i]:
            w -= fm_w[(a.faction, a.match)]
            n -= fm_n[(a.faction, a.match)]
        out[i] = logit(shrunk_rate(w, n, base, prior_n))
    return out


def append_results(rows: list[str]) -> None:
    path = os.path.join(ROOT, "RESULTS.md")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("# Running log\n\nOne row per experiment. AUC / log-loss on the stated split "
                    "(decisive games only).\n\n| date-step | experiment | split | n | AUC | log-loss | notes |\n"
                    "|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(r + "\n")


def fit_logistic(X: np.ndarray, y: np.ndarray, l2=0.0, offset=None, w=None,
                 iters: int = 100, tol: float = 1e-9):
    """Penalised logistic regression by Newton-Raphson (IRLS).

    `l2` is a scalar or a per-column vector of ridge penalties (0 = unpenalised,
    use 0 for the intercept).  Objective: sum_i w_i * loglik_i - 0.5 * sum_j l2_j b_j^2.
    Returns (coef, covariance) where covariance is the inverse penalised Hessian.
    Deterministic and dependency-free so every model in the study uses the same fitter.
    """
    n, p = X.shape
    off = np.zeros(n) if offset is None else offset
    w = np.ones(n) if w is None else w
    lam = np.full(p, float(l2)) if np.isscalar(l2) else np.asarray(l2, float)
    b = np.zeros(p)
    for _ in range(iters):
        eta = X @ b + off
        mu = sigmoid(eta)
        g = X.T @ (w * (y - mu)) - lam * b
        W = w * mu * (1 - mu)
        H = (X * W[:, None]).T @ X + np.diag(lam)
        step = np.linalg.solve(H, g)
        b = b + step
        if np.max(np.abs(step)) < tol:
            break
    eta = X @ b + off
    mu = sigmoid(eta)
    W = w * mu * (1 - mu)
    H = (X * W[:, None]).T @ X + np.diag(lam)
    return b, np.linalg.inv(H)
