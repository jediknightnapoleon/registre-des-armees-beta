"""Natural experiment: what sets Army Corps (AC) versus Theatre-of-War (ToW) prices.

Step 4 of the AC pricing study (`analysis/AC_STUDY_PLAN.md`).

**The question.** Every one of the 12 032 ToW rows is a copy of an AC unit: strip
`_tow_<id>` from the ToW unit key and look the result up in the row's
`source_corps_faction_key`. Stats, size, flags, stars and cap are identical in
every pair; only the price (`multiplayer_cost`) and the division/brigade tags
differ. So the pair price ratio is a controlled experiment on *how the game's
price tables treat the same unit in two modes*. To first order
P_ToW = P_AC x N_AC/N_ToW x 0.91 (N = the corps number). This script explains
the residual

    r = log(P_ToW / P_AC) - log(N_AC / N_ToW)

for regular units first, then commanders and staff generals, by testing a list
of hypotheses (formation rebates, side/class/training/size/speed/price level, the
ToW corps, price rounding, the N slope, patch history, and the AC corps' premium
over a stats-only "fair" price), then builds the most compact readable rule for
P_ToW given P_AC and applies it to the 17 AC corps that have no ToW copy.

**Method.**
- Pairs: built from `data/generated/ntw3_units_analysis.csv`; corps numbers from
  `display_rating` in `data/generated/army_corps_catalog.csv`. A commander's class
  is its regular base unit's class.
- Variance decomposition: each grouping or predictor is fitted as a sparse
  one-hot ridge (alpha = 1, i.e. group means shrunk toward their parent) plus any
  continuous terms. Reported: in-sample R2 (plain group means / OLS), 10-fold CV
  R2 over units, and leave-corps-out CV R2 (10 folds grouped by source AC corps),
  the test that matters for corps with no pairs.
- Rebates: the game's formation rebate ((n - 1)% off a completed group of total
  cap n; a full division replaces its brigades' rebates; support divisions earn
  nothing) computed with `tools/army_builder_rules.py`
  (`build_roster_totals`, `group_discount`, `support_divisions`), as the app does.
- "Fair" price: a self-contained stats-only ridge model of log(P x N / 8), trained
  on ToW regular prices (out of fold by source AC corps for paired units). An AC
  unit's premium e_A = log(P_AC x N_AC / 8) - fair. A second version trained on AC
  prices (log N free) guards against circularity. The full AC price model (step 2)
  will replace this proxy; the test here is provisional on it.
- Patch history: `source/tables/ntw3_land_units.tsv` ships duplicate keys whose
  later rows (inert in game; the first row is loaded) carry balance-edited costs.
  They are used to flag edited units and to see which version the ToW copy follows.
- Rules are scored by exact-match share (round(pred) == true), median and 90th
  percentile absolute % error, in sample and leave-corps-out.

Fixed seeds; numpy + scikit-learn only. Runs in about 4 minutes, single process.

Outputs (`analysis/output/ac/`):
  natural_experiment_pairs.csv     one row per pair with r and the final rules' fits
  natural_experiment_effects.csv   every hypothesis / grouping with R2, effect, verdict
  ac_only_tow_equivalent.csv       the 17 AC-only corps: model-based ToW-equivalent prices
  natural_experiment_report.md     findings

    py -3.13 analysis/experiments/ac_natural_experiment.py
"""

from __future__ import annotations

import csv
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Hashable, Iterable, Sequence

import numpy as np
from scipy import sparse
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import army_builder_rules as abr  # noqa: E402

UNITS_CSV = ROOT / "data" / "generated" / "ntw3_units_analysis.csv"
BUILDER_CSV = ROOT / "data" / "generated" / "ntw3_army_builder_units.csv"
CATALOG_CSV = ROOT / "data" / "generated" / "army_corps_catalog.csv"
LAND_UNITS_TSV = ROOT / "source" / "tables" / "ntw3_land_units.tsv"
OUT = ROOT / "analysis" / "output" / "ac"

SEED = 20261010
N_FOLDS = 10
RIDGE_ALPHA = 1.0
FAIR_ALPHA = 1.0
BOOT_REPS = 400
TOW_RE = re.compile(r"_tow_\d+")
COM_RE = re.compile(r"_com_\d+$")

NUM_STATS = ("accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense",
             "charge_bonus", "range", "projectile_damage", "guns")
FLAGS = ("can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "scares_enemies", "skirmish",
         "guard_mode", "can_snipe", "can_place_mines", "can_build_barricades", "pike_square")
TRAINING = ("elite", "well_trained", "trained", "poorly_trained", "mob")
ARMS = ("infantry", "cavalry", "artillery")


def log(msg: str) -> None:
    print(msg, flush=True)


