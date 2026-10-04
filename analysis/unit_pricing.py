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
import re
import sys
import time
from collections import Counter, defaultdict
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
    sorted (stat, a) pairs (absent = 1); `faction` adds a faction modifier."""
    linear: frozenset[str] = frozenset()
    mult: frozenset[str] = frozenset()
    const: bool = False
    extras: frozenset[str] = frozenset()
    size: str = "n"
    p: float = 1.0
    powers: tuple[tuple[str, float], ...] = ()
    faction: bool = False

    def power_of(self, stat: str) -> float:
        return dict(self.powers).get(stat, 1.0)

    def describe(self) -> str:
        lin = ", ".join(sorted(self.linear)) or "—"
        size = "models" if self.size == "n" else "guns"
        mul = " × ".join([f"{size}^{self.p:g}"] + sorted(self.mult))
        parts = [f"β·x + [{lin}]", f"× {mul}"]
        if self.const:
            parts.append("+ c")
        if self.extras:
            parts.append("extras: " + ", ".join(sorted(self.extras)))
        bent = [f"{s}^{a:g}" for s, a in self.powers if a != 1.0]
        if bent:
            parts.append("stat powers: " + ", ".join(bent))
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
    raise KeyError(var)


def build_design(units: Sequence[Unit], arm: str, *, linear: frozenset[str] = frozenset(),
                 extras: frozenset[str] = frozenset(), powers: dict[str, float] | None = None,
                 const_inside: bool = False, use_gs: bool = False) -> Design:
    """Per-size feature matrix f(x). The per-size constant b0 is the regression
    intercept, not a column. `linear` holds the candidate variables placed in the
    linear part; `extras` the ablation features; `powers` raise numeric stats to
    a power (stats stay additive); `const_inside` adds a c/n column (used only by
    the coverage design)."""
    powers = powers or {}
    columns: list[np.ndarray] = []
    names: list[str] = []
    dropped: list[str] = []
    references: dict[str, str] = {}

    def add(values: np.ndarray, name: str) -> None:
        columns.append(np.asarray(values, float))
        names.append(name)

    for column in NUMERIC:
        if column == "range" and "no_range" in extras:
            continue
        values = np.array([u.values[column] for u in units])
        if np.ptp(values) == 0:
            dropped.append(f"{column} (constant)")
            continue
        a = powers.get(column, 1.0)
        add(values ** a if a != 1.0 else values, column)

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
    if arm == "artillery":
        families.append(("shot", lambda u: u.shot))
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

    if arm == "artillery":
        # Crew per gun is fixed by type, so guns/n is a function of the class and
        # this column is always aliased (reported) — kept for the identity.
        add(np.array([u.guns / u.n for u in units]), "guns_per_model")
    if const_inside:
        add(np.array([1.0 / u.n for u in units]), "per_unit_const")

    X = np.column_stack(columns) if columns else np.zeros((len(units), 0))
    X, names, aliases = prune_aliases(X, names)
    return Design(X=X, names=names, references=references, dropped=dropped, aliases=aliases)


def design_for(spec: Spec, units: Sequence[Unit], arm: str) -> Design:
    return build_design(units, arm, linear=spec.linear, extras=spec.extras, powers=dict(spec.powers))


# --- Model --------------------------------------------------------------------

class PriceModel:
    """Per-size price y = cost/size = M·g·(b0 + β·f(x)) + c/size, where
    g = size^(p−1) carries the size power and M = Π_k m_k (one factor per
    variable in spec.mult; categorical factors have one m per level with the
    reference fixed at 1, rank_depth has m = 1 + δ·(rank_depth − median)).

    Fitted by alternating least squares on Σ (y − M·g·(b0 + β·f(x)) − c/size)²:
    the β/c step is exact least squares on the columns [M·g, M·g·X, 1/size];
    each factor step is a closed-form regression on y − c/size given everything
    else. Every step lowers the objective, which is asserted. A faction modifier,
    when asked for, is fitted afterwards on the scaled part:
    m_f = Σ (y − c/size)·q / Σ q², q = M·g·base.
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
        self.iterations = 0
        self.sse = float("nan")

    def _factor(self, var: str, values: np.ndarray) -> np.ndarray:
        if var in CATEGORICAL:
            table = self.levels[var]
            return np.array([table.get(v, 1.0) for v in values.tolist()])
        return 1 + self.delta[var] * (values - self.refs[var])

    def fit(self, X: np.ndarray, y: np.ndarray, inv: np.ndarray, g: np.ndarray,
            fvals: dict[str, np.ndarray], factions: np.ndarray) -> "PriceModel":
        mult = sorted(self.spec.mult)
        codes: dict[str, tuple[np.ndarray, list]] = {}
        for var in mult:
            values = fvals[var]
            if var in CATEGORICAL:
                levels = sorted(set(values.tolist()), key=str)
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
            Z = [scale[:, None], scale[:, None] * X] + ([inv[:, None]] if self.spec.const else [])
            coef, *_ = np.linalg.lstsq(np.hstack(Z), y, rcond=None)
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
                if var in CATEGORICAL:
                    code, levels = codes[var]
                    numerator = np.bincount(code, weights=target * q, minlength=len(levels))
                    denominator = np.bincount(code, weights=q * q, minlength=len(levels))
                    m = np.divide(numerator, denominator, out=np.ones(len(levels)), where=denominator > 0)
                    m[levels.index(self.refs[var])] = 1.0
                    self.levels[var] = dict(zip(levels, m.tolist()))
                    factor[var] = m[code]
                else:
                    d = fvals[var] - self.refs[var]
                    denominator = float(((d * q) ** 2).sum())
                    self.delta[var] = float(((target - q) * d * q).sum()) / denominator if denominator else 0.0
                    factor[var] = 1 + self.delta[var] * d
            M = np.prod([factor[var] for var in mult], axis=0) if mult else np.ones(len(y))
            sse = float(((y - M * base - self.c * inv) ** 2).sum())
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
                self.faction_m[faction] = float((target[mask] * q[mask]).sum() / (q[mask] ** 2).sum())
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
        return scaled, self.c * inv

    def predict(self, X, inv, g, fvals, factions) -> np.ndarray:
        scaled, const = self.parts(X, inv, g, fvals, factions)
        return scaled + const

    def unseen(self, fvals: dict[str, np.ndarray], factions: np.ndarray) -> int:
        """Test rows predicted with a fallback multiplier of 1 (level/faction not in training)."""
        bad = np.zeros(len(factions), bool)
        for var in self.spec.mult:
            if var in CATEGORICAL:
                bad |= np.array([v not in self.levels[var] for v in fvals[var].tolist()])
        if self.spec.faction:
            bad |= np.array([f not in self.faction_m for f in factions])
        return int(bad.sum())

    def n_params(self, X: np.ndarray) -> int:
        count = 1 + X.shape[1] + (1 if self.spec.const else 0)
        for var in self.spec.mult:
            count += len(self.levels[var]) - 1 if var in CATEGORICAL else 1
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
                  groups: np.ndarray, n_seeds: int) -> SplitPlan:
    """Try `n_seeds` assignments; keep the one with zero coverage violations and
    the most uniform spread of `balance` keys across test folds."""
    pinned, pinned_labels = pinned_groups(C, groups, names)
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
                      for var in ("rating", "training", "drill", "side", "rank_depth", "size")})


