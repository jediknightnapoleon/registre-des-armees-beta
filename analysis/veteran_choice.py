"""Veteran's choice: what elite players' Army Corps builds reveal about card value beyond the prices.

Step 3–4 of the study (the plan in work_in_progress/VETERAN_PROGRESS.md; report: analysis/VETERAN_CHOICE_REPORT.md).
Inputs are replay-derived and stay local (analysis/local/veteran/, gitignored): the builds extracted by
analysis/veteran_builds.py and the elite list the user picked (players.txt). Only code and aggregate
results are committed.

The idea. An elite player's build was chosen under the game's rules, prices and formation discounts. If
the card values we assume were what the player valued, the build should beat every build one card away
from it that the rules allow. So each elite build is compared with its legal one-card neighbours:
  - swap: one card out, another roster card in;  - drop: one card out;  - add: one roster card in;
always keeping the commander slot. Commander variants (combat generals leading a unit) are never swapped,
dropped or added either: the generals on offer rotate every few hours, so another general often wasn't
an option, and the user notes these choices are less reliable than the formation choices. A commander
variant takes the correction of the plain unit it leads. A neighbour must be recruitable: the cost after formation rebates
without the removed card, plus the list price of the added card, stays within 10 000 (the app's recruit
rule: a card is affordable when the discounted total so far plus its list price fits), and the rules
engine's limits hold (check_known_limits). The full set of builds is intractable; one-card changes respect
every rule and only ask that each choice was locally the best.

The model. A build's utility U = Σ card values + the commander's command term (slope · morale deficit D,
as analysis/ac_builds.py values the staff general; 0 when a combat general holds the slot). Among a build
and its neighbours, P(observed) = exp(s·U) / Σ exp(s·U'), a conditional logit with scale s. The command
term gets its own fitted weight κ (U = Σ values + κ · command term), so the card multipliers measure only
relative value, and κ says how strongly the builds back the hand-set command correction (1 = as set).
  - quality   card value = value_sb, the AC size-band model ("Quality" in the app); only s is fitted;
  - linear    value_sb · exp(θ_cell), one θ per class segment × size band cell (the cells of the
              size-band model itself), ridge prior θ ~ N(0, τ²): no evidence → Quality;
  - blend     value_sb^(1−a) · list price^a: one parameter a between the model (0) and the game's own price
              (1) — added after the net turned out to be mostly this (corr −0.92 with log value/price);
  - net       value_sb · exp(g(x)), g a small MLP of card features that every AC, ToW and Custom card has
              (stats, class, speed, size, training, abilities, price per model, value/price),
              output initialised at 0 (untrained = Quality), weight decay.
Prolific players are down-weighted: no player counts for more than CAP_PER_PLAYER builds. A parallel run
(--weighting winrate, the user's idea) also weights each player by their AC win odds: the Redcoatz AC win
rate shrunk toward the group's with WINRATE_PRIOR pseudo-games, as odds (wins per loss), scaled to mean 1
over builds — so the stronger the player, the more their choices count. Players marked "average weight"
in players.txt get multiplier 1 (the user's call when a win rate isn't a fair measure).

    py -3.13 analysis/veteran_choice.py neighbours [--workers 4]   # legal one-card neighbours (cached)
    py -3.13 analysis/veteran_choice.py fit [--weighting winrate]  # fits, validation, report
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac_builds as ab  # noqa: E402
import ac_pricing as ap  # noqa: E402
import checkpoints as ckpt  # noqa: E402
import class_structure as cs  # noqa: E402
import common  # noqa: E402
import cost_effective_builds as ceb  # noqa: E402
import unit_pricing as up  # noqa: E402
from pricing.final import FINAL  # noqa: E402

sys.path.insert(0, str(common.ROOT))
from tools import army_builder_rules as abr  # noqa: E402

LOCAL = common.LOCAL / "veteran"
FUNDS = 10_000
MAX_CARDS = common.MAX_CARDS
CAP_PER_PLAYER = 40               # no player counts for more than this many builds
WINRATE_PRIOR = 10                # --weighting winrate: pseudo-games at the group's win rate
COM_SUFFIX = re.compile(r"_com_\d+$")


# --- elite builds ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Build:
    match_id: str
    played_at: str
    faction: str
    player: str                   # the elite list's canonical name (first name on its line)
    commander: str
    units: tuple[str, ...]        # in recruit order


def read_players(path: Path = LOCAL / "players.txt") -> dict[str, str]:
    """Every name on the elite list → its line's first (canonical) name."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        names = [n.strip() for n in line.split("#", 1)[0].split(" | ") if n.strip()]
        for n in names:
            out[n] = names[0]
    return out


