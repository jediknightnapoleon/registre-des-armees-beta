"""Unit-pricing model for NTW3 Theatre-of-War and Custom armies.

Structure (per the ex-dev: price is a linear combination of unit type, speed,
stats, traits and abilities, then multiplied by unit size and other factors):

    price = M × size^p × (b0 + Σ_j β_j·stat_j^(a_j) + flags + categoricals) + c

  size  unit size: models (men_raw / 2) for infantry and cavalry, GUNS for
        artillery (crew per gun is 10 foot / 6 horse, so models misprice one type
        against the other)
  p     size power — profiled by cross-validation
  a_j   per-stat powers on the numeric stats (still added together) — fitted by
        coordinate descent inside each training fold (nested CV)
  M     product of one factor per variable placed "multiplicative"
  c     optional flat per-unit constant, outside the multiplier

Which of corps rating, training level, drill set (infantry), packing
(rank_depth) and side belong in β·x, in M, or nowhere is searched
exhaustively; the headline is the simplest model within one standard error of
the best. Faction modifiers are fitted on top of the final model. Staff
generals keep their own model: price = 1 + (1 + δ(r − 8))·(b·stars + q·stars²).

Validation is 5-fold cross-validation where every fold is an 80/20 split built
to keep identical units together, stratify by unit type, cover every
categorical level in train, and spread each faction evenly.

Inputs:  data/generated/ntw3_units_analysis.csv  (tools/build_analysis_dataset.py)
         data/generated/army_corps_catalog.csv   (corps ratings)
Outputs: analysis/output/unit_pricing_report.md
         analysis/output/search_results.csv
         analysis/output/coefficients.csv
         analysis/output/oof_predictions.csv

Run from the repository root (takes ~20 minutes):

    python analysis/unit_pricing.py [--seeds 500]

Depends on numpy and scikit-learn only (pandas is not assumed to be installed).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parent.parent
DATA_CSV = ROOT / "data" / "generated" / "ntw3_units_analysis.csv"
CATALOG_CSV = ROOT / "data" / "generated" / "army_corps_catalog.csv"
OUT_DIR = ROOT / "analysis" / "output"

# Dev/test corps: "1. Lordz", "Lordz", "0. Placeholder A/B". Prices of 500-9 500
# that no real roster uses.
DEV_CORPS = frozenset({"aaa_lordz", "austria", "saxony", "hannover"})
# Custom Armies have catalog side "custom"; these two count as imperial (Denmark
# confirmed by the user — allied to France 1807-1814). The rest are coalition.
IMPERIAL_CUSTOM = frozenset({"france", "denmark"})
# "[1809] 7. Polska, sojusznicy" — pricing suspected wrong; run with and without.
POLAND = "ntw3_tow_c08_x8_048"
# Wellesley in "[1809] 10. UK, España, Portugal" — known arbitrary price (8★ at
# 1 746 vs an 8★ median of 1 197). Kept as a valid datapoint, reported.
WELLESLEY = "ntw3_gen_staff_163_8_0195_tow_020"

ARMS = ("infantry", "cavalry", "artillery")
SIDES = ("imperial", "coalition", "merged")
N_SPLITS = 5
TEST_SHARE = 1 / N_SPLITS
MIN_FLAG_ROWS = 5         # drop a 0/1 trait whose minority value covers fewer rows
MIN_STRATUM_GROUPS = 5    # collapse unit_class × speed to unit_class below this
MIN_BALANCE_ROWS = 10     # smaller factions can't approach 20% and don't drive the max
REF_RATING = 8            # rating at which the rating multiplier is 1 (the median corps)
MAX_ITER = 300
TOLERANCE = 1e-10

# Size power profile: p from 0.40 to 2.40. Size kinds tried per arm (first = default).
P_GRID = tuple(round(0.40 + 0.05 * i, 2) for i in range(41))
SIZE_KINDS = {"infantry": ("n",), "cavalry": ("n",), "artillery": ("guns", "n")}
# Stat-power coordinate descent: candidate powers per stat, and a ± window for p.
POWER_GRID = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
P_WINDOW = 0.30
MAX_PASSES = 4
# Fine local refinement around the coarse powers: a ±half window at a fine step
# per coordinate, re-centred (up to MAX_RECENTRE times) when the best value
# lands on a window edge — so powers stuck at the coarse grid's limits can move.
FINE_STAT_STEP, FINE_STAT_HALF = 0.05, 10     # stats: ±0.50 in steps of 0.05
FINE_P_STEP, FINE_P_HALF = 0.01, 15           # size power: ±0.15 in steps of 0.01
MIN_POWER = 0.05
MAX_RECENTRE = 4
FINE_PASSES = 3
# Powered stat columns are (stat / POWER_SCALE)^a, keeping large exponents
# numerically tame; predictions are unchanged, only the coefficient's unit.
POWER_SCALE = 100.0

# Shape options for how shooting and firearm/calibre information enters β·x.
#   fire  (infantry, cavalry): "range" — the numeric range stat; "firearm" — a
#         firearm one-hot (each firearm has exactly one range, so it holds all of
#         range plus whatever else differs between firearms)
#   cal   (artillery): "full" — range + projectile damage + projectile reload;
#         "calibre" — (damage/100)^a_cal with the shot-type one-hot (damage is a
#         consistent calibre label; within round shot it tracks range at r 0.99
#         and gun reload at r 0.92); "projectile" — a cannon-type one-hot
#   shoot "additive" — accuracy, ammo, reload_skill as separate columns;
#         "product" — one column shoot = Π (stat/100)^a × rate^a_rate, where
#         rate = RATE_SCALE / projectile reload time is the gun's intrinsic fire
#         rate (independent of the crew's reload_skill); "product_type" — the same
#         with one shooting slope per firearm / cannon type (artillery "calibre":
#         calibre inside the product instead)
#   cal   smooth calibre functions of log range r and log damage d, replacing the
#         cannon-type one-hot (analysis/calibre_function.py): "power2" —
#         (range/100)^a_r + (damage/100)^a_d; "spline_r" / "spline_d" — a natural
#         cubic spline in r or d with `cal_df` degrees of freedom; "spline_rd" — both
#         splines; "poly2" — a quadratic surface in (r, d) with the interaction
#   shot  (artillery) "onehot" — shot-type one-hot; "none" — left out, letting a 2-D
#         calibre function separate howitzers / unicorns from round shot
SHAPE_DEFAULTS = {"fire": "range", "cal": "full", "shoot": "additive", "cal_df": "3", "shot": "onehot"}
SHOOT_STATS = {
    "infantry": ("accuracy", "ammo", "reload_skill"),
    "cavalry": ("accuracy", "ammo", "reload_skill"),
    "artillery": ("accuracy", "reload_skill"),     # artillery ammo is a constant 30
}
RATE_SCALE = 20.0          # fire rate = 20 / reload time: ≈ 1 for a musket (14-20 s)

NUMERIC = (
    "accuracy", "reload_skill", "ammo", "morale",
    "melee_attack", "melee_defense", "charge_bonus", "range",
)
# Traits and abilities shown in the description "Abilities:" line.
ABILITIES = (
    "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
    "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
    "scares_enemies", "can_build_barricades",
)
# In-game abilities the description line omits — fixed in β·x (per the user).
EXTRA_ABILITIES = ("guard_mode", "skirmish", "can_snipe")

# Candidate variables for the structure search: categorical ones get a one-hot
# block (linear) or one free multiplier per level (multiplicative); rank_depth
# gets γ·rank_depth (linear) or 1 + δ·(rank_depth − median) (multiplicative).
CATEGORICAL = ("rating", "training", "drill", "side")
# Army-level price groupings (from the blind study, blind-pricing-study branch):
# one multiplier per faction (= army) and one per faction × unit_class cell, as
# NTW3 prices look hand-set per corps per unit class. Only ever multipliers, and
# fitted with a ridge pull towards 1 worth κ pseudo-units of average price, so
# they need no reference level and an unseen cell falls back to its faction's
# factor (then 1). Kept out of CATEGORICAL, which also drives linear placements.
GROUPING = ("faction", "fclass")
MULT_CATEGORICAL = CATEGORICAL + GROUPING
CANDIDATES = {
    "infantry": ("rating", "training", "drill", "rank_depth", "side"),
    "cavalry": ("rating", "training", "rank_depth", "side"),
    "artillery": ("rating", "training", "rank_depth", "side"),
}
# Linear-part ablations: groups of mutually exclusive alternatives.
ABLATIONS = {
    "infantry": {
        "solid square": [("+ pike_square", frozenset({"pike_square"}))],
        "firearm vs range": [
            ("firearm instead of range", frozenset({"firearm", "no_range"})),
            ("firearm + range", frozenset({"firearm"})),
            ("range + firearm reload time", frozenset({"proj_reload"})),
        ],
    },
    "cavalry": {
        "firearm vs range": [
            ("firearm instead of range", frozenset({"firearm", "no_range"})),
            ("firearm + range", frozenset({"firearm"})),
        ],
    },
    "artillery": {
        "calibre": [
            ("+ projectile damage", frozenset({"damage"})),
            ("+ projectile damage + reload time", frozenset({"damage", "proj_reload"})),
        ],
    },
}
# The game's own speed class closes every unit name: "... [L4]". It is
# game-authored, so it beats the pipeline-derived speed_code (which mislabels
# camels as L1 — see resolve_speed in build_ntw3_army_builder_database.py).
SPEED_TAG_RE = re.compile(r"\[([A-Z]+)(\d*)\]\s*$")


# --- Loading ------------------------------------------------------------------

@dataclass
class Unit:
    key: str
    name: str
    faction: str
    corps: str
    side: str            # imperial | coalition
    rating: int          # corps display_rating
    arm: str             # infantry | cavalry | artillery
    unit_class: str
    n: float             # models = men_raw / 2
    cost: int
    raw_tag: str         # speed tag exactly as in the name ("GS2", "DR")
    speed: str           # GS folded into S ("S2"); "DR" for camels
    speed_code: str      # pipeline value, kept only for the mismatch check
    is_camel: bool
    is_gs: bool
    training: str
    drill: str
    shot: str
    firearm: str
    weapon: str
    projectile: str
    rank_depth: float
    guns: float
    values: dict[str, float] = field(default_factory=dict)


@dataclass
class Staff:
    key: str
    name: str
    faction: str
    corps: str
    side: str
    rating: int
    stars: int
    cost: int


def load_ratings() -> dict[str, int]:
    """faction_key -> display_rating, the number that opens a corps name."""
    with CATALOG_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {row["faction_key"]: int(row["display_rating"])
                for row in csv.DictReader(handle) if row["display_rating"].strip().isdigit()}


def side_of(row: dict[str, str]) -> str:
    if row["corps_side"] == "tow_french_imperial" or row["faction_key"] in IMPERIAL_CUSTOM:
        return "imperial"
    return "coalition"


def in_scope(row: dict[str, str]) -> bool:
    return row["faction_kind"] in ("theatre_of_war", "custom") and row["faction_key"] not in DEV_CORPS


def num(text: str) -> float:
    text = text.strip()
    return float(text) if text else 0.0


def load(ratings: dict[str, int]) -> tuple[list[Unit], list[Staff], list[str], list[str]]:
    with DATA_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    missing = [c for c in ("skirmish", "projectile_damage", "rank_depth") if c not in rows[0]]
    if missing:
        sys.exit(f"{DATA_CSV.name} lacks {missing} — re-run tools/build_analysis_dataset.py")
    units: list[Unit] = []
    staff: list[Staff] = []
    unparsed: list[str] = []
    unrated: set[str] = set()
    for row in rows:
        if not in_scope(row):
            continue
        faction = row["faction_key"]
        if faction not in ratings:
            unrated.add(faction)
            continue
        if row["is_general"] == "true":
            # Staff rule: raw Men ∈ {32, 122} (Men/2 ∈ {16, 61}); only 32 occurs here.
            if row["men_raw"] in ("32", "122"):
                staff.append(Staff(
                    key=row["unit_key"], name=row["unit_name"], faction=faction,
                    corps=row["army_corps_name"], side=side_of(row), rating=ratings[faction],
                    stars=int(num(row["command_stars"])), cost=int(row["base_mp_cost"]),
                ))
            continue
        if row["unit_class"] == "artillery_fixed":
            continue
        match = SPEED_TAG_RE.search(row["unit_name"])
        if not match:
            unparsed.append(row["unit_key"])
            continue
        letter, tier = match.groups()
        raw_tag = letter + tier
        values = {column: num(row[column]) for column in NUMERIC}
        values["has_range"] = 1.0 if values["range"] > 0 else 0.0
        for column in ABILITIES + EXTRA_ABILITIES + ("pike_square",):
            values[column] = 1.0 if row[column] == "true" else 0.0
        values["proj_damage"] = num(row["projectile_damage"])
        values["proj_reload"] = num(row["projectile_reload_time"])
        units.append(Unit(
            key=row["unit_key"], name=row["unit_name"], faction=faction, corps=row["army_corps_name"],
            side=side_of(row), rating=ratings[faction],
            arm=row["unit_class"].split("_")[0], unit_class=row["unit_class"],
            n=int(row["men_raw"]) / 2, cost=int(row["base_mp_cost"]),
            raw_tag=raw_tag, speed=("S" if letter == "GS" else letter) + tier, speed_code=row["speed_code"],
            is_camel=raw_tag == "DR", is_gs=letter == "GS",
            training=row["unit_training_level"], drill=row["unit_drill_set"],
            shot=row["range_selection_method"], firearm=row["firearm"] or row["weapon_key"] or "none",
            weapon=row["weapon_key"], projectile=row["projectile_key"],
            rank_depth=num(row["rank_depth"]), guns=num(row["guns"]), values=values,
        ))
    return units, staff, unparsed, sorted(unrated)


# --- Model specification ------------------------------------------------------

@dataclass(frozen=True)
class Spec:
    """One model. `linear` / `mult` hold candidate variables; `const` adds c
    outside the multiplier; `extras` are linear-part ablation features; `size`
    is "n" (models) or "guns"; `p` the size power; `powers` per-stat powers as
    sorted (stat, a) pairs (absent = 1); `faction` adds a faction modifier.

    Blind-study options (defaults leave the model unchanged): `fixed_rating`
    replaces the free rating levels by the divisor REF_RATING / rating (drop
    "rating" from mult); "faction" / "fclass" in `mult` fit those groupings jointly
    with ridge strength `kappa`; `fclass = "residual"` adds a faction × unit_class
    modifier after the faction modifier, shrunk towards it with `kappa`; `loss =
    "lad"` fits least absolute deviation on total price by IRLS."""
    linear: frozenset[str] = frozenset()
    mult: frozenset[str] = frozenset()
    const: bool = False
    extras: frozenset[str] = frozenset()
    size: str = "n"
    p: float = 1.0
    powers: tuple[tuple[str, float], ...] = ()
    faction: bool = False
    shape: tuple[tuple[str, str], ...] = ()      # non-default SHAPE_DEFAULTS entries
    fixed_rating: bool = False
    fclass: str = "none"                         # "none" | "residual"
    kappa: float = 0.0
    loss: str = "ls"                             # "ls" | "lad"

    def power_of(self, stat: str) -> float:
        return dict(self.powers).get(stat, 1.0)

    def shape_of(self, key: str) -> str:
        return dict(self.shape).get(key, SHAPE_DEFAULTS[key])

    def describe(self) -> str:
        lin = ", ".join(sorted(self.linear)) or "—"
        size = "models" if self.size == "n" else "guns"
        mul = " × ".join([f"{size}^{self.p:g}"] + sorted(self.mult))
        parts = [f"β·x + [{lin}]", f"× {mul}"]
        if self.const:
            parts.append("+ c")
        # Artillery calibre / cannon-type shapes replace these extras (build_design drops them).
        shown = self.extras - ({"damage", "proj_reload"} if self.shape_of("cal") != "full" else set())
        if shown:
            parts.append("extras: " + ", ".join(sorted(shown)))
        if self.shape:
            parts.append("shape: " + ", ".join(f"{k}={v}" for k, v in self.shape))
        bent = [f"{s}^{a:g}" for s, a in self.powers if a != 1.0]
        if bent:
            parts.append("stat powers: " + ", ".join(bent))
        if self.fixed_rating:
            parts.append(f"rating fixed ({REF_RATING}/N)")
        if self.mult & set(GROUPING) or self.fclass != "none":
            parts.append(f"κ={self.kappa:g}")
        if self.fclass == "residual":
            parts.append("+ residual faction×class")
        if self.loss != "ls":
            parts.append(f"loss {self.loss}")
        return " ".join(parts)


def with_powers(spec: Spec, powers: dict[str, float], p: float) -> Spec:
    return replace(spec, powers=tuple(sorted((s, a) for s, a in powers.items() if a != 1.0)), p=p)


# --- Design matrix ------------------------------------------------------------

@dataclass
class Design:
    X: np.ndarray
    names: list[str]
    references: dict[str, str]   # categorical family -> reference (omitted) level
    dropped: list[str]           # candidate columns dropped as constant / too rare
    aliases: list[str] = field(default_factory=list)   # dropped as exact combinations of kept columns
    power_keys: list[str] = field(default_factory=list)   # exponents this design can fit


def most_common_level(levels: Sequence) -> object:
    counts = Counter(levels)
    return sorted(counts, key=lambda level: (-counts[level], str(level)))[0]


def prune_aliases(X: np.ndarray, names: Sequence[str]) -> tuple[np.ndarray, list[str], list[str]]:
    """Drop every column that is an exact linear combination of the constant and
    the columns kept before it, recording the identity it satisfies.

    The data has structural redundancies — artillery crew per gun is fixed by
    type (foot 10, horse 6), so guns/n is a function of the class; heavy cavalry
    are exactly the C1+C2 speeds; and so on. Pruning keeps OLS and every
    coefficient readable. Column order is the priority.
    """
    kept: list[int] = []
    kept_names: list[str] = []
    aliases: list[str] = []
    basis = [np.ones(len(X))]
    for j, name in enumerate(names):
        column = X[:, j]
        A = np.column_stack(basis)
        coef, *_ = np.linalg.lstsq(A, column, rcond=None)
        if np.abs(column - A @ coef).max() <= 1e-8 * max(1.0, float(np.abs(column).max())):
            terms = [f"{c:+.4g}·{n}" for c, n in zip(coef, ["1"] + kept_names) if abs(c) > 1e-8]
            aliases.append(f"`{name}` = " + " ".join(terms))
            continue
        basis.append(column)
        kept.append(j)
        kept_names.append(name)
    return X[:, kept], kept_names, aliases


def spline_knots(x: np.ndarray, df: int) -> np.ndarray:
    """df + 1 knots (boundary ones included) at unit-weighted quantiles of x; if
    heavy ties collapse them (338 batteries are 6-pdrs), quantiles of the distinct
    values are used instead."""
    knots = np.unique(np.quantile(x, np.linspace(0, 1, df + 1)))
    if len(knots) < df + 1:
        knots = np.quantile(np.unique(x), np.linspace(0, 1, df + 1))
    return knots


def natural_spline_basis(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Natural cubic spline basis (without the constant): x and K − 2 cubic terms,
    K = len(knots), so df = K − 1. Linear beyond the boundary knots, so it
    extrapolates sanely. Standard truncated-power construction:
    N_k = d_k − d_{K−1}, d_k(x) = ((x − ξ_k)³₊ − (x − ξ_K)³₊) / (ξ_K − ξ_k)."""
    K = len(knots)
    def d(k: int) -> np.ndarray:
        return (np.maximum(x - knots[k], 0) ** 3 - np.maximum(x - knots[-1], 0) ** 3) / (knots[-1] - knots[k])
    columns = [x] + [d(k) - d(K - 2) for k in range(K - 2)]
    return np.column_stack(columns)


def factor_values(units: Sequence[Unit], var: str) -> np.ndarray:
    if var == "rating":
        return np.array([u.rating for u in units])
    if var == "training":
        return np.array([u.training for u in units])
    if var == "drill":
        return np.array([u.drill for u in units])
    if var == "side":
        return np.array([u.side for u in units])
    if var == "rank_depth":
        return np.array([u.rank_depth for u in units], float)
    if var == "size":
        # Diagnostic only: a multiplier 1 + δ·(n − median) tests whether price
        # per model changes with unit size (rank_depth tracks n at r ≈ 0.97).
        return np.array([u.n for u in units], float)
    if var == "faction":
        return np.array([u.faction for u in units])
    if var == "fclass":
        return np.array([f"{u.faction}|{u.unit_class}" for u in units])
    raise KeyError(var)