def data_for(spec: Spec, units: Sequence[Unit]) -> SliceData:
    return slice_data(units, spec.size, spec.p)


def sub(fvals: dict[str, np.ndarray], index: np.ndarray) -> dict[str, np.ndarray]:
    return {k: v[index] for k, v in fvals.items()}


def fit_on(spec: Spec, design: Design, d: SliceData, rows: np.ndarray) -> PriceModel:
    return PriceModel(spec).fit(design.X[rows], d.y[rows], d.inv[rows], d.g[rows], sub(d.fvals, rows), d.factions[rows])


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
        sum(len(set(d.fvals[v].tolist())) - 1 if v in CATEGORICAL else 1 for v in spec.mult))
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


def make_slice(arm: str, side: str, units: list[Unit], n_seeds: int) -> Slice:
    rich = rich_design(units, arm)
    groups = group_ids(rich.X, [u.n for u in units])
    strata = strata_for(units, groups)
    balance = np.array([u.faction for u in units])
    plan = search_splits(rich.X, rich.names, strata, balance, groups, n_seeds)
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


# --- Stat powers (nested coordinate descent) ----------------------------------

def descend_powers(spec: Spec, units: Sequence[Unit], arm: str, rows: np.ndarray) -> tuple[dict[str, float], float, int]:
    """Coordinate descent on the training SSE (per-size space, the model's own
    objective) over one power per numeric stat and the size power p.

    Each stat's power is tried on POWER_GRID with the others held, then p on a
    0.05 grid within ±P_WINDOW of the current p; up to MAX_PASSES passes, stopping
    when a full pass changes nothing. Returns (powers, p, passes used)."""
    stats = [s for s in NUMERIC if s in design_for(spec, units, arm).names]
    powers = {s: spec.power_of(s) for s in stats}
    p = spec.p
    designs: dict[tuple, Design] = {}
    datas: dict[float, SliceData] = {}

    def sse(trial: dict[str, float], p_trial: float) -> float:
        key = tuple(sorted(trial.items()))
        design = designs.get(key)
        if design is None:
            design = designs[key] = build_design(units, arm, linear=spec.linear, extras=spec.extras, powers=trial)
        d = datas.get(p_trial)
        if d is None:
            d = datas[p_trial] = slice_data(units, spec.size, p_trial)
        return fit_on(replace(spec, p=p_trial), design, d, rows).sse

    current = sse(powers, p)
    for passes in range(1, MAX_PASSES + 1):
        changed = False
        for s in stats:
            for a in POWER_GRID:
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
    nested: CVRun                     # powers + p fitted inside each training fold
    fold_powers: list[tuple[dict[str, float], float]]
    full_powers: dict[str, float]
    full_p: float
    kept: bool


