"""Per-card features and their army-level sums.

Every army-level feature is a SUM over the cards of the build of a per-card
feature times its number of copies.  That keeps every model linear in the
copies of each card, so the best build under any model is an exact
integer-linear programme (see optimise.py).

Per-card features (one row per card, `CARD_FEATURES` order):

* unit            1 for every non-staff card                (one unit slot used)
* surplus_k       (adjusted normative value - cost) / 1000  (paper value beyond the price)
* cost_k_<arm>    cost / 1000 for infantry / cavalry / artillery cards
* n_<class>       1 for a card of that unit class           (11 classes)
* commander       1 for a commander card                    (a named combat general)
* stars           staff general's command stars             (staff card only)
* tier_<tag>      speed-tag digit minus 3, per tag letter    (L, G, S, C, F, H)
* models_k        models / 1000                             (unit size)
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from common import Army, Card

CLASSES = ["infantry_line", "infantry_light", "infantry_grenadiers", "infantry_militia",
           "infantry_skirmishers", "infantry_irregulars", "cavalry_heavy", "cavalry_light",
           "cavalry_standard", "cavalry_lancers", "cavalry_missile", "artillery_foot",
           "artillery_horse"]
ARMS = ["infantry", "cavalry", "artillery"]
TAGS = ["L", "G", "S", "C", "F", "H"]

CARD_FEATURES = (["unit", "surplus_k"] + [f"cost_k_{a}" for a in ARMS]
                 + [f"n_{c}" for c in CLASSES] + ["commander", "stars"]
                 + [f"tier_{t}" for t in TAGS] + ["models_k"])
FI = {k: i for i, k in enumerate(CARD_FEATURES)}


def card_vector(c: Card) -> np.ndarray:
    v = np.zeros(len(CARD_FEATURES))
    if c.kind == "staff":
        v[FI["stars"]] = c.stars
        return v
    v[FI["unit"]] = 1
    v[FI["surplus_k"]] = (c.value_adj - c.cost) / 1000
    v[FI[f"cost_k_{c.arm}"]] = c.cost / 1000
    v[FI[f"n_{c.cls}"]] = 1
    v[FI["commander"]] = 1 if c.kind == "commander" else 0
    if c.tag in TAGS:
        v[FI[f"tier_{c.tag}"]] = c.tier - 3
    v[FI["models_k"]] = c.models / 1000
    return v


class CardIndex:
    """Global integer index over all (faction, card_key) pairs."""

    def __init__(self, cards: dict[str, dict[str, Card]]):
        self.keys: list[tuple[str, str]] = []
        self.pos: dict[tuple[str, str], int] = {}
        for f in sorted(cards):
            for k in sorted(cards[f]):
                self.pos[(f, k)] = len(self.keys)
                self.keys.append((f, k))
        self.card = [cards[f][k] for f, k in self.keys]
        self.F = np.array([card_vector(c) for c in self.card])   # n_cards x n_features

    def count_matrix(self, armies: list[Army]) -> sp.csr_matrix:
        """Armies x cards matrix of copies (staff included)."""
        rows, cols, vals = [], [], []
        for i, a in enumerate(armies):
            for k, n in a.counts.items():
                rows.append(i)
                cols.append(self.pos[(a.faction, k)])
                vals.append(n)
        return sp.csr_matrix((vals, (rows, cols)), shape=(len(armies), len(self.keys)))