def build_design(units: Sequence[Unit], arm: str, *, linear: frozenset[str] = frozenset(),
                 extras: frozenset[str] = frozenset(), powers: dict[str, float] | None = None,
                 const_inside: bool = False, use_gs: bool = False, shape: dict[str, str] | None = None) -> Design:
    """Per-size feature matrix f(x). The per-size constant b0 is the regression
    intercept, not a column. `linear` holds the candidate variables placed in the
    linear part; `extras` the ablation features; `powers` the exponents — on
    additive numeric stats (key = stat), inside the shooting product (key =
    "shoot:<stat>", "shoot:rate", "shoot:damage") and on the artillery calibre
    column ("cal:damage"); `shape` how shooting and firearm/calibre enter (see
    SHAPE_DEFAULTS); `const_inside` adds a c/n column (coverage design only)."""
    powers = powers or {}
    shape = {**SHAPE_DEFAULTS, **(shape or {})}
    fire, cal, shoot = shape["fire"], shape["cal"], shape["shoot"]
    extras = set(extras)
    if fire == "firearm" and arm != "artillery":
        extras |= {"firearm", "no_range"}
    if arm == "artillery" and cal != "full":
        # Calibre / cannon type carry range and the gun's reload time.
        extras = (extras - {"damage", "proj_reload"}) | {"no_range"}
    shoot_stats = SHOOT_STATS[arm] if shoot != "additive" else ()
    columns: list[np.ndarray] = []
    names: list[str] = []
    dropped: list[str] = []
    references: dict[str, str] = {}
    power_keys: list[str] = []

    def add(values: np.ndarray, name: str) -> None:
        columns.append(np.asarray(values, float))
        names.append(name)

    def stat(column: str) -> np.ndarray:
        return np.array([u.values[column] for u in units], float)

    for column in NUMERIC:
        if (column == "range" and "no_range" in extras) or column in shoot_stats:
            continue
        values = stat(column)
        if np.ptp(values) == 0:
            dropped.append(f"{column} (constant)")
            continue
        a = powers.get(column, 1.0)
        add((values / POWER_SCALE) ** a if a != 1.0 else values, column)
        power_keys.append(column)

    flags = (("has_range",) if "no_range" not in extras else ()) + ABILITIES + EXTRA_ABILITIES
    if "pike_square" in extras:
        flags += ("pike_square",)
    for column in flags:
        values = np.array([u.values[column] for u in units])
        minority = int(min(values.sum(), len(values) - values.sum()))
        if minority < MIN_FLAG_ROWS:
            dropped.append(f"{column} ({minority} minority rows)")
            continue
        add(values, column)

    # Explicit traits are kept however rare (they are the point of the feature);
    # the split pins singleton levels to train and reports them as unvalidated.
    if arm == "cavalry":
        camel = np.array([1.0 if u.is_camel else 0.0 for u in units])
        if camel.any():
            add(camel, "is_camel")
    if arm == "infantry" and use_gs:
        gs = np.array([1.0 if u.is_gs else 0.0 for u in units])
        if gs.any():
            add(gs, "is_gs")

    families: list[tuple[str, Callable[[Unit], object]]] = [
        ("unit_class", lambda u: u.unit_class),
        # Camels carry is_camel instead of a speed level (all speed dummies 0).
        ("speed", lambda u: None if u.is_camel else u.speed),
    ]
    if "training" in linear:
        families.append(("training", lambda u: u.training))
    if "drill" in linear and arm == "infantry":
        families.append(("drill", lambda u: u.drill))
    if arm == "artillery" and shape["shot"] != "none":
        families.append(("shot", lambda u: u.shot))
    if arm == "artillery" and cal == "projectile":
        families.append(("projectile", lambda u: u.projectile))
    if "firearm" in extras:
        families.append(("firearm", lambda u: u.firearm))
    if "rating" in linear:
        families.append(("rating", lambda u: u.rating))
    if "side" in linear:
        families.append(("side", lambda u: u.side))
    for family, getter in families:
        levels = [getter(u) for u in units]
        present = [level for level in levels if level is not None]
        if len(set(present)) < 2:
            dropped.append(f"{family} (single level)")
            continue
        if family == "rating" and REF_RATING in present:
            reference = REF_RATING
        else:
            reference = most_common_level(present)
        references[family] = str(reference)
        for level in sorted(set(present) - {reference}, key=str):
            add(np.array([1.0 if value == level else 0.0 for value in levels]), f"{family}={level}")

    if "rank_depth" in linear:
        add(np.array([u.rank_depth for u in units]), "rank_depth")
    if "damage" in extras:
        add(np.array([u.values["proj_damage"] for u in units]), "projectile_damage")
    if "proj_reload" in extras:
        add(np.array([u.values["proj_reload"] for u in units]), "projectile_reload_time")

    if arm == "artillery" and cal == "calibre":
        add((stat("proj_damage") / POWER_SCALE) ** powers.get("cal:damage", 1.0), "calibre")
        power_keys.append("cal:damage")
    if arm == "artillery" and cal == "power2":
        add((stat("range") / POWER_SCALE) ** powers.get("cal:range", 1.0), "calibre_range")
        add((stat("proj_damage") / POWER_SCALE) ** powers.get("cal:damage", 1.0), "calibre_damage")
        power_keys += ["cal:range", "cal:damage"]
    if arm == "artillery" and cal in ("spline_r", "spline_d", "spline_rd", "poly2"):
        log_r, log_d = np.log(stat("range")), np.log(stat("proj_damage"))
        df = int(shape["cal_df"])
        if cal in ("spline_r", "spline_rd"):
            for j, column in enumerate(natural_spline_basis(log_r, spline_knots(log_r, df)).T):
                add(column, f"cal_r{j + 1}")
        if cal in ("spline_d", "spline_rd"):
            for j, column in enumerate(natural_spline_basis(log_d, spline_knots(log_d, df)).T):
                add(column, f"cal_d{j + 1}")
        if cal == "poly2":
            r, d = log_r - log_r.mean(), log_d - log_d.mean()
            for column, name in ((r, "cal_lr"), (d, "cal_ld"), (r * r, "cal_lr2"), (d * d, "cal_ld2"), (r * d, "cal_lrld")):
                add(column, name)

    if shoot_stats:
        # Shooting effectiveness compounded: accuracy, ammo and the crew's reload
        # skill multiply with the gun's intrinsic fire rate (independent of crew
        # skill). Not shifted: zero ammo or accuracy really means no shooting.
        product = np.ones(len(units))
        for column in shoot_stats:
            product *= (stat(column) / POWER_SCALE) ** powers.get(f"shoot:{column}", 1.0)
        reload_time = stat("proj_reload")
        rate = np.divide(RATE_SCALE, reload_time, out=np.zeros(len(units)), where=reload_time > 0)
        product *= rate ** powers.get("shoot:rate", 1.0)
        power_keys += [f"shoot:{column}" for column in shoot_stats] + ["shoot:rate"]
        by_type = None
        if shoot == "product_type":
            if arm == "artillery" and cal == "calibre":
                product *= (stat("proj_damage") / POWER_SCALE) ** powers.get("shoot:damage", 1.0)
                power_keys.append("shoot:damage")
            elif arm == "artillery" and cal == "projectile":
                by_type = ("projectile", [u.projectile for u in units])
            elif "firearm" in extras:
                by_type = ("firearm", [u.firearm for u in units])
        if by_type:
            family, levels = by_type
            for level in sorted(set(levels)):
                add(product * np.array([1.0 if value == level else 0.0 for value in levels]), f"shoot×{family}={level}")
        else:
            add(product, "shoot")

    if arm == "artillery":
        # Crew per gun is fixed by type, so guns/n is a function of the class and
        # this column is always aliased (reported) — kept for the identity.
        add(np.array([u.guns / u.n for u in units]), "guns_per_model")
    if const_inside:
        add(np.array([1.0 / u.n for u in units]), "per_unit_const")

    X = np.column_stack(columns) if columns else np.zeros((len(units), 0))
    X, names, aliases = prune_aliases(X, names)
    # An exponent is fittable only while its column survived alias pruning.
    shooting_kept = any(name == "shoot" or name.startswith("shoot×") for name in names)
    cal_columns = {"cal:damage": ("calibre", "calibre_damage"), "cal:range": ("calibre_range",)}
    power_keys = [k for k in power_keys
                  if (k.startswith("shoot:") and shooting_kept)
                  or (k in cal_columns and any(c in names for c in cal_columns[k]))
                  or k in names]
    return Design(X=X, names=names, references=references, dropped=dropped, aliases=aliases, power_keys=power_keys)


def design_for(spec: Spec, units: Sequence[Unit], arm: str) -> Design:
    return build_design(units, arm, linear=spec.linear, extras=spec.extras, powers=dict(spec.powers),
                        shape=dict(spec.shape))


# --- Model --------------------------------------------------------------------