def elite_builds() -> list[Build]:
    names = read_players()
    out = []
    with (LOCAL / "ac_builds.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["legal"] == "1" and r["player"] in names:
                out.append(Build(r["match_id"], r["played_at"], r["faction_key"], names[r["player"]],
                                 r["commander_key"], tuple(r["unit_keys"].split())))
    return out


# --- the cards ---------------------------------------------------------------------------------------

@dataclass
class Cards:
    """Every valued AC card (units and commander variants; values_ac.csv), indexed 0..n-1."""
    keys: list[tuple[str, str]]               # (faction, unit_key)
    index: dict[tuple[str, str], int]
    value: np.ndarray                         # value_sb (gold at corps 8)
    cell: np.ndarray                          # class segment × size band, index into `cells`
    cells: list[str]
    is_com: np.ndarray                        # commander variant
    base: np.ndarray                          # the plain unit a commander variant leads (itself otherwise)
    deficit: np.ndarray                       # models × (M_REF − morale)₊, for the command term
    price: np.ndarray                         # list price (mp_cost)


def card_table() -> Cards:
    _, values, extra, _, _, _ = ab.load_inputs()
    command = ceb.Command(ab.LAMBDA["sb"], ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus())
    units, _ = ap.ac_units()
    cell_of: dict[tuple[str, str], str] = {}
    for u in units:
        kind = FINAL[u.arm].size
        cell_of[(u.faction, u.key)] = f"{cs.segment(u)}|{ap.band_of(up.size_of(u, kind), kind, common.SB_BANDS)}"
    keys = sorted(k for k in values["sb"] if not common.is_wip(k[0]))
    cell_names, cells = [], []
    for f, k in keys:
        c = cell_of.get((f, k)) or cell_of.get((f, COM_SUFFIX.sub("", k)))
        if c is None:
            raise SystemExit(f"no size-band cell for {f} {k}")
        cell_names.append(c)
    cells = sorted(set(cell_names))
    pos = {c: i for i, c in enumerate(cells)}
    index = {k: i for i, k in enumerate(keys)}
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    list_price = {(c.faction_key, c.unit_key): c.mp_cost for c in catalog.cards}
    base = np.array([index.get((f, COM_SUFFIX.sub("", k)), i) for i, (f, k) in enumerate(keys)])
    return Cards(keys, index, np.array([values["sb"][k] for k in keys]),
                 np.array([pos[c] for c in cell_names]), cells,
                 np.array([bool(COM_SUFFIX.search(k)) for _, k in keys]), base,
                 np.array([command.deficit(extra[k]) for k in keys]),
                 np.array([float(list_price[k]) for k in keys]))


def command_slope(faction: str, commander: str, extra: dict, command: ceb.Command, catalog) -> float:
    """Gold per unit of morale deficit that the commander slot adds (0 for a combat general in it)."""
    card = next(c for c in catalog.cards_for_faction(faction) if c.unit_key == commander)
    if abr.classify_general(card) != "staff":
        return 0.0
    e = extra[(faction, commander)]
    return command.slope({"stars": e["stars"], "fast": e["fast"]})


# --- neighbourhoods ----------------------------------------------------------------------------------

_W: dict = {}                     # per worker process: the catalog, rosters and valued keys


def _init_worker() -> None:
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    valued = defaultdict(set)
    with (common.TEAMS_OUT / "values_ac.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            valued[r["faction_key"]].add(r["unit_key"])
    _W.update(catalog=catalog, valued=valued)


def neighbours_of(build: Build) -> list[tuple[str | None, str | None]]:
    """The legal one-card neighbours of a build as (card out, card in); None = nothing out / in."""
    if not _W:
        _init_worker()
    catalog, f = _W["catalog"], build.faction
    roster = catalog.cards_for_faction(f)
    valued = _W["valued"][f]
    cards = catalog.resolve_selection(f, list(build.units))
    commander = catalog.resolve_selection(f, [build.commander])
    addable = [c for c in roster if c.unit_key in valued and c.unit_class != "artillery_fixed"]

    def legal(selection: list) -> bool:
        sel = selection + commander
        if len(sel) > MAX_CARDS:
            return False
        return abr.check_known_limits(sel, f, staff_slot_index=len(sel) - 1, recruitable_cards=roster).valid

    def cost(selection: list) -> int:
        return abr.calculate_army_cost(selection + commander, roster, f).final_cost

    out: list[tuple[str | None, str | None]] = []
    base_cost = cost(cards)
    for c in addable:                                               # add one card
        if base_cost + c.mp_cost <= FUNDS and legal(cards + [c]):
            out.append((None, c.unit_key))
    seen = set()
    for i, card in enumerate(cards):
        if card.unit_key in seen or card.unit_key not in valued:   # unvalued cards (e.g. a staff general
            continue                                                # fielded as a unit) stay in place
        seen.add(card.unit_key)
        rest = cards[:i] + cards[i + 1:]
        rest_cost = cost(rest)
        if rest_cost > FUNDS:                                       # removing it breaks a rebate group
            continue
        out.append((card.unit_key, None))                          # drop one card
        for c in addable:                                           # swap it for another
            if c.unit_key != card.unit_key and rest_cost + c.mp_cost <= FUNDS and legal(rest + [c]):
                out.append((card.unit_key, c.unit_key))
    return out


def all_neighbours(builds: list[Build], workers: int, started: float, fresh: bool = False) -> list[list]:
    """Neighbourhoods of every build, cached per build (match, faction, player)."""
    path = ckpt.veteran("neighbours")
    cache: dict = {} if fresh or not path.exists() else common.load_pickle(path)
    key = lambda b: (b.match_id, b.faction, b.player, b.commander, b.units)
    todo = [b for b in builds if key(b) not in cache]
    if todo:
        common.log(f"neighbourhoods: {len(todo)} builds to do ({len(builds) - len(todo)} cached), {workers} workers",
                   started)
        chunk = 100
        with ProcessPoolExecutor(workers, initializer=_init_worker) as pool:
            for start in range(0, len(todo), chunk):
                part = todo[start:start + chunk]
                for b, nb in zip(part, pool.map(neighbours_of, part, chunksize=5)):
                    cache[key(b)] = nb
                common.save_pickle(path, cache)
                common.log(f"  {min(start + chunk, len(todo))} / {len(todo)}", started)
    return [cache[key(b)] for b in builds]


# --- the choice problem --------------------------------------------------------------------------------

@dataclass
class Problem:
    """Every (build, neighbour) comparison. Row k: neighbour of build b[k] that takes card out[k] out and
    puts card inn[k] in (n_cards = no card); cmd[k] = the change in the commander's command term."""
    b: np.ndarray
    out: np.ndarray
    inn: np.ndarray
    cmd: np.ndarray
    w: np.ndarray                 # per build: player weight
    n_builds: int
    n_cards: int

    def subset(self, keep: np.ndarray, w: np.ndarray | None = None) -> "Problem":
        """The builds where keep[b], renumbered (optionally with new weights for them)."""
        new = np.cumsum(keep) - 1
        rows = keep[self.b]
        return Problem(new[self.b[rows]], self.out[rows], self.inn[rows], self.cmd[rows],
                       self.w[keep] if w is None else w, int(keep.sum()), self.n_cards)


def average_weight_players(path: Path = LOCAL / "players.txt") -> set[str]:
    """Players the user marked \"average weight\" in players.txt: their win rate isn't a fair measure (e.g. their
    AC wins aren't from clan league), so the win-rate run gives them the group-average multiplier."""
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        body, _, comment = line.partition("#")
        names = [n.strip() for n in body.split(" | ") if n.strip()]
        if names and "average weight" in comment:
            out.add(names[0])
    return out


def player_win_odds(players: set[str]) -> dict[str, float]:
    """Each elite player's AC win odds (Redcoatz results; clan games have none), shrunk toward the group's
    win rate with WINRATE_PRIOR pseudo-games."""
    names = read_players()
    wins, losses = Counter(), Counter()
    with (LOCAL / "ac_builds.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            p = names.get(r["player"])
            if p in players and r["result"] in ("win", "loss"):
                (wins if r["result"] == "win" else losses)[p] += 1
    pooled = sum(wins.values()) / max(1, sum(wins.values()) + sum(losses.values()))
    rate = {p: (wins[p] + WINRATE_PRIOR * pooled) / (wins[p] + losses[p] + WINRATE_PRIOR) for p in players}
    return {p: r / (1 - r) for p, r in rate.items()}


def player_weights(builds: list[Build], weighting: str = "equal") -> np.ndarray:
    n = Counter(b.player for b in builds)
    w = np.array([min(1.0, CAP_PER_PLAYER / n[b.player]) for b in builds])
    if weighting == "winrate":
        odds = player_win_odds({b.player for b in builds})
        m = np.array([odds[b.player] for b in builds])
        average = np.array([b.player in average_weight_players() for b in builds])
        m = m / np.average(m[~average], weights=w[~average])  # mean multiplier 1 over the others' builds
        m[average] = 1.0                                    # the marked players: the group average
        w = w * m / np.average(m, weights=w)
    return w


def assemble(builds: list[Build], nbs: list[list], cards: Cards, weighting: str = "equal") -> Problem:
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    _, _, extra, _, _, _ = ab.load_inputs()
    command = ceb.Command(ab.LAMBDA["sb"], ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus())
    n = len(cards.keys)
    dfx = np.append(cards.deficit, 0.0)
    rb, ro, ri, rc = [], [], [], []
    for bi, (b, nb) in enumerate(zip(builds, nbs)):
        slope = command_slope(b.faction, b.commander, extra, command, catalog)
        for o, i in nb:
            oi = n if o is None else cards.index[(b.faction, o)]
            ii = n if i is None else cards.index[(b.faction, i)]
            if (oi < n and cards.is_com[oi]) or (ii < n and cards.is_com[ii]):
                continue                                             # commander variants stay fixed
            rb.append(bi)
            ro.append(oi)
            ri.append(ii)
            rc.append(slope * (dfx[ii] - dfx[oi]))
    return Problem(np.array(rb), np.array(ro), np.array(ri), np.array(rc), player_weights(builds, weighting),
                   len(builds), n)


def nll(V: np.ndarray, log_s: float, prob: Problem, grad: bool = True, log_k: float = 0.0):
    """Σ_b w_b · −log P(build b), and its gradient in the card values V, log s and log κ."""
    s, k = np.exp(log_s), np.exp(log_k)
    Vx = np.append(V, 0.0)
    u = Vx[prob.inn] - Vx[prob.out] + k * prob.cmd                   # U(neighbour) − U(build)
    d = s * u
    m = np.zeros(prob.n_builds)
    np.maximum.at(m, prob.b, d)
    e = np.exp(d - m[prob.b])
    z = np.exp(-m) + np.bincount(prob.b, e, prob.n_builds)
    lse = m + np.log(z)                                              # −log P(build)
    loss = float(prob.w @ lse)
    if not grad:
        return loss, lse
    gd = prob.w[prob.b] * e / z[prob.b]                              # ∂loss/∂d
    gu = gd * s
    gV = (np.bincount(prob.inn, gu, prob.n_cards + 1) - np.bincount(prob.out, gu, prob.n_cards + 1))[:prob.n_cards]
    return loss, gV, float(gd @ d), float(gu @ (k * prob.cmd))


def beats_share(V: np.ndarray, prob: Problem, log_k: float = 0.0) -> np.ndarray:
    """Per build: the share of its legal one-card neighbours it is worth more than (1 for none)."""
    Vx = np.append(V, 0.0)
    worse = (Vx[prob.inn] - Vx[prob.out] + np.exp(log_k) * prob.cmd) < 0
    n = np.bincount(prob.b, minlength=prob.n_builds)
    k = np.bincount(prob.b, worse.astype(float), prob.n_builds)
    return np.where(n > 0, k / np.maximum(n, 1), 1.0)


LOG_K_BOUNDS = (np.log(0.01), np.log(10.0))     # κ, the command term's weight, kept within 0.01–10


def _minimize(fun, x0: np.ndarray, maxiter: int = 2000) -> np.ndarray:
    """L-BFGS-B; the last parameter is always log κ, bounded (its MLE can run to 0)."""
    from scipy.optimize import minimize
    bounds = [(None, None)] * (x0.size - 1) + [LOG_K_BOUNDS]
    res = minimize(fun, x0, jac=True, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": maxiter, "maxfun": 4 * maxiter})
    return res.x


# Quality: the size-band values as they are; only the scale s is fitted.
def fit_quality(prob: Problem, cards: Cards) -> dict:
    def fun(x):
        loss, _, gs, gk = nll(cards.value, x[0], prob, log_k=x[1])
        return loss, np.array([gs, gk])
    x = _minimize(fun, np.array([np.log(1 / 100), 0.0]))
    return {"kind": "quality", "log_s": float(x[0]), "log_k": float(x[1])}


# Linear: one log-multiplier per size-band cell, ridge prior N(0, τ²). A commander variant shares its
# plain unit's cell, so it gets that unit's multiplier.
def linear_values(cards: Cards, theta: np.ndarray) -> np.ndarray:
    return cards.value * np.exp(theta[cards.cell])


def fit_linear(prob: Problem, cards: Cards, tau: float, x0: np.ndarray | None = None) -> dict:
    nc = len(cards.cells)

    def fun(x):
        theta, log_s, log_k = x[:-2], x[-2], x[-1]
        V = linear_values(cards, theta)
        loss, gV, gs, gk = nll(V, log_s, prob, log_k=log_k)
        g_theta = np.bincount(cards.cell, gV * V, nc)
        return (loss + 0.5 * float(theta @ theta) / tau ** 2,
                np.concatenate([g_theta + theta / tau ** 2, [gs, gk]]))
    x = _minimize(fun, np.concatenate([np.zeros(nc), [np.log(1 / 100), 0.0]]) if x0 is None else x0)
    return {"kind": "linear", "tau": tau, "theta": x[:-2], "log_s": float(x[-2]), "log_k": float(x[-1]), "x": x}


# Blend: value_sb^(1−a) · price^a, between the price model (a = 0) and the game's list price (a = 1).
def blend_values(cards: Cards, a: float) -> np.ndarray:
    return cards.value * np.exp(a * np.log(cards.price / cards.value))


def fit_blend(prob: Problem, cards: Cards) -> dict:
    lr = np.log(cards.price / cards.value)

    def fun(x):
        a, log_s, log_k = x
        V = blend_values(cards, a)
        loss, gV, gs, gk = nll(V, log_s, prob, log_k=log_k)
        return loss, np.array([float(gV @ (V * lr)), gs, gk])
    x = _minimize(fun, np.array([0.0, np.log(1 / 100), 0.0]))
    return {"kind": "blend", "a": float(x[0]), "log_s": float(x[1]), "log_k": float(x[2])}


def model_values(model: dict, cards: Cards, X: np.ndarray | None = None) -> np.ndarray:
    if model["kind"] == "quality":
        return cards.value
    if model["kind"] == "blend":
        return blend_values(cards, model["a"])
    if model["kind"] == "linear":
        return linear_values(cards, model["theta"])
    return cards.value * np.exp(Net.forward(model["params"], X)[0][cards.base])   # commanders: their unit's g


# --- the small neural net (step 3b) ----------------------------------------------------------------------

NUMERIC = ("morale", "melee_attack", "melee_defense", "charge_bonus", "accuracy", "reload_skill", "range", "ammo",
           "rank_depth", "projectile_damage", "projectile_reload_time", "command_stars")
FLAGS = ("can_form_square", "has_stamina", "is_shock_resistant", "can_inspire", "has_guerrilla_deployment",
         "can_place_stakes", "can_place_mines", "scares_enemies", "can_build_barricades", "skirmish", "guard_mode",
         "can_snipe", "pike_square")
HIDDEN = 32


def card_features(cards: Cards) -> tuple[np.ndarray, list[str]]:
    """Inputs every AC, ToW and Custom card has (no corps identity, theatre or formation membership):
    stats, abilities, class, speed class, training, size (log models, guns), commander flag, log price per
    model and log(value_sb / price). Standardised over the AC cards."""
    with common.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = {(r["faction_key"], r["unit_key"]): r for r in csv.DictReader(fh)}
    rs = [rows[k] for k in cards.keys]
    num = lambda r, c: up.num(r[c]) if r[c] not in ("", None) else 0.0
    speed = [((up.SPEED_TAG_RE.search(r["unit_name"]) or [None, ""])[1] or "?").replace("GS", "S") for r in rs]
    cats = {"class": [cs.SEGMENT_OF.get(r["unit_class"], r["unit_class"]) for r in rs], "speed": speed,
            "training": [r["unit_training_level"] or "?" for r in rs]}
    cols, names = [], []
    for c in NUMERIC:
        cols.append([num(r, c) for r in rs])
        names.append(c)
    for c in FLAGS:
        cols.append([float(r[c] in ("1", "true", "True")) for r in rs])
        names.append(c)
    models = np.array([max(num(r, "men_raw") / 2, 1.0) for r in rs])
    price = np.array([max(num(r, "base_mp_cost"), 1.0) for r in rs])
    cols += [np.log(models), [num(r, "guns") for r in rs], cards.is_com.astype(float), np.log(price / models),
             np.log(np.maximum(cards.value, 1.0) / price)]
    names += ["log_models", "guns", "commander", "log_price_per_model", "log_value_over_price"]
    for cat, vals in cats.items():
        for level in sorted(set(vals)):
            cols.append([float(v == level) for v in vals])
            names.append(f"{cat}={level}")
    X = np.array(cols, float).T
    sd = X.std(0)
    X = (X - X.mean(0)) / np.where(sd > 0, sd, 1.0)
    return X, names


class Net:
    """g(x) = w3 · tanh(W2 · tanh(W1 x + b1) + b2) + b3, parameters as one flat vector."""

    @staticmethod
    def shapes(d: int) -> list[tuple[int, ...]]:
        return [(d, HIDDEN), (HIDDEN,), (HIDDEN, HIDDEN), (HIDDEN,), (HIDDEN,), (1,)]

    @staticmethod
    def unpack(p: np.ndarray, d: int) -> list[np.ndarray]:
        out, i = [], 0
        for s in Net.shapes(d):
            k = int(np.prod(s))
            out.append(p[i:i + k].reshape(s))
            i += k
        return out

    @staticmethod
    def init(d: int, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        W1 = rng.normal(0, 1 / np.sqrt(d), (d, HIDDEN))
        W2 = rng.normal(0, 1 / np.sqrt(HIDDEN), (HIDDEN, HIDDEN))
        return np.concatenate([W1.ravel(), np.zeros(HIDDEN), W2.ravel(), np.zeros(HIDDEN), np.zeros(HIDDEN), [0.0]])

    @staticmethod
    def forward(p: np.ndarray, X: np.ndarray):
        W1, b1, W2, b2, w3, b3 = Net.unpack(p, X.shape[1])
        h1 = np.tanh(X @ W1 + b1)
        h2 = np.tanh(h1 @ W2 + b2)
        return h2 @ w3 + b3[0], (h1, h2)

    @staticmethod
    def backward(p: np.ndarray, X: np.ndarray, cache, gg: np.ndarray) -> np.ndarray:
        W1, b1, W2, b2, w3, b3 = Net.unpack(p, X.shape[1])
        h1, h2 = cache
        gw3 = h2.T @ gg
        gh2 = np.outer(gg, w3) * (1 - h2 ** 2)
        gW2 = h1.T @ gh2
        gh1 = (gh2 @ W2.T) * (1 - h1 ** 2)
        gW1 = X.T @ gh1
        return np.concatenate([gW1.ravel(), gh1.sum(0), gW2.ravel(), gh2.sum(0), gw3, [gg.sum()]])

    @staticmethod
    def decay_mask(d: int) -> np.ndarray:
        """1 for weights and the output bias, 0 for the hidden biases."""
        return np.concatenate([np.ones(d * HIDDEN), np.zeros(HIDDEN), np.ones(HIDDEN * HIDDEN), np.zeros(HIDDEN),
                               np.ones(HIDDEN), [1.0]])                # the output bias too: its level would
                                                                       # otherwise trade off against s and κ


def fit_net(prob: Problem, cards: Cards, X: np.ndarray, lam: float, seed: int = 0, maxiter: int = 400) -> dict:
    d = X.shape[1]
    mask = Net.decay_mask(d)
    used = np.zeros(cards.value.size, bool)                         # only cards in some comparison carry signal
    used[prob.out[prob.out < prob.n_cards]] = True
    used[prob.inn[prob.inn < prob.n_cards]] = True
    idx = np.flatnonzero(used)
    Xu, vu = X[idx], cards.value[idx]
    remap = np.full(cards.value.size + 1, idx.size)
    remap[idx] = np.arange(idx.size)
    sub = Problem(prob.b, remap[prob.out], remap[prob.inn], prob.cmd, prob.w, prob.n_builds, idx.size)

    def fun(x):
        p, log_s, log_k = x[:-2], x[-2], x[-1]
        g, cache = Net.forward(p, Xu)
        V = vu * np.exp(g)
        loss, gV, gs, gk = nll(V, log_s, sub, log_k=log_k)
        gp = Net.backward(p, Xu, cache, gV * V)
        return loss + 0.5 * lam * float((mask * p) @ p), np.concatenate([gp + lam * mask * p, [gs, gk]])
    x = _minimize(fun, np.concatenate([Net.init(d, seed), [np.log(1 / 100), 0.0]]), maxiter)
    return {"kind": "net", "lam": lam, "params": x[:-2], "log_s": float(x[-2]), "log_k": float(x[-1])}


# --- validation --------------------------------------------------------------------------------------------

def group_folds(groups: list[str], weights: np.ndarray, k: int = 5) -> np.ndarray:
    """Fold per build: whole groups (players or corps), balanced by total weight, largest first."""
    tot = defaultdict(float)
    for g, w in zip(groups, weights):
        tot[g] += w
    load, fold_of = np.zeros(k), {}
    for g in sorted(tot, key=lambda g: (-tot[g], g)):
        f = int(np.argmin(load))
        fold_of[g] = f
        load[f] += tot[g]
    return np.array([fold_of[g] for g in groups])


TAUS = (0.1, 0.25, 0.5, 1.0)              # linear: prior sd of the log-multipliers
LAMS = (1.0, 10.0, 100.0)                # net: weight decay
N_BOOT = 200                             # bootstrap resamples of players (linear θ uncertainty)
TIME_SPLIT_QUANTILE = 0.8                # time split: the latest 20% of builds are held out

_P: dict = {}                            # per worker process: the problem, cards and net inputs


def _init_fit(prob: Problem, cards: Cards, X: np.ndarray) -> None:
    _P.update(prob=prob, cards=cards, X=X)


def _fit(kind: str, hyper: float | None, prob: Problem) -> dict:
    cards, X = _P["cards"], _P["X"]
    if kind == "quality":
        return fit_quality(prob, cards)
    if kind == "linear":
        return fit_linear(prob, cards, hyper)
    if kind == "blend":
        return fit_blend(prob, cards)
    return fit_net(prob, cards, X, hyper)


def _fold_job(job: tuple) -> tuple:
    """Fit on every fold but one, score the held-out one: (job, test mask, log P, beats, values)."""
    scheme, kind, hyper, folds, f = job
    prob, cards, X = _P["prob"], _P["cards"], _P["X"]
    tr, te = folds != f, folds == f
    model = _fit(kind, hyper, prob.subset(tr))
    sub = prob.subset(te)
    V = model_values(model, cards, X)
    lk = model["log_k"]
    return ((scheme, kind, hyper, f), te, -nll(V, model["log_s"], sub, grad=False, log_k=lk)[1],
            beats_share(V, sub, lk), V / np.exp(lk))   # the optimiser maximises Σ V/κ + command term


def _boot_job(job: tuple) -> np.ndarray:
    tau, seed, players = job
    prob = _P["prob"]
    rng = np.random.default_rng(seed)
    names = sorted(set(players))
    draw = Counter(rng.choice(len(names), len(names), replace=True).tolist())
    mult = np.array([draw[names.index(p)] for p in players], float)
    keep = mult > 0
    return fit_linear(prob.subset(keep, prob.w[keep] * mult[keep]), _P["cards"], tau)["theta"]


def cluster_diff(a: np.ndarray, b: np.ndarray, w: np.ndarray, players: list[str]) -> tuple[float, float]:
    """Weighted mean of a − b per build, with a standard error clustered by player (ratio estimator)."""
    d = a - b
    mean = float(w @ d / w.sum())
    tot, wt = defaultdict(float), defaultdict(float)
    for di, wi, p in zip(d, w, players):
        tot[p] += wi * di
        wt[p] += wi
    resid = np.array([tot[p] - mean * wt[p] for p in tot])
    return mean, float(np.sqrt((resid ** 2).sum()) / w.sum())


# --- build agreement: does the optimiser, valued this way, field what held-out veterans field? -------------

_S: dict = {}


def _init_solve() -> None:
    catalog, values, extra, _, _, t3 = ab.load_inputs()
    _S.update(catalog=catalog, extra=extra, t3=t3,
              command=ceb.Command(ab.LAMBDA["sb"], ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus()))


def _solve_job(job: tuple) -> tuple:
    tag, faction, values = job
    res = ab.solve_corps(faction, _S["catalog"], values, _S["extra"], _S["t3"], _S["command"], MAX_CARDS)
    chosen = {} if res is None else {c.unit_key: k for c, k in res["chosen"]}
    return tag, faction, chosen


def committed_builds(version: str, catalog) -> dict[str, Counter]:
    """ac_builds.py's committed optimal builds: faction → unit counts (staff generals left out)."""
    staff = {(c.faction_key, c.unit_key) for c in catalog.cards if abr.classify_general(c) == "staff"}
    out: dict[str, Counter] = defaultdict(Counter)
    with (common.TEAMS_OUT / f"ac_builds_{version}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r["faction_key"], r["unit_key"]) not in staff:
                out[r["faction_key"]][r["unit_key"]] += 1
    return out


def overlap(observed: tuple[str, ...], optimal: Counter, price: dict[str, int]) -> float:
    """Share of the observed build's list gold that the optimiser's build also fields (card by card)."""
    obs = Counter(observed)
    total = sum(price[k] * n for k, n in obs.items())
    return sum(price[k] * min(n, optimal.get(k, 0)) for k, n in obs.items()) / total if total else 0.0


# --- the run --------------------------------------------------------------------------------------------

def fit_all(builds: list[Build], nbs: list[list], workers: int, started: float, weighting: str = "equal") -> None:
    cards = card_table()
    prob = assemble(builds, nbs, cards, weighting)
    suffix = "" if weighting == "equal" else f"_{weighting}"
    X, xnames = card_features(cards)
    players = [b.player for b in builds]
    common.log(f"{prob.b.size} comparisons (commander variants fixed), {len(cards.cells)} size-band cells, "
               f"{X.shape[1]} net inputs", started)
    schemes = {"player": group_folds(players, prob.w), "corps": group_folds([b.faction for b in builds], prob.w)}
    when = np.array([b.played_at[:19] for b in builds], dtype="datetime64[s]").astype(float)
    schemes["time"] = (when >= np.quantile(when, TIME_SPLIT_QUANTILE)).astype(int)
    hypers = {"quality": (None,), "blend": (None,), "linear": TAUS, "net": LAMS}
    jobs = [(sc, kind, h, folds, f) for sc, folds in schemes.items() for kind, hs in hypers.items() for h in hs
            for f in (sorted(set(folds.tolist())) if sc != "time" else [1])]
    results: dict = defaultdict(lambda: {"lp": np.full(prob.n_builds, np.nan), "beat": np.full(prob.n_builds, np.nan),
                                         "V": {}})
    with ProcessPoolExecutor(workers, initializer=_init_fit, initargs=(prob, cards, X)) as pool:
        for i, ((sc, kind, h, f), te, lp, beat, V) in enumerate(pool.map(_fold_job, jobs), 1):
            r = results[(sc, kind, h)]
            r["lp"][te], r["beat"][te] = lp, beat
            r["V"][f] = V
            if i % 10 == 0 or i == len(jobs):
                common.log(f"  held-out fits {i} / {len(jobs)}", started)
    w = prob.w

    def score(sc, kind, h):
        r = results[(sc, kind, h)]
        m = ~np.isnan(r["lp"])
        return float(w[m] @ r["lp"][m] / w[m].sum()), float(w[m] @ r["beat"][m] / w[m].sum()), m
    best = {kind: max(hs, key=lambda h: score("player", kind, h)[0]) for kind, hs in hypers.items()}
    common.log(f"chosen by player CV: τ = {best['linear']}, weight decay = {best['net']}", started)

    # Final fits on every build, and the linear θ's bootstrap uncertainty (players resampled).
    with ProcessPoolExecutor(workers, initializer=_init_fit, initargs=(prob, cards, X)) as pool:
        boot = np.array(list(pool.map(_boot_job, [(best["linear"], s, players) for s in range(N_BOOT)])))
    _init_fit(prob, cards, X)
    final = {kind: _fit(kind, best[kind], prob) for kind in hypers}
    common.log(f"final fits and {N_BOOT} bootstrap fits done", started)

    # Build agreement on the player folds: the optimiser's build per held-out corps under each fold's values.
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    price = {(c.faction_key, c.unit_key): c.mp_cost for c in catalog.cards}
    folds = schemes["player"]
    solve_jobs = []
    for kind in ("blend", "linear", "net"):
        for f, V in results[("player", kind, best[kind])]["V"].items():
            for faction in sorted({b.faction for b, fb in zip(builds, folds) if fb == f}):
                vals = {cards.keys[i]: float(V[i]) for i in range(len(cards.keys)) if cards.keys[i][0] == faction}
                solve_jobs.append(((kind, f), faction, vals))
    solved: dict = {}
    with ProcessPoolExecutor(workers, initializer=_init_solve) as pool:
        for i, (tag, faction, chosen) in enumerate(pool.map(_solve_job, solve_jobs, chunksize=4), 1):
            solved[(tag, faction)] = Counter(chosen)
            if i % 100 == 0 or i == len(solve_jobs):
                common.log(f"  optimiser builds {i} / {len(solve_jobs)}", started)
    base = {v: committed_builds(v, catalog) for v in ("sb", "noise", "price")}
    agree = defaultdict(list)
    for b, f in zip(builds, folds):
        pr = {k: price[(b.faction, k)] for k in set(b.units)}
        for v in base:
            agree[v].append(overlap(b.units, base[v].get(b.faction, Counter()), pr))
        for kind in ("blend", "linear", "net"):
            agree[kind].append(overlap(b.units, solved[((kind, int(f)), b.faction)], pr))
    agree = {k: np.array(v) for k, v in agree.items()}

    # Outputs: replay-derived card values stay local; the aggregate report is committed.
    LOCAL.mkdir(parents=True, exist_ok=True)
    # Values as the optimiser would use them: it adds the hand-set command term, so V / κ.
    Vs = {kind: model_values(final[kind], cards, X) / np.exp(final[kind]["log_k"]) for kind in final}
    with (LOCAL / f"veteran_values{suffix}.csv").open("w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["faction_key", "unit_key", "cell", "list_price", "value_sb", "value_blend", "value_linear",
                     "value_net"])
        for i, (f, k) in enumerate(cards.keys):
            wr.writerow([f, k, cards.cells[cards.cell[i]], int(cards.price[i]), f"{cards.value[i]:.3f}",
                         f"{Vs['blend'][i]:.3f}", f"{Vs['linear'][i]:.3f}", f"{Vs['net'][i]:.3f}"])
    common.save_pickle(ckpt.veteran(f"fits{suffix}"), {"final": final, "best": best, "boot": boot, "agree": agree,
                                              "scores": {k: score(*k)[:2] for k in results}})
    write_report(builds, prob, cards, X, results, score, best, final, boot, agree, players, started, weighting)


def write_report(builds, prob, cards, X, results, score, best, final, boot, agree, players, started,
                 weighting: str = "equal") -> None:
    w = prob.w
    L = ["# Veteran's choice — what elite players' Army Corps builds say about card value"
         + (" (players weighted by AC win rate)" if weighting == "winrate" else ""),
         "", "Generated by `analysis/veteran_choice.py fit` (method in its docstring). Aggregates only: the",
         "row-level replay data (builds, player names) stays in `analysis/local/` and is not committed.", ""]
    years = Counter(b.played_at[:4] for b in builds)
    L += ["## Data", "",
          f"- **Builds:** {len(builds)} Army Corps builds by {len(set(players))} hand-picked elite players, in "
          f"{len({b.faction for b in builds})} corps; all legal at today's prices and rules. By year: "
          + ", ".join(f"{y} {n}" for y, n in sorted(years.items())) + ".",
          f"- **Comparisons:** {prob.b.size} legal one-card neighbours (swap, drop or add a card), commander "
          "variants and the commander slot kept fixed.",
          f"- **Weights:** no player counts for more than {CAP_PER_PLAYER} builds"
          + ("" if weighting == "equal" else
             f"; then × the player's AC win odds (Redcoatz results shrunk with {WINRATE_PRIOR} pseudo-games), scaled "
             f"to mean 1 — per-player multipliers from {min(w / player_weights(builds)):.2f} to "
             f"{max(w / player_weights(builds)):.2f}")
          + f" (effective builds {w.sum():.0f}).",
          f"- **Sources:** {sum(b.match_id.startswith('clan:') for b in builds)} of the builds are from Clan Games "
          "replays not on Redcoatz.", ""]
    L += ["## Held-out fit", "",
          "Mean log P(observed build among its neighbours) per build, out of sample, and the share of legal "
          "one-card alternatives the observed build is worth more than. Player folds: 5 folds of whole players. "
          "Corps folds: 5 folds of whole corps (unseen corps). Time: trained on the earliest 80%, tested on the "
          "latest 20%.", ""]
    rows = []
    q = {sc: results[(sc, "quality", None)]["lp"] for sc in ("player", "corps", "time")}
    for kind, hs in (("quality", (None,)), ("blend", (None,)), ("linear", TAUS), ("net", LAMS)):
        for h in hs:
            cells = [(f"blend (a = {final['blend']['a']:.2f})" if kind == "blend" else kind) if h is None
                     else f"{kind} ({'τ' if kind == 'linear' else 'decay'} {h:g})"]
            for sc in ("player", "corps", "time"):
                lp, beat, m = score(sc, kind, h)
                if kind == "quality":
                    cells.append(f"{lp:.4f} · {beat:.3f}")
                else:
                    d, se = cluster_diff(results[(sc, kind, h)]["lp"][m], q[sc][m], w[m], [p for p, k in zip(players, m) if k])
                    cells.append(f"{lp:.4f} · {beat:.3f} (Δ {d:+.4f} ± {se:.4f})")
            rows.append(cells + ["✓" if best.get(kind) == h and kind not in ("quality", "blend") else ""])
    L += common.table(["model", "player folds: log P · beats", "corps folds", "time split", "chosen"], rows)
    L += ["", "Δ = held-out log P minus Quality's on the same builds, ± a standard error clustered by player.", ""]
    L += ["## Command weight κ", "",
          "The commander's command term (λ · stars · morale deficit, hand-set) enters with a fitted weight κ: how "
          "strongly the elite builds back the hand-set correction (1 = as set; 0 = they ignore it).", ""]
    L += common.table(["model", "κ (final fit)"],
                      [[k, ("≤ 0.01 (at the bound: no support)" if final[k]['log_k'] <= LOG_K_BOUNDS[0] + 1e-6
                            else f"{np.exp(final[k]['log_k']):.2f}")] for k in ("quality", "blend", "linear", "net")])
    L += [""]

    nc = len(cards.cells)
    theta, se = final["linear"]["theta"], boot.std(0)
    used = np.zeros(nc)
    for arr in (prob.out, prob.inn):
        ok = arr < prob.n_cards
        used += np.bincount(cards.cell[arr[ok]], minlength=nc)
    L += ["## The linear correction (final fit)", "",
          f"One multiplier per class segment × size band (τ = {best['linear']}), × the Quality value. Only their "
          "ratios matter between cards (the overall level trades off with κ and s); ± a bootstrap "
          f"standard error over {N_BOOT} resamples of players. Sorted by multiplier; cells in fewer than 50 "
          "comparisons left out.", ""]
    order = [i for i in np.argsort(-theta) if used[i] >= 50]
    L += common.table(["class segment | size band", "multiplier", "± (log)", "comparisons"],
                      [[cards.cells[i], f"×{np.exp(theta[i]):.2f}", f"{se[i]:.2f}", int(used[i])] for i in order])
    raw_net = model_values(final["net"], cards, X)
    seg = defaultdict(list)
    for i, (f, k) in enumerate(cards.keys):
        if not cards.is_com[i]:
            seg[cards.cells[cards.cell[i]].split("|")[0]].append(np.log(raw_net[i] / cards.value[i]))
    L += ["", "## The neural style model (final fit)", "",
          f"Weight decay {best['net']:g}. Mean multiplier it applies per class segment (plain units; as above, "
          "only ratios between cards matter):", ""]
    L += common.table(["class segment", "mean multiplier", "spread (sd of log)"],
                      [[s, f"×{np.exp(np.mean(v)):.2f}", f"{np.std(v):.2f}"] for s, v in sorted(seg.items())])
    # What the net learned: a linear surrogate of its log-multiplier on its (standardised) inputs.
    plain = ~cards.is_com
    g = np.log(raw_net / cards.value)[plain]
    g = g - g.mean()
    Xp = X[plain]
    A = np.column_stack([Xp, np.ones(len(Xp))])
    fit = np.linalg.lstsq(A, g, rcond=None)[0]
    r2 = 1 - ((g - A @ fit) ** 2).sum() / (g ** 2).sum()
    coef = fit[:-1]
    xnames = card_features(cards)[1]
    lvp = np.log(cards.value / cards.price)[plain]
    lvp_net = np.log(raw_net / cards.price)[plain]
    L += ["", "### What the net learned", "",
          f"- A linear fit of its log-multiplier on its inputs explains R² = {r2:.2f} of it, so it is close to linear.",
          f"- Its log-multiplier correlates {np.corrcoef(lvp, g)[0, 1]:+.2f} with log(Quality value / list price): where the "
          "price model sees a bargain, the net shrinks it back toward the list price. The spread (sd) of log(value / "
          f"price) falls from {lvp.std():.3f} (Quality) to {lvp_net.std():.3f}; correlation of log value with log price "
          f"rises from {np.corrcoef(np.log(cards.value[plain]), np.log(cards.price[plain]))[0, 1]:.3f} to "
          f"{np.corrcoef(np.log(raw_net[plain]), np.log(cards.price[plain]))[0, 1]:.3f}.",
          f"- The one-parameter blend measures the same thing directly: value = Quality^(1−a) · price^a with "
          f"a = {final['blend']['a']:.2f}.",
          "- Its largest other inputs (log-multiplier per standard deviation of the input):", ""]
    order = [j for j in np.argsort(-np.abs(coef)) if xnames[j] != "log_value_over_price"][:8]
    L += common.table(["input", "per sd", "correlation with the multiplier"],
                      [[xnames[j], f"{coef[j]:+.3f}", f"{np.corrcoef(Xp[:, j], g)[0, 1]:+.2f}"] for j in order])
    L += ["", "## Build agreement (player folds)", "",
          "For each held-out elite build: the share of its list gold that the optimiser's best build for the same "
          "corps also fields, card by card, with the optimiser valuing cards each way. Quality / Quantity / "
          "Formation discount only are the committed builds (analysis/ac_builds.py); the veteran versions are "
          "re-optimised per fold with values fitted without that build's player.", ""]
    names = {"sb": "Quality (size bands)", "noise": "Quantity", "price": "Formation discount only",
             "blend": "Veteran's choice, blend", "linear": "Veteran's choice, linear", "net": "Veteran's choice, net"}
    L += common.table(["valuation", "mean overlap", "vs Quality"],
                      [[names[k], f"{np.average(v, weights=w):.3f}",
                        "" if k == "sb" else "{:+.3f} ± {:.3f}".format(*cluster_diff(v, agree["sb"], w, players))]
                       for k, v in agree.items()])
    adopt = {}
    for kind in ("blend", "linear", "net"):
        d, s_ = cluster_diff(results[("player", kind, best[kind])]["lp"], q["player"], w, players)
        a, sa = cluster_diff(agree[kind], agree["sb"], w, players)
        adopt[kind] = (d > 2 * s_) and (a > 2 * sa)
    L += ["", "## Decision", "",
          "Adoption rule (the plan): held-out likelihood and build agreement must both improve on Quality "
          "(here: by more than two standard errors, player folds).", ""]
    L += [f"- **{names[k]}:** {'passes' if v else 'does not pass'}." for k, v in adopt.items()]
    path = common.ANALYSIS / ("VETERAN_CHOICE_REPORT.md" if weighting == "equal"
                              else f"VETERAN_CHOICE_REPORT_{weighting.upper()}.md")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    common.log(f"report → {path}", started)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("neighbours", "fit"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--weighting", choices=("equal", "winrate"), default="equal")
    args = parser.parse_args()
    started = time.time()
    builds = elite_builds()
    common.log(f"{len(builds)} elite builds from {len({b.player for b in builds})} players, "
               f"{len({b.faction for b in builds})} corps", started)
    nbs = all_neighbours(builds, args.workers, started, args.fresh)
    sizes = np.array([len(n) for n in nbs])
    kinds = Counter(("add" if o is None else "drop" if i is None else "swap") for n in nbs for o, i in n)
    common.log(f"neighbours per build: median {np.median(sizes):.0f}, min {sizes.min()}, max {sizes.max()}; "
               f"{dict(kinds)}", started)
    if args.step == "fit":
        fit_all(builds, nbs, args.workers, started, args.weighting)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