def fnum(text: str) -> float:
    text = (text or "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def arm_of(unit_class: str) -> str:
    return unit_class.split("_")[0]


def is_imperial(corps_side: str) -> bool:
    return corps_side in ("empire", "tow_french_imperial")


# --------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------

@dataclass
class Pair:
    kind: str                     # regular / commander / staff
    ac: dict[str, str]
    tow: dict[str, str]
    unit_class: str               # a commander takes its base unit's class
    n_ac: int
    n_tow: int
    p_ac: int
    p_tow: int
    ac_name: str
    tow_name: str
    theatre: str
    edited_ac: bool               # AC key has superseded rows with another cost
    edited_tow: bool
    ac_costs_all: list[int]
    tow_costs_all: list[int]
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def acf(self) -> str:
        return self.ac["faction_key"]

    @property
    def twf(self) -> str:
        return self.tow["faction_key"]

    @property
    def side(self) -> str:
        return "imperial" if is_imperial(self.ac["corps_side"]) else "coalition"

    @property
    def tow_side(self) -> str:
        return "imperial" if is_imperial(self.tow["corps_side"]) else "coalition"

    @property
    def arm(self) -> str:
        return arm_of(self.unit_class)

    @property
    def campaign(self) -> str:
        return self.acf.split("_")[2]

    @property
    def xclass(self) -> str:
        return self.acf.split("_")[3]

    @property
    def stars(self) -> int:
        return int(fnum(self.ac["command_stars"]))

    @property
    def r(self) -> float:
        return math.log(self.p_tow / self.p_ac) - math.log(self.n_ac / self.n_tow)


def read_rows() -> list[dict[str, str]]:
    with UNITS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_catalog() -> dict[str, dict[str, str]]:
    with CATALOG_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return {row["faction_key"]: row for row in csv.DictReader(handle)}


def read_cost_history() -> dict[str, list[int]]:
    """Every multiplayer_cost a key carries in ntw3_land_units, in file order.

    The table ships duplicate keys; the game loads the first row and ignores later
    (balance-edited) ones (see resolve_first_occurrence in
    tools/build_ntw3_army_builder_database.py)."""
    history: dict[str, list[int]] = defaultdict(list)
    with LAND_UNITS_TSV.open(encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        handle.readline()
        key_i = header.index("key")
        cost_i = header.index("multiplayer_cost")
        for line in handle:
            values = line.rstrip("\n").split("\t")
            if len(values) > cost_i and values[cost_i].strip():
                history[values[key_i]].append(int(values[cost_i]))
    return history


def build_pairs(rows: list[dict[str, str]], catalog: dict[str, dict[str, str]],
                history: dict[str, list[int]]) -> list[Pair]:
    by_key = {(r["faction_key"], r["unit_key"]): r for r in rows}
    rating = {k: int(c["display_rating"]) for k, c in catalog.items() if c["display_rating"].strip().isdigit()}
    pairs: list[Pair] = []
    for tow in rows:
        if tow["faction_kind"] != "theatre_of_war":
            continue
        ac_key = TOW_RE.sub("", tow["unit_key"])
        ac = by_key[(tow["source_corps_faction_key"], ac_key)]
        if tow["is_general"] == "true":
            kind = "staff" if "_gen_staff_" in tow["unit_key"] else "commander"
        else:
            kind = "regular"
        unit_class = ac["unit_class"]
        if kind == "commander":
            base = by_key.get((ac["faction_key"], COM_RE.sub("", ac_key)))
            if base is not None:
                unit_class = base["unit_class"]
        a_hist = history.get(ac_key, [int(ac["base_mp_cost"])])
        t_hist = history.get(tow["unit_key"], [int(tow["base_mp_cost"])])
        pairs.append(Pair(
            kind=kind, ac=ac, tow=tow, unit_class=unit_class,
            n_ac=rating[ac["faction_key"]], n_tow=rating[tow["faction_key"]],
            p_ac=int(ac["base_mp_cost"]), p_tow=int(tow["base_mp_cost"]),
            ac_name=catalog[ac["faction_key"]]["army_corps_name"],
            tow_name=catalog[tow["faction_key"]]["army_corps_name"],
            theatre=catalog[ac["faction_key"]]["theatre_name"],
            edited_ac=len(set(a_hist)) > 1, edited_tow=len(set(t_hist)) > 1,
            ac_costs_all=a_hist, tow_costs_all=t_hist,
        ))
    return pairs


# --------------------------------------------------------------------------------
# Formation rebates (the game's Lua rule, through the app's Python port)
# --------------------------------------------------------------------------------

@dataclass(frozen=True)
class CorpsRebate:
    full_division_frac: float     # all non-support divisions complete: share of full roster cost saved
    full_brigade_frac: float      # all brigades complete (no division)
    division_size: dict[int, int]
    brigade_size: dict[tuple[int, int], int]
    support: frozenset[int]


def corps_rebates() -> dict[str, CorpsRebate]:
    cards = abr.load_unit_cards(BUILDER_CSV)
    by_faction: dict[str, list[abr.UnitCard]] = defaultdict(list)
    for card in cards:
        by_faction[card.faction_key].append(card)
    out: dict[str, CorpsRebate] = {}
    for faction, fcards in by_faction.items():
        if "_ac_" not in faction:
            continue
        divisions, brigades = abr.build_roster_totals(fcards, faction)
        total = sum(c.cap * c.mp_cost for c in fcards if not c.is_general)
        div_disc = sum(abr.group_discount(t) for t in divisions.values())
        brig_disc = sum(abr.group_discount(t) for t in brigades.values())
        out[faction] = CorpsRebate(
            full_division_frac=div_disc / total if total else 0.0,
            full_brigade_frac=brig_disc / total if total else 0.0,
            division_size={d: t.required_count for d, t in divisions.items()},
            brigade_size={b: t.required_count for b, t in brigades.items()},
            support=frozenset(abr.support_divisions(fcards, faction)),
        )
    return out


def unit_rebates(row: dict[str, str], info: CorpsRebate | None) -> tuple[float, float]:
    """(brigade rebate, division rebate) as fractions for the unit's own groups."""
    if info is None or not row["division_id"]:
        return 0.0, 0.0
    d = int(row["division_id"])
    b = int(row["brigade_id"]) if row["brigade_id"] else -1
    nd = info.division_size.get(d, 0)
    nb = info.brigade_size.get((d, b), 0)
    return (max(nb - 1, 0) / 100.0, max(nd - 1, 0) / 100.0)


# --------------------------------------------------------------------------------
# Stats-only "fair" price model (proxy for step 2's model)
# --------------------------------------------------------------------------------

class FairModel:
    """Ridge on standardised stats features, per arm and per class, with class,
    speed-code and side indicators. Target log(P x N / 8) (fixed 1/N, as the
    adopted ToW model) or log P with log N as a free feature."""

    def __init__(self, classes: Sequence[str], speeds: Sequence[str], free_n: bool) -> None:
        self.classes = list(classes)
        self.speeds = list(speeds)
        self.free_n = free_n
        self.mu: np.ndarray | None = None
        self.sd: np.ndarray | None = None
        self.model: Ridge | None = None

    def features(self, row: dict[str, str], n: int) -> np.ndarray:
        base = np.array([math.log(max(fnum(row["men_raw"]), 1.0))]
                        + [fnum(row[c]) for c in NUM_STATS]
                        + [1.0 if row[c] == "true" else 0.0 for c in FLAGS]
                        + [1.0 if row["unit_training_level"] == t else 0.0 for t in TRAINING])
        arm = arm_of(row["unit_class"])
        blocks = [base * (1.0 if arm == a else 0.0) for a in ARMS]
        blocks += [base * (1.0 if row["unit_class"] == c else 0.0) for c in self.classes]
        extra = ([1.0 if row["unit_class"] == c else 0.0 for c in self.classes]
                 + [1.0 if row["speed_code"] == s else 0.0 for s in self.speeds]
                 + [1.0 if is_imperial(row["corps_side"]) else 0.0])
        if self.free_n:
            extra.append(math.log(n))
        return np.concatenate(blocks + [np.array(extra)])

    def target(self, price: int, n: int) -> float:
        return math.log(price) if self.free_n else math.log(price * n / 8.0)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "FairModel":
        self.mu = X.mean(0)
        self.sd = X.std(0) + 1e-9
        self.model = Ridge(alpha=FAIR_ALPHA).fit((X - self.mu) / self.sd, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.model is not None and self.mu is not None and self.sd is not None
        return self.model.predict((X - self.mu) / self.sd)


def fair_log_price_at(model: FairModel, pred: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Model output -> log fair price at corps number n."""
    if model.free_n:
        return pred
    return pred - np.log(n / 8.0)


# --------------------------------------------------------------------------------
# Generic evaluation: sparse one-hot ridge + continuous terms
# --------------------------------------------------------------------------------

def one_hot(levels: Sequence[Hashable]) -> sparse.csr_matrix:
    index: dict[Hashable, int] = {}
    cols = np.array([index.setdefault(v, len(index)) for v in levels])
    return sparse.csr_matrix((np.ones(len(levels)), (np.arange(len(levels)), cols)),
                             shape=(len(levels), len(index)))


def design(factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None, n: int) -> sparse.csr_matrix:
    blocks = [one_hot(f) for f in factors]
    if conts is not None and conts.size:
        c = conts.reshape(n, -1)
        blocks.append(sparse.csr_matrix(c - c.mean(0)))
    if not blocks:
        return sparse.csr_matrix(np.zeros((n, 1)))
    return sparse.hstack(blocks).tocsr()


def ridge_fit_predict(X: sparse.csr_matrix, y: np.ndarray, train: np.ndarray, test: np.ndarray,
                      alpha: float) -> np.ndarray:
    model = Ridge(alpha=alpha, solver="lsqr", tol=1e-8, fit_intercept=True)
    model.fit(X[train], y[train])
    return model.predict(X[test])


def r2(y: np.ndarray, pred: np.ndarray) -> float:
    return float(1.0 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def unit_folds(n: int) -> list[tuple[np.ndarray, np.ndarray]]:
    return list(KFold(N_FOLDS, shuffle=True, random_state=SEED).split(np.arange(n)))


def corps_folds(groups: Sequence[str]) -> list[tuple[np.ndarray, np.ndarray]]:
    # GroupKFold is deterministic; shuffle group labels with the seed for balance.
    rng = np.random.default_rng(SEED)
    labels = sorted(set(groups))
    perm = {g: int(i) for g, i in zip(labels, rng.permutation(len(labels)))}
    codes = np.array([perm[g] for g in groups])
    return list(GroupKFold(N_FOLDS).split(np.arange(len(groups)), groups=codes))


def cv_predict(X: sparse.csr_matrix, y: np.ndarray, folds: list[tuple[np.ndarray, np.ndarray]],
               alpha: float = RIDGE_ALPHA) -> np.ndarray:
    pred = np.zeros_like(y)
    for train, test in folds:
        pred[test] = ridge_fit_predict(X, y, train, test, alpha)
    return pred


def in_sample_r2(factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None, y: np.ndarray) -> float:
    """Plain group means (one factor, no covariate) or near-OLS otherwise."""
    if len(factors) == 1 and (conts is None or not conts.size):
        sums: dict[Hashable, list[float]] = defaultdict(list)
        for k, v in zip(factors[0], y):
            sums[k].append(v)
        means = {k: float(np.mean(v)) for k, v in sums.items()}
        return r2(y, np.array([means[k] for k in factors[0]]))
    X = design(factors, conts, len(y))
    idx = np.arange(len(y))
    return r2(y, ridge_fit_predict(X, y, idx, idx, 1e-4))


def n_levels(factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None) -> int:
    k = sum(len(set(f)) for f in factors)
    if conts is not None and conts.size:
        k += conts.reshape(len(conts), -1).shape[1]
    return k


# --------------------------------------------------------------------------------
# Rule scoring
# --------------------------------------------------------------------------------

def score(true: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    pred_int = np.maximum(np.round(pred), 1)
    ape = np.abs(pred_int / true - 1.0) * 100
    return {
        "exact": float(np.mean(pred_int == true)),
        "within1": float(np.mean(np.abs(pred_int - true) <= 1)),
        "median_ape": float(np.median(ape)),
        "p90_ape": float(np.percentile(ape, 90)),
        "mae": float(np.mean(np.abs(pred_int - true))),
    }


def fmt_score(s: dict[str, float]) -> str:
    return (f"exact {100 * s['exact']:.1f}%, within 1 gold {100 * s['within1']:.1f}%, "
            f"median |err| {s['median_ape']:.1f}%, P90 {s['p90_ape']:.1f}%, MAE {s['mae']:.1f}")


# --------------------------------------------------------------------------------
# Effects table
# --------------------------------------------------------------------------------

@dataclass
class Effect:
    hypothesis: str
    kind: str
    test: str
    n_params: int | str
    effect: str
    r2_in: float | None
    r2_cv_unit: float | None
    r2_cv_corps: float | None
    verdict: str


def fmt(x: float | None, digits: int = 3) -> str:
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


class Evaluator:
    def __init__(self, y: np.ndarray, corps: Sequence[str]) -> None:
        self.y = y
        self.ufolds = unit_folds(len(y))
        self.cfolds = corps_folds(corps)

    def run(self, factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None = None,
            corps_cv: bool = True) -> tuple[float, float, float | None, int]:
        X = design(factors, conts, len(self.y))
        rin = in_sample_r2(factors, conts, self.y)
        rcv = r2(self.y, cv_predict(X, self.y, self.ufolds))
        rco = r2(self.y, cv_predict(X, self.y, self.cfolds)) if corps_cv else None
        return rin, rcv, rco, n_levels(factors, conts)


def slope_within(y: np.ndarray, x: np.ndarray, keys: Sequence[Hashable]) -> tuple[float, np.ndarray, np.ndarray]:
    idx: dict[Hashable, list[int]] = defaultdict(list)
    for i, k in enumerate(keys):
        idx[k].append(i)
    yd = y.copy()
    xd = x.copy()
    for ii in idx.values():
        ii_a = np.array(ii)
        yd[ii_a] -= y[ii_a].mean()
        xd[ii_a] -= x[ii_a].mean()
    den = float((xd * xd).sum())
    return (float((xd * yd).sum() / den) if den > 0 else float("nan")), yd, xd


def cluster_bootstrap_slope(y: np.ndarray, x: np.ndarray, keys: Sequence[Hashable],
                            clusters: Sequence[str], reps: int = BOOT_REPS) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    members: dict[str, list[int]] = defaultdict(list)
    for i, c in enumerate(clusters):
        members[c].append(i)
    names = sorted(members)
    est = []
    for _ in range(reps):
        pick = rng.integers(0, len(names), len(names))
        rows: list[int] = []
        new_keys: list[Hashable] = []
        for ci in pick:
            ii = members[names[ci]]
            rows.extend(ii)
            new_keys.extend(keys[i] for i in ii)
        rows_a = np.array(rows)
        b, _, _ = slope_within(y[rows_a], x[rows_a], new_keys)
        if not math.isnan(b):
            est.append(b)
    lo, hi = np.percentile(est, [2.5, 97.5])
    return float(lo), float(hi)


# --------------------------------------------------------------------------------
# Main analysis
# --------------------------------------------------------------------------------

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    catalog = read_catalog()
    history = read_cost_history()
    pairs = build_pairs(rows, catalog, history)
    rebates = corps_rebates()
    rating = {k: int(c["display_rating"]) for k, c in catalog.items() if c["display_rating"].strip().isdigit()}
    effects: list[Effect] = []
    report: dict[str, object] = {}

    kinds = Counter(p.kind for p in pairs)
    log(f"pairs: {dict(kinds)}")
    regular = [p for p in pairs if p.kind == "regular"]
    commanders = [p for p in pairs if p.kind == "commander" and p.p_ac > 1 and p.p_tow > 1]
    staff_all = [p for p in pairs if p.kind == "staff"]
    staff = [p for p in staff_all if p.p_ac > 1 and p.p_tow > 1]
    report["counts"] = dict(regular=len(regular), commander_all=kinds["commander"], commander=len(commanders),
                            staff_all=len(staff_all), staff=len(staff))
    side_mismatch = sum(1 for p in pairs if p.side != p.tow_side)
    report["side_mismatch"] = side_mismatch

    paired_ac = {p.acf for p in pairs}
    with_regulars = {r["faction_key"] for r in rows if r["is_general"] == "false"}
    ac_only = sorted(f for f in rating if "_ac_" in f and f not in paired_ac and f in with_regulars)
    report["ac_only"] = ac_only
    log(f"AC-only corps with units: {len(ac_only)}")

    # --- unit-level attributes ---------------------------------------------------
    for p in pairs:
        info = rebates.get(p.acf)
        brig, div = unit_rebates(p.ac, info)
        p.extra["brig_reb"] = brig
        p.extra["div_reb"] = div
        p.extra["corps_div_reb"] = info.full_division_frac if info else 0.0
        p.extra["corps_brig_reb"] = info.full_brigade_frac if info else 0.0

    # --- fair-price models -------------------------------------------------------
    reg_rows = [r for r in rows if r["is_general"] == "false" and r["unit_class"] != "artillery_fixed"]
    classes = sorted({r["unit_class"] for r in reg_rows})
    speeds = sorted({r["speed_code"] for r in reg_rows})
    tow_train = [r for r in reg_rows if r["faction_kind"] == "theatre_of_war"]
    fm_t = FairModel(classes, speeds, free_n=False)
    Xt = np.array([fm_t.features(r, rating[r["faction_key"]]) for r in tow_train])
    yt = np.array([fm_t.target(int(r["base_mp_cost"]), rating[r["faction_key"]]) for r in tow_train])
    gt = [r["source_corps_faction_key"] for r in tow_train]
    oof_t = np.zeros_like(yt)
    for train, test in corps_folds(gt):
        oof_t[test] = FairModel(classes, speeds, False).fit(Xt[train], yt[train]).predict(Xt[test])
    fair_t_full = FairModel(classes, speeds, False).fit(Xt, yt)
    fair_t_rmse = float(np.sqrt(np.mean((yt - oof_t) ** 2)))
    tow_oof = {(r["faction_key"], r["unit_key"]): v for r, v in zip(tow_train, oof_t)}

    ac_train = [r for r in reg_rows if r["faction_kind"] == "army_corps"]
    fm_a = FairModel(classes, speeds, free_n=True)
    Xa = np.array([fm_a.features(r, rating[r["faction_key"]]) for r in ac_train])
    ya = np.array([fm_a.target(int(r["base_mp_cost"]), rating[r["faction_key"]]) for r in ac_train])
    ga = [r["faction_key"] for r in ac_train]
    oof_a = np.zeros_like(ya)
    for train, test in corps_folds(ga):
        oof_a[test] = FairModel(classes, speeds, True).fit(Xa[train], ya[train]).predict(Xa[test])
    fair_a_full = FairModel(classes, speeds, True).fit(Xa, ya)
    fair_a_rmse = float(np.sqrt(np.mean((ya - oof_a) ** 2)))
    ac_oof = {(r["faction_key"], r["unit_key"]): v for r, v in zip(ac_train, oof_a)}
    report["fair_rmse"] = dict(tow=fair_t_rmse, ac=fair_a_rmse)
    log(f"fair model CV rmse(log): ToW-trained {fair_t_rmse:.3f}, AC-trained {fair_a_rmse:.3f}")

    # premium of each regular pair: e_A (AC price over ToW-fair at N_AC), e_T (ToW over ToW-fair)
    for p in regular:
        v = tow_oof.get((p.twf, p.tow["unit_key"]))
        va = ac_oof.get((p.acf, p.ac["unit_key"]))
        if v is None or va is None:
            # artillery_fixed (4 pairs): outside the fair model; premium set to 0 (on the curve)
            p.extra.update(fair_t=float("nan"), eA=0.0, eT=p.r, eA2=0.0, eT2=p.r)
            continue
        p.extra["fair_t"] = v  # log(fair x N / 8)
        p.extra["eA"] = math.log(p.p_ac * p.n_ac / 8.0) - v
        p.extra["eT"] = math.log(p.p_tow * p.n_tow / 8.0) - v
        # AC-trained fair: e_A2 = log P_AC - fairA(N_AC); e_T2 = log P_ToW - fairA(N_ToW)
        base = va - fair_a_full.model.coef_[-1] / fair_a_full.sd[-1] * math.log(p.n_ac)  # type: ignore[union-attr]
        slope_n = fair_a_full.model.coef_[-1] / fair_a_full.sd[-1]  # type: ignore[union-attr]
        p.extra["eA2"] = math.log(p.p_ac) - va
        p.extra["eT2"] = math.log(p.p_tow) - (base + slope_n * math.log(p.n_tow))
    report["fair_a_logN_coef"] = float(fair_a_full.model.coef_[-1] / fair_a_full.sd[-1])  # type: ignore[union-attr]

    def cell_mean(units: Sequence[Pair], key: Callable[[Pair], Hashable], val: str) -> dict[Hashable, float]:
        acc: dict[Hashable, list[float]] = defaultdict(list)
        for u in units:
            acc[key(u)].append(u.extra[val])
        return {k: float(np.mean(v)) for k, v in acc.items()}

    cell_eA = cell_mean(regular, lambda p: (p.acf, p.unit_class), "eA")
    corps_eA = cell_mean(regular, lambda p: p.acf, "eA")
    cell_eA2 = cell_mean(regular, lambda p: (p.acf, p.unit_class), "eA2")
    for p in regular:
        p.extra["eA_cell"] = cell_eA[(p.acf, p.unit_class)]
        p.extra["eA_corps"] = corps_eA[p.acf]
        p.extra["eA2_cell"] = cell_eA2[(p.acf, p.unit_class)]

    # =============================================================================
    # Regular units: hypotheses
    # =============================================================================
    y = np.array([p.r for p in regular])
    corps = [p.acf for p in regular]
    ev = Evaluator(y, corps)
    report["r_stats"] = dict(median=float(np.median(y)), mean=float(y.mean()), sd=float(y.std()),
                             factor=float(np.exp(np.median(y))))
    log(f"regular r: median {np.median(y):.4f} sd {y.std():.4f}")

    F = {
        "class": [p.unit_class for p in regular],
        "arm": [p.arm for p in regular],
        "side": [p.side for p in regular],
        "training": [p.ac["unit_training_level"] for p in regular],
        "speed": [p.ac["speed_code"] for p in regular],
        "cap": [p.ac["unit_cap"] for p in regular],
        "ac": corps,
        "tow": [p.twf for p in regular],
        "campaign": [p.campaign for p in regular],
        "xclass": [p.xclass for p in regular],
        "theatre": [p.theatre for p in regular],
        "pair_n": [(p.n_ac, p.n_tow) for p in regular],
        "edited": [(p.edited_ac, p.edited_tow) for p in regular],
    }
    cross = lambda *names: [tuple(F[n][i] for n in names) for i in range(len(regular))]  # noqa: E731
    F["side_class"] = cross("side", "class")
    F["ac_class"] = cross("ac", "class")
    F["tow_class"] = cross("tow", "class")
    F["campaign_class"] = cross("campaign", "class")
    F["xclass_class"] = cross("xclass", "class")
    F["ac_class_training"] = cross("ac", "class", "training")
    F["ac_class_speed"] = cross("ac", "class", "speed")
    F["ac_class_cap"] = cross("ac", "class", "cap")
    F["ac_brigade"] = [(p.acf, p.ac["division_brigade_code"]) for p in regular]
    F["ac_division"] = [(p.acf, p.ac["division_id"]) for p in regular]
    F["ac_class_division"] = [(p.acf, p.unit_class, p.ac["division_id"]) for p in regular]
    F["ac_class_brigade"] = [(p.acf, p.unit_class, p.ac["division_brigade_code"]) for p in regular]
    F["tow_class_towdiv"] = [(p.twf, p.unit_class, p.tow["division_id"]) for p in regular]
    F["ac_speed"] = cross("ac", "speed")
    log_pa = np.array([math.log(p.p_ac) for p in regular])
    log_men = np.array([math.log(max(fnum(p.ac["men_raw"]), 1.0)) for p in regular])
    lnr = np.array([math.log(p.n_ac / p.n_tow) for p in regular])

    def add(h: str, test: str, factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None = None,
            effect: str = "", verdict: str = "", corps_cv: bool = True, kind: str = "regular") -> tuple[float, float, float | None]:
        rin, rcv, rco, k = ev.run(factors, conts, corps_cv)
        effects.append(Effect(h, kind, test, k, effect, rin, rcv, rco, verdict))
        log(f"  {h:4s} {test:55s} k={k:5d} R2 in {rin:.3f} cv {rcv:.3f} lco {fmt(rco)}")
        return rin, rcv, rco

    res: dict[str, tuple[float, float, float | None]] = {}

    # H1 rebates ---------------------------------------------------------------
    for name, label in (("brig_reb", "unit's own brigade rebate (n_b - 1)%"),
                        ("div_reb", "unit's own division rebate (n_d - 1)%"),
                        ("corps_div_reb", "corps full-division rebate share"),
                        ("corps_brig_reb", "corps full-brigade rebate share")):
        x = np.array([math.log(1.0 - p.extra[name]) for p in regular])
        slope, icpt = np.polyfit(x, y, 1)
        corr = float(np.corrcoef(x, y)[0, 1])
        # fixed-slope test: ToW = AC x (1 - rebate) -> r = c + log(1 - rebate)
        c0 = float(np.mean(y - x))
        r2_fixed = r2(y, c0 + x)
        mean_reb = float(np.mean([p.extra[name] for p in regular]))
        res[name] = add("H1", label, [], x[:, None],
                        effect=(f"corr {corr:+.3f}; free slope {slope:+.2f} (rule predicts +1); "
                                f"slope fixed at 1: R2 {r2_fixed:+.3f}; mean rebate {100 * mean_reb:.1f}%"),
                        verdict="Rejected" if abs(corr) < 0.2 else "Partly")
        report[f"H1_{name}"] = dict(corr=corr, slope=float(slope), r2_fixed=r2_fixed, mean=mean_reb)
    # corps-level correlation
    cm = defaultdict(list)
    for p in regular:
        cm[p.acf].append(p)
    cr = np.array([np.mean([q.r for q in v]) for v in cm.values()])
    cx = np.array([math.log(1 - v[0].extra["corps_div_reb"]) for v in cm.values()])
    report["H1_corps_level_corr"] = float(np.corrcoef(cx, cr)[0, 1])
    report["H1_corps_div_pct"] = [float(v) for v in np.percentile([v[0].extra["corps_div_reb"] for v in cm.values()], [10, 50, 90])]

    # H2 unit attributes ---------------------------------------------------------
    res["class"] = add("H2", "class", [F["class"]], effect="", verdict="")
    res["side"] = add("H2", "side (imperial / coalition)", [F["side"]])
    res["side_class"] = add("H2", "side x class", [F["side_class"]])
    res["training"] = add("H2", "training level", [F["training"]])
    res["speed"] = add("H2", "speed code", [F["speed"]])
    res["size"] = add("H2", "size: log men", [], log_men[:, None])
    res["price"] = add("H2", "price level: log P_AC", [], log_pa[:, None])
    res["cap"] = add("H2", "unit cap", [F["cap"]])
    res["all_unit"] = add("H2", "side x class + training + speed + log men + log P_AC",
                          [F["side_class"], F["training"], F["speed"]], np.c_[log_men, log_pa])
    # interactions with the source corps
    res["ac"] = add("H2", "source AC corps", [F["ac"]], corps_cv=False)
    res["ac_class"] = add("H2", "source AC corps x class", [F["ac_class"]], corps_cv=False)
    res["ac_class_training"] = add("H2", "AC corps x class x training", [F["ac_class"], F["ac_class_training"]], corps_cv=False)
    res["ac_class_speed"] = add("H2", "AC corps x class x speed", [F["ac_class"], F["ac_class_speed"]], corps_cv=False)
    res["ac_class_cap"] = add("H2", "AC corps x class x cap", [F["ac_class"], F["ac_class_cap"]], corps_cv=False)
    res["ac_class_logp"] = add("H2", "AC corps x class + within-cell log P_AC slope", [F["ac_class"]], log_pa[:, None], corps_cv=False)
    res["ac_class_logmen"] = add("H2", "AC corps x class + within-cell log men slope", [F["ac_class"]], log_men[:, None], corps_cv=False)
    res["ac_division"] = add("H2", "AC corps x division", [F["ac_division"]], corps_cv=False)
    res["ac_brigade"] = add("H2", "AC corps x brigade", [F["ac_brigade"]], corps_cv=False)
    res["ac_class_division"] = add("H2", "AC corps x class x division", [F["ac_class"], F["ac_class_division"]], corps_cv=False)
    res["ac_class_brigade"] = add("H2", "AC corps x class x brigade", [F["ac_class"], F["ac_class_brigade"]], corps_cv=False)
    # within-cell slopes on log P and log men
    b_lp, yd, xd = slope_within(y, log_pa, F["ac_class"])
    b_lm, _, xm = slope_within(y, log_men, F["ac_class"])
    report["within_cell"] = dict(var=float(yd.var()), sd=float(yd.std()), slope_logp=b_lp, slope_logmen=b_lm,
                                 r2_logp=float(1 - ((yd - b_lp * xd) ** 2).sum() / (yd ** 2).sum()),
                                 r2_logmen=float(1 - ((yd - b_lm * xm) ** 2).sum() / (yd ** 2).sum()))

    # H3 ToW corps ---------------------------------------------------------------
    res["tow"] = add("H3", "ToW corps", [F["tow"]], corps_cv=False)
    res["tow_class"] = add("H3", "ToW corps x class", [F["tow_class"]])
    res["tow_class_plus_ac"] = add("H3", "ToW corps x class + source AC corps (additive)", [F["tow_class"], F["ac"]], corps_cv=False)
    res["tow_class_towdiv"] = add("H3", "ToW corps x class x ToW division", [F["tow_class"], F["tow_class_towdiv"]])

    # H4 rounding ----------------------------------------------------------------
    def mult_share(vals: Iterable[int], m: int) -> float:
        v = list(vals)
        return float(np.mean([x % m == 0 for x in v]))
    rounding = {}
    for nm, vals in (("AC regular", [p.p_ac for p in regular]), ("ToW regular", [p.p_tow for p in regular]),
                     ("AC commander", [p.p_ac for p in commanders]), ("ToW commander", [p.p_tow for p in commanders]),
                     ("AC staff", [p.p_ac for p in staff]), ("ToW staff", [p.p_tow for p in staff])):
        rounding[nm] = {m: mult_share(vals, m) for m in (2, 5, 10, 25)}
    report["rounding"] = rounding
    digits_ac = Counter(p.p_ac % 10 for p in regular)
    digits_tow = Counter(p.p_tow % 10 for p in regular)
    chi = lambda c: float(sum((c[d] - len(regular) / 10) ** 2 / (len(regular) / 10) for d in range(10)))  # noqa: E731
    report["last_digit_chi2"] = dict(ac=chi(digits_ac), tow=chi(digits_tow))
    # cell-factor quantisation (tight cells)
    cells: dict[Hashable, list[Pair]] = defaultdict(list)
    for p in regular:
        cells[(p.acf, p.unit_class)].append(p)
    tight_f = []
    for ps in cells.values():
        if len(ps) >= 3:
            lr = np.log([q.p_tow / q.p_ac for q in ps])
            if lr.std() <= 0.02:
                tight_f.append(float(np.exp(np.median(lr))) * ps[0].n_tow / ps[0].n_ac)
    tight_f_a = np.array(tight_f)
    grid = {step: float(np.mean(np.abs(tight_f_a / step - np.round(tight_f_a / step)))) for step in (0.05, 0.025, 0.01)}
    report["quantisation"] = dict(n=len(tight_f), grid=grid)
    # exact generating rule per cell: does one factor k reproduce every unit of the cell?
    exact_cells = {}
    for mode in ("round", "floor", "ceil"):
        ok_cells = 0
        ok_units = 0
        tot_cells = 0
        tot_units = 0
        for ps in cells.values():
            if len(ps) < 2:
                continue
            tot_cells += 1
            tot_units += len(ps)
            lo, hi = -1e9, 1e9
            for q in ps:
                if mode == "round":
                    a, b = (q.p_tow - 0.5) / q.p_ac, (q.p_tow + 0.5) / q.p_ac
                elif mode == "floor":
                    a, b = q.p_tow / q.p_ac, (q.p_tow + 1) / q.p_ac
                else:
                    a, b = (q.p_tow - 1) / q.p_ac, q.p_tow / q.p_ac
                lo, hi = max(lo, a), min(hi, b)
            if lo < hi:
                ok_cells += 1
                ok_units += len(ps)
        exact_cells[mode] = dict(cells=tot_cells, units=tot_units, exact_cells=ok_cells, exact_units=ok_units)
    report["exact_cells"] = exact_cells
    effects.append(Effect(
        "H4", "regular", "prices on multiples of 5 / 10 (AC, ToW)", 0,
        f"x5: AC {100 * rounding['AC regular'][5]:.1f}%, ToW {100 * rounding['ToW regular'][5]:.1f}% (chance 20%); "
        f"x10: {100 * rounding['AC regular'][10]:.1f}% / {100 * rounding['ToW regular'][10]:.1f}% (chance 10%); "
        f"last-digit chi2 {report['last_digit_chi2']['ac']:.1f} / {report['last_digit_chi2']['tow']:.1f} (9 df)",
        None, None, None, "Rejected: plain integers, no rounding"))
    effects.append(Effect(
        "H4", "regular", "cell factors F = k_cell x N_ToW/N_AC on a round grid (cells with sd <= 2%)", 0,
        f"{len(tight_f)} cells; mean distance to nearest 0.05 / 0.025 / 0.01 step = "
        f"{grid[0.05]:.3f} / {grid[0.025]:.3f} / {grid[0.01]:.3f} of a step (uniform 0.25)",
        None, None, None, "Rejected: no quantised factors"))
    er = exact_cells["round"]
    effects.append(Effect(
        "H4", "regular", "one exact k per AC corps x class cell, P_ToW = round/floor/ceil(P_AC x k)", "1 per cell",
        f"round: {er['exact_cells']}/{er['cells']} cells, {er['exact_units']}/{er['units']} units; floor: "
        f"{exact_cells['floor']['exact_units']} units; ceil: {exact_cells['ceil']['exact_units']} units",
        None, None, None, "Rejected: no exact per-cell generating rule"))
    # within-cell residual sd per AC corps (clean vs noisy corps)
    resid_by_corps: dict[str, list[float]] = defaultdict(list)
    cm_r = {k: float(np.mean([q.r for q in v])) for k, v in cells.items()}
    for p in regular:
        resid_by_corps[p.acf].append(p.r - cm_r[(p.acf, p.unit_class)])
    corps_sd = sorted((float(np.sqrt(np.mean(np.square(v)))), f"{catalog[k]['army_corps_name']} ({100 * float(np.sqrt(np.mean(np.square(v)))):.1f}%)")
                      for k, v in resid_by_corps.items() if len(v) >= 8)
    report["corps_within_sd"] = dict(p10=float(np.percentile([s for s, _ in corps_sd], 10)),
                                     median=float(np.median([s for s, _ in corps_sd])),
                                     p90=float(np.percentile([s for s, _ in corps_sd], 90)),
                                     cleanest=corps_sd[:3], noisiest=corps_sd[-3:])

    # H5 slope on log(N_AC / N_ToW) ---------------------------------------------
    y_raw = np.array([math.log(p.p_tow / p.p_ac) for p in regular])
    raw_slope = float(np.polyfit(lnr, y_raw, 1)[0])
    s_tow, _, _ = slope_within(y_raw, lnr, F["tow"])
    s_towc, _, _ = slope_within(y_raw, lnr, F["tow_class"])
    ci = cluster_bootstrap_slope(y_raw, lnr, F["tow_class"], corps)
    report["n_ratio"] = dict(r2=float(np.corrcoef(lnr, y_raw)[0, 1] ** 2), mean_lnr=float(lnr.mean()),
                             median_raw=float(np.exp(np.median(y_raw))), median_nratio=float(np.exp(np.median(lnr))),
                             share_cheaper=float(np.mean(y_raw < 0)))
    report["H5_regular"] = dict(raw=raw_slope, within_tow=s_tow, within_tow_class=s_towc, ci=ci)
    effects.append(Effect("H5", "regular", "slope of log(P_ToW/P_AC) on log(N_AC/N_ToW), within ToW corps x class",
                          1, f"slope {s_towc:.3f} (95% cluster-bootstrap CI {ci[0]:.3f}-{ci[1]:.3f}); raw {raw_slope:.3f}",
                          None, None, None,
                          "Not exactly 1" if not (ci[0] <= 1.0 <= ci[1]) else "Consistent with 1"))
    log(f"  H5 slope within ToW x class {s_towc:.3f} CI {ci}")

    # H6 patch history ------------------------------------------------------------
    res["campaign"] = add("H6", "campaign code (a03, b08, ...)", [F["campaign"]])
    res["campaign_class"] = add("H6", "campaign x class", [F["campaign"], F["campaign_class"]])
    res["xclass"] = add("H6", "faction-key x-class (x2-x8, r3-r7)", [F["xclass"]])
    res["xclass_class"] = add("H6", "x-class x class", [F["xclass"], F["xclass_class"]])
    res["theatre"] = add("H6", "AC theatre (catalog)", [F["theatre"]])
    res["pair_n"] = add("H6", "(N_AC, N_ToW) pair", [F["pair_n"]])
    res["edited"] = add("H6", "unit has superseded balance-edit rows (AC, ToW)", [F["edited"]])
    # do units with superseded rows deviate more; which version does the ToW copy follow?
    clean_cells: dict[Hashable, list[float]] = defaultdict(list)
    for p in regular:
        if not p.edited_ac and not p.edited_tow:
            clean_cells[(p.acf, p.unit_class)].append(math.log(p.p_tow / p.p_ac))
    cmed = {k: float(np.median(v)) for k, v in clean_cells.items() if len(v) >= 2}
    dev_clean = [abs(math.log(p.p_tow / p.p_ac) - cmed[(p.acf, p.unit_class)]) for p in regular
                 if (p.acf, p.unit_class) in cmed and not p.edited_ac and not p.edited_tow]
    dev_edit = [abs(math.log(p.p_tow / p.p_ac) - cmed[(p.acf, p.unit_class)]) for p in regular
                if (p.acf, p.unit_class) in cmed and p.edited_ac]
    first_closer = later_closer = 0
    for p in regular:
        k = (p.acf, p.unit_class)
        if k in cmed and p.edited_ac and not p.edited_tow:
            e0 = abs(math.log(p.p_tow / p.ac_costs_all[0]) - cmed[k])
            e1 = min(abs(math.log(p.p_tow / c) - cmed[k]) for c in p.ac_costs_all[1:])
            if e0 < e1:
                first_closer += 1
            else:
                later_closer += 1
    edited_campaigns = Counter(p.campaign for p in regular if p.edited_ac)
    effects.append(Effect(
        "H6", "regular", "superseded balance-edit rows: distance from the cell's median ratio", 0,
        f"edited units {100 * float(np.median(dev_edit)):.1f}% vs unedited {100 * float(np.median(dev_clean)):.1f}%; "
        f"ToW follows the live AC row in {first_closer} vs a superseded row in {later_closer} cases",
        None, None, None, "Edits add noise (1812 and 1814 campaigns only); ToW copies follow the live AC rows"))
    report["H6_edits"] = dict(n_edited_ac=sum(p.edited_ac for p in regular),
                              n_edited_both=sum(p.edited_ac and p.edited_tow for p in regular),
                              dev_clean=float(np.median(dev_clean)), dev_edit=float(np.median(dev_edit)),
                              first_closer=first_closer, later_closer=later_closer,
                              campaigns=dict(edited_campaigns))

    # H7 fair-price premium ------------------------------------------------------
    eA = np.array([p.extra["eA"] for p in regular])
    eT = np.array([p.extra["eT"] for p in regular])
    eA_cell = np.array([p.extra["eA_cell"] for p in regular])
    eA_corps = np.array([p.extra["eA_corps"] for p in regular])
    eA2 = np.array([p.extra["eA2"] for p in regular])
    eT2 = np.array([p.extra["eT2"] for p in regular])
    eA2_cell = np.array([p.extra["eA2_cell"] for p in regular])
    report["levels"] = dict(eA_mean=float(eA.mean()), eA_median=float(np.median(eA)),
                            eT_mean=float(eT.mean()), eT_median=float(np.median(eT)))

    def level_fit(keyf: Callable[[Pair], Hashable], a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float]:
        idx: dict[Hashable, list[int]] = defaultdict(list)
        for i, p in enumerate(regular):
            idx[keyf(p)].append(i)
        ga_ = np.array([a[v].mean() for v in idx.values()])
        gr_ = np.array([y[v].mean() for v in idx.values()])
        gb_ = np.array([b[v].mean() for v in idx.values()])
        w = np.array([len(v) for v in idx.values()], float)
        slope = float(np.polyfit(ga_, gr_, 1, w=np.sqrt(w))[0])
        pred = np.polyval(np.polyfit(ga_, gr_, 1, w=np.sqrt(w)), ga_)
        wr2 = float(1 - (w * (gr_ - pred) ** 2).sum() / (w * (gr_ - np.average(gr_, weights=w)) ** 2).sum())
        return slope, wr2, float(np.sqrt(np.average((ga_ - np.average(ga_, weights=w)) ** 2, weights=w))), \
            float(np.sqrt(np.average((gb_ - np.average(gb_, weights=w)) ** 2, weights=w)))

    # robustness: the committed adopted ToW model, stats only (oof_final, slice 'merged')
    adopted: dict[tuple[str, str], float] = {}
    oof_path = ROOT / "analysis" / "output" / "oof_predictions.csv"
    if oof_path.exists():
        with oof_path.open(encoding="utf-8-sig", newline="") as handle:
            for row_ in csv.DictReader(handle):
                if row_["slice"] == "merged" and row_["model"] != "staff" and row_["oof_final"]:
                    if float(row_["oof_final"]) > 0:
                        adopted[(row_["faction_key"], row_["unit_key"])] = float(row_["oof_final"])
    eA3 = np.full(len(regular), np.nan)
    eT3 = np.full(len(regular), np.nan)
    for i, p in enumerate(regular):
        s_ = adopted.get((p.twf, p.tow["unit_key"]))
        if s_ is not None:
            eT3[i] = math.log(p.p_tow / s_)
            eA3[i] = math.log(p.p_ac / (s_ * p.n_tow / p.n_ac))
    m3 = ~np.isnan(eA3)
    report["adopted_n"] = int(m3.sum())

    def level_fit_masked(keyf: Callable[[Pair], Hashable], a: np.ndarray, b: np.ndarray,
                         mask: np.ndarray) -> tuple[float, float, float, float]:
        idx: dict[Hashable, list[int]] = defaultdict(list)
        for i, p in enumerate(regular):
            if mask[i]:
                idx[keyf(p)].append(i)
        ga_ = np.array([a[v].mean() for v in idx.values()])
        gr_ = np.array([y[v].mean() for v in idx.values()])
        gb_ = np.array([b[v].mean() for v in idx.values()])
        w = np.array([len(v) for v in idx.values()], float)
        coef = np.polyfit(ga_, gr_, 1, w=np.sqrt(w))
        pred = np.polyval(coef, ga_)
        wr2 = float(1 - (w * (gr_ - pred) ** 2).sum() / (w * (gr_ - np.average(gr_, weights=w)) ** 2).sum())
        sd_a = float(np.sqrt(np.average((ga_ - np.average(ga_, weights=w)) ** 2, weights=w)))
        sd_b = float(np.sqrt(np.average((gb_ - np.average(gb_, weights=w)) ** 2, weights=w)))
        return float(coef[0]), wr2, sd_a, sd_b

    h7 = {}
    for lvl, keyf in (("unit", lambda p: (p.acf, p.ac["unit_key"])), ("cell", lambda p: (p.acf, p.unit_class)),
                      ("corps", lambda p: p.acf)):
        h7[lvl] = dict(tow_fair=level_fit(keyf, eA, eT), ac_fair=level_fit(keyf, eA2, eT2),
                       adopted=level_fit_masked(keyf, eA3, eT3, m3) if m3.any() else None)
    report["H7"] = h7
    res["eA_unit"] = add("H7", "AC premium over stats-fair price, unit (ToW-trained fair)", [], eA[:, None])
    res["eA_cell"] = add("H7", "AC premium, AC corps x class cell mean (ToW-trained fair)", [], eA_cell[:, None])
    res["eA_corps"] = add("H7", "AC premium, AC corps mean (ToW-trained fair)", [], eA_corps[:, None])
    res["eA_unit_cell"] = add("H7", "AC premium, unit + cell mean", [], np.c_[eA, eA_cell])
    res["eA2_cell"] = add("H7", "AC premium, cell mean (AC-trained fair, log N free)", [], eA2_cell[:, None])
    res["tow_class_eA_cell"] = add("H7", "ToW corps x class + AC premium cell mean", [F["tow_class"]], eA_cell[:, None])
    res["side_class_eA"] = add("H7", "side x class + log ratio slope + AC premium (unit, cell)",
                               [F["side_class"]], np.c_[lnr, eA, eA_cell])

    # =============================================================================
    # Rules for P_ToW given P_AC (regular)
    # =============================================================================
    pt = np.array([p.p_tow for p in regular], float)
    pa = np.array([p.p_ac for p in regular], float)
    ratio_n = np.array([p.n_ac / p.n_tow for p in regular])
    yl = np.log(pt / pa)  # log(P_ToW / P_AC), raw
    rules: dict[str, dict[str, object]] = {}

    def fit_linear(cols: list[np.ndarray], factors: Sequence[Sequence[Hashable]], rows_idx: np.ndarray,
                   test_idx: np.ndarray, alpha: float = 1e-4) -> np.ndarray:
        X = design(factors, np.column_stack(cols) if cols else None, len(regular))
        return ridge_fit_predict(X, yl, rows_idx, test_idx, alpha)

    all_idx = np.arange(len(regular))
    cf = corps_folds(corps)

    def rule_eval(name: str, cols: list[np.ndarray], factors: Sequence[Sequence[Hashable]], params: int,
                  alpha: float = 1e-4) -> np.ndarray:
        pred_in = fit_linear(cols, factors, all_idx, all_idx, alpha)
        pred_lco = np.zeros_like(yl)
        for train, test in cf:
            pred_lco[test] = fit_linear(cols, factors, train, test, alpha)
        p_in = pa * np.exp(pred_in)
        p_lco = pa * np.exp(pred_lco)
        rules[name] = dict(params=params, in_sample=score(pt, p_in), lco=score(pt, p_lco),
                           pred_in=p_in, pred_lco=p_lco, resid_lco=np.log(pt) - np.log(p_lco))
        log(f"  rule {name}: in {fmt_score(rules[name]['in_sample'])} | LCO {fmt_score(rules[name]['lco'])}")
        return pred_in

    # A: one global factor with the exact N ratio
    kA = float(np.exp(np.median(y)))
    pA = pa * ratio_n * kA
    pA_lco = np.zeros_like(pa)
    for train, test in cf:
        pA_lco[test] = pa[test] * ratio_n[test] * float(np.exp(np.median(y[train])))
    rules["A"] = dict(params=1, in_sample=score(pt, pA), lco=score(pt, pA_lco), pred_in=pA, pred_lco=pA_lco,
                      resid_lco=np.log(pt) - np.log(pA_lco), k=kA)
    log(f"  rule A: in {fmt_score(rules['A']['in_sample'])} | LCO {fmt_score(rules['A']['lco'])}")
    # F: ToW price from the stats-fair curve alone (ignores P_AC), out of fold by source corps
    fair_t_arr = np.array([p.extra["fair_t"] for p in regular])
    has_fair = ~np.isnan(fair_t_arr)
    pF = np.exp(fair_t_arr[has_fair]) * 8.0 / np.array([p.n_tow for p in regular])[has_fair]
    rules["F"] = dict(params="stats model", in_sample=score(pt[has_fair], pF), lco=None, pred_in=None,
                      pred_lco=None, resid_lco=None)
    log(f"  rule F (fair only, out of fold): {fmt_score(rules['F']['in_sample'])}")
    # B: free N slope + side x class factor
    rule_eval("B", [lnr], [F["side_class"]], 1 + len(set(F["side_class"])))
    # C: B + AC premium (unit and cell mean)
    rule_eval("C", [lnr, eA, eA_cell], [F["side_class"]], 3 + len(set(F["side_class"])))
    # C1: B + AC premium cell only
    rule_eval("C1", [lnr, eA_cell], [F["side_class"]], 2 + len(set(F["side_class"])))
    # C2: C + campaign x class (ridge, transferable to AC-only corps of a paired campaign)
    rule_eval("C2", [lnr, eA, eA_cell], [F["side_class"], F["campaign"], F["campaign_class"]],
              3 + len(set(F["side_class"])) + len(set(F["campaign"])) + len(set(F["campaign_class"])), alpha=1.0)
    # D: per-cell factor (needs pairs): P_ToW = round(P_AC x k_cell), k = median ratio of the cell
    ratio = pt / pa
    kcell: dict[Hashable, float] = {}
    for k_, ps in cells.items():
        kcell[k_] = float(np.median([q.p_tow / q.p_ac for q in ps]))
    pD = np.array([p.p_ac * kcell[(p.acf, p.unit_class)] for p in regular])
    # leave-one-out within cell (cells with >= 2 units)
    loo_mask = np.array([len(cells[(p.acf, p.unit_class)]) >= 2 for p in regular])
    cell_idx: dict[Hashable, list[int]] = defaultdict(list)
    for i, p in enumerate(regular):
        cell_idx[(p.acf, p.unit_class)].append(i)
    pD_loo = np.full_like(pa, np.nan)
    for ii in cell_idx.values():
        if len(ii) < 2:
            continue
        for i in ii:
            others = [j for j in ii if j != i]
            pD_loo[i] = pa[i] * float(np.median(ratio[others]))
    rules["D"] = dict(params=len(cells), in_sample=score(pt, pD), lco=score(pt[loo_mask], pD_loo[loo_mask]),
                      pred_in=pD, pred_lco=pD_loo, resid_lco=np.log(pt) - np.log(pD_loo),
                      in_multi=score(pt[loo_mask], pD[loo_mask]), n_multi=int(loo_mask.sum()),
                      in_3=score(pt[np.array([len(cells[(p.acf, p.unit_class)]) >= 3 for p in regular])],
                                 pD[np.array([len(cells[(p.acf, p.unit_class)]) >= 3 for p in regular])]))
    log(f"  rule D: in {fmt_score(rules['D']['in_sample'])} | LOO-in-cell {fmt_score(rules['D']['lco'])}")
    # D2: per-cell affine (in sample only; how close to an exact rule can a cell get)
    pD2 = np.zeros_like(pa)
    for ii in cell_idx.values():
        ii_a = np.array(ii)
        if len(ii) >= 3:
            A = np.c_[pa[ii_a], np.ones(len(ii))]
            coef, *_ = np.linalg.lstsq(A, pt[ii_a], rcond=None)
            pD2[ii_a] = A @ coef
        else:
            pD2[ii_a] = pa[ii_a] * float(np.median(ratio[ii_a]))
    m3c = np.array([len(cells[(p.acf, p.unit_class)]) >= 3 for p in regular])
    rules["D2"] = dict(params=2 * len(cells), in_sample=score(pt, pD2), lco=None, pred_in=pD2, pred_lco=None,
                       resid_lco=None, in_3=score(pt[m3c], pD2[m3c]))
    log(f"  rule D2 (per-cell affine, in-sample): {fmt_score(rules['D2']['in_sample'])}")

    # coefficients of the final transferable rule (C) for the report
    Xc = design([F["side_class"]], np.column_stack([lnr, eA, eA_cell]), len(regular))
    mC = Ridge(alpha=1e-4, solver="lsqr", tol=1e-10).fit(Xc, yl)
    nsc = len(set(F["side_class"]))
    gamma_c, beta_u, beta_c = (float(v) for v in mC.coef_[nsc:nsc + 3])
    # side x class factors at eA = mean, lnr = mean -> report as multiplicative k
    sc_levels: dict[Hashable, int] = {}
    for v in F["side_class"]:
        sc_levels.setdefault(v, len(sc_levels))
    means = np.array([lnr.mean(), eA.mean(), eA_cell.mean()])
    sc_k = {lvl: float(np.exp(mC.intercept_ + mC.coef_[j] - mC.coef_[nsc:nsc + 3] @ means))
            for lvl, j in sc_levels.items()}
    report["rule_C"] = dict(gamma=gamma_c, beta_unit=beta_u, beta_cell=beta_c, k=sc_k,
                            n=Counter(F["side_class"]))
    # simple B coefficients
    Xb = design([F["side_class"]], lnr[:, None], len(regular))
    mB = Ridge(alpha=1e-4, solver="lsqr", tol=1e-10).fit(Xb, yl)
    report["rule_B"] = dict(gamma=float(mB.coef_[nsc]),
                            k={lvl: float(np.exp(mB.intercept_ + mB.coef_[j] - mB.coef_[nsc] * lnr.mean()))
                               for lvl, j in sc_levels.items()})

    # LCO residual quantiles of rule C per arm -> interval for AC-only corps
    residC = rules["C"]["resid_lco"]
    q_arm = {}
    for arm in ARMS:
        m = np.array([p.arm == arm for p in regular])
        q_arm[arm] = (float(np.percentile(residC[m], 10)), float(np.percentile(residC[m], 90)))
    report["intervals"] = q_arm

    # =============================================================================
    # Commanders
    # =============================================================================
    reg_by = {(p.acf, p.ac["unit_key"]): p for p in regular}
    com_ok = []
    for p in commanders:
        base = reg_by.get((p.acf, COM_RE.sub("", p.ac["unit_key"])))
        if base is not None:
            p.extra["base_pa"] = base.p_ac
            p.extra["base_pt"] = base.p_tow
            com_ok.append(p)
    yc = np.array([p.r for p in com_ok])
    evc = Evaluator(yc, [p.acf for p in com_ok])
    Fc = {
        "class": [p.unit_class for p in com_ok],
        "side_class": [(p.side, p.unit_class) for p in com_ok],
        "stars": [p.stars for p in com_ok],
        "ac_class": [(p.acf, p.unit_class) for p in com_ok],
        "tow_class": [(p.twf, p.unit_class) for p in com_ok],
        "ac": [p.acf for p in com_ok],
    }
    base_r = np.array([math.log(p.extra["base_pt"] / p.extra["base_pa"]) - math.log(p.n_ac / p.n_tow) for p in com_ok])

    def addc(test: str, factors: Sequence[Sequence[Hashable]], conts: np.ndarray | None = None,
             corps_cv: bool = True, effect: str = "", verdict: str = "") -> tuple[float, float, float | None]:
        rin, rcv, rco, k = evc.run(factors, conts, corps_cv)
        effects.append(Effect("C", "commander", test, k, effect, rin, rcv, rco, verdict))
        log(f"  com {test:55s} k={k:5d} R2 in {rin:.3f} cv {rcv:.3f} lco {fmt(rco)}")
        return rin, rcv, rco

    resc: dict[str, tuple[float, float, float | None]] = {}
    resc["class"] = addc("class", [Fc["class"]])
    resc["stars"] = addc("stars", [Fc["stars"]])
    resc["tow_class"] = addc("ToW corps x class", [Fc["tow_class"]])
    resc["ac_class"] = addc("source AC corps x class", [Fc["ac_class"]], corps_cv=False)
    resc["base_r"] = addc("r of the commander's own regular unit", [], base_r[:, None])
    y_c_raw = np.array([math.log(p.p_tow / p.p_ac) for p in com_ok])
    lnr_c = np.array([math.log(p.n_ac / p.n_tow) for p in com_ok])
    s_c, _, _ = slope_within(y_c_raw, lnr_c, Fc["tow_class"])
    ci_c = cluster_bootstrap_slope(y_c_raw, lnr_c, Fc["tow_class"], Fc["ac"])
    report["H5_commander"] = dict(within_tow_class=s_c, ci=ci_c)
    effects.append(Effect("H5", "commander", "slope of log ratio on log(N_AC/N_ToW), within ToW corps x class", 1,
                          f"slope {s_c:.3f} (95% CI {ci_c[0]:.3f}-{ci_c[1]:.3f})", None, None, None,
                          "Not 1: commanders are not priced proportionally"))
    # commander rules given the ToW price of the regular unit
    pc_t = np.array([p.p_tow for p in com_ok], float)
    pc_a = np.array([p.p_ac for p in com_ok], float)
    pr_t = np.array([p.extra["base_pt"] for p in com_ok], float)
    pr_a = np.array([p.extra["base_pa"] for p in com_ok], float)
    d_a = pc_a - pr_a
    d_t = pc_t - pr_t
    com_rules: dict[str, dict[str, object]] = {}
    cfc = corps_folds(Fc["ac"])

    def com_rule(name: str, make: Callable[[np.ndarray], Callable[[np.ndarray], np.ndarray]], params: int) -> None:
        pred_in = make(np.arange(len(com_ok)))(np.arange(len(com_ok)))
        pred_lco = np.zeros_like(pc_t)
        for train, test in cfc:
            pred_lco[test] = make(train)(test)
        com_rules[name] = dict(params=params, in_sample=score(pc_t, pred_in), lco=score(pc_t, pred_lco),
                               pred_in=pred_in, pred_lco=pred_lco)
        log(f"  com rule {name}: in {fmt_score(com_rules[name]['in_sample'])} | LCO {fmt_score(com_rules[name]['lco'])}")

    side_c = np.array([p.side == "imperial" for p in com_ok])

    def ratio_inherit(train: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
        return lambda test: pc_a[test] * pr_t[test] / pr_a[test]

    def premium_scaled(train: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
        ks = {}
        for s in (True, False):
            m = train[side_c[train] == s]
            ks[s] = float((d_a[m] * d_t[m]).sum() / (d_a[m] ** 2).sum())
        return lambda test: pr_t[test] + np.where(side_c[test], ks[True], ks[False]) * d_a[test]

    def proportional(train: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
        k = float(np.exp(np.median(yc[train])))
        return lambda test: pc_a[test] * (np.exp(lnr_c[test])) * k

    com_rule("proportional (P_AC x N_AC/N_ToW x k)", proportional, 1)
    com_rule("ratio-inherit (P_AC,com x P_ToW,reg / P_AC,reg)", ratio_inherit, 0)
    com_rule("premium (P_ToW,reg + k_side x (P_AC,com - P_AC,reg))", premium_scaled, 2)
    k_prem = {s: float((d_a[side_c == s] * d_t[side_c == s]).sum() / (d_a[side_c == s] ** 2).sum()) for s in (True, False)}
    report["com_k"] = {"imperial": k_prem[True], "coalition": k_prem[False]}
    report["com_premium_pct"] = dict(ac=[float(v) for v in np.percentile(d_a, [10, 50, 90])],
                                     tow=[float(v) for v in np.percentile(d_t, [10, 50, 90])])
    report["com_counts"] = dict(n=len(com_ok), excluded_price1=kinds["commander"] - len(commanders))

    # =============================================================================
    # Staff generals: P x N invariance
    # =============================================================================
    st_rows = []
    for p in staff:
        st_rows.append((p.stars, p.p_ac * p.n_ac, p.p_tow * p.n_tow))
    v_ac: dict[int, list[int]] = defaultdict(list)
    v_tow: dict[int, list[int]] = defaultdict(list)
    for s_, a_, t_ in st_rows:
        v_ac[s_].append(a_)
        v_tow[s_].append(t_)
    vtab = {s_: (float(np.median(v_ac[s_])), float(np.median(v_tow[s_])), len(v_ac[s_])) for s_ in sorted(v_ac)}
    f_staff = float(np.median([t_ / a_ for _, a_, t_ in st_rows]))
    pt_s = np.array([p.p_tow for p in staff], float)
    pa_s = np.array([p.p_ac for p in staff], float)
    rn_s = np.array([p.n_ac / p.n_tow for p in staff])
    pred_s1 = pa_s * rn_s * f_staff
    pred_s2 = np.array([vtab[p.stars][1] / p.n_tow for p in staff])
    ac_v_exact = float(np.mean([abs(p.p_ac * p.n_ac - vtab[p.stars][0]) <= p.n_ac / 2 for p in staff]))
    tow_v_exact = float(np.mean([abs(p.p_tow * p.n_tow - vtab[p.stars][1]) <= p.n_tow / 2 for p in staff]))
    within_pct = float(np.mean([abs(t_ / a_ / f_staff - 1) <= 0.01 for _, a_, t_ in st_rows]))
    dev_ac = [math.log(a_ / vtab[s_][0]) for s_, a_, _ in st_rows]
    dev_tow = [math.log(t_ / vtab[s_][1]) for s_, _, t_ in st_rows]
    hi_stars = [s_ for s_ in vtab if s_ >= 7]
    report["staff_spread"] = dict(
        sd_ac=float(np.percentile(np.abs(dev_ac), 90)), sd_tow=float(np.percentile(np.abs(dev_tow), 90)),
        hi_n=int(sum(vtab[s_][2] for s_ in hi_stars)),
        hi_ratio=[float(vtab[s_][1] / vtab[s_][0]) for s_ in hi_stars],
        lo_ratio=[float(vtab[s_][1] / vtab[s_][0]) for s_ in vtab if s_ < 7])
    report["staff"] = dict(f=f_staff, vtab=vtab, rule1=score(pt_s, pred_s1), rule2=score(pt_s, pred_s2),
                           ac_v_exact=ac_v_exact, tow_v_exact=tow_v_exact, within1pct=within_pct,
                           n=len(staff), n_all=len(staff_all),
                           price1=Counter((p.p_ac == 1, p.p_tow == 1) for p in staff_all))
    y_s = np.array([p.r for p in staff])
    y_s_raw = np.log(pt_s / pa_s)
    lnr_s = np.log(rn_s)
    s_s, _, _ = slope_within(y_s_raw, lnr_s, [(p.twf,) for p in staff])
    report["H5_staff"] = dict(within_tow=s_s, raw=float(np.polyfit(lnr_s, y_s_raw, 1)[0]))
    effects.append(Effect("H5", "staff", "P x N invariance: P_ToW x N_ToW / (P_AC x N_AC)", 1,
                          f"median {f_staff:.3f}; {100 * within_pct:.0f}% of pairs within 1% of it; "
                          f"slope within ToW corps {s_s:.3f}", None, None, None,
                          "Near-exact: staff price = V(stars)/N, ToW V = AC V x " + f"{f_staff:.3f}"))
    log(f"  staff f {f_staff:.4f}, rule1 {fmt_score(report['staff']['rule1'])}, rule2 {fmt_score(report['staff']['rule2'])}")

    # =============================================================================
    # Verdicts for the regular-unit table (filled after all numbers exist)
    # =============================================================================
    def grade(e: Effect) -> str:
        v = e.r2_cv_corps if e.r2_cv_corps is not None else e.r2_cv_unit
        if v is None:
            return ""
        scope = "LCO" if e.r2_cv_corps is not None else "CV"
        for cut, word in ((0.5, "Major"), (0.25, "Substantial"), (0.10, "Moderate"), (0.03, "Small")):
            if v >= cut:
                return f"{word} ({scope} R2 {v:.2f})"
        return f"Negligible ({scope} R2 {v:.2f})"

    notes = {
        "class": "classes differ, but mostly through corps x class",
        "side (imperial / coalition)": "",
        "side x class + training + speed + log men + log P_AC": "unit attributes together transfer little to unseen corps",
        "source AC corps": "a corps-wide factor",
        "source AC corps x class": "the main structure: one factor per AC corps x class cell",
        "AC corps x class x training": "adds little beyond corps x class",
        "AC corps x class x speed": "adds little beyond corps x class",
        "AC corps x class x cap": "adds little beyond corps x class",
        "AC corps x class + within-cell log P_AC slope": "adds little beyond corps x class",
        "AC corps x class + within-cell log men slope": "adds little beyond corps x class",
        "AC corps x class x division": "adds little beyond corps x class",
        "AC corps x class x brigade": "adds little beyond corps x class",
        "AC corps x division": "weaker than corps x class",
        "AC corps x brigade": "weaker than corps x class",
        "ToW corps": "",
        "ToW corps x class": "about two-thirds of the cell structure; not the whole story",
        "ToW corps x class + source AC corps (additive)": "the source corps adds what the ToW cell misses",
        "ToW corps x class x ToW division": "adds little beyond ToW corps x class",
        "campaign code (a03, b08, ...)": "",
        "campaign x class": "partly transferable to unseen corps of a paired campaign",
        "faction-key x-class (x2-x8, r3-r7)": "",
        "x-class x class": "",
        "AC theatre (catalog)": "",
        "(N_AC, N_ToW) pair": "the N pair itself is not the driver",
        "unit has superseded balance-edit rows (AC, ToW)": "no level shift; edited units are noisier (see report)",
        "AC premium over stats-fair price, unit (ToW-trained fair)": "ToW pulls AC prices toward the stats curve",
        "AC premium, AC corps x class cell mean (ToW-trained fair)": "best single transferable predictor",
        "AC premium, AC corps mean (ToW-trained fair)": "",
        "AC premium, unit + cell mean": "",
        "AC premium, cell mean (AC-trained fair, log N free)": "same with an AC-trained fair model: not circular",
        "ToW corps x class + AC premium cell mean": "",
    }
    for e in effects:
        if e.kind != "regular" or e.hypothesis not in ("H2", "H3", "H6", "H7") or e.r2_cv_unit is None:
            continue
        g = grade(e)
        note = notes.get(e.test, "")
        e.verdict = g + (f"; {note}" if note else "")
    side_arr = np.array(F["side"])
    for e in effects:
        if e.kind == "regular" and e.test == "side (imperial / coalition)":
            e.effect = (f"median r imperial {np.median(y[side_arr == 'imperial']):+.3f}, "
                        f"coalition {np.median(y[side_arr == 'coalition']):+.3f}")
        if e.kind == "regular" and e.test == "side x class + log ratio slope + AC premium (unit, cell)":
            e.verdict = grade(e) + "; = final transferable rule C"

    # =============================================================================
    # AC-only corps: ToW-equivalent prices
    # =============================================================================
    ac_only_rows = [r for r in rows if r["faction_key"] in ac_only]
    reg_only = [r for r in ac_only_rows if r["is_general"] == "false"]
    log(f"AC-only regular units: {len(reg_only)}")
    # premiums with the ToW-trained fair model (fit on all ToW units; these units were never seen)
    eA_only = {}
    for r in reg_only:
        n = rating[r["faction_key"]]
        if r["unit_class"] == "artillery_fixed":
            continue
        v = float(fair_t_full.predict(fm_t.features(r, n)[None, :])[0])
        eA_only[r["unit_key"]] = math.log(int(r["base_mp_cost"]) * n / 8.0) - v
    cell_only: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in reg_only:
        if r["unit_key"] in eA_only:
            cell_only[(r["faction_key"], r["unit_class"])].append(eA_only[r["unit_key"]])
    cell_only_m = {k: float(np.mean(v)) for k, v in cell_only.items()}

    def rule_c_log(side: str, unit_class: str, lnr_v: float, ea: float, ea_cell: float) -> float:
        j = sc_levels.get((side, unit_class))
        level = mC.coef_[j] if j is not None else float(np.mean(mC.coef_[:nsc]))
        return float(mC.intercept_ + level + gamma_c * (lnr_v - means[0]) + beta_u * (ea - means[1])
                     + beta_c * (ea_cell - means[2]))

    def rule_b_log(side: str, unit_class: str, lnr_v: float) -> float:
        j = sc_levels.get((side, unit_class))
        level = mB.coef_[j] if j is not None else float(np.mean(mB.coef_[:nsc]))
        return float(mB.intercept_ + level + mB.coef_[nsc] * (lnr_v - means[0]))

    # commanders' and staff ToW-equivalents use their own rules on top of the regular estimate
    by_key_only = {(r["faction_key"], r["unit_key"]): r for r in ac_only_rows}
    out_rows: list[dict[str, object]] = []
    reg_est: dict[tuple[str, str, int], tuple[float, float, float]] = {}

    def regular_estimate(r: dict[str, str], n_t: int) -> tuple[float, float, float, str]:
        n_a = rating[r["faction_key"]]
        side = "imperial" if is_imperial(r["corps_side"]) else "coalition"
        lnr_v = math.log(n_a / n_t)
        pa_v = int(r["base_mp_cost"])
        arm = arm_of(r["unit_class"])
        if r["unit_key"] in eA_only:
            lr = rule_c_log(side, r["unit_class"], lnr_v, eA_only[r["unit_key"]],
                            cell_only_m[(r["faction_key"], r["unit_class"])])
            rule = "C"
        else:
            lr = rule_b_log(side, r["unit_class"], lnr_v)
            rule = "B"
        q = q_arm.get(arm, q_arm["infantry"])
        est = pa_v * math.exp(lr)
        return est, est * math.exp(q[0]), est * math.exp(q[1]), rule

    for r in ac_only_rows:
        n_a = rating[r["faction_key"]]
        kind = ("staff" if "_gen_staff_" in r["unit_key"] else "commander") if r["is_general"] == "true" else "regular"
        rec: dict[str, object] = dict(
            faction_key=r["faction_key"], army_corps_name=catalog[r["faction_key"]]["army_corps_name"],
            side="imperial" if is_imperial(r["corps_side"]) else "coalition", n_ac=n_a, kind=kind,
            unit_key=r["unit_key"], unit_name=r["unit_name"], unit_class=r["unit_class"],
            stars=r["command_stars"], p_ac=int(r["base_mp_cost"]),
        )
        for tag, n_t in (("own_n", n_a), ("n8", 8)):
            if kind == "regular":
                est, lo, hi, rule = regular_estimate(r, n_t)
            elif kind == "commander":
                base = by_key_only.get((r["faction_key"], COM_RE.sub("", r["unit_key"])))
                if base is None or int(r["base_mp_cost"]) <= 1:
                    est = lo = hi = float(max(int(r["base_mp_cost"]), 1))
                    rule = "price 1 kept" if int(r["base_mp_cost"]) <= 1 else "no base unit"
                else:
                    b_est, b_lo, b_hi, _ = regular_estimate(base, n_t)
                    side = "imperial" if is_imperial(r["corps_side"]) else "coalition"
                    k_ = report["com_k"][side]  # type: ignore[index]
                    d_ = int(r["base_mp_cost"]) - int(base["base_mp_cost"])
                    est, lo, hi = (max(1.0, b_est + k_ * d_), max(1.0, b_lo + k_ * d_), max(1.0, b_hi + k_ * d_))
                    rule = "commander premium on rule C"
            else:
                pa_v = int(r["base_mp_cost"])
                if pa_v <= 1:
                    est = lo = hi = 1.0
                    rule = "price 1 kept"
                else:
                    stars_v = int(fnum(r["command_stars"]))
                    if stars_v in vtab and vtab[stars_v][2] >= 10:
                        est = vtab[stars_v][1] / n_t
                        sres = np.log(pt_s / pred_s2)
                        rule = "staff V_ToW(stars)/N"
                    else:
                        est = pa_v * n_a / n_t * f_staff
                        sres = np.log(pt_s / pred_s1)
                        rule = "staff P x N x f"
                    lo, hi = est * math.exp(float(np.percentile(sres, 10))), est * math.exp(float(np.percentile(sres, 90)))
            rec[f"tow_eq_{tag}"] = round(est)
            rec[f"tow_eq_{tag}_low"] = round(lo)
            rec[f"tow_eq_{tag}_high"] = round(hi)
            rec["rule"] = rule
        out_rows.append(rec)
    out_rows.sort(key=lambda d: (str(d["faction_key"]), str(d["kind"]), str(d["unit_class"]), -int(d["p_ac"])))  # type: ignore[arg-type]
    with (OUT / "ac_only_tow_equivalent.csv").open("w", encoding="utf-8", newline="") as handle:
        cols = ["faction_key", "army_corps_name", "side", "n_ac", "kind", "unit_key", "unit_name", "unit_class",
                "stars", "p_ac", "tow_eq_own_n", "tow_eq_own_n_low", "tow_eq_own_n_high",
                "tow_eq_n8", "tow_eq_n8_low", "tow_eq_n8_high", "rule"]
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        for rec in out_rows:
            w.writerow({c: rec.get(c, "") for c in cols})
    # per-corps summary
    only_summary = []
    for f in ac_only:
        rr = [d for d in out_rows if d["faction_key"] == f and d["kind"] == "regular"]
        if not rr:
            continue
        tot_ac = sum(int(d["p_ac"]) for d in rr)  # type: ignore[arg-type]
        tot_eq = sum(int(d["tow_eq_own_n"]) for d in rr)  # type: ignore[arg-type]
        only_summary.append((f, catalog[f]["army_corps_name"], rating[f], len(rr), tot_eq / tot_ac,
                             float(np.mean([cell_only_m.get((f, d["unit_class"]), float("nan")) for d in rr
                                            if (f, d["unit_class"]) in cell_only_m]))))
    report["ac_only_summary"] = only_summary
    report["ac_only_counts"] = Counter(str(d["kind"]) for d in out_rows)

    # =============================================================================
    # Write pairs and effects
    # =============================================================================
    reg_index = {id(p): i for i, p in enumerate(regular)}
    com_index = {id(p): i for i, p in enumerate(com_ok)}
    st_index = {id(p): i for i, p in enumerate(staff)}
    com_best = "premium (P_ToW,reg + k_side x (P_AC,com - P_AC,reg))"
    with (OUT / "natural_experiment_pairs.csv").open("w", encoding="utf-8", newline="") as handle:
        cols = ["kind", "ac_unit_key", "tow_unit_key", "ac_faction_key", "tow_faction_key", "ac_corps_name",
                "tow_corps_name", "unit_name", "unit_class", "side", "stars", "n_ac", "n_tow", "p_ac", "p_tow", "r",
                "edited_ac", "edited_tow", "brigade_rebate", "division_rebate", "corps_full_division_rebate",
                "ac_premium_unit", "ac_premium_cell", "rule_A_pred", "final_rule", "final_pred",
                "final_pred_lco", "final_resid_log", "final_resid_log_lco", "cell_lookup_pred", "cell_lookup_pred_loo"]
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        for p in pairs:
            rec = dict(kind=p.kind, ac_unit_key=p.ac["unit_key"], tow_unit_key=p.tow["unit_key"],
                       ac_faction_key=p.acf, tow_faction_key=p.twf, ac_corps_name=p.ac_name, tow_corps_name=p.tow_name,
                       unit_name=p.ac["unit_name"], unit_class=p.unit_class, side=p.side, stars=p.ac["command_stars"],
                       n_ac=p.n_ac, n_tow=p.n_tow, p_ac=p.p_ac, p_tow=p.p_tow,
                       r=f"{p.r:.5f}" if p.p_ac > 0 and p.p_tow > 0 else "",
                       edited_ac=int(p.edited_ac), edited_tow=int(p.edited_tow),
                       brigade_rebate=f"{p.extra['brig_reb']:.2f}", division_rebate=f"{p.extra['div_reb']:.2f}",
                       corps_full_division_rebate=f"{p.extra['corps_div_reb']:.4f}")
            if id(p) in reg_index:
                i = reg_index[id(p)]
                rec.update(ac_premium_unit=f"{p.extra['eA']:.4f}", ac_premium_cell=f"{p.extra['eA_cell']:.4f}",
                           rule_A_pred=f"{rules['A']['pred_in'][i]:.1f}", final_rule="C (regular)",  # type: ignore[index]
                           final_pred=f"{rules['C']['pred_in'][i]:.1f}",  # type: ignore[index]
                           final_pred_lco=f"{rules['C']['pred_lco'][i]:.1f}",  # type: ignore[index]
                           final_resid_log=f"{math.log(p.p_tow / rules['C']['pred_in'][i]):.4f}",  # type: ignore[index]
                           final_resid_log_lco=f"{rules['C']['resid_lco'][i]:.4f}",  # type: ignore[index]
                           cell_lookup_pred=f"{rules['D']['pred_in'][i]:.1f}",  # type: ignore[index]
                           cell_lookup_pred_loo="" if np.isnan(rules["D"]["pred_lco"][i]) else f"{rules['D']['pred_lco'][i]:.1f}")  # type: ignore[index]
            elif id(p) in com_index:
                i = com_index[id(p)]
                pin = com_rules[com_best]["pred_in"][i]  # type: ignore[index]
                plc = com_rules[com_best]["pred_lco"][i]  # type: ignore[index]
                rec.update(final_rule="commander premium (given P_ToW of the regular unit)",
                           final_pred=f"{pin:.1f}", final_pred_lco=f"{plc:.1f}",
                           final_resid_log=f"{math.log(p.p_tow / max(pin, 1.0)):.4f}",
                           final_resid_log_lco=f"{math.log(p.p_tow / max(plc, 1.0)):.4f}")
            elif id(p) in st_index:
                i = st_index[id(p)]
                rec.update(final_rule="staff P x N", final_pred=f"{pred_s1[i]:.1f}",
                           final_resid_log=f"{math.log(p.p_tow / pred_s1[i]):.4f}")
            w.writerow(rec)
    with (OUT / "natural_experiment_effects.csv").open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["hypothesis", "kind", "test", "n_params", "r2_in_sample", "r2_cv_units", "r2_cv_leave_corps_out",
                    "effect", "verdict"])
        for e in effects:
            w.writerow([e.hypothesis, e.kind, e.test, e.n_params, fmt(e.r2_in), fmt(e.r2_cv_unit), fmt(e.r2_cv_corps),
                        e.effect, e.verdict])
        for name, rd in rules.items():
            w.writerow(["RULE", "regular", f"rule {name}", rd["params"], "", "", "",
                        "in-sample: " + fmt_score(rd["in_sample"])  # type: ignore[arg-type]
                        + ("" if rd["lco"] is None else " | out-of-sample: " + fmt_score(rd["lco"])),  # type: ignore[arg-type]
                        ""])
        for name, rd in com_rules.items():
            w.writerow(["RULE", "commander", name, rd["params"], "", "", "",
                        "in-sample: " + fmt_score(rd["in_sample"]) + " | LCO: " + fmt_score(rd["lco"]), ""])  # type: ignore[arg-type]
        w.writerow(["RULE", "staff", "P_ToW = P_AC x N_AC/N_ToW x f", 1, "", "", "",
                    fmt_score(report["staff"]["rule1"]), ""])  # type: ignore[index]
        w.writerow(["RULE", "staff", "P_ToW = V_ToW(stars) / N_ToW", len(vtab), "", "", "",
                    fmt_score(report["staff"]["rule2"]), ""])  # type: ignore[index]

    write_report(report, res, resc, rules, com_rules, effects)
    log(f"wrote {OUT}")


# --------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------

def write_report(rep: dict, res: dict, resc: dict, rules: dict, com_rules: dict, effects: list[Effect]) -> None:
    rs = rep["r_stats"]
    h5 = rep["H5_regular"]
    h7 = rep["H7"]
    lv = rep["levels"]
    st = rep["staff"]
    rc = rep["rule_C"]
    wc = rep["within_cell"]
    C = rules["C"]
    lines: list[str] = []
    a = lines.append

    def row(*cells: object) -> None:
        a("| " + " | ".join(str(c) for c in cells) + " |")

    def pct(x: float) -> str:
        return f"{100 * x:.1f}%"

    cnt = rep["counts"]
    ad = h7["corps"]["adopted"]
    a("# Natural experiment: what sets AC versus ToW prices")
    a("")
    a("*Step 4 of the AC pricing study (`analysis/AC_STUDY_PLAN.md`). Generated by "
      "`analysis/experiments/ac_natural_experiment.py`; every number below comes from that run. Outputs in "
      "`analysis/output/ac/`.*")
    a("")
    a("## Headline")
    a("")
    a(f"Every ToW unit is a copy of an AC unit with identical stats, size, flags, stars and cap, so the pair price "
      f"ratio isolates how the two modes price the same unit ({cnt['regular']} regular, {cnt['commander']} commander "
      f"and {cnt['staff']} staff pairs with prices above 1). The residual after the corps-number ratio, "
      f"r = log(P_ToW/P_AC) - log(N_AC/N_ToW), has median {rs['median']:+.3f} (x{rs['factor']:.3f}) and sd {rs['sd']:.3f}.")
    a("")
    a("**What makes ToW copies cheaper than their AC originals:**")
    a("")
    nr = rep["n_ratio"]
    a(f"1. **The corps number sets the spread, not the cut.** The median ToW/AC price ratio is {nr['median_raw']:.3f} "
      f"({pct(nr['share_cheaper'])} of copies are cheaper). The ratio N_AC/N_ToW explains {pct(nr['r2'])} of the "
      f"variance of log(P_ToW/P_AC), since prices scale with 1/N in both modes (AC slightly flatter: slope "
      f"{h5['within_tow_class']:.3f}, 95% CI {h5['ci'][0]:.3f}-{h5['ci'][1]:.3f}). But the median N ratio is "
      f"{nr['median_nratio']:.3f}, so it does not make copies cheaper on average: after it ToW is still "
      f"x{rs['factor']:.3f} (median).")
    a(f"2. **That remaining cut is AC's own hand-set corps x class multipliers, which ToW largely undoes.** Measured against a "
      f"stats-only price curve, the ToW copies sit on the curve (mean premium e_T {lv['eT_mean']:+.3f}) while the AC "
      f"originals sit {100 * (math.exp(lv['eA_mean']) - 1):.0f}% above it on average (e_A {lv['eA_mean']:+.3f}) "
      f"and scatter by corps and class. The ToW price moves {abs(h7['corps']['tow_fair'][0]):.2f} log points down per "
      f"log point of the AC corps' premium (corps level, R2 {h7['corps']['tow_fair'][1]:.2f}; "
      + (f"{abs(ad[0]):.2f} and R2 {ad[1]:.2f} with the committed adopted ToW model; " if ad else "")
      + f"{abs(h7['cell']['tow_fair'][0]):.2f} at corps x class level). So the ~9% average cut is the average AC "
      f"premium over the common curve, and the corps x class spread of r is mostly the spread of that premium.")
    a(f"3. **Formation rebates play no part.** Neither the unit's own brigade or division rebate nor the corps' "
      f"full-formation rebate tracks r (|corr| <= "
      f"{max(abs(rep['H1_brig_reb']['corr']), abs(rep['H1_div_reb']['corr']), abs(rep['H1_corps_div_reb']['corr'])):.2f}). "
      f"The mean division rebate ({pct(rep['H1_div_reb']['mean'])}) matches the average AC premium in size, which "
      f"fits a design intent ('AC list prices carry roughly what a full division gives back'), but no unit or "
      f"corps is priced by its actual rebate.")
    a(f"4. **There is no exact generating rule** for regular units: no rounding, no quantised factors, and even one "
      f"factor per AC corps x class cell leaves a within-cell scatter of sd {100 * wc['sd']:.1f}% that no stat, size, "
      f"price level or formation explains. Some corps are clean (within-cell sd "
      f"{100 * rep['corps_within_sd']['p10']:.1f}% at the 10th percentile), others noisy "
      f"({100 * rep['corps_within_sd']['p90']:.1f}% at the 90th).")
    a(f"5. **Staff generals are near-exact:** price x N is a fixed value per star level in each mode, the ToW value is "
      f"x{st['f']:.3f} the AC value, and V_ToW(stars)/N_ToW reproduces {pct(st['rule2']['exact'])} of ToW staff prices "
      f"exactly. **Commanders** keep their AC mark-up over their regular unit, shrunk but not N-scaled: "
      f"P_ToW,com = P_ToW,reg + k x (P_AC,com - P_AC,reg), k = {rep['com_k']['imperial']:.2f} imperial / "
      f"{rep['com_k']['coalition']:.2f} coalition (median error {com_rules['premium (P_ToW,reg + k_side x (P_AC,com - P_AC,reg))']['lco']['median_ape']:.1f}%).")
    a("")
    a("**Compact rule** (regular units, usable for corps with no ToW copy; leave-corps-out median error "
      f"{C['lco']['median_ape']:.1f}%, P90 {C['lco']['p90_ape']:.1f}%, exact {pct(C['lco']['exact'])}):")
    a("")
    a("```")
    a(f"P_ToW = P_AC x (N_AC/N_ToW)^{rc['gamma']:.3f} x k[side, class] x exp({rc['beta_unit']:+.3f} e_A {rc['beta_cell']:+.3f} e_A,cell)")
    a("```")
    a("")
    a("where e_A is the unit's AC premium over the stats curve and e_A,cell its AC corps x class mean (details below).")
    a("")

    a("## Hypotheses (regular units unless stated)")
    a("")
    a("R2 is on r. *R2 in* = plain group means or OLS; *CV* = 10-fold over units; *LCO* = leave-corps-out "
      "(10 folds grouped by source AC corps), the test that matters for corps with no ToW copy; n/a where the "
      "grouping is the AC corps itself. Groupings are one-hot ridge (alpha 1, i.e. group means shrunk toward their "
      "parent). Verdict words grade the LCO R2 (else CV): Major >= 0.5, Substantial >= 0.25, Moderate >= 0.10, "
      "Small >= 0.03. Full table: `natural_experiment_effects.csv`.")
    a("")
    row("#", "Hypothesis / grouping", "Params", "R2 in", "R2 CV", "R2 LCO", "Effect", "Verdict")
    row(*["---"] * 8)
    for e in effects:
        if e.kind != "regular":
            continue
        row(e.hypothesis, e.test, e.n_params, fmt(e.r2_in), fmt(e.r2_cv_unit), fmt(e.r2_cv_corps) or "n/a",
            e.effect, e.verdict)
    a("")
    a("### Notes per hypothesis")
    a("")
    a(f"**H1 rebates** (`tools/army_builder_rules.py`: `build_roster_totals`, `group_discount`, `support_divisions`). "
      f"If ToW = AC minus the formation rebate, r would move one-for-one with log(1 - rebate). Correlations: own "
      f"brigade {rep['H1_brig_reb']['corr']:+.3f}, own division {rep['H1_div_reb']['corr']:+.3f}, corps full-division "
      f"share {rep['H1_corps_div_reb']['corr']:+.3f} (corps means {rep['H1_corps_level_corr']:+.3f}), corps "
      f"full-brigade share {rep['H1_corps_brig_reb']['corr']:+.3f}; the free slopes have the wrong sign or are near 0. "
      f"With the slope fixed at 1 the R2 is {rep['H1_div_reb']['r2_fixed']:+.3f} (division) and "
      f"{rep['H1_corps_div_reb']['r2_fixed']:+.3f} (corps), worse than a constant. The corps full-division rebate "
      f"ranges {pct(rep['H1_corps_div_pct'][0])}-{pct(rep['H1_corps_div_pct'][2])} (10th-90th percentile) and is "
      f"unrelated to r. **Rejected.**")
    a("")
    a(f"**H2 unit attributes.** Class explains {res['class'][0]:.2f} and side x class {res['side_class'][0]:.2f}; "
      f"coalition copies are cut less than imperial ones. Training, speed, size, cap and price level add at most a "
      f"few percent each; all together reach LCO R2 {fmt(res['all_unit'][2])}. The source corps x class cell is the "
      f"main structure ({res['ac_class'][0]:.2f} in sample, {res['ac_class'][1]:.2f} CV). Inside those cells "
      f"(residual sd {100 * wc['sd']:.1f}%) price level has slope {wc['slope_logp']:+.3f} (R2 {wc['r2_logp']:.3f}) and "
      f"size {wc['slope_logmen']:+.3f} (R2 {wc['r2_logmen']:.3f}); training, speed, cap, division and brigade add "
      f"nothing out of sample (CV R2 {res['ac_class'][1]:.3f} for corps x class against "
      f"{res['ac_class_training'][1]:.3f} / {res['ac_class_speed'][1]:.3f} / {res['ac_class_cap'][1]:.3f} / "
      f"{res['ac_class_division'][1]:.3f} / {res['ac_class_brigade'][1]:.3f} with them).")
    a("")
    a(f"**H3 the ToW corps.** ToW corps x class explains {res['tow_class'][0]:.2f} (CV {res['tow_class'][1]:.2f}) "
      f"against {res['ac_class'][0]:.2f} for the source corps x class; adding the source corps as a level gives "
      f"{res['tow_class_plus_ac'][0]:.2f} (CV {res['tow_class_plus_ac'][1]:.2f}). Each AC corps feeds exactly one ToW "
      f"corps, so the source cell nests the ToW cell. r is **not** one factor per ToW corps x class applied to all "
      f"its source corps: source corps in the same ToW cell get different factors, and those follow each source "
      f"corps' AC premium (ToW corps x class + cell premium: LCO R2 {fmt(res['tow_class_eA_cell'][2])}).")
    a("")
    rd = rep["rounding"]
    q = rep["quantisation"]
    ec = rep["exact_cells"]["round"]
    D = rules["D"]
    a(f"**H4 rounding.** Prices are plain integers: {pct(rd['AC regular'][5])} (AC) and {pct(rd['ToW regular'][5])} "
      f"(ToW) are multiples of 5 against 20% by chance, {pct(rd['AC regular'][10])} / {pct(rd['ToW regular'][10])} "
      f"multiples of 10; last digits are uniform (chi2 {rep['last_digit_chi2']['ac']:.1f} / "
      f"{rep['last_digit_chi2']['tow']:.1f}, 9 df). The factors of the {q['n']} tight cells (sd <= 2%) sit no closer to "
      f"a 0.05 grid than random ({q['grid'][0.05]:.3f} of a step; 0.25 = uniform). One factor k with "
      f"P_ToW = round(P_AC x k) fits every unit in only {ec['exact_cells']} of {ec['cells']} cells with 2+ units "
      f"({ec['exact_units']} of {ec['units']} units, mostly 2-unit cells by chance; floor "
      f"{rep['exact_cells']['floor']['exact_units']}, ceil {rep['exact_cells']['ceil']['exact_units']}). The cell-median "
      f"lookup reproduces {pct(D['in_multi']['exact'])} of prices exactly in cells with 2+ units "
      f"({pct(D['in_3']['exact'])} with 3+), but that counts each cell's median unit, exact by construction; "
      f"leave-one-out it is {pct(D['lco']['exact'])}. A per-cell affine fit reaches "
      f"{pct(rules['D2']['in_3']['exact'])} in cells with 3+. Staff P x N is the only near-exact pattern "
      f"(below). **No rounding and no exact per-cell rule for regular units.**")
    a("")
    a(f"**H5 the N slope.** Within ToW corps x class (N_ToW fixed, N_AC varying across source corps) the slope of "
      f"log(P_ToW/P_AC) on log(N_AC/N_ToW) is **{h5['within_tow_class']:.3f}** (95% cluster bootstrap over AC corps "
      f"{h5['ci'][0]:.3f}-{h5['ci'][1]:.3f}; raw {h5['raw']:.3f}): not exactly 1. AC prices fall a little less than 1/N "
      f"relative to ToW (the AC-trained fair model has log N coefficient {rep['fair_a_logN_coef']:.3f}). The slope "
      f"cannot be estimated inside one AC corps, because each AC corps feeds exactly one ToW corps. Once the AC "
      f"premium is in the rule the fitted exponent is {rc['gamma']:.3f}. Commanders: "
      f"{rep['H5_commander']['within_tow_class']:.3f} (CI {rep['H5_commander']['ci'][0]:.3f}-"
      f"{rep['H5_commander']['ci'][1]:.3f}), because the commander mark-up is not N-scaled. **Exact price x N "
      f"invariance holds only for staff generals**, within each mode.")
    a("")
    h6 = rep["H6_edits"]
    a(f"**H6 patch history.** Campaign code explains {res['campaign'][0]:.2f} (LCO {fmt(res['campaign'][2])}), campaign "
      f"x class {res['campaign_class'][0]:.2f} (LCO {fmt(res['campaign_class'][2])}); the faction-key x-class "
      f"{res['xclass'][0]:.2f} (LCO {fmt(res['xclass'][2])}). These largely restate corps x class. "
      f"`ntw3_land_units` carries superseded balance-edit rows (inert in game; the first row is loaded) for "
      f"{h6['n_edited_ac']} regular AC units, all in campaigns {', '.join(sorted(h6['campaigns']))} (1812 and 1814); "
      f"{h6['n_edited_both']} of them have a matching edit on the ToW copy. Edited units sit "
      f"{100 * h6['dev_edit']:.1f}% from their cell's median ratio against {100 * h6['dev_clean']:.1f}% for unedited "
      f"ones. Where only the AC key was edited, the ToW price matches the live AC row better in {h6['first_closer']} "
      f"cases and a superseded row in {h6['later_closer']}. So the ToW copies follow the live AC prices, and the "
      f"later balance passes edited AC and ToW rows together. Patch history adds noise, not the level.")
    a("")
    a(f"**H7 AC premium over a stats-fair price.** The fair price is a stats-only ridge model of log(P x N/8) trained "
      f"on ToW regulars (CV rmse {rep['fair_rmse']['tow']:.3f} log; out of fold by source corps for paired units). "
      f"e_A = log(P_AC x N_AC/8) - fair and e_T = log(P_ToW x N_ToW/8) - fair, so r = e_T - e_A exactly. "
      f"Mean e_A {lv['eA_mean']:+.3f}, mean e_T {lv['eT_mean']:+.3f}. Weighted regressions of mean r on mean e_A:")
    a("")
    row("Level", "slope", "R2", "sd e_A", "sd e_T", "slope, AC-trained fair", "R2", "slope, adopted ToW model", "R2")
    row(*["---"] * 9)
    for lvl in ("unit", "cell", "corps"):
        t_ = h7[lvl]["tow_fair"]
        a_ = h7[lvl]["ac_fair"]
        d_ = h7[lvl]["adopted"]
        row(lvl, f"{t_[0]:+.3f}", f"{t_[1]:.3f}", f"{t_[2]:.3f}", f"{t_[3]:.3f}", f"{a_[0]:+.3f}", f"{a_[1]:.3f}",
            "" if d_ is None else f"{d_[0]:+.3f}", "" if d_ is None else f"{d_[1]:.3f}")
    a("")
    a(f"A slope of -1 would mean ToW removes the AC premium completely, 0 not at all. At corps level the ToW copies "
      f"sit within sd {h7['corps']['tow_fair'][3]:.3f} of the curve while the AC originals scatter sd "
      f"{h7['corps']['tow_fair'][2]:.3f}. Three fair-price definitions agree: the self-contained ToW-trained proxy, "
      f"one trained on AC prices with log N free (so the result is not circular), and the committed adopted ToW model "
      f"(`analysis/output/oof_predictions.csv`, `oof_final`, stats only, {rep['adopted_n']} pairs). A noisier fair "
      f"price attenuates the slopes toward 0, so the true pull toward the curve is if anything stronger. "
      f"Provisional until step 2's AC model replaces the proxy.")
    a("")

    a("## Rules for P_ToW given P_AC")
    a("")
    a("### Regular units")
    a("")
    a("```")
    a(f"Rule C:  P_ToW = P_AC x (N_AC/N_ToW)^{rc['gamma']:.3f} x k[side, class] x exp({rc['beta_unit']:+.3f} e_A {rc['beta_cell']:+.3f} e_A,cell)")
    a("  e_A      = log(P_AC x N_AC / 8) - log fair(stats)   the unit's AC premium over the stats curve")
    a("  e_A,cell = mean of e_A over the unit's AC corps x class")
    a("```")
    a("")
    a(f"A whole cell priced x(1 + p) above the curve in AC loses about {100 * -(rc['beta_unit'] + rc['beta_cell']):.0f}% "
      f"of that premium (in logs) in ToW; a single unit off its cell's level loses {100 * -rc['beta_unit']:.0f}% of "
      f"its own deviation. k is the fitted factor at e_A = 0 and N_AC = N_ToW. Rule B is the simplest readable "
      f"fallback, with no stats model: P_ToW = P_AC x (N_AC/N_ToW)^{rep['rule_B']['gamma']:.3f} x k_B[side, class].")
    a("")
    row("Class", "C: k imperial", "C: k coalition", "B: k imperial", "B: k coalition", "pairs (imp / coa)")
    row(*["---"] * 6)
    kb = rep["rule_B"]["k"]
    for c in sorted({c for _, c in rc["k"]}):
        vals = [rc["k"].get(("imperial", c)), rc["k"].get(("coalition", c)), kb.get(("imperial", c)),
                kb.get(("coalition", c))]
        row(c, *["" if v is None else f"{v:.3f}" for v in vals],
            f"{rc['n'].get(('imperial', c), 0)} / {rc['n'].get(('coalition', c), 0)}")
    a("")
    a("Accuracy, integer-rounded (exact = equals the game's ToW price):")
    a("")
    row("Rule", "Params", "Exact", "Median abs % err", "P90 abs % err", "MAE (gold)",
        "Out of sample: exact / median / P90 / MAE")
    row(*["---"] * 7)
    labels = {
        "A": f"A: P_AC x N_AC/N_ToW x {rules['A']['k']:.3f}",
        "F": "F: stats-fair price alone, ignoring P_AC (out of fold)",
        "B": f"B: P_AC x (N_AC/N_ToW)^{rep['rule_B']['gamma']:.3f} x k[side, class]",
        "C1": "C1: B + cell premium",
        "C": "**C: B + AC premium (unit + cell)**",
        "C2": "C2: C + campaign x class (ridge)",
        "D": "D: P_AC x k_cell, k = cell median ratio (lookup; needs the pairs)",
        "D2": "D2: per-cell affine a x P_AC + b (in sample)",
    }
    for name in ("A", "F", "B", "C1", "C", "C2", "D", "D2"):
        rd_ = rules[name]
        s_in = rd_["in_sample"]
        s_o = rd_["lco"]
        oos = "" if s_o is None else (f"{pct(s_o['exact'])} / {s_o['median_ape']:.1f}% / {s_o['p90_ape']:.1f}% / "
                                       f"{s_o['mae']:.1f}" + (" (leave-one-out in cell)" if name == "D" else " (LCO)"))
        row(labels[name], rd_["params"], pct(s_in["exact"]), f"{s_in['median_ape']:.1f}%",
            f"{s_in['p90_ape']:.1f}%", f"{s_in['mae']:.1f}", oos)
    a("")
    a(f"Rule C is adopted: it needs only the AC price, the two corps numbers, side, class and a stats-fair price, so "
      f"it applies to corps with no ToW copy. Out of sample it cuts the median error from "
      f"{rules['A']['lco']['median_ape']:.1f}% (A) and {rules['B']['lco']['median_ape']:.1f}% (B) to "
      f"{C['lco']['median_ape']:.1f}%, and the P90 from {rules['A']['lco']['p90_ape']:.1f}% to "
      f"{C['lco']['p90_ape']:.1f}%. The AC price and the stats curve each carry information the other lacks "
      f"(A alone {rules['A']['lco']['median_ape']:.1f}%, F alone {rules['F']['in_sample']['median_ape']:.1f}%). "
      f"Campaign x class (C2) helps a little more but only for corps whose campaign has ToW copies. Exact matches "
      f"stay rare under every rule; the cell lookup D (1 661 factors) is the ceiling for any one-factor-per-cell rule.")
    a("")
    a("### Commanders (given the ToW price of the commander's own regular unit)")
    a("")
    row("Rule", "Params", "In sample", "Leave-corps-out")
    row(*["---"] * 4)
    for name, cr_ in com_rules.items():
        row(name, cr_["params"], fmt_score(cr_["in_sample"]), fmt_score(cr_["lco"]))
    a("")
    pc = rep["com_premium_pct"]
    a(f"The commander mark-up P_com - P_reg (median {pc['ac'][1]:+.0f} gold in AC, {pc['tow'][1]:+.0f} in ToW; AC "
      f"10th-90th percentile {pc['ac'][0]:+.0f} to {pc['ac'][2]:+.0f}) carries over shrunk by k = "
      f"{rep['com_k']['imperial']:.2f} / {rep['com_k']['coalition']:.2f} (imperial / coalition) and is **not** rescaled "
      f"by the N ratio. That additive, unscaled part is why the commander N slope is "
      f"{rep['H5_commander']['within_tow_class']:.2f}. Commander r on its own: class R2 {resc['class'][0]:.2f}, stars "
      f"{resc['stars'][0]:.2f}, ToW corps x class {resc['tow_class'][0]:.2f}, source corps x class "
      f"{resc['ac_class'][0]:.2f}, the regular unit's own r {resc['base_r'][0]:.2f}. "
      f"{rep['com_counts']['excluded_price1']} commander pairs priced 1 gold on one side are left out.")
    a("")
    a("### Staff generals (price above 1)")
    a("")
    row("Stars", "AC median P x N", "ToW median P x N", "ToW / AC", "pairs")
    row(*["---"] * 5)
    for s_, (va, vt, n_) in st["vtab"].items():
        row(s_, f"{va:.0f}", f"{vt:.0f}", f"{vt / va:.3f}", n_)
    a("")
    pr1 = st["price1"]
    a(f"- P_ToW = P_AC x N_AC/N_ToW x {st['f']:.3f}: {fmt_score(st['rule1'])}.")
    a(f"- P_ToW = V_ToW(stars)/N_ToW, ignoring P_AC: {fmt_score(st['rule2'])}.")
    a(f"- P x N is within rounding of its star value for {pct(st['tow_v_exact'])} of ToW staff but only "
      f"{pct(st['ac_v_exact'])} of AC staff. **ToW staff prices are regenerated from a per-star value, not scaled from "
      f"the AC price** (90th percentile |deviation| from the star value: AC "
      f"{100 * rep['staff_spread']['sd_ac']:.1f}%, ToW {100 * rep['staff_spread']['sd_tow']:.1f}%). "
      f"The ToW/AC ratio is "
      f"{min(rep['staff_spread']['lo_ratio']):.3f}-{max(rep['staff_spread']['lo_ratio']):.3f} for 1-6 stars, but "
      f"{min(rep['staff_spread']['hi_ratio']):.3f}-{max(rep['staff_spread']['hi_ratio']):.3f} for the "
      f"{rep['staff_spread']['hi_n']} pairs with 7+ stars.")
    a(f"- 0-star staff cost 1 gold in both modes ({pr1.get((True, True), 0)} pairs); {pr1.get((False, True), 0)} "
      f"0-star staff cost 2 in AC and 1 in ToW.")
    a("")

    a("## AC-only corps: ToW-equivalent prices (model-based)")
    a("")
    oc = rep["ac_only_counts"]
    a(f"`ac_only_tow_equivalent.csv` gives every unit of the {len(rep['ac_only'])} AC corps without a ToW copy "
      f"({oc.get('regular', 0)} regular, {oc.get('commander', 0)} commander and {oc.get('staff', 0)} staff rows) an "
      f"**estimated** ToW-equivalent price: what it would cost in a ToW army at its own corps number "
      f"(`tow_eq_own_n`) and at N = 8 (`tow_eq_n8`). **These are model estimates, not game data.**")
    a("")
    a("- Regular units: rule C, with the corps' own AC premium measured against the ToW-trained stats curve "
      "(fitted on all ToW units; these units were never seen). Fixed artillery uses rule B.")
    a("- Commanders: the regular estimate plus k x their AC mark-up.")
    a("- Staff: V_ToW(stars)/N for star levels with 10+ pairs, else P_AC x N_AC/N x f.")
    a("- Low/high: the 10th/90th percentiles of each rule's out-of-sample residuals (regular: rule C leave-corps-out "
      "per arm, " + ", ".join(f"{k} {100 * (math.exp(v[0]) - 1):+.0f}% / {100 * (math.exp(v[1]) - 1):+.0f}%"
                                  for k, v in rep["intervals"].items()) + ").")
    a("")
    row("AC corps", "N", "regular units", "sum ToW-eq / sum AC price (own N)", "mean cell premium e_A")
    row(*["---"] * 5)
    for f, name, n, k_, ratio, eam in rep["ac_only_summary"]:
        row(f"{name} (`{f}`)", n, k_, f"{ratio:.3f}", f"{eam:+.3f}")
    a("")
    a("A corps with a large positive premium (its AC prices well above the stats curve) gets the biggest ToW-equivalent "
      "cut; a corps priced near or below the curve keeps close to its AC price at its own N.")
    a("")

    a("## What remains unexplained")
    a("")
    a(f"- **Within-cell scatter**, sd {100 * wc['sd']:.1f}% (about {100 * (1 - res['ac_class'][0]):.0f}% of r's variance). "
      f"It is unrelated to stats, size, price level, training, speed, cap or formation, and it is not rounding. It is "
      f"largest in a few corps ({', '.join(n for _, n in rep['corps_within_sd']['noisiest'])}) and smallest in others "
      f"({', '.join(n for _, n in rep['corps_within_sd']['cleanest'])}). That points to unit-by-unit hand edits in "
      f"one mode, of which the superseded 1812/1814 rows are the visible part.")
    a(f"- **About {100 * (1 - (res['side_class_eA'][2] or 0) / max(res['ac_class'][1], 1e-9)):.0f}% of the "
      f"cross-validated cell structure** (CV R2 {res['ac_class'][1]:.2f} for the corps x class lookup against LCO R2 "
      f"{fmt(res['side_class_eA'][2])} for rule C) is not predictable without the pairs. Part of it is the proxy fair "
      f"price's own error.")
    a("- **Why each AC corps x class premium exists.** This study shows that ToW removes most of it; the AC price "
      "model (step 2) should say whether it is systematic (by N, side, era) or hand-set.")
    a("")
    a("## Caveats")
    a("")
    a(f"- The fair price is a self-contained ridge proxy (CV rmse {rep['fair_rmse']['tow']:.3f} log), weaker than the "
      "adopted ToW model. Rerun H7 and rule C once step 2's out-of-fold AC predictions exist.")
    a("- The N slope is identified only across source corps inside one ToW corps.")
    if rep["side_mismatch"]:
        a(f"- {rep['side_mismatch']} pairs have a different side label in AC and ToW; the AC side is used.")
    a("- AC-only estimates at N = 3-4 extrapolate below ToW's corps numbers (5-12) and rely on the fixed 1/N of the "
      "fair curve; the interval reflects the pairs' spread, not that extrapolation.")
    a("- Fixed artillery (4 pairs) is outside the fair model; its premium is set to 0.")
    a("- The commander rule's leave-corps-out score equals its in-sample score (2 parameters). The staff rules are "
      "in-sample: one factor, or one value per star level.")
    a("")
    (OUT / "natural_experiment_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