class PriceModel:
    """Per-size price y = cost/size = M·g·(b0 + β·f(x)) + c/size, where
    g = size^(p−1) carries the size power and M = Π_k m_k (one factor per
    variable in spec.mult; categorical factors have one m per level with the
    reference fixed at 1, rank_depth has m = 1 + δ·(rank_depth − median)).

    Fitted by alternating least squares on Σ w·(y − M·g·(b0 + β·f(x)) − c/size)²
    (w = 1 unless IRLS row weights are passed): the β/c step is exact least
    squares on the columns [M·g, M·g·X, 1/size]; each factor step is a
    closed-form regression on y − c/size given everything else. Every step lowers
    the objective, which is asserted. Grouping factors (faction, faction × class)
    carry no reference level; instead the objective adds λ·Σ (m − 1)² with
    λ = κ·mean(w·y²) — κ pseudo-units of average price at m = 1 — so their step
    is m = (Σ w·t·q + λ) / (Σ w·q² + λ).

    A faction modifier, when asked for, is fitted afterwards on the scaled part:
    m_f = Σ (y − c/size)·q / Σ q², q = M·g·base; a residual faction × class
    modifier then multiplies it, shrunk towards 1 (i.e. towards m_f) the same way.
    """

    def __init__(self, spec: Spec):
        self.spec = spec
        self.b0 = 0.0
        self.beta = np.zeros(0)
        self.c = 0.0
        self.levels: dict[str, dict[object, float]] = {}
        self.refs: dict[str, object] = {}
        self.delta: dict[str, float] = {}
        self.faction_m: dict[str, float] = {}
        self.fclass_m: dict[str, float] = {}
        self.ridge: dict[str, float] = {}
        self.iterations = 0
        self.sse = float("nan")

    def _factor(self, var: str, values: np.ndarray) -> np.ndarray:
        if var in MULT_CATEGORICAL:
            table = self.levels[var]
            return np.array([table.get(v, 1.0) for v in values.tolist()])
        return 1 + self.delta[var] * (values - self.refs[var])

    def fit(self, X: np.ndarray, y: np.ndarray, inv: np.ndarray, g: np.ndarray,
            fvals: dict[str, np.ndarray], factions: np.ndarray,
            weights: np.ndarray | None = None) -> "PriceModel":
        mult = sorted(self.spec.mult)
        w = np.ones(len(y)) if weights is None else weights
        sw = None if weights is None else np.sqrt(weights)
        scale2 = float(np.mean(w * y * y))
        codes: dict[str, tuple[np.ndarray, list]] = {}
        for var in mult:
            values = fvals[var]
            if var in MULT_CATEGORICAL:
                levels = sorted(set(values.tolist()), key=str)
                if var in GROUPING:
                    self.refs[var] = None
                    self.ridge[var] = self.spec.kappa * scale2
                else:
                    ref = REF_RATING if var == "rating" and REF_RATING in levels else most_common_level(values.tolist())
                    self.refs[var] = ref
                self.levels[var] = {level: 1.0 for level in levels}
                index = {level: i for i, level in enumerate(levels)}
                codes[var] = (np.array([index[v] for v in values.tolist()]), levels)
            else:
                self.refs[var] = float(np.median(values))
                self.delta[var] = 0.0
        factor = {var: np.ones(len(y)) for var in mult}
        M = np.ones(len(y))
        previous = np.inf
        for self.iterations in range(1, MAX_ITER + 1):
            scale = M * g
            Z = np.hstack([scale[:, None], scale[:, None] * X] + ([inv[:, None]] if self.spec.const else []))
            if sw is None:
                coef, *_ = np.linalg.lstsq(Z, y, rcond=None)
            else:
                coef, *_ = np.linalg.lstsq(Z * sw[:, None], y * sw, rcond=None)
            self.b0 = float(coef[0])
            self.beta = coef[1:1 + X.shape[1]]
            self.c = float(coef[-1]) if self.spec.const else 0.0
            base = g * (self.b0 + X @ self.beta)
            target = y - self.c * inv
            for var in mult:
                q = base.copy()
                for other in mult:
                    if other != var:
                        q *= factor[other]
                wq = q if weights is None else w * q
                if var in MULT_CATEGORICAL:
                    code, levels = codes[var]
                    numerator = np.bincount(code, weights=target * wq, minlength=len(levels))
                    denominator = np.bincount(code, weights=q * wq, minlength=len(levels))
                    if var in GROUPING:
                        lam = self.ridge[var]
                        m = np.divide(numerator + lam, denominator + lam, out=np.ones(len(levels)),
                                      where=denominator + lam > 0)
                    else:
                        m = np.divide(numerator, denominator, out=np.ones(len(levels)), where=denominator > 0)
                        m[levels.index(self.refs[var])] = 1.0
                    self.levels[var] = dict(zip(levels, m.tolist()))
                    factor[var] = m[code]
                else:
                    d = fvals[var] - self.refs[var]
                    if weights is None:
                        denominator = float(((d * q) ** 2).sum())
                        numerator = float(((target - q) * d * q).sum())
                    else:
                        denominator = float((w * (d * q) ** 2).sum())
                        numerator = float((w * (target - q) * d * q).sum())
                    self.delta[var] = numerator / denominator if denominator else 0.0
                    factor[var] = 1 + self.delta[var] * d
            M = np.prod([factor[var] for var in mult], axis=0) if mult else np.ones(len(y))
            residual = y - M * base - self.c * inv
            sse = float((residual ** 2).sum()) if weights is None else float((w * residual ** 2).sum())
            sse += sum(lam * sum((m - 1) ** 2 for m in self.levels[var].values()) for var, lam in self.ridge.items())
            if not mult:
                break
            if sse > previous * (1 + 1e-7) + 1e-9:
                raise AssertionError(f"ALS objective rose: {previous} -> {sse} ({self.spec.describe()})")
            if np.isfinite(previous) and previous - sse <= TOLERANCE * previous:
                break
            previous = sse
        self.sse = sse
        if self.spec.faction:
            q = M * g * (self.b0 + X @ self.beta)
            target = y - self.c * inv
            self.faction_m = {}
            for faction in set(factions.tolist()):
                mask = factions == faction
                if weights is None:
                    self.faction_m[faction] = float((target[mask] * q[mask]).sum() / (q[mask] ** 2).sum())
                else:
                    wm = w[mask]
                    self.faction_m[faction] = float((wm * target[mask] * q[mask]).sum() / (wm * q[mask] ** 2).sum())
            if self.spec.fclass == "residual":
                s = q * np.array([self.faction_m[f] for f in factions.tolist()])
                ws = s if weights is None else w * s
                lam = self.spec.kappa * scale2
                cells = fvals["fclass"].tolist()
                code_of = {cell: i for i, cell in enumerate(sorted(set(cells)))}
                code = np.array([code_of[cell] for cell in cells])
                numerator = np.bincount(code, weights=target * ws, minlength=len(code_of))
                denominator = np.bincount(code, weights=s * ws, minlength=len(code_of))
                m = np.divide(numerator + lam, denominator + lam, out=np.ones(len(code_of)),
                              where=denominator + lam > 0)
                self.fclass_m = dict(zip(code_of, m.tolist()))
        return self

    def multiplier(self, fvals: dict[str, np.ndarray], size: int) -> np.ndarray:
        M = np.ones(size)
        for var in self.spec.mult:
            M = M * self._factor(var, fvals[var])
        return M

    def parts(self, X: np.ndarray, inv: np.ndarray, g: np.ndarray, fvals: dict[str, np.ndarray],
              factions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(scaled per-size part M·m_f·g·(b0 + β·f(x)), constant per-size part c/size)."""
        scaled = self.multiplier(fvals, len(X)) * g * (self.b0 + X @ self.beta)
        if self.spec.faction:
            scaled = scaled * np.array([self.faction_m.get(f, 1.0) for f in factions])
            if self.spec.fclass == "residual":
                scaled = scaled * np.array([self.fclass_m.get(c, 1.0) for c in fvals["fclass"].tolist()])
        return scaled, self.c * inv

    def predict(self, X, inv, g, fvals, factions) -> np.ndarray:
        scaled, const = self.parts(X, inv, g, fvals, factions)
        return scaled + const

    def unseen(self, fvals: dict[str, np.ndarray], factions: np.ndarray) -> int:
        """Test rows predicted with a fallback multiplier of 1 (level/faction not in
        training). An unseen faction × class cell counts too, although it falls
        back to its faction's factor rather than to 1."""
        bad = np.zeros(len(factions), bool)
        for var in self.spec.mult:
            if var in MULT_CATEGORICAL:
                bad |= np.array([v not in self.levels[var] for v in fvals[var].tolist()])
        if self.spec.faction:
            bad |= np.array([f not in self.faction_m for f in factions])
            if self.spec.fclass == "residual":
                bad |= np.array([c not in self.fclass_m for c in fvals["fclass"].tolist()])
        return int(bad.sum())

    def n_params(self, X: np.ndarray) -> int:
        """Free coefficients; ridge-shrunk grouping levels and residual faction ×
        class cells count in full (an upper bound on their effective number); the
        plain faction modifier is not counted, as before."""
        count = 1 + X.shape[1] + (1 if self.spec.const else 0)
        for var in self.spec.mult:
            if var in GROUPING:
                count += len(self.levels[var])
            else:
                count += len(self.levels[var]) - 1 if var in CATEGORICAL else 1
        if self.spec.fclass == "residual":
            count += len(self.fclass_m)
        return count


def metrics(cost: np.ndarray, pred: np.ndarray, size: np.ndarray | None = None,
            mape_mask: np.ndarray | None = None) -> dict[str, float]:
    error = cost - pred
    sst = float(((cost - cost.mean()) ** 2).sum())
    mask = np.ones(len(cost), bool) if mape_mask is None else mape_mask
    ape = np.abs(error[mask]) / cost[mask]
    out = {
        "r2": 1 - float((error ** 2).sum()) / sst if sst else float("nan"),
        "mae": float(np.abs(error).mean()),
        "mape": float(ape.mean() * 100) if mask.any() else float("nan"),
        "medape": float(np.median(ape) * 100) if mask.any() else float("nan"),
    }
    if size is not None:
        per, per_pred = cost / size, pred / size
        sst_pm = float(((per - per.mean()) ** 2).sum())
        out["r2_pm"] = 1 - float(((per - per_pred) ** 2).sum()) / sst_pm
    return out


# --- Coverage-guaranteed, faction-balanced 80/20 splits -----------------------

Fold = tuple[np.ndarray, np.ndarray]   # (train indices, test indices)


@dataclass
class SplitPlan:
    seed: int
    folds: list[Fold]
    pinned: list[str]          # coverage columns whose single minority group is pinned to train
    n_pinned_rows: int
    violations_before_repair: int
    repairs: list[str]
    balance_max: float         # max |test share − 20%| over balance keys with ≥ MIN_BALANCE_ROWS
    balance_spread: tuple[float, float, float]   # min / median / max test share, fold 1


def group_ids(C: np.ndarray, extra: Sequence[object]) -> np.ndarray:
    """Rows with identical coverage features (and identical `extra`) share a group,
    so a duplicate unit can never sit in train and test at once."""
    seen: dict[tuple, int] = {}
    return np.array([
        seen.setdefault(tuple(np.round(row, 9)) + (key,), len(seen))
        for row, key in zip(C, extra)
    ])


def pinned_groups(C: np.ndarray, groups: np.ndarray, names: Sequence[str]) -> tuple[set[int], list[str]]:
    """A 0/1 column whose minority value lives in a single group can never be in
    both train and test; pin that group to train in every fold."""
    pinned: set[int] = set()
    labels: list[str] = []
    for j, name in enumerate(names):
        column = C[:, j]
        if not np.isin(column, (0.0, 1.0)).all():
            continue
        for value in (0.0, 1.0):
            holders = set(groups[column == value].tolist())
            if len(holders) == 1 and len(set(groups.tolist())) > 1:
                pinned |= holders
                labels.append(name if value == 1.0 else f"{name} (=0)")
    return pinned, labels


def assign_folds(strata: np.ndarray, balance: np.ndarray, groups: np.ndarray,
                 eligible: np.ndarray, seed: int) -> np.ndarray:
    """Stratified, grouped, faction-interleaved fold assignment.

    Groups are ordered by (stratum, balance key, seeded random key) and dealt
    round-robin into the folds from a seeded offset. Every stratum is a
    consecutive run, so each stratum is spread across folds with counts differing
    by at most one; inside a stratum each balance key (faction) is also a
    consecutive run, so it is spread the same way. Same guarantees as sklearn's
    StratifiedGroupKFold for this data (almost every group is a single unit), at
    a cost of milliseconds rather than a second per split.
    """
    rng = np.random.default_rng(seed)
    unique = np.unique(groups[eligible])
    first_row = {g: i for i, g in reversed(list(enumerate(groups))) if eligible[i]}
    random_key = dict(zip(unique.tolist(), rng.permutation(len(unique)).tolist()))
    order = sorted(unique.tolist(), key=lambda g: (
        strata[first_row[g]], balance[first_row[g]], random_key[g]))
    offset = int(rng.integers(N_SPLITS))
    fold_of_group = {g: (offset + position) % N_SPLITS for position, g in enumerate(order)}
    fold = np.full(len(groups), -1)
    for i in np.flatnonzero(eligible):
        fold[i] = fold_of_group[groups[i]]
    return fold


def unidentified(C: np.ndarray, train: np.ndarray, test: np.ndarray) -> np.ndarray:
    """Columns constant in train but taking another value in test — their
    coefficient is undefined, so those test predictions would be arbitrary."""
    lo, hi = C[train].min(axis=0), C[train].max(axis=0)
    constant = lo == hi
    return constant & ((C[test].min(axis=0) != lo) | (C[test].max(axis=0) != hi))


def folds_from(fold: np.ndarray) -> list[Fold]:
    everything = np.arange(len(fold))
    out = []
    for k in range(N_SPLITS):
        test = np.flatnonzero(fold == k)
        out.append((np.setdiff1d(everything, test), test))   # pinned rows (-1) always train
    return out


def balance_scores(folds: list[Fold], balance: np.ndarray) -> tuple[float, float, tuple[float, float, float]]:
    totals = Counter(balance.tolist())
    big = [key for key, total in totals.items() if total >= MIN_BALANCE_ROWS]
    worst, sse = 0.0, 0.0
    fold1_shares: list[float] = []
    for k, (_, test) in enumerate(folds):
        in_test = Counter(balance[test].tolist())
        for key, total in totals.items():
            share = in_test.get(key, 0) / total
            sse += total * (share - TEST_SHARE) ** 2
            if key in big:
                worst = max(worst, abs(share - TEST_SHARE))
                if k == 0:
                    fold1_shares.append(share)
    spread = (min(fold1_shares), float(np.median(fold1_shares)), max(fold1_shares)) if fold1_shares else (0, 0, 0)
    return worst, sse, spread


def repair(folds: list[Fold], C: np.ndarray, groups: np.ndarray, names: Sequence[str]) -> tuple[list[Fold], list[str]]:
    log: list[str] = []
    fixed: list[Fold] = []
    for k, (train, test) in enumerate(folds):
        train, test = train.copy(), test.copy()
        while True:
            bad = np.flatnonzero(unidentified(C, train, test))
            if bad.size == 0:
                break
            j = bad[0]
            constant = C[train, j][0]
            movers = set(groups[test][C[test, j] != constant].tolist())
            move = np.isin(groups[test], list(movers))
            log.append(f"fold {k + 1}: moved {int(move.sum())} row(s) to train for `{names[j]}`")
            train = np.sort(np.concatenate([train, test[move]]))
            test = test[~move]
        fixed.append((train, test))
    return fixed, log


def search_splits(C: np.ndarray, names: Sequence[str], strata: np.ndarray, balance: np.ndarray,
                  groups: np.ndarray, n_seeds: int, extra_pinned: set[int] | None = None) -> SplitPlan:
    """Try `n_seeds` assignments; keep the one with zero coverage violations and
    the most uniform spread of `balance` keys across test folds. `extra_pinned`
    groups are always trained on too (analysis/extreme_pinning.py)."""
    pinned, pinned_labels = pinned_groups(C, groups, names)
    if extra_pinned:
        pinned = pinned | extra_pinned
        pinned_labels = pinned_labels + [f"{len(extra_pinned)} extra group(s)"]
    eligible = ~np.isin(groups, list(pinned))
    best: tuple | None = None
    for seed in range(n_seeds):
        folds = folds_from(assign_folds(strata, balance, groups, eligible, seed))
        violations = sum(int(unidentified(C, tr, te).sum()) for tr, te in folds)
        worst, sse, spread = balance_scores(folds, balance)
        score = (violations, round(worst, 9), sse)
        if best is None or score < best[0]:
            best = (score, seed, folds, spread)
    (violations, worst, _), seed, folds, spread = best
    folds, log = repair(folds, C, groups, names) if violations else (folds, [])
    return SplitPlan(
        seed=seed, folds=folds, pinned=sorted(set(pinned_labels)),
        n_pinned_rows=int((~eligible).sum()), violations_before_repair=violations,
        repairs=log, balance_max=worst, balance_spread=spread,
    )


def restrict(plan: SplitPlan, keep: np.ndarray, C: np.ndarray, groups: np.ndarray,
             names: Sequence[str]) -> SplitPlan:
    """The same folds with some rows removed (the Poland-excluded runs), re-checked
    for coverage and repaired if removing rows broke it."""
    new_index = -np.ones(len(keep), int)
    new_index[keep] = np.arange(int(keep.sum()))
    folds = [(new_index[tr[keep[tr]]], new_index[te[keep[te]]]) for tr, te in plan.folds]
    violations = sum(int(unidentified(C, tr, te).sum()) for tr, te in folds)
    folds, log = repair(folds, C, groups, names) if violations else (folds, [])
    return SplitPlan(
        seed=plan.seed, folds=folds, pinned=plan.pinned, n_pinned_rows=plan.n_pinned_rows,
        violations_before_repair=violations, repairs=log,
        balance_max=plan.balance_max, balance_spread=plan.balance_spread,
    )


# --- Cross-validation ---------------------------------------------------------

@dataclass
class CVRun:
    label: str
    fold_metrics: list[dict[str, float]]
    oof: np.ndarray
    oof_fold: np.ndarray
    spec: Spec | None = None
    full: PriceModel | None = None
    names: list[str] = field(default_factory=list)
    references: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    params: int = 0
    fallbacks: int = 0      # test rows predicted with a fallback multiplier of 1

    def coef(self, name: str) -> float:
        return float(self.full.beta[self.names.index(name)]) if name in self.names else float("nan")

    def mean(self, metric: str) -> float:
        return float(np.mean([m[metric] for m in self.fold_metrics]))

    def sd(self, metric: str) -> float:
        return float(np.std([m[metric] for m in self.fold_metrics], ddof=1))

    def se(self, metric: str) -> float:
        return self.sd(metric) / np.sqrt(len(self.fold_metrics))

    def fold1(self, metric: str) -> float:
        return self.fold_metrics[0][metric]


@dataclass
class SliceData:
    n: np.ndarray        # models
    size: np.ndarray     # models or guns — the multiplied size
    cost: np.ndarray
    y: np.ndarray        # cost / size
    inv: np.ndarray      # 1 / size
    g: np.ndarray        # size^(p − 1)
    factions: np.ndarray
    fvals: dict[str, np.ndarray]


def size_of(u: Unit, kind: str) -> float:
    return u.guns if kind == "guns" else u.n


def slice_data(units: Sequence[Unit], kind: str = "n", p: float = 1.0) -> SliceData:
    n = np.array([u.n for u in units])
    size = np.array([size_of(u, kind) for u in units])
    cost = np.array([u.cost for u in units], float)
    return SliceData(n, size, cost, cost / size, 1 / size, size ** (p - 1), np.array([u.faction for u in units]),
                     {var: factor_values(units, var)
                      for var in ("rating", "training", "drill", "side", "rank_depth", "size") + GROUPING})


def data_for(spec: Spec, units: Sequence[Unit]) -> SliceData:
    d = slice_data(units, spec.size, spec.p)
    if spec.fixed_rating:
        # Rating as a fixed divisor: price ∝ REF_RATING / rating, folded into g so
        # it scales the β part (c stays outside, like every multiplier).
        d = replace(d, g=d.g * REF_RATING / d.fvals["rating"].astype(float))
    return d


def sub(fvals: dict[str, np.ndarray], index: np.ndarray) -> dict[str, np.ndarray]:
    return {k: v[index] for k, v in fvals.items()}


IRLS_STEPS = 10          # loss = "lad": reweighted least-squares passes
IRLS_FLOOR = 1.0         # gold; |residual| floor in the IRLS weights


def fit_on(spec: Spec, design: Design, d: SliceData, rows: np.ndarray) -> PriceModel:
    args = (design.X[rows], d.y[rows], d.inv[rows], d.g[rows], sub(d.fvals, rows), d.factions[rows])
    model = PriceModel(spec).fit(*args)
    if spec.loss == "lad":
        # Least absolute deviation on total price, Σ size·|y − ŷ|, by IRLS on the
        # per-size objective: w = size / |y − ŷ| = size² / |total residual|.
        size = d.size[rows]
        X, y, inv, g, fvals, factions = args
        for _ in range(IRLS_STEPS):
            resid = size * np.abs(y - model.predict(X, inv, g, fvals, factions))
            model = PriceModel(spec).fit(*args, weights=size ** 2 / np.maximum(resid, IRLS_FLOOR))
    return model


def predict_total(model: PriceModel, design: Design, d: SliceData, rows: np.ndarray) -> np.ndarray:
    return d.size[rows] * model.predict(design.X[rows], d.inv[rows], d.g[rows], sub(d.fvals, rows), d.factions[rows])


def cv_spec(spec: Spec, units: Sequence[Unit], folds: list[Fold], arm: str, *,
            full_fit: bool = True, label: str | None = None, design: Design | None = None,
            data: SliceData | None = None) -> CVRun:
    design = design or design_for(spec, units, arm)
    d = data or data_for(spec, units)
    # Rows pinned to train never get an out-of-fold prediction: they stay NaN.
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics, fallbacks = [], 0
    for k, (train, test) in enumerate(folds):
        model = fit_on(spec, design, d, train)
        pred = predict_total(model, design, d, test)
        fallbacks += model.unseen(sub(d.fvals, test), d.factions[test])
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(d.cost[test], pred, d.size[test]))
    full = fit_on(spec, design, d, np.arange(len(units))) if full_fit else None
    params = full.n_params(design.X) if full else (
        1 + design.X.shape[1] + int(spec.const) +
        sum(len(set(d.fvals[v].tolist())) - (v in CATEGORICAL) if v in MULT_CATEGORICAL else 1 for v in spec.mult))
    return CVRun(label or spec.describe(), fold_metrics, oof, oof_fold, spec, full,
                 design.names, design.references, design.aliases, params, fallbacks)


def cv_baseline(units: Sequence[Unit], folds: list[Fold]) -> CVRun:
    """Mean price per model of the unit's class (from the training fold) × n."""
    d = slice_data(units)
    classes = np.array([u.unit_class for u in units])
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics = []
    for k, (train, test) in enumerate(folds):
        means = {c: d.y[train][classes[train] == c].mean() for c in set(classes[train].tolist())}
        fallback = d.y[train].mean()
        pred = d.n[test] * np.array([means.get(c, fallback) for c in classes[test]])
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(d.cost[test], pred, d.n[test]))
    return CVRun("baseline (class mean × n)", fold_metrics, oof, oof_fold)


# --- Slices -------------------------------------------------------------------

@dataclass
class Slice:
    arm: str
    side: str
    units: list[Unit]
    plan: SplitPlan
    groups: np.ndarray
    runs: dict[str, CVRun] = field(default_factory=dict)
    coverage: dict[str, tuple[int, int, int]] = field(default_factory=dict)


def strata_for(units: Sequence[Unit], groups: np.ndarray) -> np.ndarray:
    cell = [f"{u.unit_class}|{u.speed}" for u in units]
    groups_per_cell: dict[str, set[int]] = defaultdict(set)
    for c, g in zip(cell, groups.tolist()):
        groups_per_cell[c].add(g)
    return np.array([
        c if len(groups_per_cell[c]) >= MIN_STRATUM_GROUPS else u.unit_class
        for c, u in zip(cell, units)
    ])


def coverage_report(units: Sequence[Unit], folds: list[Fold], arm: str) -> dict[str, tuple[int, int, int]]:
    """family -> (levels in both sets in fold 1, min over folds, total levels)."""
    families: dict[str, Callable[[Unit], object]] = {
        "unit_class": lambda u: u.unit_class,
        "speed": lambda u: u.speed,
        "training": lambda u: u.training,
        "rating": lambda u: u.rating,
    }
    if arm == "infantry":
        families["drill"] = lambda u: u.drill
    if arm == "artillery":
        families["shot"] = lambda u: u.shot
    out = {}
    for family, getter in families.items():
        levels = np.array([getter(u) for u in units])
        total = len(set(levels.tolist()))
        both = [len(set(levels[tr].tolist()) & set(levels[te].tolist())) for tr, te in folds]
        out[family] = (both[0], min(both), total)
    return out


def rich_design(units: Sequence[Unit], arm: str) -> Design:
    """Every column any variant can use. Coverage is checked on these, so every
    variant (a subset of them) inherits the guarantee."""
    return build_design(units, arm, linear=frozenset(CATEGORICAL) | {"rank_depth"},
                        extras=frozenset({"pike_square", "firearm", "damage", "proj_reload"}), const_inside=True)


def make_slice(arm: str, side: str, units: list[Unit], n_seeds: int,
               extra_pinned: Callable[[np.ndarray], set[int]] | None = None) -> Slice:
    """`extra_pinned(groups)` returns further group ids to pin to train."""
    rich = rich_design(units, arm)
    groups = group_ids(rich.X, [u.n for u in units])
    strata = strata_for(units, groups)
    balance = np.array([u.faction for u in units])
    plan = search_splits(rich.X, rich.names, strata, balance, groups, n_seeds,
                         extra_pinned(groups) if extra_pinned else None)
    sl = Slice(arm, side, units, plan, groups)
    sl.coverage = coverage_report(units, plan.folds, arm)
    return sl


def slice_units(units: Sequence[Unit], arm: str, side: str, exclude: frozenset[str] = frozenset()) -> list[Unit]:
    return [u for u in units if u.arm == arm and (side == "merged" or u.side == side) and u.faction not in exclude]


def side_spec(spec: Spec) -> Spec:
    """A merged-slice structure for a side slice: side is constant there."""
    return replace(spec, linear=spec.linear - {"side"}, mult=spec.mult - {"side"})


# The previous run's final structures (size = models, p = 1, linear stats) and
# their merged-slice CV MAE — the generalised fitter must reproduce these.
PREVIOUS_FINAL = {
    "infantry": (Spec(mult=frozenset({"rating", "side"}), const=True), 38.4983),
    "cavalry": (Spec(mult=frozenset({"rank_depth", "rating"})), 60.5637),
    "artillery": (Spec(linear=frozenset({"rating"}), const=True), 74.5768),
}


# --- Size power profile -------------------------------------------------------

@dataclass
class Profile:
    arm: str
    curves: dict[tuple[str, bool], list[tuple[float, float, float]]]   # (size, const) -> [(p, mae, se)]
    best_size: str
    best_p: float
    best_const: bool
    best_mae: float


def profile_p(spec: Spec, sl: Slice, kinds: Sequence[str], consts: Sequence[bool],
              grid: Sequence[float] = P_GRID) -> Profile:
    design = design_for(spec, sl.units, sl.arm)
    curves: dict[tuple[str, bool], list] = {}
    best = None
    for kind in kinds:
        for const in consts:
            curve = []
            for p in grid:
                variant = replace(spec, size=kind, const=const, p=p)
                run = cv_spec(variant, sl.units, sl.plan.folds, sl.arm, full_fit=False, design=design,
                              data=slice_data(sl.units, kind, p))
                curve.append((p, run.mean("mae"), run.se("mae")))
                if best is None or run.mean("mae") < best[0]:
                    best = (run.mean("mae"), kind, p, const)
            curves[(kind, const)] = curve
    return Profile(sl.arm, curves, best[1], best[2], best[3], best[0])


# --- Structure search ---------------------------------------------------------

@dataclass
class SearchResult:
    arm: str
    runs: list[CVRun]                      # every structure, merged slice
    best: CVRun
    headline: CVRun                        # simplest within 1 SE of best
    placement: dict[str, dict[str, float]]  # var -> placement -> best MAE


def enumerate_specs(arm: str, side: str, kind: str, p: float) -> list[Spec]:
    candidates = [v for v in CANDIDATES[arm] if side == "merged" or v != "side"]
    specs = []
    for placement in itertools.product(("out", "linear", "mult"), repeat=len(candidates)):
        linear = frozenset(v for v, w in zip(candidates, placement) if w == "linear")
        mult = frozenset(v for v, w in zip(candidates, placement) if w == "mult")
        for const in (False, True):
            specs.append(Spec(linear=linear, mult=mult, const=const, size=kind, p=p))
    return specs


def structure_search(sl: Slice, kind: str, p: float) -> SearchResult:
    data = slice_data(sl.units, kind, p)
    designs: dict[frozenset, Design] = {}
    runs = []
    for spec in enumerate_specs(sl.arm, sl.side, kind, p):
        design = designs.setdefault(spec.linear, design_for(spec, sl.units, sl.arm))
        runs.append(cv_spec(spec, sl.units, sl.plan.folds, sl.arm, full_fit=False, design=design, data=data))
    runs.sort(key=lambda r: (r.mean("mae"), r.params))
    best = runs[0]
    threshold = best.mean("mae") + best.se("mae")
    headline = min((r for r in runs if r.mean("mae") <= threshold), key=lambda r: (r.params, r.mean("mae")))
    placement: dict[str, dict[str, float]] = {}
    for var in CANDIDATES[sl.arm]:
        placement[var] = {}
        for where in ("out", "linear", "mult"):
            pool = [r for r in runs if (var in r.spec.linear) == (where == "linear")
                    and (var in r.spec.mult) == (where == "mult")]
            placement[var][where] = min(r.mean("mae") for r in pool) if pool else float("nan")
    return SearchResult(sl.arm, runs, best, headline, placement)


# --- Parallel workers ---------------------------------------------------------
#
# The nested power searches run one independent descent per outer fold plus one
# on all rows; those jobs go to a process pool. Each job is a pure function of
# its arguments, so results are identical to a serial run. Workers are spawned
# fresh (Windows), so the tunable module settings are copied into them, and a
# worker never opens a pool of its own.