def nested_powers(spec: Spec, sl: Slice, base: CVRun) -> PowerResult:
    units, arm = sl.units, sl.arm
    cost = np.array([u.cost for u in units], float)
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics, fold_powers = [], []
    for k, (train, test) in enumerate(sl.plan.folds):
        powers, p, _ = descend_powers(spec, units, arm, train)
        fold_powers.append((powers, p))
        fitted = with_powers(spec, powers, p)
        design, d = design_for(fitted, units, arm), data_for(fitted, units)
        model = fit_on(fitted, design, d, train)
        pred = predict_total(model, design, d, test)
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(metrics(cost[test], pred, d.size[test]))
    nested = CVRun("stat powers + p, fitted inside each training fold", fold_metrics, oof, oof_fold, spec)
    full_powers, full_p, _ = descend_powers(spec, units, arm, np.arange(len(units)))
    kept = nested.mean("mae") < base.mean("mae") - base.se("mae")
    return PowerResult(base, nested, fold_powers, full_powers, full_p, kept)


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


# --- Staff generals (unchanged model family) ----------------------------------

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
}


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

    return {
        "S1": run("S1: a + b·stars (free constant)", s1),
        "S2q": run("S2q: 1 + b·stars + q·stars² (no rating/faction)", s2_quadratic),
        "S3q": run("S3q: 1 + b_f·stars + q·stars² (faction, no rating)", s3_quadratic),
        "T1": run("T1: 1 + (b + γ·(r−8))·stars + q·stars²", rating_model("T1", False)),
        "T2": run("T2: 1 + (1 + δ·(r−8))·(b·stars + q·stars²), free", rating_model("T2", False)),
        "TF1": run("TF1: T1 + faction modifier", rating_model("T1", True)),
        "TF2": run("TF2: T2 + faction modifier", rating_model("T2", True)),
    }


def staff_full(gens: Sequence[Staff], form: str) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    stars = np.array([g.stars for g in gens], float)
    cost = np.array([g.cost for g in gens], float)
    factions = np.array([g.faction for g in gens])
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
    elapsed: float = 0.0