WORKERS = max(1, min(6, (os.cpu_count() or 1) // 2))    # --workers; 1 = serial
SHARED_SETTINGS = ("P_GRID", "POWER_GRID", "MAX_PASSES", "FINE_PASSES", "MAX_ITER", "TOLERANCE", "ARTILLERY_CAL")
_POOL: ProcessPoolExecutor | None = None


def _init_worker(settings: dict) -> None:
    globals().update(settings, WORKERS=1)


def _call(job: tuple) -> object:
    fn, args = job
    return fn(*args)


def parallel_map(fn: Callable, jobs: Sequence[tuple]) -> list:
    """[fn(*job) for job in jobs], on the worker pool when WORKERS > 1."""
    global _POOL
    if WORKERS <= 1 or len(jobs) <= 1:
        return [fn(*job) for job in jobs]
    if _POOL is None:
        _POOL = ProcessPoolExecutor(WORKERS, initializer=_init_worker,
                                    initargs=({k: globals()[k] for k in SHARED_SETTINGS},))
    return list(_POOL.map(_call, [(fn, tuple(job)) for job in jobs]))


# --- Stat powers (nested coordinate descent) ----------------------------------

def descend_powers(spec: Spec, units: Sequence[Unit], arm: str, rows: np.ndarray) -> tuple[dict[str, float], float, int]:
    """Coordinate descent on the training SSE (per-size space, the model's own
    objective) over one power per numeric stat and the size power p.

    Each exponent (the design's power keys: additive stats, shooting-product
    factors, the calibre column) is tried on POWER_GRID with the others held —
    the gun fire-rate exponent also on 0, meaning "the gun's reload time doesn't
    matter" — then p on a 0.05 grid within ±P_WINDOW of the current p; up to
    MAX_PASSES passes, stopping when a full pass changes nothing.
    Returns (powers, p, passes used)."""
    stats = design_for(spec, units, arm).power_keys
    powers = {s: spec.power_of(s) for s in stats}
    p = spec.p
    designs: dict[tuple, Design] = {}
    datas: dict[float, SliceData] = {}

    def sse(trial: dict[str, float], p_trial: float) -> float:
        key = tuple(sorted(trial.items()))
        design = designs.get(key)
        if design is None:
            design = designs[key] = build_design(units, arm, linear=spec.linear, extras=spec.extras, powers=trial,
                                                 shape=dict(spec.shape))
        d = datas.get(p_trial)
        if d is None:
            d = datas[p_trial] = slice_data(units, spec.size, p_trial)
        return fit_on(replace(spec, p=p_trial), design, d, rows).sse

    current = sse(powers, p)
    for passes in range(1, MAX_PASSES + 1):
        changed = False
        for s in stats:
            for a in ((0.0,) + POWER_GRID if s == "shoot:rate" else POWER_GRID):
                if a == powers[s]:
                    continue
                trial = {**powers, s: a}
                value = sse(trial, p)
                if value < current * (1 - 1e-9):
                    powers, current, changed = trial, value, True
        for step in range(-int(round(P_WINDOW / 0.05)), int(round(P_WINDOW / 0.05)) + 1):
            p_trial = round(p + 0.05 * step, 2)
            if p_trial <= 0 or p_trial == p:
                continue
            value = sse(powers, p_trial)
            if value < current * (1 - 1e-9):
                p, current, changed = p_trial, value, True
        if not changed:
            break
    return powers, p, passes


@dataclass
class PowerResult:
    base: CVRun                       # final structure, linear stats
    nested: CVRun                     # coarse powers + p fitted inside each training fold
    fold_powers: list[tuple[dict[str, float], float]]
    full_powers: dict[str, float]
    full_p: float
    kept: bool                        # coarse powers beat linear by > 1 SE
    fine: "FineResult | None" = None


@dataclass
class FineResult:
    nested: CVRun                     # fine powers + p, refined inside each training fold
    fold_powers: list[tuple[dict[str, float], float]]
    full_powers: dict[str, float]
    full_p: float
    profiles: list[dict]              # local CV curves per coordinate
    choice: str                       # "linear" | "coarse" | "fine"


class PowerObjective:
    """Training SSE (per-size space, the model's own objective) for a set of
    stat powers and a size power, with designs and size data cached."""

    def __init__(self, spec: Spec, units: Sequence[Unit], arm: str, rows: np.ndarray):
        self.spec, self.units, self.arm, self.rows = spec, units, arm, rows
        self.designs: dict[tuple, Design] = {}
        self.datas: dict[float, SliceData] = {}
        self.values: dict[tuple, float] = {}

    def __call__(self, powers: dict[str, float], p: float) -> float:
        key = (tuple(sorted((s, round(a, 4)) for s, a in powers.items())), round(p, 4))
        if key in self.values:
            return self.values[key]
        design = self.designs.get(key[0])
        if design is None:
            design = self.designs[key[0]] = build_design(self.units, self.arm, linear=self.spec.linear,
                                                         extras=self.spec.extras, powers=dict(key[0]),
                                                         shape=dict(self.spec.shape))
        d = self.datas.get(key[1])
        if d is None:
            d = self.datas[key[1]] = slice_data(self.units, self.spec.size, key[1])
        value = fit_on(replace(self.spec, p=key[1]), design, d, self.rows).sse
        self.values[key] = value
        return value


def power_floor(key: str) -> float:
    """Smallest exponent tried. The gun fire-rate exponent may reach 0 (its reload
    time then has no effect); other exponents stay positive — a shooting-product
    factor at 0 would turn a zero stat into a 1."""
    return 0.0 if key == "shoot:rate" else MIN_POWER


def line_search(f: Callable[[float], float], center: float, step: float, half: int,
                floor: float) -> tuple[float, float]:
    """Best value of f on center ± half·step (≥ floor), re-centring on the best
    point while it sits on a window edge, up to MAX_RECENTRE times."""
    best = (f(center), center)
    for _ in range(MAX_RECENTRE + 1):
        grid = [round(center + step * k, 4) for k in range(-half, half + 1)]
        grid = [g for g in grid if g >= floor - 1e-12]
        value, point = min((f(g), g) for g in grid)
        if value < best[0]:
            best = (value, point)
        on_edge = point == grid[-1] or (point == grid[0] and grid[0] > floor + 1e-12)
        if not on_edge:
            break
        center = point
    return best[1], best[0]


def refine_powers(spec: Spec, units: Sequence[Unit], arm: str, rows: np.ndarray,
                  powers: dict[str, float], p: float) -> tuple[dict[str, float], float]:
    """Fine coordinate descent from a coarse solution: each stat on a ±0.5 window
    in steps of 0.05, then p on ±0.15 in steps of 0.01, windows re-centred at
    edges; up to FINE_PASSES passes until nothing changes."""
    objective = PowerObjective(spec, units, arm, rows)
    stats = design_for(spec, units, arm).power_keys
    powers = {s: powers.get(s, 1.0) for s in stats}
    current = objective(powers, p)
    for _ in range(FINE_PASSES):
        changed = False
        for s in stats:
            a, value = line_search(lambda v: objective({**powers, s: v}, p), powers[s],
                                   FINE_STAT_STEP, FINE_STAT_HALF, power_floor(s))
            if value < current * (1 - 1e-9):
                powers, current, changed = {**powers, s: a}, value, True
        q, value = line_search(lambda v: objective(powers, v), p, FINE_P_STEP, FINE_P_HALF, MIN_POWER)
        if value < current * (1 - 1e-9):
            p, current, changed = q, value, True
        if not changed:
            break
    return powers, p


def local_profiles(spec: Spec, sl: Slice, powers: dict[str, float], p: float) -> list[dict]:
    """Exploratory CV curves: each coordinate varied over its fine window around
    the full-data fine solution (the others held there), plus its linear value
    (power 1 / p = 1). Holding the others at full-data values makes the curves
    slightly optimistic, so they show shape and identifiability, not accuracy."""
    out = []
    coordinates = [(s, FINE_STAT_STEP, FINE_STAT_HALF) for s in powers] + [("size power p", FINE_P_STEP, FINE_P_HALF)]
    for name, step, half in coordinates:
        center = p if name == "size power p" else powers[name]
        floor = MIN_POWER if name == "size power p" else power_floor(name)
        grid = sorted({round(center + step * k, 4) for k in range(-half, half + 1) if center + step * k >= floor - 1e-12}
                      | {1.0})
        curve = []
        for v in grid:
            trial_powers = powers if name == "size power p" else {**powers, name: v}
            trial = with_powers(spec, trial_powers, v if name == "size power p" else p)
            run = cv_spec(trial, sl.units, sl.plan.folds, sl.arm, full_fit=False)
            curve.append((v, run.mean("mae"), run.se("mae")))
        best_v, best_mae, best_se = min(curve, key=lambda t: (t[1], t[0]))
        window = [t for t in curve if abs(t[0] - center) <= step * half + 1e-9]
        within = [v for v, mae, _ in window if mae <= best_mae + best_se]
        out.append({
            "name": name, "center": center, "best": best_v, "best_mae": best_mae, "se": best_se,
            "lo": min(within), "hi": max(within),
            "at_center": next(mae for v, mae, _ in curve if v == round(center, 4)),
            "at_linear": next(mae for v, mae, _ in curve if v == 1.0),
            "edge": min(within) <= window[0][0] + 1e-9 or max(within) >= window[-1][0] - 1e-9,
        })
    return out


def nested_fine(spec: Spec, sl: Slice, coarse: PowerResult) -> FineResult:
    """Fine refinement nested inside each training fold, starting from that
    fold's coarse powers; then a full-data refinement and local CV curves.
    The model choice: powers are kept only if the better of coarse / fine beats
    linear stats by more than one SE, and then whichever of the two is lower."""
    units, arm = sl.units, sl.arm
    cost = np.array([u.cost for u in units], float)
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics, fold_powers = [], []
    everything = np.arange(len(units))
    refined = parallel_map(refine_powers, [(spec, units, arm, train, *coarse.fold_powers[k])
                                           for k, (train, _) in enumerate(sl.plan.folds)]
                           + [(spec, units, arm, everything, coarse.full_powers, coarse.full_p)])
    for k, (train, test) in enumerate(sl.plan.folds):
        powers, p = refined[k]
        fold_powers.append((powers, p))
        fitted = with_powers(spec, powers, p)
        design, d = design_for(fitted, units, arm), data_for(fitted, units)
        model = fit_on(fitted, design, d, train)
        pred = predict_total(model, design, d, test)
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(cost[test], pred, d.size[test]))
    nested = CVRun("fine powers + p, refined inside each training fold", fold_metrics, oof, oof_fold, spec)
    full_powers, full_p = refined[-1]
    profiles = local_profiles(spec, sl, full_powers, full_p)
    base = coarse.base
    best_power = min(coarse.nested.mean("mae"), nested.mean("mae"))
    if best_power >= base.mean("mae") - base.se("mae"):
        choice = "linear"
    else:
        choice = "fine" if nested.mean("mae") <= coarse.nested.mean("mae") else "coarse"
    return FineResult(nested, fold_powers, full_powers, full_p, profiles, choice)


def nested_powers(spec: Spec, sl: Slice, base: CVRun) -> PowerResult:
    units, arm = sl.units, sl.arm
    cost = np.array([u.cost for u in units], float)
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics, fold_powers = [], []
    descents = parallel_map(descend_powers, [(spec, units, arm, train) for train, _ in sl.plan.folds]
                            + [(spec, units, arm, np.arange(len(units)))])
    for k, (train, test) in enumerate(sl.plan.folds):
        powers, p, _ = descents[k]
        fold_powers.append((powers, p))
        fitted = with_powers(spec, powers, p)
        design, d = design_for(fitted, units, arm), data_for(fitted, units)
        model = fit_on(fitted, design, d, train)
        pred = predict_total(model, design, d, test)
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(cost[test], pred, d.size[test]))
    nested = CVRun("stat powers + p, fitted inside each training fold", fold_metrics, oof, oof_fold, spec)
    full_powers, full_p, _ = descents[-1]
    kept = nested.mean("mae") < base.mean("mae") - base.se("mae")
    return PowerResult(base, nested, fold_powers, full_powers, full_p, kept)


# --- Shape variants: firearm/calibre representation × shooting cluster --------

@dataclass
class VariantResult:
    key: str                 # e.g. "F1·SH2"
    label: str
    spec: Spec               # linear exponents; powers live in `power`
    power: PowerResult       # nested coarse stat powers for this shape
    params: int              # fitted parameters incl. exponents and p
    unseen: int              # test rows hitting a level absent from their training fold
    adopted: bool = False
    eligible: bool = True    # product variants: beat their own summation by > 1 SE

    def mean(self) -> float:
        return self.power.nested.mean("mae")

    def se(self) -> float:
        return self.power.nested.se("mae")


# --artillery-cal: restrict the artillery calibre representations screened.
# "auto" screens them all; otherwise F0 (the baseline) plus the named one.
ARTILLERY_CAL = "auto"
ARTILLERY_CAL_KEYS = {"calibre": "F1", "projectile": "F2", "spline": "F3"}


def shape_variants(arm: str) -> list[tuple[str, str, tuple[tuple[str, str], ...]]]:
    """(key, label, shape) for every variant of one arm. F = firearm / calibre
    representation, SH = shooting: 0 additive, 1 product, 2 product per type."""
    if arm == "artillery":
        # F3: the smooth calibre function from analysis/calibre_function.py — a
        # natural cubic spline in log range (df 5) with the shot type, which matched
        # the cannon-type one-hot (49.68 vs 49.43 nested MAE) with 9 fewer parameters.
        reps = [("F0", "range + damage + gun reload", ()),
                ("F1", "calibre", (("cal", "calibre"),)),
                ("F2", "cannon type", (("cal", "projectile"),)),
                ("F3", "range spline (df 5)", (("cal", "spline_r"), ("cal_df", "5")))]
        if ARTILLERY_CAL != "auto":
            reps = [r for r in reps if r[0] in ("F0", ARTILLERY_CAL_KEYS[ARTILLERY_CAL])]
        per_type = {"F1": "calibre inside the shooting product", "F2": "shooting product per cannon type"}
    else:
        reps = [("F0", "range", ()), ("F1", "firearm one-hot", (("fire", "firearm"),))]
        per_type = {"F1": "shooting product per firearm"}
    out = []
    for fkey, flabel, fshape in reps:
        shoots = [("SH0", "additive shooting", ()), ("SH1", "shooting product", (("shoot", "product"),))]
        if fkey in per_type:
            shoots.append(("SH2", per_type[fkey], (("shoot", "product_type"),)))
        for skey, slabel, sshape in shoots:
            out.append((f"{fkey}·{skey}", f"{flabel}; {slabel}", tuple(sorted(fshape + sshape))))
    return out


def screen_variants(pre: Spec, sl: Slice, log_fn: Callable[[str], None]) -> list[VariantResult]:
    """Nested coarse CV for every shape variant of one arm, then the adoption
    rule, with summation as the default (per the user — a product is probably
    not how the game implements shooting):

    1. A shooting-product variant (SH1/SH2) is eligible only if it beats the
       summation variant with the same firearm/calibre representation (its
       F·SH0) by more than one SE. Summation variants are always eligible.
    2. F0·SH0 is the current model. An eligible variant is adopted only if it
       beats F0·SH0 by more than one SE.
    3. Among those within one SE of the best, summation is preferred, then the
       fewest parameters."""
    out = []
    for key, label, shape in shape_variants(sl.arm):
        spec = replace(pre, shape=shape)
        base = cv_spec(spec, sl.units, sl.plan.folds, sl.arm, full_fit=False, label=f"{key}, linear exponents")
        power = nested_powers(spec, sl, base)
        design = design_for(spec, sl.units, sl.arm)
        unseen = 0
        for train, test in sl.plan.folds:
            bad = unidentified(design.X, train, test)
            if bad.any():
                unseen += int(np.any(design.X[test][:, bad] != design.X[train][0, bad], axis=1).sum())
        params = base.params + len(design.power_keys) + 1
        out.append(VariantResult(key, label, spec, power, params, unseen))
        log_fn(f"variant   {sl.arm:9} {key} {label:45} linear {base.mean('mae'):6.2f}  nested {power.nested.mean('mae'):6.2f}")
    adopt_variant(out)
    return out


def adopt_variant(out: list[VariantResult]) -> VariantResult:
    """Apply the adoption rule (see screen_variants) and mark the pick. out[0]
    is F0·SH0, the current model."""
    current = out[0]
    summation = {v.key.split("·")[0]: v for v in out if v.key.endswith("SH0")}
    for v in out:
        if v.key.endswith("SH0"):
            v.eligible = True
        else:
            ref = summation[v.key.split("·")[0]]
            v.eligible = v.mean() < ref.mean() - ref.se()
    beats = [v for v in out[1:] if v.eligible and v.mean() < current.mean() - current.se()]
    if beats:
        best = min(beats, key=lambda v: v.mean())
        pool = [v for v in beats if v.mean() <= best.mean() + best.se()]
        pick = min(pool, key=lambda v: (not v.key.endswith("SH0"), v.params, v.mean()))
    else:
        pick = current
    pick.adopted = True
    return pick


def variant_details(variants: list[VariantResult], sl: Slice) -> dict:
    """Full-data fits of the best F1 (and, for artillery, F2) variant, for the
    report: per-firearm coefficients, or the calibre curve and cannon-type
    coefficients."""
    def full_fit(v: VariantResult) -> tuple[Spec, Design, PriceModel]:
        spec = with_powers(v.spec, v.power.full_powers, v.power.full_p)
        design, d = design_for(spec, sl.units, sl.arm), data_for(spec, sl.units)
        return spec, design, fit_on(spec, design, d, np.arange(len(sl.units)))

    def best_of(prefix: str) -> VariantResult | None:
        # A representation may be absent (e.g. --artillery-cal restricts the screen).
        pool = [v for v in variants if v.key.startswith(prefix)]
        return min(pool, key=lambda v: v.mean()) if pool else None

    out: dict = {}
    f1 = best_of("F1")
    if sl.arm == "artillery":
        if f1:
            spec, design, model = full_fit(f1)
            coef = dict(zip(design.names, model.beta))
            a = spec.power_of("cal:damage")
            projectiles: dict[str, tuple[str, float]] = {}
            for u in sl.units:
                projectiles.setdefault(u.projectile, (u.shot, u.values["proj_damage"]))
            out["calibre"] = {
                "variant": f1.key, "beta": coef.get("calibre", float("nan")), "a": a,
                "rows": [(proj, shot, dmg, coef.get("calibre", float("nan")) * (dmg / POWER_SCALE) ** a)
                         for proj, (shot, dmg) in sorted(projectiles.items(), key=lambda t: (t[1][0], t[1][1]))],
            }
        f2 = best_of("F2")
        if f2:
            spec2, design2, model2 = full_fit(f2)
            out["cannon"] = {"variant": f2.key, "reference": design2.references.get("projectile"),
                             "rows": [(n, c) for n, c in zip(design2.names, model2.beta)
                                      if n.startswith("projectile=") or n.startswith("shoot×projectile=")]}
    elif f1:
        spec, design, model = full_fit(f1)
        coef = dict(zip(design.names, model.beta))
        out["firearm"] = {"variant": f1.key, "reference": design.references.get("firearm"),
                          "rows": [(n, c) for n, c in coef.items()
                                   if n.startswith("firearm=") or n.startswith("shoot×firearm=") or n == "shoot"]}
    return out


# --- Faction modifier shared across arms --------------------------------------

def shared_modifier(blocks: Sequence[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> dict[str, float]:
    """One multiplier per faction across every arm, on the scaled part of the
    price: m_f = Σ (cost − c)·s / Σ s² over (factions, cost − c, s) blocks in
    total price. Total-price least squares weights units by their price, so a
    near-zero prediction can't dominate."""
    num: dict[str, float] = defaultdict(float)
    den: dict[str, float] = defaultdict(float)
    for factions, target, scaled in blocks:
        for f, t, s in zip(factions.tolist(), target.tolist(), scaled.tolist()):
            num[f] += t * s
            den[f] += s * s
    return {f: num[f] / den[f] for f in den if den[f] > 0}


def shared_faction_runs(slices: dict[tuple[str, str], Slice], side: str,
                        final: dict[str, Spec]) -> tuple[dict[str, CVRun], dict[str, float]]:
    """Final model × one faction modifier shared by all three arms. Fold k of
    each arm holds disjoint units, so pooling the training rows of fold k across
    arms leaks nothing into any arm's fold-k test rows."""
    per_arm = {}
    for arm in ARMS:
        sl = slices[(arm, side)]
        spec = final[arm] if side == "merged" else side_spec(final[arm])
        design, d = design_for(spec, sl.units, arm), data_for(spec, sl.units)

        def parts(model, rows):
            s, c = model.parts(design.X[rows], d.inv[rows], d.g[rows], sub(d.fvals, rows), d.factions[rows])
            return d.size[rows] * s, d.size[rows] * c       # total price: scaled part, flat c

        fits = []
        for train, test in sl.plan.folds:
            model = fit_on(spec, design, d, train)
            fits.append((train, test, *parts(model, train), *parts(model, test)))
        full = fit_on(spec, design, d, np.arange(len(sl.units)))
        per_arm[arm] = (d, fits, parts(full, np.arange(len(sl.units))))
    oof = {arm: np.full(len(slices[(arm, side)].units), np.nan) for arm in ARMS}
    oof_fold = {arm: np.zeros(len(slices[(arm, side)].units), int) for arm in ARMS}
    fold_metrics: dict[str, list] = {arm: [] for arm in ARMS}
    fallbacks = Counter()
    for k in range(N_SPLITS):
        blocks = []
        for arm in ARMS:
            d, fits, _ = per_arm[arm]
            train, _, s_tr, c_tr, _, _ = fits[k]
            blocks.append((d.factions[train], d.cost[train] - c_tr, s_tr))
        m = shared_modifier(blocks)
        for arm in ARMS:
            d, fits, _ = per_arm[arm]
            _, test, _, _, s_te, c_te = fits[k]
            factor = np.array([m.get(f, 1.0) for f in d.factions[test]])
            pred = s_te * factor + c_te
            fallbacks[arm] += int(sum(f not in m for f in d.factions[test]))
            oof[arm][test], oof_fold[arm][test] = pred, k + 1
            fold_metrics[arm].append(metrics(d.cost[test], pred, d.size[test]))
    full_m = shared_modifier([(per_arm[arm][0].factions, per_arm[arm][0].cost - per_arm[arm][2][1], per_arm[arm][2][0])
                              for arm in ARMS])
    runs = {arm: CVRun("final × shared faction modifier", fold_metrics[arm], oof[arm], oof_fold[arm],
                       fallbacks=fallbacks[arm]) for arm in ARMS}
    return runs, full_m


# --- Faction × unit-class modifier (from the blind study) ---------------------
#
# NTW3 prices look hand-set per corps per unit class (blind study, branch
# blind-pricing-study; tested here by analysis/blind_ideas.py). Two forms:
#   RFC  residual: the final model × per-arm faction modifier × a faction × class
#        cell, shrunk towards 1 (i.e. towards the faction modifier);
#   JFC  joint: a faction × class multiplier inside the ALS fit around the fixed
#        divisor REF_RATING / rating, so stat coefficients are fitted net of it.
# The ridge strength κ is chosen by inner CV inside each outer training fold.

FCLASS_GRID = {"RFC": (0.0, 0.5, 1.0, 3.0, 10.0, 30.0), "JFC": (0.5, 1.0, 3.0, 10.0, 30.0)}
FCLASS_LABEL = {"RFC": "residual faction × class", "JFC": f"joint faction × class around {REF_RATING}/N"}
# Adopted by analysis/blind_ideas.py (see blind_ideas_report.md): (variant, loss).
FCLASS_FORM: tuple[str, str] | None = ("JFC", "ls")


def residual_fclass_spec(spec: Spec, kappa: float) -> Spec:
    return replace(spec, faction=True, fclass="residual", kappa=kappa)


def joint_fclass_spec(spec: Spec, kappa: float) -> Spec:
    return replace(spec, mult=(spec.mult - {"rating"}) | {"fclass"}, fixed_rating=True, kappa=kappa)


FCLASS_MAKERS: dict[str, Callable[[Spec, float], Spec]] = {"RFC": residual_fclass_spec, "JFC": joint_fclass_spec}


def fold_run(label: str, specs: Sequence[Spec], full_spec: Spec, units: Sequence[Unit], folds: list[Fold],
             arm: str, design: Design) -> CVRun:
    """CV with one spec per outer fold (e.g. κ chosen per fold), plus a full-data fit."""
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics, fallbacks = [], 0
    for k, ((train, test), spec) in enumerate(zip(folds, specs)):
        d = data_for(spec, units)
        model = fit_on(spec, design, d, train)
        pred = predict_total(model, design, d, test)
        fallbacks += model.unseen(sub(d.fvals, test), d.factions[test])
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(d.cost[test], pred, d.size[test]))
    d = data_for(full_spec, units)
    full = fit_on(full_spec, design, d, np.arange(len(units)))
    return CVRun(label, fold_metrics, oof, oof_fold, full_spec, full, design.names, design.references,
                 design.aliases, full.n_params(design.X), fallbacks)


def inner_kappa(make: Callable[[Spec, float], Spec], base: Spec, grid: Sequence[float], units: Sequence[Unit],
                folds: list[Fold], arm: str, design: Design, k: int) -> float:
    """κ with the lowest pooled MAE over inner folds = the other outer folds' test
    sets, each fitted on the rest of outer fold k's training rows."""
    train = folds[k][0]
    best = (np.inf, grid[0])
    for kappa in grid:
        spec = make(base, kappa)
        d = data_for(spec, units)
        errors = []
        for j, (_, inner_test) in enumerate(folds):
            if j == k:
                continue
            model = fit_on(spec, design, d, np.setdiff1d(train, inner_test))
            errors.append(np.abs(predict_total(model, design, d, inner_test) - d.cost[inner_test]))
        score = float(np.concatenate(errors).mean())
        if score < best[0] - 1e-12:
            best = (score, kappa)
    return best[1]


@dataclass
class FclassResult:
    run: CVRun                                   # nested: κ chosen per outer fold
    kappas: list[float]                          # κ per outer fold
    grid: list[tuple[float, CVRun]]              # non-nested CV per κ (full fit uses the best)
    full_kappa: float


def fclass_cv(variant: str, base: Spec, units: Sequence[Unit], folds: list[Fold], arm: str,
              design: Design | None = None, kappas: Sequence[float] | None = None) -> FclassResult:
    """Faction × class variant with nested κ. `kappas` reuses per-fold κ (e.g. LAD
    on the least-squares choice) instead of re-selecting them."""
    make, grid = FCLASS_MAKERS[variant], FCLASS_GRID[variant]
    design = design or design_for(base, units, arm)
    grid_runs = []
    for kappa in grid:
        spec = make(base, kappa)
        grid_runs.append((kappa, cv_spec(spec, units, folds, arm, label=f"{variant} κ={kappa:g}", design=design,
                                         data=data_for(spec, units), full_fit=False)))
    full_kappa = min(grid_runs, key=lambda t: t[1].mean("mae"))[0]
    chosen = list(kappas) if kappas is not None else [
        inner_kappa(make, base, grid, units, folds, arm, design, k) for k in range(len(folds))]
    label = FCLASS_LABEL[variant] + (", LAD" if base.loss == "lad" else "")
    run = fold_run(label, [make(base, kappa) for kappa in chosen], make(base, full_kappa), units, folds, arm, design)
    return FclassResult(run, chosen, grid_runs, full_kappa)


def fclass_multiplier(model: PriceModel, u: Unit) -> float:
    """A unit's army multiplier relative to the plain REF_RATING / rating rule:
    1 = priced as the rating alone predicts."""
    cell = f"{u.faction}|{u.unit_class}"
    if model.spec.fclass == "residual":
        m = model.faction_m.get(u.faction, 1.0) * model.fclass_m.get(cell, 1.0)
        if "rating" in model.spec.mult:
            m *= model.levels["rating"].get(u.rating, 1.0) / (REF_RATING / u.rating)
        return m
    return model.levels["fclass"].get(cell, 1.0)


# --- Staff generals ------------------------------------------------------------

@dataclass
class StaffRun:
    label: str
    fold_metrics: list[dict[str, float]]
    oof: np.ndarray
    fallbacks: int = 0

    def mean(self, metric: str) -> float:
        return float(np.mean([m[metric] for m in self.fold_metrics]))

    def sd(self, metric: str) -> float:
        return float(np.std([m[metric] for m in self.fold_metrics], ddof=1))

    def fold1(self, metric: str) -> float:
        return self.fold_metrics[0][metric]


def staff_rating_design(stars: np.ndarray, d: np.ndarray, form: str) -> np.ndarray:
    """cost − 1 as a no-intercept linear model; d = rating − 8.
    T1: rating shifts the price per star.  T2: rating scales both the per-star
    and the per-star² price (= (1 + δd)(b·s + q·s²) with free coefficients)."""
    if form == "T1":
        return np.column_stack([stars, d * stars, stars ** 2])
    return np.column_stack([stars, stars ** 2, d * stars, d * stars ** 2])


STAFF_RATING_NAMES = {
    "T1": ["b (per star)", "γ (per star per rating point)", "q (per star²)"],
    "T2": ["b (per star)", "q (per star²)", "γ (per star per rating point)", "κ (per star² per rating point)"],
    "T3": ["b (gold per star^q at rating 8)", "q (star power)"],
}


STAFF_POWER_GRID = np.round(np.arange(0.5, 3.0001, 0.005), 3)


def staff_power_fit(stars: np.ndarray, cost: np.ndarray, rating: np.ndarray) -> tuple[float, float]:
    """T3 (from the blind study): a starred general costs b·stars^q·(REF_RATING / rating),
    one without stars 1 gold. q on a 0.005 grid, b by least squares given q; fitted
    on starred generals only."""
    starred = stars > 0
    s, c, divisor = stars[starred], cost[starred], REF_RATING / rating[starred]
    best = (np.inf, 0.0, 1.0)
    for q in STAFF_POWER_GRID:
        x = s ** q * divisor
        b = float((c * x).sum() / (x * x).sum())
        sse = float(((c - b * x) ** 2).sum())
        if sse < best[0]:
            best = (sse, b, float(q))
    return best[1], best[2]


def staff_power_price(stars: np.ndarray, rating: np.ndarray, b: float, q: float) -> np.ndarray:
    return np.where(stars > 0, b * stars ** q * REF_RATING / rating, 1.0)


def staff_faction_m(cost: np.ndarray, p: np.ndarray, factions: np.ndarray) -> dict[str, float]:
    """Faction modifier on the star part: cost − 1 ≈ m_f × (p − 1)."""
    out = {}
    for faction in set(factions.tolist()):
        mask = factions == faction
        denominator = float(((p[mask] - 1) ** 2).sum())
        if denominator > 0:
            out[faction] = float(((cost[mask] - 1) * (p[mask] - 1)).sum()) / denominator
    return out


def staff_cv(gens: Sequence[Staff], folds: list[Fold]) -> dict[str, StaffRun]:
    stars = np.array([g.stars for g in gens], float)
    cost = np.array([g.cost for g in gens], float)
    factions = np.array([g.faction for g in gens])
    d = np.array([g.rating - REF_RATING for g in gens], float)
    starred = stars > 0

    def run(label: str, predict: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, int]]) -> StaffRun:
        oof = np.full(len(gens), np.nan)
        fold_metrics, fallbacks = [], 0
        for train, test in folds:
            pred, fb = predict(train, test)
            oof[test] = pred
            fallbacks += fb
            # MAPE over starred generals only: a 1-gold miss on a 1-gold general reads as 100%.
            fold_metrics.append(metrics(cost[test], pred, mape_mask=starred[test]))
        return StaffRun(label, fold_metrics, oof, fallbacks)

    def s1(train, test):
        model = LinearRegression().fit(stars[train, None], cost[train])
        return model.predict(stars[test, None]), 0

    def s2_quadratic(train, test):
        design = lambda index: np.column_stack([stars[index], stars[index] ** 2])
        coef, *_ = np.linalg.lstsq(design(train), cost[train] - 1, rcond=None)
        return 1 + design(test) @ coef, 0

    def s3_quadratic(train, test):
        levels = sorted(set(factions[train].tolist()))
        def design(index):
            return np.column_stack([stars[index] * (factions[index] == f) for f in levels] + [stars[index] ** 2])
        coef, *_ = np.linalg.lstsq(design(train), cost[train] - 1, rcond=None)
        return 1 + design(test) @ coef, 0

    def rating_model(form: str, with_faction: bool):
        def predict(train, test):
            X = staff_rating_design(stars, d, form)
            coef, *_ = np.linalg.lstsq(X[train], cost[train] - 1, rcond=None)
            p = 1 + X @ coef
            if not with_faction:
                return p[test], 0
            m = staff_faction_m(cost[train], p[train], factions[train])
            fb = int(sum(1 for i in test if factions[i] not in m and stars[i] > 0))
            return 1 + np.array([m.get(factions[i], 1.0) for i in test]) * (p[test] - 1), fb
        return predict

    rating = np.array([g.rating for g in gens], float)

    def power_rule(with_faction: bool):
        def predict(train, test):
            b, q = staff_power_fit(stars[train], cost[train], rating[train])
            p = staff_power_price(stars, rating, b, q)
            if not with_faction:
                return p[test], 0
            m = staff_faction_m(cost[train], p[train], factions[train])
            fb = int(sum(1 for i in test if factions[i] not in m and stars[i] > 0))
            return 1 + np.array([m.get(factions[i], 1.0) for i in test]) * (p[test] - 1), fb
        return predict

    return {
        "S1": run("S1: a + b·stars (free constant)", s1),
        "S2q": run("S2q: 1 + b·stars + q·stars² (no rating/faction)", s2_quadratic),
        "S3q": run("S3q: 1 + b_f·stars + q·stars² (faction, no rating)", s3_quadratic),
        "T1": run("T1: 1 + (b + γ·(r−8))·stars + q·stars²", rating_model("T1", False)),
        "T2": run("T2: 1 + (1 + δ·(r−8))·(b·stars + q·stars²), free", rating_model("T2", False)),
        "TF1": run("TF1: T1 + faction modifier", rating_model("T1", True)),
        "TF2": run("TF2: T2 + faction modifier", rating_model("T2", True)),
        "T3": run(f"T3: b·stars^q·({REF_RATING}/r), 1 without stars", power_rule(False)),
        "TF3": run("TF3: T3 + faction modifier", power_rule(True)),
    }


def staff_full(gens: Sequence[Staff], form: str) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    stars = np.array([g.stars for g in gens], float)
    cost = np.array([g.cost for g in gens], float)
    factions = np.array([g.faction for g in gens])
    if form == "T3":
        rating = np.array([g.rating for g in gens], float)
        b, q = staff_power_fit(stars, cost, rating)
        p = staff_power_price(stars, rating, b, q)
        return np.array([b, q]), p, staff_faction_m(cost, p, factions)
    d = np.array([g.rating - REF_RATING for g in gens], float)
    X = staff_rating_design(stars, d, form)
    coef, *_ = np.linalg.lstsq(X, cost - 1, rcond=None)
    p = 1 + X @ coef
    return coef, p, staff_faction_m(cost, p, factions)


@dataclass
class StaffSlice:
    side: str
    gens: list[Staff]
    plan: SplitPlan
    runs: dict[str, StaffRun]


def staff_coverage(gens: Sequence[Staff]) -> tuple[np.ndarray, list[str]]:
    factions = sorted({g.faction for g in gens})
    star_levels = sorted({g.stars for g in gens})
    C = np.column_stack(
        [[1.0 if g.faction == f else 0.0 for g in gens] for f in factions]
        + [[1.0 if g.stars == s else 0.0 for g in gens] for s in star_levels]
    )
    return C, [f"faction={f}" for f in factions] + [f"stars={s}" for s in star_levels]


def make_staff_slice(side: str, gens: list[Staff], n_seeds: int) -> StaffSlice:
    C, names = staff_coverage(gens)
    groups = group_ids(C, [0] * len(gens))
    strata = np.array([g.faction for g in gens])
    balance = np.array([str(g.stars) for g in gens])
    plan = search_splits(C, names, strata, balance, groups, n_seeds)
    return StaffSlice(side, gens, plan, staff_cv(gens, plan.folds))


# --- Data diagnostics ---------------------------------------------------------

LB_PER = {"funt": 0.9028, "okka": 2.828}   # Russian funt 409.5 g; Ottoman oka 1.2829 kg
SHELL_WORDS = ("yedinorog", "howitz", "haubit", "obus", "humbara", "qhādhif", "unicorn")


def eastern_calibre_rows(units: Sequence[Unit]) -> list[list[object]]:
    """Name calibre in its native unit vs the projectile the game fires.

    Flags a round shot whose pounder rating is more than 1.5× (or under 0.67×)
    the name's calibre converted to pounds, and a shell fired by a gun whose name
    gives a calibre but doesn't call it a howitzer or unicorn."""
    found: Counter = Counter()
    for u in units:
        if u.arm != "artillery":
            continue
        name = u.name
        m = (re.search(r"(\d+(?:\.\d+)?)-?\s*funt", name) or re.search(r"(\d+(?:\.\d+)?)\s*okka", name)
             or re.search(r"(\d+)\s*pewend", name) or re.search(r"iy[aā]r\s*(\d+)", name))
        if not m:
            continue
        unit = ("funt" if "funt" in name else "okka" if "okka" in name else "pewend" if "pewend" in name else "‘iyār")
        found[(unit, m.group(1), u.projectile, u.values["proj_damage"], u.weapon,
               any(w in name.lower() for w in SHELL_WORDS))] += 1
    rows = []
    for (unit, value, projectile, damage, weapon, named_shell), count in sorted(
            found.items(), key=lambda t: (t[0][0], float(t[0][1]))):
        lb = float(value) * LB_PER[unit] if unit in LB_PER else None
        flag = ""
        shot = re.match(r"cannon_(\d+)_pounder_shot", projectile)
        if shot and lb:
            ratio = int(shot.group(1)) / lb
            if ratio > 1.5 or ratio < 0.67:
                flag = f"⚠ fires a {shot.group(1)}-pdr shot (×{ratio:.1f} the name calibre)"
        if "shell" in projectile and not named_shell:
            flag = ("howitzer weapon; the name just doesn't say so" if "howitzer" in weapon
                    else "⚠ fires a shell, but neither name nor weapon is a howitzer/unicorn")
        rows.append([f"{value} {unit}", f"{lb:.1f}" if lb else "—", f"`{weapon}`", f"`{projectile}`",
                     f"{damage:g}", count, flag])
    return rows


def firearm_range_overlap(units: Sequence[Unit]) -> dict[str, float]:
    ranged = [u for u in units if u.values["range"] > 0]
    by_firearm: dict[str, set] = defaultdict(set)
    by_range: dict[float, set] = defaultdict(set)
    for u in ranged:
        by_firearm[u.firearm].add(u.values["range"])
        by_range[u.values["range"]].add(u.firearm)
    r = np.array([u.values["range"] for u in ranged])
    firearms = np.array([u.firearm for u in ranged])
    within = sum(float(((r[firearms == f] - r[firearms == f].mean()) ** 2).sum()) for f in set(firearms.tolist()))
    total = float(((r - r.mean()) ** 2).sum())
    return {
        "firearms": len(by_firearm), "ranges": len(by_range),
        "ranges_per_firearm_max": max(len(v) for v in by_firearm.values()),
        "firearms_per_range_max": max(len(v) for v in by_range.values()),
        "single_range_firearms": sum(len(v) == 1 for v in by_firearm.values()),
        "eta2": 1 - within / total if total else float("nan"),
    }


# --- Report helpers -----------------------------------------------------------

def f1(x: float) -> str:
    return f"{x:,.1f}"


def f2(x: float) -> str:
    return f"{x:,.2f}"


def f3(x: float) -> str:
    return f"{x:.3f}"