def log(message: str, started: float) -> None:
    print(f"[{time.time() - started:5.0f}s] {message}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500, help="split seeds to search (default 500)")
    parser.add_argument("--linear", action="store_true",
                        help="fully linear run: size = models, p = 1, linear stats (no size or stat powers)")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default analysis/output)")
    args = parser.parse_args()
    global OUT_DIR
    if args.out is not None:
        OUT_DIR = args.out.resolve()
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

    # 4. Stat powers, nested CV.
    powers: dict[str, PowerResult] = {}
    final: dict[str, Spec] = dict(pre_power) if args.linear else {}
    for arm in ARMS if not args.linear else ():
        sl = slices[(arm, "merged")]
        base = cv_spec(pre_power[arm], sl.units, sl.plan.folds, arm, full_fit=False, label="final structure, linear stats")
        powers[arm] = nested_powers(pre_power[arm], sl, base)
        pw = powers[arm]
        final[arm] = with_powers(pre_power[arm], pw.full_powers, pw.full_p) if pw.kept else pre_power[arm]
        log(f"powers    {arm:9} base {base.mean('mae'):.2f} nested {pw.nested.mean('mae'):.2f} kept={pw.kept}; "
            f"final [{final[arm].describe()}]", started)

    # 5. Final model on every slice, baseline, faction modifiers.
    for arm in ARMS:
        for side in SIDES:
            sl = slices[(arm, side)]
            spec = final[arm] if side == "merged" else side_spec(final[arm])
            sl.runs["baseline"] = cv_baseline(sl.units, sl.plan.folds)
            sl.runs["final"] = cv_spec(spec, sl.units, sl.plan.folds, arm, label="final model")
            sl.runs["RF"] = cv_spec(replace(spec, faction=True), sl.units, sl.plan.folds, arm,
                                    label="final × per-arm faction modifier")
    shared_m: dict[str, dict[str, float]] = {}
    for side in SIDES:
        runs, shared_m[side] = shared_faction_runs(slices, side, final)
        for arm in ARMS:
            slices[(arm, side)].runs["RFs"] = runs[arm]
    log("final models and faction modifiers done", started)

    # 5b. Packing vs unit size on the final model.
    packing: dict[str, dict] = {}
    for arm in ARMS:
        sl = slices[(arm, "merged")]
        spec = final[arm]
        rd = np.array([u.rank_depth for u in sl.units])
        n = np.array([u.n for u in sl.units])
        variants = [("final model", spec), ("+ size multiplier", replace(spec, mult=spec.mult | {"size"}))]
        if "rank_depth" in spec.mult | spec.linear:
            no_rd = replace(spec, mult=spec.mult - {"rank_depth"}, linear=spec.linear - {"rank_depth"})
            variants.append(("rank_depth removed", no_rd))
        else:
            variants.append(("+ rank_depth multiplier", replace(spec, mult=spec.mult | {"rank_depth"})))
        runs = []
        for label, variant in variants:
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
    staff_head = min(("T1", "T2"), key=lambda k: staff_slices["merged"].runs[k].mean("mae"))
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
                  linear=args.linear)
    res.elapsed = time.time() - started
    write_outputs(res)
    log(f"done → {OUT_DIR.relative_to(ROOT)}", started)
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
            for key in ("final", "RF"):
                run = sl.runs[key]
                model, spec = run.full, run.spec
                refs = "reference levels: " + "; ".join(f"{k}={v}" for k, v in run.references.items())
                writer.writerow([arm, side, key, "size", spec.size, "models = men_raw/2" if spec.size == "n" else "guns"])
                writer.writerow([arm, side, key, "size power p", f"{spec.p:g}", "price ∝ size^p"])
                for stat, a in spec.powers:
                    writer.writerow([arm, side, key, f"stat power {stat}", f"{a:g}", "the β column is stat^power"])
                writer.writerow([arm, side, key, "(intercept: per-size constant b0)", f"{model.b0:.10g}",
                                 spec.describe() + " | " + refs])
                for name, coef in zip(run.names, model.beta):
                    writer.writerow([arm, side, key, name, f"{coef:.10g}", "gold per size unit^p"])
                if spec.const:
                    writer.writerow([arm, side, key, "c (per unit, outside the multiplier)", f"{model.c:.10g}", "gold per unit"])
                for var in sorted(spec.mult):
                    if var in CATEGORICAL:
                        for level, m in sorted(model.levels[var].items(), key=lambda t: str(t[0])):
                            writer.writerow([arm, side, key, f"multiplier {var}={level}", f"{m:.10g}",
                                             f"reference {model.refs[var]}"])
                    else:
                        writer.writerow([arm, side, key, f"multiplier {var} δ", f"{model.delta[var]:.10g}",
                                         f"m = 1 + δ·({var} − {model.refs[var]:g})"])
                for faction, m in sorted(model.faction_m.items()):
                    writer.writerow([arm, side, key, f"faction modifier {faction}", f"{m:.10g}",
                                     "per-arm; multiplies the scaled part"])
        for side, mods in res.shared_m.items():
            for faction, m in sorted(mods.items()):
                writer.writerow(["all arms", side, "RFs", f"faction modifier {faction}", f"{m:.10g}",
                                 "one per corps across arms; multiplies each arm's scaled part"])
        for side, ss in res.staff_slices.items():
            for form in ("T1", "T2"):
                coef, _, fm = staff_full(ss.gens, form)
                for name, c in zip(STAFF_RATING_NAMES[form], coef):
                    writer.writerow(["staff", side, form, name, f"{c:.10g}", "cost = 1 + …; r − 8"])
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
                         "oof_final", "oof_final_faction", "oof_final_faction_shared",
                         "resid_pct_final", "full_fit_pred_final"])
        cell = lambda v: "" if not np.isfinite(v) else f"{v:.3f}"   # NaN = pinned to train
        for (arm, side), sl in res.slices.items():
            fin, rf, rfs = sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
            full_pred = full_fit_prices(fin, sl.units, arm)
            for i, u in enumerate(sl.units):
                resid = (u.cost - fin.oof[i]) / fin.oof[i] * 100 if np.isfinite(fin.oof[i]) else np.nan
                writer.writerow([arm, side, u.key, u.faction, u.corps, u.side, u.rating, u.unit_class,
                                 "DR" if u.is_camel else u.speed, f"{u.n:g}", f"{u.guns:g}", u.cost,
                                 fin.oof_fold[i] or "", cell(fin.oof[i]), cell(rf.oof[i]), cell(rfs.oof[i]),
                                 cell(resid), f"{full_pred[i]:.3f}"])
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
                                 cell(rate.oof[i]), cell(rf.oof[i]), "", cell(resid), f"{full_p[i]:.3f}"])


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
    for arm in ARMS:
        sl = slices[(arm, "merged")]
        b, f_, r_, s_ = sl.runs["baseline"], sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
        rows.append([arm] + [f"{f1(run.mean('mape'))}% / {f1(run.mean('mae'))}"
                             for run in (b, res.regression[arm], f_, r_, s_)] +
                    [f3(f_.mean("r2")), f"`{res.final[arm].describe()}`"])
    L += table(["arm", "baseline", "previous", "final", "final + per-arm faction", "final + shared faction",
                "R² final", "final structure"], rows)
    add("")
    ss = res.staff_slices["merged"]
    add(f"Staff generals (merged, unchanged model family): {res.staff_head} MAE "
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
    add("## 7. Stat powers")
    add("")
    if res.linear:
        add("Not fitted in the fully linear run: every stat enters β·x linearly.")
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
        for stat in list(NUMERIC) + ["size power p"]:
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

    # ---- 8. Final accuracy
    add("## 8. Final model — accuracy on every slice")
    add("")
    rows = []
    for (arm, side), sl in slices.items():
        b, fin, rf, rfs = sl.runs["baseline"], sl.runs["final"], sl.runs["RF"], sl.runs["RFs"]
        rows.append([arm, side, pm(b, "mae", f1), pm(fin, "mae", f1), pm(fin, "mape", f1), pm(fin, "r2", f3),
                     f1(rf.mean("mae")), f1(rfs.mean("mae")), f1(fin.full.c) if fin.spec.const else "—",
                     fin.full.iterations])
    L += table(["arm", "side", "baseline MAE", "final MAE", "MAPE %", "R²", "+ per-arm m_f MAE",
                "+ shared m_f MAE", "c (gold/unit)", "ALS iterations"], rows)
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
        "unit^p; where a stat has a power, its column is stat^power.")
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
    add("## 14. Staff generals (model family unchanged)")
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
        ", ".join(f"{n} = {c:+.2f}" for n, c in zip(STAFF_RATING_NAMES[res.staff_head], coef)) + ".")
    add("")

    add("## 15. Follow-ups")
    add("")
    add("- `resolve_speed` in `tools/build_ntw3_army_builder_database.py` mislabels the camels as `L1`, and "
        "two other units are off by a tier against their name tags.")
    add("- The Ottoman 5-okka gun fires the 24-pdr shot (section 1); worth checking against the mod's weapon tables.")
    add("- `search_results.csv` lists every searched structure. `oof_predictions.csv` carries out-of-fold "
        "predictions plus the final model's full-fit prediction, for hand checks against `coefficients.csv`.")
    return L


if __name__ == "__main__":
    raise SystemExit(main())