def pm(run, metric: str, fmt: Callable[[float], str]) -> str:
    return f"{fmt(run.mean(metric))} ± {fmt(run.sd(metric))}"


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def pct_resid(actual: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """(actual − predicted) / predicted × 100: positive = game price above formula."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return (actual - pred) / pred * 100


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Rank correlation (average ranks for ties), without importing scipy."""
    def ranks(values: Sequence[float]) -> np.ndarray:
        values = np.asarray(values, float)
        order = np.argsort(values, kind="mergesort")
        out = np.empty(len(values))
        out[order] = np.arange(len(values))
        for value in np.unique(values):
            tied = values == value
            out[tied] = out[tied].mean()
        return out
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def describe_factors(model: PriceModel) -> str:
    parts = []
    for var in sorted(model.spec.mult):
        if var in CATEGORICAL:
            parts.append(f"m_{var}: " + ", ".join(f"{k}: {v:.3f}" for k, v in sorted(model.levels[var].items(), key=lambda t: str(t[0]))))
        else:
            parts.append(f"m_{var} = 1 {model.delta[var]:+.4f}·({var} − {model.refs[var]:g})")
    return "; ".join(parts) or "—"


# --- Main ---------------------------------------------------------------------

@dataclass
class Results:
    units: list[Unit]
    staff: list[Staff]
    slices: dict[tuple[str, str], Slice]
    regression: dict[str, CVRun]
    profiles: dict[str, Profile]
    search: dict[str, SearchResult]
    reprofiles: dict[str, Profile]
    ablations: dict[str, list[tuple[str, str, CVRun, bool]]]   # arm -> (group, label, run, accepted)
    powers: dict[str, PowerResult]
    final: dict[str, Spec]
    packing: dict[str, dict]
    poland: dict[tuple[str, str], dict]
    transfer: dict[tuple[str, str], dict]
    staff_slices: dict[str, StaffSlice]
    staff_head: str
    staff_poland: dict[str, dict]
    tag_mismatches: list[Unit]
    ratings: dict[str, int]
    n_seeds: int
    shared_m: dict[str, dict[str, float]] = field(default_factory=dict)
    linear: bool = False
    variants: dict[str, list] = field(default_factory=dict)        # arm -> [VariantResult]
    variant_detail: dict[str, dict] = field(default_factory=dict)
    fclass: dict[tuple[str, str], "FclassResult"] = field(default_factory=dict)
    elapsed: float = 0.0


def log(message: str, started: float) -> None:
    print(f"[{time.time() - started:5.0f}s] {message}", flush=True)


def main() -> int:
    global OUT_DIR, ARTILLERY_CAL, WORKERS
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500, help="split seeds to search (default 500)")
    parser.add_argument("--linear", action="store_true",
                        help="fully linear run: size = models, p = 1, linear stats (no size or stat powers)")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default analysis/output)")
    parser.add_argument("--artillery-cal", choices=["auto", *ARTILLERY_CAL_KEYS], default="auto",
                        help="artillery calibre representations to screen: all (auto), or only F0 plus this one")
    parser.add_argument("--workers", type=int, default=WORKERS,
                        help=f"worker processes for the nested power searches (default {WORKERS}; 1 = serial)")
    args = parser.parse_args()
    if args.out is not None:
        OUT_DIR = args.out.resolve()
    ARTILLERY_CAL = args.artillery_cal
    WORKERS = args.workers
    started = time.time()

    for path in (DATA_CSV, CATALOG_CSV):
        if not path.exists():
            print(f"missing {path} — run tools/build_analysis_dataset.py first", file=sys.stderr)
            return 1
    ratings = load_ratings()
    units, staff, unparsed, unrated = load(ratings)
    if unparsed or unrated:
        print(f"unparseable speed tags {unparsed[:3]} / corps without rating {unrated}", file=sys.stderr)
        return 1
    tag_mismatches = [u for u in units if u.raw_tag != u.speed_code]
    log(f"loaded {len(units)} regular units, {len(staff)} staff generals", started)

    slices = {(arm, side): make_slice(arm, side, slice_units(units, arm, side), args.seeds)
              for arm in ARMS for side in SIDES}

    # 1. Regression check: last run's finals (models, p = 1, linear stats).
    regression = {}
    for arm in ARMS:
        spec, _ = PREVIOUS_FINAL[arm]
        regression[arm] = cv_spec(spec, slices[(arm, "merged")].units, slices[(arm, "merged")].plan.folds, arm,
                                  full_fit=False)
        log(f"regression {arm:9} MAE {regression[arm].mean('mae'):.4f} (previous {PREVIOUS_FINAL[arm][1]})", started)

    # 2. Size power profile on last run's final structure, with and without c.
    # In --linear mode the "profile" is the single point size = models, p = 1.
    kinds_for = (lambda arm: ("n",)) if args.linear else (lambda arm: SIZE_KINDS[arm])
    grid = (1.0,) if args.linear else P_GRID
    profiles = {}
    for arm in ARMS:
        spec, _ = PREVIOUS_FINAL[arm]
        profiles[arm] = profile_p(spec, slices[(arm, "merged")], kinds_for(arm), (False, True), grid)
        pr = profiles[arm]
        log(f"profile   {arm:9} best size={pr.best_size} p={pr.best_p} c={pr.best_const} MAE {pr.best_mae:.2f}", started)

    # 3. Structure re-search with each arm's size and p*, then re-profile p.
    search, reprofiles, headline = {}, {}, {}
    for arm in ARMS:
        pr = profiles[arm]
        search[arm] = structure_search(slices[(arm, "merged")], pr.best_size, pr.best_p)
        head = search[arm].headline.spec
        reprofiles[arm] = profile_p(head, slices[(arm, "merged")], (pr.best_size,), (head.const,), grid)
        headline[arm] = replace(head, p=reprofiles[arm].best_p)
        log(f"search    {arm:9} {len(search[arm].runs)} models; headline [{headline[arm].describe()}] "
            f"MAE {reprofiles[arm].best_mae:.2f}", started)

    # 3b. Linear-part ablations on the headline.
    ablations: dict[str, list] = {}
    pre_power: dict[str, Spec] = {}
    for arm in ARMS:
        sl = slices[(arm, "merged")]
        head = cv_spec(headline[arm], sl.units, sl.plan.folds, arm, full_fit=False)
        accepted: frozenset[str] = frozenset()
        ablations[arm] = []
        for group, options in ABLATIONS[arm].items():
            runs = [(label, cv_spec(replace(headline[arm], extras=extras), sl.units, sl.plan.folds, arm,
                                    full_fit=False, label=label)) for label, extras in options]
            label, best = min(runs, key=lambda t: t[1].mean("mae"))
            keep = best.mean("mae") < head.mean("mae") - head.se("mae")
            for lab, run in runs:
                ablations[arm].append((group, lab, run, keep and lab == label, head))
            if keep:
                accepted |= best.spec.extras
        pre_power[arm] = replace(headline[arm], extras=accepted)

    # 4. Shape variants (firearm/calibre representation × shooting cluster), each
    #    with stat powers fitted by nested coarse descent; then the fine search on
    #    the adopted variant.
    powers: dict[str, PowerResult] = {}
    variants: dict[str, list[VariantResult]] = {}
    variant_detail: dict[str, dict] = {}
    final: dict[str, Spec] = dict(pre_power) if args.linear else {}
    for arm in ARMS if not args.linear else ():
        sl = slices[(arm, "merged")]
        variants[arm] = screen_variants(pre_power[arm], sl, lambda m: log(m, started))
        adopted = next(v for v in variants[arm] if v.adopted)
        variant_detail[arm] = variant_details(variants[arm], sl)
        pw = powers[arm] = adopted.power
        spec = adopted.spec
        log(f"adopted   {arm:9} {adopted.label} (nested {pw.nested.mean('mae'):.2f})", started)
        # 4b. Fine local refinement around the adopted variant's coarse powers, nested again.
        pw.fine = nested_fine(spec, sl, pw)
        fine = pw.fine
        if fine.choice == "fine":
            final[arm] = with_powers(spec, fine.full_powers, fine.full_p)
        elif fine.choice == "coarse":
            final[arm] = with_powers(spec, pw.full_powers, pw.full_p)
        else:
            final[arm] = spec
        log(f"fine      {arm:9} fine nested {fine.nested.mean('mae'):.2f} → choice {fine.choice}; "
            f"final [{final[arm].describe()}]", started)

    # 5. Final model on every slice, baseline, faction modifiers (+ faction × class).
    fclass: dict[tuple[str, str], FclassResult] = {}
    for arm in ARMS:
        for side in SIDES:
            sl = slices[(arm, side)]
            spec = final[arm] if side == "merged" else side_spec(final[arm])
            sl.runs["baseline"] = cv_baseline(sl.units, sl.plan.folds)
            sl.runs["final"] = cv_spec(spec, sl.units, sl.plan.folds, arm, label="final model")
            sl.runs["RF"] = cv_spec(replace(spec, faction=True), sl.units, sl.plan.folds, arm,
                                    label="final × per-arm faction modifier")
            if FCLASS_FORM:
                variant, loss = FCLASS_FORM
                fc = fclass_cv(variant, replace(spec, loss=loss), sl.units, sl.plan.folds, arm)
                sl.runs["FC"], fclass[(arm, side)] = fc.run, fc
    shared_m: dict[str, dict[str, float]] = {}
    for side in SIDES:
        runs, shared_m[side] = shared_faction_runs(slices, side, final)
        for arm in ARMS:
            slices[(arm, side)].runs["RFs"] = runs[arm]
    log("final models and faction modifiers done" + (
        "; faction × class " + ", ".join(f"{arm} {slices[(arm, 'merged')].runs['FC'].mean('mae'):.2f}" for arm in ARMS)
        if FCLASS_FORM else ""), started)

    # 5b. Packing vs unit size on the final model.
    packing: dict[str, dict] = {}
    for arm in ARMS:
        sl = slices[(arm, "merged")]
        spec = final[arm]
        rd = np.array([u.rank_depth for u in sl.units])
        n = np.array([u.n for u in sl.units])
        packing_variants = [("final model", spec), ("+ size multiplier", replace(spec, mult=spec.mult | {"size"}))]
        if "rank_depth" in spec.mult | spec.linear:
            no_rd = replace(spec, mult=spec.mult - {"rank_depth"}, linear=spec.linear - {"rank_depth"})
            packing_variants.append(("rank_depth removed", no_rd))
        else:
            packing_variants.append(("+ rank_depth multiplier", replace(spec, mult=spec.mult | {"rank_depth"})))
        runs = []
        for label, variant in packing_variants:
            run = cv_spec(variant, sl.units, sl.plan.folds, arm, label=label)
            note = "; ".join(f"δ_{v} = {run.full.delta[v]:+.4f} (ref {run.full.refs[v]:g})"
                             for v in ("rank_depth", "size") if v in variant.mult)
            runs.append((label, run, note))
        packing[arm] = {"corr": float(np.corrcoef(rd, n)[0, 1]), "runs": runs}

    # 6. 7. Poland: same folds minus Poland's rows, on the final model.
    poland: dict[tuple[str, str], dict] = {}
    for arm in ARMS:
        for side in ("imperial", "merged"):
            sl = slices[(arm, side)]
            keep = np.array([u.faction != POLAND for u in sl.units])
            if keep.all():
                continue
            kept = [u for u, k in zip(sl.units, keep) if k]
            rich = rich_design(kept, arm)
            plan = restrict(sl.plan, keep, rich.X, sl.groups[keep], rich.names)
            spec = final[arm] if side == "merged" else side_spec(final[arm])
            without = cv_spec(spec, kept, plan.folds, arm, label="without Poland")
            with_run = sl.runs["final"]
            resid = pct_resid(np.array([u.cost for u in sl.units], float)[~keep], with_run.oof[~keep])
            resid = resid[np.isfinite(resid)]
            poland[(arm, side)] = {"with": with_run, "without": without, "n": int((~keep).sum()),
                                   "median_resid": float(np.median(resid)),
                                   "share_over": float(np.mean(resid > 0) * 100)}

    # 7. Transfer: imperial → coalition and back, final model (side dropped), merged columns.
    transfer: dict[tuple[str, str], dict] = {}
    for arm in ARMS:
        spec = side_spec(final[arm])
        merged = slices[(arm, "merged")]
        design, d = design_for(spec, merged.units, arm), data_for(spec, merged.units)
        sides = np.array([u.side for u in merged.units])
        for source, target in (("imperial", "coalition"), ("coalition", "imperial")):
            train, test = np.flatnonzero(sides == source), np.flatnonzero(sides == target)
            model = fit_on(spec, design, d, train)
            pred = predict_total(model, design, d, test)
            bad = unidentified(design.X, train, test)
            affected = np.any(design.X[test][:, bad] != design.X[train][0, bad], axis=1) if bad.any() \
                else np.zeros(len(test), bool)
            for var in spec.mult & set(CATEGORICAL):
                affected |= ~np.isin(d.fvals[var][test], list(model.levels[var]))
            m = metrics(d.cost[test], pred, d.size[test])
            m["affected"] = int(affected.sum())
            m["unidentified"] = [design.names[j] for j in np.flatnonzero(bad)]
            m["unseen_ratings"] = sorted(set(d.fvals["rating"][test].tolist()) - set(d.fvals["rating"][train].tolist()))
            in_side = slices[(arm, target)].runs["final"]
            m["in_side_mae"], m["in_side_mape"] = in_side.mean("mae"), in_side.mean("mape")
            transfer[(arm, f"{source} → {target}")] = m

    # 8. Staff generals.
    staff_slices = {side: make_staff_slice(side, [g for g in staff if side == "merged" or g.side == side], args.seeds)
                    for side in SIDES}
    staff_head = min(("T1", "T2", "T3"), key=lambda k: staff_slices["merged"].runs[k].mean("mae"))
    staff_poland: dict[str, dict] = {}
    for side in ("imperial", "merged"):
        ss = staff_slices[side]
        keep = np.array([g.faction != POLAND for g in ss.gens])
        kept = [g for g, k in zip(ss.gens, keep) if k]
        C, names = staff_coverage(kept)
        plan = restrict(ss.plan, keep, C, group_ids(C, [0] * len(kept)), names)
        runs = staff_cv(kept, plan.folds)
        cost = np.array([g.cost for g in ss.gens], float)
        staff_poland[side] = {"n": int((~keep).sum()), "key": staff_head,
                              "with_mae": ss.runs[staff_head].mean("mae"), "without_mae": runs[staff_head].mean("mae"),
                              "resid": float(np.nanmean(cost[~keep] - ss.runs[staff_head].oof[~keep]))}

    res = Results(units, staff, slices, regression, profiles, search, reprofiles, ablations, powers, final, packing,
                  poland, transfer, staff_slices, staff_head, staff_poland, tag_mismatches, ratings, args.seeds, shared_m,
                  linear=args.linear, variants=variants, variant_detail=variant_detail, fclass=fclass)
    res.elapsed = time.time() - started
    write_outputs(res)
    log(f"done → {OUT_DIR.relative_to(ROOT) if OUT_DIR.is_relative_to(ROOT) else OUT_DIR}", started)
    return 0


# --- Output -------------------------------------------------------------------

def write_outputs(res: Results) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_search(res)
    write_coefficients(res)
    write_oof(res)
    (OUT_DIR / "unit_pricing_report.md").write_text("\n".join(report_lines(res)) + "\n", encoding="utf-8")


def write_search(res: Results) -> None:
    with (OUT_DIR / "search_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(["arm", "rank", "size", "p", "linear", "multiplicative", "const_c", "params", "mae_mean",
                         "mae_sd", "mape_mean", "r2_mean", "best", "headline"])
        for arm, s in res.search.items():
            for rank, run in enumerate(s.runs, 1):
                writer.writerow([arm, rank, run.spec.size, run.spec.p, " ".join(sorted(run.spec.linear)),
                                 " ".join(sorted(run.spec.mult)), int(run.spec.const), run.params,
                                 f"{run.mean('mae'):.4f}", f"{run.sd('mae'):.4f}", f"{run.mean('mape'):.4f}",
                                 f"{run.mean('r2'):.5f}", int(run is s.best), int(run is s.headline)])


def write_coefficients(res: Results) -> None:
    with (OUT_DIR / "coefficients.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(["model", "slice", "variant", "feature", "coefficient", "note"])
        for (arm, side), sl in res.slices.items():
            for key in ("final", "RF", "FC"):
                if key not in sl.runs:
                    continue
                run = sl.runs[key]
                model, spec = run.full, run.spec
                refs = "reference levels: " + "; ".join(f"{k}={v}" for k, v in run.references.items())
                writer.writerow([arm, side, key, "size", spec.size, "models = men_raw/2" if spec.size == "n" else "guns"])
                writer.writerow([arm, side, key, "size power p", f"{spec.p:g}", "price ∝ size^p"])
                for shape_key in SHAPE_DEFAULTS:
                    writer.writerow([arm, side, key, f"shape {shape_key}", spec.shape_of(shape_key),
                                     "how shooting / firearm / calibre enter β·x (see SHAPE_DEFAULTS)"])
                for stat, a in spec.powers:
                    if stat.startswith("shoot:"):
                        note = (f"exponent inside shoot = Π (stat/{POWER_SCALE:g})^a × ({RATE_SCALE:g}/gun reload "
                                f"time)^a_rate; absent exponents are 1")
                    elif stat.startswith("cal:"):
                        source = "projectile damage" if stat == "cal:damage" else "range"
                        note = f"calibre column = ({source} / {POWER_SCALE:g})^power"
                    else:
                        note = f"the β column is (stat / {POWER_SCALE:g})^power"
                    writer.writerow([arm, side, key, f"stat power {stat}", f"{a:g}", note])
                writer.writerow([arm, side, key, "(intercept: per-size constant b0)", f"{model.b0:.10g}",
                                 spec.describe() + " | " + refs])
                for name, coef in zip(run.names, model.beta):
                    writer.writerow([arm, side, key, name, f"{coef:.10g}", "gold per size unit^p"])
                if spec.const:
                    writer.writerow([arm, side, key, "c (per unit, outside the multiplier)", f"{model.c:.10g}", "gold per unit"])
                if spec.fixed_rating:
                    writer.writerow([arm, side, key, "rating divisor", f"{REF_RATING}/rating",
                                     "fixed; scales the β part like a multiplier"])
                for var in sorted(spec.mult):
                    if var in MULT_CATEGORICAL:
                        note = (f"ridge κ = {spec.kappa:g}, no reference (unseen cell → 1)" if var in GROUPING
                                else f"reference {model.refs[var]}")
                        for level, m in sorted(model.levels[var].items(), key=lambda t: str(t[0])):
                            writer.writerow([arm, side, key, f"multiplier {var}={level}", f"{m:.10g}", note])
                    else:
                        writer.writerow([arm, side, key, f"multiplier {var} δ", f"{model.delta[var]:.10g}",
                                         f"m = 1 + δ·({var} − {model.refs[var]:g})"])
                for faction, m in sorted(model.faction_m.items()):
                    writer.writerow([arm, side, key, f"faction modifier {faction}", f"{m:.10g}",
                                     "per-arm; multiplies the scaled part"])
                for cell, m in sorted(model.fclass_m.items()):
                    writer.writerow([arm, side, key, f"faction×class modifier {cell}", f"{m:.10g}",
                                     f"residual, ridge κ = {spec.kappa:g}; multiplies faction modifier × scaled part"])
        for side, mods in res.shared_m.items():
            for faction, m in sorted(mods.items()):
                writer.writerow(["all arms", side, "RFs", f"faction modifier {faction}", f"{m:.10g}",
                                 "one per corps across arms; multiplies each arm's scaled part"])
        for side, ss in res.staff_slices.items():
            for form in ("T1", "T2", "T3"):
                coef, _, fm = staff_full(ss.gens, form)
                note = (f"cost = b·stars^q·({REF_RATING}/r); 1 without stars" if form == "T3"
                        else "cost = 1 + …; r − 8")
                for name, c in zip(STAFF_RATING_NAMES[form], coef):
                    writer.writerow(["staff", side, form, name, f"{c:.10g}", note])
                for faction, m in sorted(fm.items()):
                    writer.writerow(["staff", side, f"TF{form[1]}", f"faction modifier {faction}", f"{m:.10g}",
                                     "multiplies (cost − 1)"])


def full_fit_prices(run: CVRun, units: Sequence[Unit], arm: str) -> np.ndarray:
    design, d = design_for(run.spec, units, arm), data_for(run.spec, units)
    return predict_total(run.full, design, d, np.arange(len(units)))


def write_oof(res: Results) -> None:
    with (OUT_DIR / "oof_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(["model", "slice", "unit_key", "faction_key", "army_corps_name", "side", "rating",
                         "unit_class", "speed", "n_models", "guns", "cost", "fold",
                         "oof_final", "oof_final_faction", "oof_final_faction_shared", "oof_final_faction_class",
                         "resid_pct_final", "full_fit_pred_final"])
        cell = lambda v: "" if not np.isfinite(v) else f"{v:.3f}"   # NaN = pinned to train
        for (arm, side), sl in res.slices.items():
            fin, rf, rfs = sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
            fc = sl.runs.get("FC")
            full_pred = full_fit_prices(fin, sl.units, arm)
            for i, u in enumerate(sl.units):
                resid = (u.cost - fin.oof[i]) / fin.oof[i] * 100 if np.isfinite(fin.oof[i]) else np.nan
                writer.writerow([arm, side, u.key, u.faction, u.corps, u.side, u.rating, u.unit_class,
                                 "DR" if u.is_camel else u.speed, f"{u.n:g}", f"{u.guns:g}", u.cost,
                                 fin.oof_fold[i] or "", cell(fin.oof[i]), cell(rf.oof[i]), cell(rfs.oof[i]),
                                 cell(fc.oof[i]) if fc else "", cell(resid), f"{full_pred[i]:.3f}"])
        for side, ss in res.staff_slices.items():
            fold_of = np.zeros(len(ss.gens), int)
            for k, (_, test) in enumerate(ss.plan.folds):
                fold_of[test] = k + 1
            _, full_p, _ = staff_full(ss.gens, res.staff_head)
            rate, rf = ss.runs[res.staff_head], ss.runs[f"TF{res.staff_head[1]}"]
            for i, g in enumerate(ss.gens):
                resid = ((g.cost - rate.oof[i]) / rate.oof[i] * 100
                         if np.isfinite(rate.oof[i]) and rate.oof[i] else np.nan)
                writer.writerow(["staff", side, g.key, g.faction, g.corps, g.side, g.rating, "general_staff",
                                 f"stars={g.stars}", 16, "", g.cost, fold_of[i] or "",
                                 cell(rate.oof[i]), cell(rf.oof[i]), "", "", cell(resid), f"{full_p[i]:.3f}"])


def corps_resid_stats(res: Results, key: str, min_units: int = 20):
    """Per corps (merged slices, three arms pooled): units, mean/median resid %, share above."""
    per: dict[str, list[float]] = defaultdict(list)
    for arm in ARMS:
        sl = res.slices[(arm, "merged")]
        r = pct_resid(np.array([u.cost for u in sl.units], float), sl.runs[key].oof)
        for u, value in zip(sl.units, r):
            if np.isfinite(value):
                per[u.faction].append(float(value))
    return [(f, len(v), float(np.mean(v)), float(np.median(v)), float(np.mean(np.array(v) > 0) * 100))
            for f, v in per.items() if len(v) >= min_units]


def bargains(res: Results, arm: str) -> tuple[list[dict], list[dict]]:
    """Top 10 by absolute and by relative funds saved: model price − actual.
    Out-of-fold predictions (full-fit for the few units pinned to train),
    identical (name, corps, cost) rows merged, non-positive predictions skipped."""
    sl = res.slices[(arm, "merged")]
    run = sl.runs["final"]
    full = full_fit_prices(run, sl.units, arm)
    groups: dict[tuple, dict] = {}
    for i, u in enumerate(sl.units):
        pinned = not np.isfinite(run.oof[i])
        pred = float(full[i] if pinned else run.oof[i])
        if pred <= 0:
            continue
        key = (u.name, u.corps, u.cost, round(pred))
        item = groups.setdefault(key, {"unit": u, "pred": pred, "pinned": pinned, "count": 0})
        item["count"] += 1
    items = list(groups.values())
    for item in items:
        item["saved"] = item["pred"] - item["unit"].cost
        item["rel"] = item["saved"] / item["pred"] * 100
    return (sorted(items, key=lambda t: -t["saved"])[:10], sorted(items, key=lambda t: -t["rel"])[:10])


def power_key_order(res: "Results") -> list[str]:
    """Every exponent key used by any arm's adopted variant (coarse or fine):
    additive stats in NUMERIC order, then shooting / calibre keys."""
    used = set()
    for pw in res.powers.values():
        used |= set(pw.full_powers)
        if pw.fine:
            used |= set(pw.fine.full_powers)
    return [k for k in NUMERIC if k in used] + sorted(used - set(NUMERIC))


def fclass_report(res: Results, top: int = 8) -> list[str]:
    """Section 10b: the adopted faction × unit-class modifier."""
    variant, loss = FCLASS_FORM
    L = [f"### Faction × unit-class modifier ({FCLASS_LABEL[variant]}{', LAD loss' if loss == 'lad' else ''})", "",
         "From the blind study (branch `blind-pricing-study`; tested in `blind_ideas_report.md`): NTW3 prices look "
         "hand-set per corps *per unit class*, which one faction modifier per arm cannot capture. "
         + ("Here each faction × class cell multiplies the final model × faction modifier, shrunk towards 1 "
            "(stats fitted first, unchanged). " if variant == "RFC" else
            f"Here the free rating levels are replaced by the divisor {REF_RATING}/N and each faction × class cell "
            "is a multiplier fitted jointly with the stat coefficients. ")
         + "A cell's ridge pull is κ pseudo-units of average price at 1; κ is chosen by inner CV inside each outer "
           "training fold (an unseen cell falls back to its faction / to 1).", ""]
    rows = []
    for (arm, side), fc in res.fclass.items():
        sl = res.slices[(arm, side)]
        rf = sl.runs["RF"]
        diff = np.array([a["mae"] - b["mae"] for a, b in zip(fc.run.fold_metrics, rf.fold_metrics)])
        rows.append([arm, side, pm(rf, "mae", f1), pm(fc.run, "mae", f1), pm(fc.run, "mape", f1),
                     f"{diff.mean():+.2f} ± {diff.std(ddof=1) / np.sqrt(len(diff)):.2f}",
                     ", ".join(f"{k:g}" for k in fc.kappas), f"{fc.full_kappa:g}", fc.run.fallbacks])
    L += table(["arm", "side", "MAE + per-arm m_f", "MAE + faction × class", "MAPE %", "Δ vs m_f (paired SE)",
                "κ per fold", "κ full fit", "test rows in unseen cells"], rows)
    L += [""]
    for arm in ARMS:
        fc = res.fclass.get((arm, "merged"))
        if not fc:
            continue
        sl = res.slices[(arm, "merged")]
        cells: dict[str, list[Unit]] = defaultdict(list)
        for u in sl.units:
            cells[f"{u.faction}|{u.unit_class}"].append(u)
        ranked = sorted((fclass_multiplier(fc.run.full, us[0]), us[0].corps, us[0].unit_class, len(us))
                        for us in cells.values())
        L += [f"**{arm}** — most extreme cells, army multiplier relative to the plain {REF_RATING}/N rule "
              f"(full-data fit, κ = {fc.full_kappa:g}):", ""]
        L += table(["corps", "unit class", "units", "multiplier"],
                   [[c, uc, n, f"×{m:.3f}"] for m, c, uc, n in ranked[:top] + ranked[-top:]])
        L += [""]
    return L


def report_lines(res: Results) -> list[str]:
    L: list[str] = []
    add = L.append
    slices, ratings = res.slices, res.ratings
    add("# Unit-pricing model — ToW + Custom")
    add("")
    add("Generated by `analysis/unit_pricing.py` from `data/generated/ntw3_units_analysis.csv` and the corps "
        f"ratings in `army_corps_catalog.csv`. {res.n_seeds} split seeds searched per slice; run time "
        f"{res.elapsed / 60:.0f} min.")
    add("")
    add("**Structure.** `price = M × size^p × (b0 + Σ β_j·stat_j^(a_j) + flags + categoricals) + c`. The parts:")
    add("")
    add("- **size** is models (men_raw / 2) for infantry and cavalry, and **guns** for artillery.")
    add("- **p** is profiled by cross-validation.")
    add("- **a_j** are per-stat powers, fitted inside each training fold.")
    add("- **M** is a product of factors.")
    add("- **c** is a flat per-unit constant, outside the multiplier.")
    add("")
    add("Corps rating, training level, drill set, packing (`rank_depth`) and side are each searched "
        "in three placements: out of the model, in β·x, or as a factor of M.")
    add("")
    add("**Residual sign.** `resid % = (actual − predicted) / predicted`. Positive means the game charges more "
        "than the model.")
    add("")

    # ---- Summary
    add("## Summary")
    add("")
    add("Merged slices, mean over the 5 out-of-fold splits, shown as MAPE % / MAE gold. *Previous* is the last "
        "run's final model (models, p = 1, linear stats), refitted here on the same folds.")
    add("")
    rows = []
    has_fc = "FC" in slices[(ARMS[0], "merged")].runs
    for arm in ARMS:
        sl = slices[(arm, "merged")]
        b, f_, r_, s_ = sl.runs["baseline"], sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
        shown = (b, res.regression[arm], f_, r_, s_) + ((sl.runs["FC"],) if has_fc else ())
        rows.append([arm] + [f"{f1(run.mean('mape'))}% / {f1(run.mean('mae'))}" for run in shown] +
                    [f3(f_.mean("r2")), f"`{res.final[arm].describe()}`"])
    L += table(["arm", "baseline", "previous", "final", "final + per-arm faction", "final + shared faction"] +
               ([f"{FCLASS_LABEL[FCLASS_FORM[0]]}" + (" (LAD)" if FCLASS_FORM[1] == "lad" else "")] if has_fc else []) +
               ["R² final", "final structure"], rows)
    add("")
    ss = res.staff_slices["merged"]
    add(f"Staff generals (merged): {res.staff_head} MAE "
        f"{f1(ss.runs[res.staff_head].mean('mae'))}, with faction modifier MAE "
        f"{f1(ss.runs['TF' + res.staff_head[1]].mean('mae'))}.")
    add("")

    # ---- 1. Population & checks
    add("## 1. Population and data checks")
    add("")
    counts = Counter((u.arm, u.side) for u in res.units)
    rows = [[arm, counts[(arm, "imperial")], counts[(arm, "coalition")],
             counts[(arm, "imperial")] + counts[(arm, "coalition")]] for arm in ARMS]
    rows.append(["staff generals", sum(g.side == "imperial" for g in res.staff),
                 sum(g.side == "coalition" for g in res.staff), len(res.staff)])
    L += table(["arm", "imperial", "coalition", "merged"], rows)
    add("")
    add(f"- Scope: ToW + Custom, excluding dev corps ({', '.join(sorted(DEV_CORPS))}) and `artillery_fixed`. "
        "Custom `france` and `denmark` count as imperial; the other customs as coalition.")
    add("- **Traits and abilities in β·x:** the 9 description flags plus `guard_mode`, `skirmish` and "
        "`can_snipe`. Counts: " +
        ", ".join(f"`{a}` {sum(u.values[a] > 0 for u in res.units)}" for a in EXTRA_ABILITIES + ("pike_square",)) + ".")
    add(f"- Speed is read from each unit name's tag. It disagrees with the pipeline `speed_code` on "
        f"{len(res.tag_mismatches)} rows: " +
        ", ".join(f"`{u.key}` `[{u.raw_tag}]` vs `{u.speed_code}`" for u in res.tag_mismatches) +
        ". Camels carry `is_camel`; GS is folded into S.")
    crew = {cls: sorted({round(u.n / u.guns, 4) for u in res.units if u.unit_class == cls})
            for cls in ("artillery_foot", "artillery_horse")}
    add(f"- Artillery crew per gun is fixed by type: foot {crew['artillery_foot']}, horse "
        f"{crew['artillery_horse']}. That is why artillery is sized by guns.")
    add("")
    add("### Eastern artillery calibre — name vs what the game fires")
    add("")
    L += table(["name calibre", "≈ lb", "weapon", "projectile fired", "damage", "units", "note"],
               eastern_calibre_rows(res.units))
    add("")
    add("### Firearm vs range")
    add("")
    for arm in ("infantry", "cavalry"):
        o = firearm_range_overlap([u for u in res.units if u.arm == arm])
        add(f"- **{arm}**: {o['firearms']} firearms, {o['ranges']} distinct ranges, at most "
            f"{o['ranges_per_firearm_max']} range per firearm. Firearm explains **{o['eta2']:.1%}** of the "
            "variance in range, so the two can't be told apart.")
    add("")

    # ---- 2. Split quality
    add("## 2. Split quality — 5 × 80/20, stratified, coverage-guaranteed, faction-balanced")
    add("")
    rows = []
    for (arm, side), sl in slices.items():
        p = sl.plan
        cov = ", ".join(f"{fam} {b1}/{tot}" + ("" if mn == tot else f" (min {mn})")
                        for fam, (b1, mn, tot) in sl.coverage.items())
        lo, med, hi = p.balance_spread
        rows.append([arm, side, p.seed, p.violations_before_repair, len(p.repairs),
                     f"{lo:.0%} / {med:.0%} / {hi:.0%}", ", ".join(f"`{x}`" for x in p.pinned) or "—", cov])
    L += table(["arm", "side", "seed", "violations", "repairs", "faction test share fold 1",
                "pinned to train (not validated)", "levels in both sets, fold 1"], rows)
    add("")
    for (arm, side), sl in slices.items():
        for line in sl.plan.repairs:
            add(f"- Repair, {arm} / {side}: {line}")
    add("")

    # ---- 3. Regression check
    add("## 3. Fitter regression check")
    add("")
    add("The generalised fitter (size power and stat powers set to 1, size = models) must reproduce the "
        "previous run's final merged CV MAE on the same folds.")
    add("")
    L += table(["arm", "structure", "previous run", "reproduced", "match"],
               [[arm, f"`{PREVIOUS_FINAL[arm][0].describe()}`", f"{PREVIOUS_FINAL[arm][1]:.4f}",
                 f"{res.regression[arm].mean('mae'):.4f}",
                 "yes" if abs(res.regression[arm].mean("mae") - PREVIOUS_FINAL[arm][1]) < 0.001 else "**NO**"]
                for arm in ARMS])
    add("")

    # ---- 4. Size power
    add("## 4. Size power — how price scales with unit size")
    add("")
    if res.linear:
        add("**Fully linear run** (`--linear`): size = models for every arm (artillery too), p = 1, and linear "
            "stats. No size-power profile or stat powers are fitted. This reproduces the model as it stood before "
            "size and stat powers were introduced.")
    else:
        add("Last run's final structure with `size^p`, CV MAE for each p (every 0.10 shown). The bold cell is "
            "each curve's minimum, and a † marks p values within one SE of it. Artillery is profiled with both "
            "guns and models as the size.")
    add("")
    for arm, pr in ({} if res.linear else res.profiles).items():
        keys = list(pr.curves)
        header = ["p"] + [f"{'guns' if k == 'guns' else 'models'}{', + c' if c else ''}" for k, c in keys]
        minima = {key: min(curve, key=lambda t: t[1]) for key, curve in pr.curves.items()}
        rows = []
        for i, p in enumerate(P_GRID):
            if round(p * 100) % 10:
                continue
            row = [f"{p:.1f}"]
            for key in keys:
                _, mae, _ = pr.curves[key][i]
                best_p, best_mae, best_se = minima[key]
                cell = f1(mae)
                if p == best_p:
                    cell = f"**{cell}**"
                elif mae <= best_mae + best_se:
                    cell += " †"
                row.append(cell)
            rows.append(row)
        add(f"### {arm}")
        add("")
        add("Minimum per curve: " + "; ".join(
            f"{'guns' if k == 'guns' else 'models'}{' + c' if c else ''}: p = {minima[(k, c)][0]:g}, "
            f"MAE {f1(minima[(k, c)][1])}" for k, c in keys) + ".")
        add("")
        L += table(header, rows)
        add("")
        add(f"Chosen: size = **{'guns' if pr.best_size == 'guns' else 'models'}**, p* = **{pr.best_p:g}**. After "
            f"the structure re-search, p was re-profiled on the new headline: **p = "
            f"{res.reprofiles[arm].best_p:g}** (MAE {f1(res.reprofiles[arm].best_mae)}).")
        add("")

    # ---- 5. Structure search
    add("## 5. Structure search" + ("" if res.linear else " with the size power"))
    add("")
    add("Every combination of placements, each with and without `c`" +
        (" (size = models, p = 1)." if res.linear else ", at each arm's size and p*.") +
        " The headline is the model with the fewest parameters within one SE of the best.")
    add("")
    for arm, s in res.search.items():
        add(f"### {arm} — {len(s.runs)} models")
        add("")
        add(f"Best: `{s.best.spec.describe()}`, MAE {pm(s.best, 'mae', f1)} (SE {f2(s.best.se('mae'))}). "
            f"Headline: `{s.headline.spec.describe()}`, MAE {pm(s.headline, 'mae', f1)}, {s.headline.params} parameters.")
        add("")
        rows = []
        for var, places in s.placement.items():
            best_where = min(places, key=lambda k: places[k])
            rows.append([var] + [f"**{f1(places[w])}**" if w == best_where else f1(places[w])
                                 for w in ("out", "linear", "mult")])
        L += table(["variable", "out", "linear (in β·x)", "multiplicative (in M)"], rows)
        add("")
        rows = [[rank, f"`{run.spec.describe()}`" + (" **(headline)**" if run is s.headline else ""), run.params,
                 pm(run, "mae", f1), f1(run.mean("mape")), f3(run.mean("r2"))]
                for rank, run in enumerate(s.runs[:10], 1)]
        L += table(["rank", "structure", "params", "MAE (gold)", "MAPE %", "R²"], rows)
        if s.headline not in s.runs[:10]:
            add("")
            add(f"(Headline ranks {s.runs.index(s.headline) + 1}.)")
        add("")

    # ---- 6. Ablations
    add("## 6. Linear-part ablations on the headline")
    add("")
    rows = []
    for arm, items in res.ablations.items():
        for group, label, run, accepted, head in items:
            rows.append([arm, group, label, f1(head.mean("mae")), f1(run.mean("mae")),
                         f"{run.mean('mae') - head.mean('mae'):+.2f}", f2(head.se("mae")),
                         "**kept**" if accepted else "—"])
    L += table(["arm", "group", "option", "MAE headline", "MAE option", "Δ", "1 SE", "verdict"], rows)
    add("")

    # ---- 7. Stat powers
    add("## 7. Shooting, firearm / calibre representation, and stat powers")
    add("")
    if res.linear:
        add("Not fitted in the fully linear run: every stat enters β·x linearly.")
        add("")
    if res.variants:
        add("**Variants.** These change only how shooting and the firearm/calibre information enter β·x; "
            "everything else is the headline structure. Each is scored with its exponents fitted by nested "
            "coarse descent: the shooting-product exponents, the gun fire-rate exponent, the calibre exponent, "
            "the remaining additive stat powers, and p. **F0·SH0 is the current model.**")
        add("")
        add("- **F (infantry/cavalry):** F0 range; F1 firearm one-hot, with range dropped (each firearm has "
            "one range).")
        add("- **F (artillery):** F0 range + projectile damage + gun reload; F1 calibre = (damage/100)^a with "
            "the shot type, range and gun reload dropped; F2 cannon-type (projectile) one-hot.")
        add("- **SH:** SH0 accuracy, ammo and reload_skill additive; SH1 one shooting column "
            f"`Π (stat/100)^a × ({RATE_SCALE:g} / gun reload time)^a_rate`, so the crew's reload skill and the "
            "gun's intrinsic fire rate are separate factors; SH2 the same with one shooting slope per firearm "
            "or cannon type (artillery F1: calibre inside the product).")
        add("- Melee attack, defence and charge stay additive, like morale.")
        add("")
        add("**Adoption rule — summation is the default.** A shooting product is probably not how the game "
            "implements shooting, so:")
        add("")
        add("1. A product variant (SH1/SH2) is **eligible** only if it beats the summation variant with the same "
            "firearm/calibre representation (its F·SH0) by more than one SE.")
        add("2. An eligible variant replaces F0·SH0, the current model, only if it beats it by more than one SE.")
        add("3. Among those within one SE of the best, summation is preferred, then the fewest parameters.")
        add("")
        add("Cavalry error is already low (about 7.7% MAPE), so cavalry stays as it is unless a variant clears "
            "this bar.")
        add("")
        for arm, items in res.variants.items():
            current = items[0]
            rows = []
            for v in items:
                rows.append([f"`{v.key}`", v.label, f1(v.power.base.mean("mae")), pm(v.power.nested, "mae", f1),
                             f"{v.mean() - current.mean():+.2f}", f2(current.se()), f1(v.power.nested.mean("mape")),
                             v.params, v.unseen or "—",
                             "—" if v.key.endswith("SH0") else ("yes" if v.eligible else "no"),
                             "**adopted**" if v.adopted else ""])
            add(f"### {arm}")
            add("")
            L += table(["variant", "shape", "MAE, exponents = 1", "MAE nested (exponents fitted)", "Δ vs F0·SH0",
                        "1 SE (F0·SH0)", "MAPE nested", "params", "test rows with unseen levels",
                        "product beats its summation by > 1 SE", ""], rows)
            add("")
            keys = sorted({k for v in items for k in v.power.full_powers} - set(NUMERIC)) + \
                [k for k in NUMERIC if any(k in v.power.full_powers for v in items)]
            rows = [[f"`{k}`"] + [f"{v.power.full_powers[k]:g}" if k in v.power.full_powers else "—" for v in items]
                    for k in keys]
            rows.append(["size power p"] + [f"{v.power.full_p:g}" for v in items])
            add("Full-data exponents per variant (coarse grid; `shoot:rate` = gun fire-rate exponent, "
                "`cal:damage` = calibre exponent):")
            add("")
            L += table(["exponent"] + [f"`{v.key}`" for v in items], rows)
            add("")
            detail = res.variant_detail.get(arm, {})
            if "firearm" in detail:
                fd = detail["firearm"]
                add(f"Firearm coefficients in the best F1 variant (`{fd['variant']}`, full-data fit, gold per "
                    f"size unit^p, reference firearm `{fd['reference']}`):")
                add("")
                L += table(["column", "coefficient"], [[f"`{n}`", f"{c:+.4g}"] for n, c in fd["rows"]])
                add("")
            if "calibre" in detail:
                cd = detail["calibre"]
                add(f"Calibre curve in the best F1 variant (`{cd['variant']}`): calibre term = "
                    f"{cd['beta']:+.4g} × (damage/100)^{cd['a']:g}, in gold per gun^p, added to β·x. The shot "
                    "type's own coefficient sets each family's level.")
                add("")
                L += table(["projectile", "shot type", "damage", "calibre term"],
                           [[f"`{p}`", s, f"{d:g}", f"{t:+.1f}"] for p, s, d, t in cd["rows"]])
                add("")
            if "cannon" in detail:
                kd = detail["cannon"]
                add(f"Cannon-type coefficients in the best F2 variant (`{kd['variant']}`, reference "
                    f"`{kd['reference']}`):")
                add("")
                L += table(["column", "coefficient"], [[f"`{n}`", f"{c:+.4g}"] for n, c in kd["rows"]])
                add("")
        if ARTILLERY_CAL != "auto":
            add(f"**Artillery was restricted** (`--artillery-cal {ARTILLERY_CAL}`): only F0 and "
                f"{ARTILLERY_CAL_KEYS[ARTILLERY_CAL]} were screened, so this run fixes the calibre representation "
                "rather than choosing it.")
            add("")
        add("The adopted variant then goes through the stat-power comparison and fine search below.")
        add("")
    if res.powers:
        add(f"For each numeric stat, a power from {list(POWER_GRID)}, plus the size power p within ±{P_WINDOW}, is "
            "fitted by coordinate descent on the **training rows of each fold**, and that fold's test rows are then "
            "scored. The CV is therefore honest about the extra flexibility. The powers are kept only if they beat "
            "linear stats by more than one SE.")
        add("")
        rows = []
        for arm, pw in res.powers.items():
            rows.append([arm, pm(pw.base, "mae", f1), pm(pw.nested, "mae", f1),
                         f"{pw.nested.mean('mae') - pw.base.mean('mae'):+.2f}", f2(pw.base.se("mae")),
                         f1(pw.base.mean("mape")), f1(pw.nested.mean("mape")), "**kept**" if pw.kept else "not kept"])
        L += table(["arm", "MAE linear stats", "MAE stat powers (nested)", "Δ", "1 SE", "MAPE linear", "MAPE powers",
                    "verdict"], rows)
        add("")
        add("Fitted powers: *full* is the descent on all rows; the fold range shows how stable each power is across "
            "the 5 training folds.")
        add("")
        rows = []
        for stat in power_key_order(res) + ["size power p"]:
            row = [stat]
            for arm, pw in res.powers.items():
                if stat == "size power p":
                    folds = [p for _, p in pw.fold_powers]
                    full = pw.full_p
                else:
                    if stat not in pw.full_powers:
                        row.append("—")
                        continue
                    folds = [powers.get(stat, 1.0) for powers, _ in pw.fold_powers]
                    full = pw.full_powers[stat]
                row.append(f"{full:g} ({min(folds):g} … {max(folds):g})")
            rows.append(row)
        L += table(["stat"] + [f"{arm}: full (folds)" for arm in res.powers], rows)
        add("")

    if any(pw.fine for pw in res.powers.values()):
        add("### 7b. Fine power search")
        add("")
        add(f"Starting from each fold's coarse powers, every stat power is refined in steps of {FINE_STAT_STEP} within "
            f"±{FINE_STAT_STEP * FINE_STAT_HALF:g}, and p in steps of {FINE_P_STEP} within ±{FINE_P_STEP * FINE_P_HALF:g}. "
            "A window re-centres when its best value sits on an edge, so powers stuck at the coarse grid's limits "
            f"(0.25, 3) can move, down to a floor of {MIN_POWER}. This is nested inside each training fold again. "
            "**Decision rule:** powers are kept only if the better of coarse or fine beats linear stats by more "
            "than one SE, and then whichever of the two is lower.")
        add("")
        add("**Note on cavalry.** Cavalry error is already low, about 7.7% MAPE with linear stats. If neither the "
            "coarse nor the fine search beats linear stats by more than one SE, the power hypothesis is **dropped "
            "for cavalry**, and cavalry stays linear in its stats.")
        add("")
        rows = []
        for arm, pw in res.powers.items():
            fine = pw.fine
            se = pw.base.se("mae")
            rows.append([arm, f1(pw.base.mean("mae")), f1(pw.nested.mean("mae")), f1(fine.nested.mean("mae")),
                         f"{fine.nested.mean('mae') - pw.nested.mean('mae'):+.2f}",
                         f"{min(fine.nested.mean('mae'), pw.nested.mean('mae')) - pw.base.mean('mae'):+.2f}",
                         f2(se), f1(fine.nested.mean("mape")), f"**{fine.choice}**"])
        L += table(["arm", "MAE linear stats", "MAE coarse (nested)", "MAE fine (nested)", "fine − coarse",
                    "best powers − linear", "1 SE (linear)", "MAPE fine", "choice"], rows)
        add("")
        add("Fine powers (full-data refinement, with the range across the 5 training folds). Coarse full-data "
            "values in brackets.")
        add("")
        rows = []
        for stat in power_key_order(res) + ["size power p"]:
            row = [stat]
            for arm, pw in res.powers.items():
                fine = pw.fine
                if stat == "size power p":
                    full, folds, coarse = fine.full_p, [p for _, p in fine.fold_powers], pw.full_p
                elif stat in fine.full_powers:
                    full = fine.full_powers[stat]
                    folds = [powers.get(stat, 1.0) for powers, _ in fine.fold_powers]
                    coarse = pw.full_powers.get(stat, 1.0)
                else:
                    row.append("—")
                    continue
                row.append(f"{full:g} ({min(folds):g} … {max(folds):g}) [{coarse:g}]")
            rows.append(row)
        L += table(["stat"] + [f"{arm}: fine (folds) [coarse]" for arm in res.powers], rows)
        add("")
        add("**Local CV curves.** Each power is varied over its fine window around the full-data fine solution, "
            "with the others held there, and the power 1 / p = 1 is also scored. *Within 1 SE* is the span of "
            "values whose CV MAE is within one SE of that curve's minimum. A wide span means the exponent is "
            "poorly pinned down. *Edge* means the span reaches the window edge, so the best value may lie "
            "further out. The curves hold the other powers at full-data values, so they are slightly "
            "optimistic: read them for shape, not accuracy.")
        add("")
        for arm, pw in res.powers.items():
            add(f"#### {arm}")
            add("")
            rows = []
            for prof in pw.fine.profiles:
                rows.append([prof["name"], f"{prof['center']:g}", f"{prof['best']:g}", f1(prof["best_mae"]),
                             f"{prof['lo']:g} … {prof['hi']:g}", "yes" if prof["edge"] else "—",
                             f1(prof["at_center"]), f1(prof["at_linear"]),
                             f"{prof['at_linear'] - prof['best_mae']:+.2f}"])
            L += table(["power", "fine value", "CV-best", "CV MAE", "within 1 SE", "edge", "MAE at fine value",
                        "MAE at 1 (linear)", "linear − best"], rows)
            add("")

    # ---- 8. Final accuracy
    add("## 8. Final model — accuracy on every slice")
    add("")
    rows = []
    for (arm, side), sl in slices.items():
        b, fin, rf, rfs = sl.runs["baseline"], sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
        fc = sl.runs.get("FC")
        rows.append([arm, side, pm(b, "mae", f1), pm(fin, "mae", f1), pm(fin, "mape", f1), pm(fin, "r2", f3),
                     f1(rf.mean("mae")), f1(rfs.mean("mae")), pm(fc, "mae", f1) if fc else "—",
                     f1(fin.full.c) if fin.spec.const else "—", fin.full.iterations])
    L += table(["arm", "side", "baseline MAE", "final MAE", "MAPE %", "R²", "+ per-arm m_f MAE",
                "+ shared m_f MAE", "faction × class MAE", "c (gold/unit)", "ALS iterations"], rows)
    add("")
    rows = []
    for (arm, side), sl in slices.items():
        run = sl.runs["final"]
        oof = run.oof[np.isfinite(run.oof)]
        worst = int(np.nanargmin(run.oof))
        u = sl.units[worst]
        rows.append([arm, side, int((oof <= 0).sum()), int((oof < 20).sum()),
                     f"{u.unit_class}, {u.n:g} models / {u.guns:g} guns, cost {u.cost} → {run.oof[worst]:.1f}"])
    add("**Where the model breaks down** (out-of-fold predictions):")
    add("")
    L += table(["arm", "side", "predictions ≤ 0", "predictions < 20", "lowest prediction"], rows)
    add("")
    add("### Packing vs unit size")
    add("")
    rows = []
    for arm, p in res.packing.items():
        for label, run, note in p["runs"]:
            rows.append([arm, f"{p['corr']:+.3f}", label, pm(run, "mae", f1), note or "—"])
    L += table(["arm", "corr(rank_depth, models)", "variant", "MAE (gold)", "fitted multiplier"], rows)
    add("")

    # ---- 9. Coefficients
    add("## 9. Final model — coefficients")
    add("")
    add("Refit on all rows of each slice. Price = M × size^p × (b0 + β·f(x)) + c. β is in gold per size "
        "unit^p; where a stat has a power, its column is (stat / 100)^power.")
    add("")
    for arm in ARMS:
        runs = {side: slices[(arm, side)].runs["final"] for side in SIDES}
        names: list[str] = []
        for side in SIDES:
            for name in runs[side].names:
                if name not in names:
                    names.append(name)
        spec = res.final[arm]
        add(f"### {arm} — `{spec.describe()}`")
        add("")
        add("Reference levels (merged): " + ", ".join(f"{k} = `{v}`" for k, v in runs["merged"].references.items()))
        add("")
        rows = [["(b0)"] + [f2(runs[side].full.b0) for side in SIDES]]
        for name in names:
            label = f"`{name}`" + (f" ^{spec.power_of(name):g}" if spec.power_of(name) != 1.0 else "")
            rows.append([label] + [f2(runs[side].coef(name)) if name in runs[side].names else "—" for side in SIDES])
        if spec.const:
            rows.append(["c (gold per unit)"] + [f1(runs[side].full.c) for side in SIDES])
        L += table(["feature", "imperial", "coalition", "merged"], rows)
        add("")
        for side in SIDES:
            add(f"- Multipliers ({side}): {describe_factors(runs[side].full)}")
        add("")

    # ---- 10. Faction modifier
    add("## 10. Faction modifier — what's left once the final model is in")
    add("")
    rows = []
    for (arm, side), sl in slices.items():
        fin, rf, rfs = sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
        best = min((fin, rf, rfs), key=lambda run: run.mean("mae"))
        rows.append([arm, side] + [f"**{f1(run.mean('mae'))}**" if run is best else f1(run.mean("mae"))
                                   for run in (fin, rf, rfs)])
    L += table(["arm", "side", "MAE final", "MAE + per-arm m_f", "MAE + shared m_f"], rows)
    add("")
    stats = corps_resid_stats(res, "final")
    groups: dict[int, list[float]] = defaultdict(list)
    for f, _, _, median, _ in stats:
        groups[ratings[f]].append(median)
    rho = spearman([ratings[f] for f, *_ in stats], [median for _, _, _, median, _ in stats])
    add(f"**Is rating absorbed?** Spearman ρ(rating, corps median residual) = **{rho:+.2f}**.")
    add("")
    shared = res.shared_m["merged"]
    resid_of = {f: median for f, _, _, median, _ in stats}
    mods: dict[str, dict[str, float]] = defaultdict(dict)
    for arm in ARMS:
        for faction, m in slices[(arm, "merged")].runs["RF"].full.faction_m.items():
            mods[faction][arm] = m
    unit_count = Counter(u.faction for u in res.units)
    corps_of = {u.faction: u.corps for u in res.units}
    side_of_f = {u.faction: u.side for u in res.units}
    add("**Faction modifiers** (merged, full-data fit, sorted by shared `m_f`):")
    add("")
    rows = []
    for f in sorted(shared, key=lambda f: (-shared[f], f)):
        median = resid_of.get(f, float("nan"))
        rows.append([corps_of[f] + (" **(7. Poland)**" if f == POLAND else ""), f"`{f}`", ratings[f], side_of_f[f],
                     unit_count[f], f"**{shared[f]:.3f}**"] + [f"{mods[f][a]:.3f}" if a in mods[f] else "—" for a in ARMS] +
                    [f"{median:+.1f}%" if np.isfinite(median) else "—"])
    L += table(["corps", "faction", "rating", "side", "units", "shared m_f", "m_f infantry", "m_f cavalry",
                "m_f artillery", "median OOF resid (final)"], rows)
    add("")
    by_side = {s: [m for f, m in shared.items() if side_of_f[f] == s] for s in ("imperial", "coalition")}
    add("Shared `m_f` by side: " + ", ".join(f"{s} mean {np.mean(v):.3f}" for s, v in by_side.items()) + ".")
    add("")
    if res.fclass:
        L += fclass_report(res)

    # ---- 11. Transfer
    add("## 11. Transfer — one formula for both sides? (final model, side dropped)")
    add("")
    rows = []
    for (arm, direction), m in res.transfer.items():
        rows.append([arm, direction, f1(m["mae"]), f1(m["in_side_mae"]), f1(m["mape"]), f1(m["in_side_mape"]),
                     m["affected"], ", ".join(str(x) for x in m["unseen_ratings"]) or "—"])
    L += table(["arm", "direction", "MAE", "in-side CV MAE", "MAPE %", "in-side CV MAPE %",
                "test rows hit by unseen levels", "ratings absent from train"], rows)
    add("")

    # ---- 12. Poland
    add("## 12. 7. Poland (`ntw3_tow_c08_x8_048`)")
    add("")
    rows = [[arm, side, p["n"], f1(p["with"].mean("mae")), f1(p["without"].mean("mae")),
             f"{p['median_resid']:+.1f}%", f"{p['share_over']:.0f}%"] for (arm, side), p in res.poland.items()]
    L += table(["arm", "side", "Poland units", "MAE with", "MAE without", "Poland median resid %",
                "share above model"], rows)
    add("")
    if POLAND in shared:
        ranked = sorted(shared.values())
        rank = sum(v < shared[POLAND] for v in ranked) + 1
        peers = [shared[f] for f in shared if ratings[f] == ratings[POLAND] and f != POLAND]
        add(f"Poland's shared modifier: **{shared[POLAND]:.3f}**, rank {rank} of {len(ranked)} (1 = cheapest "
            f"relative to the model); rating-{ratings[POLAND]} peers {min(peers):.3f} … {max(peers):.3f}. Per arm: " +
            ", ".join(f"{a} {mods[POLAND][a]:.3f}" for a in ARMS if a in mods[POLAND]) + ".")
        add("")

    # ---- 13. Cost-effective units
    add("## 13. Cost-effective units")
    add("")
    add("Funds saved = the final model's fair price minus the actual price. The fair price is out-of-fold, "
        "and full-fit (†) for the few units pinned to train. Rating, side and the other multipliers are "
        "already part of the fair price, so these are bargains on top of the normal rating discount. "
        "Faction modifiers are deliberately left out, so corps that are cheap across the board show up. "
        "Identical rows are merged.")
    add("")
    for arm in ARMS:
        size_label = "guns" if res.final[arm].size == "guns" else "models"
        mape = slices[(arm, "merged")].runs["final"].mean("mape")
        top_abs, top_rel = bargains(res, arm)
        for title, items, bold in (("absolute", top_abs, "saved"), ("relative", top_rel, "rel")):
            add(f"### {arm} — {title} (typical model error {mape:.1f}%)")
            add("")
            rows = []
            for i, it in enumerate(items, 1):
                u = it["unit"]
                name = u.name.replace("|", "/") + (f" (×{it['count']})" if it["count"] > 1 else "") + (" †" if it["pinned"] else "")
                saved = f"{it['saved']:+,.0f}"
                rel = f"{it['rel']:.0f}%"
                rows.append([i, name, f"{u.corps} ({u.rating})", f"{size_of(u, res.final[arm].size):g}", f"{u.cost:,}",
                             f"{it['pred']:,.0f}", f"**{saved}**" if bold == "saved" else saved,
                             f"**{rel}**" if bold == "rel" else rel])
            L += table(["#", "unit", "corps (rating)", size_label, "cost", "model", "saved", "saved %"], rows)
            add("")

    # ---- 14. Staff
    add("## 14. Staff generals")
    add("")
    add(f"T3 (from the blind study, see `blind_ideas_report.md`): a starred general costs b·stars^q·({REF_RATING}/r), "
        "one without stars 1 gold; q on a 0.005 grid, b by least squares, fitted on starred generals.")
    add("")
    rows = []
    for side, ss_ in res.staff_slices.items():
        for key, run in ss_.runs.items():
            tag = " **(headline)**" if key == res.staff_head else ""
            rows.append([side, run.label + tag, pm(run, "mae", f1), pm(run, "mape", f1), pm(run, "r2", f3)])
    L += table(["side", "model", "MAE (gold)", "MAPE % (starred)", "R²"], rows)
    add("")
    merged = res.staff_slices["merged"]
    coef, _, _ = staff_full(merged.gens, res.staff_head)
    add(f"{res.staff_head} full-data fit (merged): " +
        ", ".join(f"{n} = {c:+.4g}" for n, c in zip(STAFF_RATING_NAMES[res.staff_head], coef)) + ".")
    add("")

    add("## 15. Next step: commander variants")
    add("")
    add("Commander variants (a general attached to a unit, `unit_class = general`, about 42% of ToW + Custom rows) "
        "are outside this model. The blind study (branch `blind-pricing-study`) prices them in a second stage from "
        "the regular price of the unit they lead: `price ≈ max(1, a·p_reg + b(stars)·10/N)`, one global set of 7 "
        "coefficients (a ≈ 0.9; b ≈ −60, −30, +20, +65, +120 for 0–4 stars), optionally with a per-army premium; "
        "in its CV that cut commander-row error from about 51 to 39 gold. With this model as stage 1 it is the "
        "immediate next extension.")
    add("")

    add("## 16. Follow-ups")
    add("")
    add("- `resolve_speed` in `tools/build_ntw3_army_builder_database.py` mislabels the camels as `L1`, and "
        "two other units are off by a tier against their name tags.")
    add("- The Ottoman 5-okka gun fires the 24-pdr shot (section 1); worth checking against the mod's weapon tables.")
    add("- `search_results.csv` lists every searched structure. `oof_predictions.csv` carries out-of-fold "
        "predictions plus the final model's full-fit prediction, for hand checks against `coefficients.csv`.")
    return L


if __name__ == "__main__":
    raise SystemExit(main())
