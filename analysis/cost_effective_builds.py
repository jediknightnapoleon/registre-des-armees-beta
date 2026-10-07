"""The most cost-effective legal build for every ToW / Custom army.

"Value" is normative: what the game's average pricing rule would charge for a
card's stats in a reference army. That is the per-class model V4 at corps number
8, imperial/coalition at the reference, and no army × unit-class adjustment.
Commander cards are valued by the commander model (given the true regular price)
applied to their unit's normative value, also at corps 8. A card whose actual
price is below its value gives more stats per gold than the game's own average
rule; a build's value ÷ cost is its cost-effectiveness.

For each army an integer programme maximises total value under the game's limits
for Theatre-of-War and Custom armies (tools/army_builder_rules.py; no brigade or
division discounts outside Army Corps):

- exactly one staff general (the army's cheapest) and at most one combat general
  (commander card), as the user specified (October 2026);
- 31 cards in total *including* the staff general, i.e. at most 30 units, as the
  app counts it (web/src/state/build.ts expandBuild puts the staff-slot card into
  the list that checkKnownLimits caps at MAX_TOTAL_UNIT_CARDS = 31; the game's
  Lua only states NTW3.MaxUnits() = 31). The app also lets a combat general take
  the staff slot; these builds always use a staff general there;
- 10 000 funds;
- foot artillery ≤ 2, horse artillery ≤ 1 (2 for a cavalry-only corps), heavy
  cavalry ≤ 10; a commander counts as its unit's class;
- each unit's `unit_cap`, shared by its commander versions;
- at most one general per unit.

Two builds per army:
- **max value:** no composition rule;
- **balanced:** at least 4 cavalry cards and 2 artillery cards, where the army
  has them.

**Left out:** units above 240 models. Both pricing models overprice very large
units by ~25–70% (PRICING_MODEL_REPORT.md §5), so their "value" would be
inflated; they are listed separately as possible bargains the model cannot value.

**Not checked:** a ToW army's roll. Its units come from several source corps on
a rotation, so a build may need a specific time window (the app's "Generate
times" finds it).

Inputs: committed outputs, analysis/commander_model_coefficients.csv, the
class_structure checkpoints. Outputs: analysis/output/cost_effective_builds.md
and cost_effective_builds.csv.

    python analysis/cost_effective_builds.py
"""

from __future__ import annotations

import csv
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402
from blind_ideas import FINAL  # noqa: E402
from class_structure import segmented, with_class_p  # noqa: E402
from commander_model import Pairs, design as commander_design  # noqa: E402

OUT = up.ROOT / "analysis" / "output"
V4_CACHE = up.ROOT / "analysis" / ".cache" / "class_structure"
BUDGET, MAX_CARDS, MAX_FOOT_ART, MAX_HEAVY_CAV = 10_000, 31, 2, 10
MAX_UNITS = MAX_CARDS - 1          # the staff general takes one of the 31 cards (as the app counts)
BIG_UNIT_MODELS = 240
NORM_FACTION = "__reference__"


def normative_values(units: list[up.Unit]) -> dict[tuple[str, str], float]:
    """V4's price for each regular unit at corps 8, coalition side, no army × class cell."""
    out = {}
    for arm in ("infantry", "cavalry", "artillery"):
        arm_units = up.slice_units(units, arm, "merged")
        kappa = pickle.loads((V4_CACHE / f"v2_{arm}_kappa.pkl").read_bytes())
        run, p_of = pickle.loads((V4_CACHE / f"v2_{arm}_V4.pkl").read_bytes())
        spec = up.joint_fclass_spec(FINAL[arm], kappa)
        d3 = segmented(up.design_for(spec, arm_units, arm), arm_units)
        norm = [replace(u, rating=up.REF_RATING, side="coalition", faction=NORM_FACTION) for u in arm_units]
        data = with_class_p(up.data_for(spec, norm), norm, spec, p_of)
        values = up.predict_total(run.full, d3, data, np.arange(len(norm)))
        out.update({(u.faction, u.key): float(v) for u, v in zip(arm_units, values)})
    return out


def commander_values(base_value: dict[tuple[str, str], float]) -> tuple[Pairs, np.ndarray]:
    """Commander model (given the true regular price) at the unit's normative value, corps 8, coalition."""
    c = Pairs()
    with open(OUT / "commander_model_coefficients.csv", encoding="utf-8") as fh:
        coef = {r["term"]: float(r["coefficient"]) for r in csv.DictReader(fh) if r["model"] == "given true P"}
    P = np.array([base_value[(r["faction_key"], r["regular_unit_key"])] for r in c.rows])
    c.corps = np.full(c.n, float(up.REF_RATING))
    c.imperial = np.zeros(c.n)
    X, names = commander_design(c, P)
    return c, np.maximum(1.0, X @ np.array([coef[n] for n in names]))


def main() -> int:
    started = time.time()
    units, staff, _, _ = up.load(up.load_ratings())
    caps = {}
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            caps[(r["faction_key"], r["unit_key"])] = int(up.num(r["unit_cap"]))
    value = normative_values(units)
    pairs, cmd_value = commander_values(value)
    up.log(f"normative values: {len(value)} regular units, {pairs.n} commanders", started)

    by_faction: dict[str, list[dict]] = defaultdict(list)
    for u in units:
        by_faction[u.faction].append({"kind": "unit", "key": u.key, "base": u.key, "name": u.name, "cls": u.unit_class,
                                      "arm": u.arm, "cost": u.cost, "value": value[(u.faction, u.key)],
                                      "models": u.n, "men": 2 * u.n, "cap": caps[(u.faction, u.key)]})
    for i, r in enumerate(pairs.rows):
        by_faction[r["faction_key"]].append({"kind": "commander", "key": r["commander_unit_key"], "base": r["regular_unit_key"],
                                             "name": r["commander_name"], "cls": r["unit_class"], "arm": r["arm"],
                                             "cost": float(r["commander_price"]), "value": float(cmd_value[i]),
                                             "models": float(r["commander_men"]) / 2, "men": float(r["commander_men"]),
                                             "cap": caps[(r["faction_key"], r["regular_unit_key"])]})
    staff_cost = defaultdict(lambda: None)     # the army's cheapest staff general
    staff_top = defaultdict(lambda: None)      # its highest-star staff general (cheapest on a tie)
    for g in staff:
        if staff_cost[g.faction] is None or g.cost < staff_cost[g.faction][0]:
            staff_cost[g.faction] = (g.cost, g.name)
        if staff_top[g.faction] is None or (-g.stars, g.cost) < (-staff_top[g.faction][2], staff_top[g.faction][0]):
            staff_top[g.faction] = (g.cost, g.name, g.stars)
    army_of = {u.faction: (u.corps, u.rating, u.side) for u in units}

    results, big_units = [], []
    for faction, cards in sorted(by_faction.items(), key=lambda t: army_of[t[0]]):
        big_units += [(army_of[faction][0], c) for c in cards if c["kind"] == "unit" and c["models"] > BIG_UNIT_MODELS]
        cards = [c for c in cards if c["models"] <= BIG_UNIT_MODELS]
        cavalry_only = not any(c["arm"] == "infantry" for c in cards)
        has_staff = staff_cost[faction] is not None
        best_counts = None
        for variant in ("max value", "balanced", "runner-up", "top staff"):
            # runner-up: the best max-value build other than the best one — at least one copy
            # fewer among the best build's cards, so it differs in at least one unit.
            # top staff: the max-value build with the army's highest-star staff general instead.
            general = staff_top[faction] if variant == "top staff" else staff_cost[faction]
            sol = solve(cards, general[0] if has_staff else None, cavalry_only,
                        "max value" if variant == "top staff" else variant,
                        exclude=best_counts if variant == "runner-up" else None)
            if sol is None:
                continue
            chosen, slot = sol
            if variant == "max value":
                position = {id(c): j for j, c in enumerate(cards)}
                best_counts = [(position[id(c)], k) for c, k in chosen]
            cost = sum(c["cost"] * k for c, k in chosen) + (general[0] if slot == "staff" else 0)
            val = sum(c["value"] * k for c, k in chosen)
            arms = Counter()
            for c, k in chosen:
                arms[c["arm"]] += k
            results.append({"faction": faction, "army": army_of[faction][0], "N": army_of[faction][1],
                            "side": army_of[faction][2], "variant": variant, "cost": cost, "value": val,
                            "efficiency": val / cost, "cards": sum(k for _, k in chosen),
                            "arms": arms, "men": sum(c["men"] * k for c, k in chosen), "chosen": chosen,
                            "slot": f"{general[1]} ({general[0]} gold)"
                                    + (f", {general[2]}★" if variant == "top staff" else "")})
        up.log(f"{army_of[faction][0][:40]:40} done", started)

    write_outputs(results, big_units, value, by_faction, started)
    return 0


def solve(cards: list[dict], staff_cost: float | None, cavalry_only: bool, variant: str,
          exclude: list[tuple[int, int]] | None = None):
    """MILP: integer copies of each regular card, 0/1 per commander card, 0/1 for the staff general.
    `exclude` = (card index, copies) of a build to rule out: at least one copy fewer among its cards."""
    n = len(cards)
    nv = n + 1                                         # last variable: staff general in the slot
    c_obj = np.array([-c["value"] + 1e-6 * c["cost"] for c in cards] + [0.0])
    ub = np.array([float(min(c["cap"] if c["cap"] > 0 else MAX_UNITS, MAX_UNITS)) if c["kind"] == "unit" else 1.0
                   for c in cards] + [1.0 if staff_cost is not None else 0.0])
    integrality = np.ones(nv)
    rows, lo, hi = [], [], []

    def add(coeffs: dict[int, float], low: float, high: float) -> None:
        row = np.zeros(nv)
        for j, v in coeffs.items():
            row[j] = v
        rows.append(row)
        lo.append(low)
        hi.append(high)

    staff = n
    cmd = [j for j, c in enumerate(cards) if c["kind"] == "commander"]
    add({**{j: c["cost"] for j, c in enumerate(cards)}, staff: staff_cost or 0.0}, 0, BUDGET)
    add({j: 1.0 for j in range(n)}, 0, MAX_UNITS)          # 30 units + the staff general = 31 cards
    add({staff: 1.0}, 1, 1)                                 # exactly one staff general
    if cmd:
        add({j: 1.0 for j in cmd}, 0, 1)                    # at most one combat general among the units
    for cls, cap in (("artillery_foot", MAX_FOOT_ART), ("artillery_horse", 2 if cavalry_only else 1), ("cavalry_heavy", MAX_HEAVY_CAV)):
        idx = [j for j, c in enumerate(cards) if c["cls"] == cls]
        if idx:
            add({j: 1.0 for j in idx}, 0, cap)
    groups: dict[str, list[int]] = defaultdict(list)
    for j, c in enumerate(cards):
        groups[c["base"]].append(j)
    for base, idx in groups.items():
        cap = cards[idx[0]]["cap"]
        if cap > 0 and len(idx) > 1:
            add({j: 1.0 for j in idx}, 0, cap)
        g_cmd = [j for j in idx if cards[j]["kind"] == "commander"]
        if len(g_cmd) > 1:
            add({j: 1.0 for j in g_cmd}, 0, 1)        # one general per unit
    if variant == "balanced":
        for arm, minimum in (("cavalry", 4), ("artillery", 2)):
            idx = [j for j, c in enumerate(cards) if c["arm"] == arm]
            if idx:
                add({j: 1.0 for j in idx}, min(minimum, sum(ub[j] for j in idx)), MAX_CARDS)
    if exclude:
        add({j: 1.0 for j, _ in exclude}, 0, sum(k for _, k in exclude) - 1)
    res = milp(c_obj, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality,
               bounds=Bounds(np.zeros(nv), ub), options={"time_limit": 60})
    if res.x is None:
        return None
    x = np.round(res.x).astype(int)
    chosen = [(cards[j], int(x[j])) for j in range(n) if x[j] > 0]
    return sorted(chosen, key=lambda t: -t[0]["value"] * t[1]), ("staff" if x[staff] else "commander")


def write_outputs(results, big_units, value, by_faction, started) -> None:
    best = [r for r in results if r["variant"] == "max value"]
    best.sort(key=lambda r: -r["efficiency"])
    L = ["# The most cost-effective build for every ToW / Custom army", "",
         "Generated by `analysis/cost_effective_builds.py`. **Value** is normative: what the game's average pricing "
         "rule charges for a card's stats in a reference army, i.e. the per-class model V4 at corps number 8 with no "
         "army × unit-class adjustment; commanders valued by the commander model on that value. **Efficiency** = "
         "total value ÷ total cost: 1.00 means the build gets exactly the stats its price buys under the average "
         "rule, 1.20 means 20% more.", "",
         "Each build is the build with the most total value under these rules:",
         "",
         "- one staff general (the army's cheapest) and at most one combat general;",
         "- 31 cards in total *including* the staff general, i.e. 30 units, as the app counts it "
         "(`web/src/state/build.ts`: the staff-slot card is part of the 31);",
         "- 10 000 funds, including the staff general;",
         "- the artillery and heavy-cavalry caps, and each unit's cap.",
         "",
         "*cards* counts the units, not the staff general.", "",
         "> **How to read this.**",
         ">",
         "> - **A higher corps number makes everything cheaper.** Price scales with 8/N, so armies with a high "
         "number come out more efficient by construction; whether the game balances that elsewhere is not in the data.",
         "> - **Value is stats as the game prices them, not battle power.** Mass and morale may matter more in "
         "battle than the price rule says (see the HRE discussion).",
         f"> - **Units above {BIG_UNIT_MODELS} models are left out**, because the models overprice very large units; "
         "they are listed at the end.",
         "> - **A ToW army's roll is not checked.** A build may need a specific time window, which the app's "
         "\"Generate times\" finds.",
         "> - **Expect some winner's curse.** The optimiser picks the cards that look most underpriced, and part of "
         "that is model error (a few % per unit), so true efficiencies are somewhat lower than shown, more so for "
         "single-unit picks than for the army ranking.", "",
         "## 1. All armies, ranked by efficiency (max-value build)", ""]
    rows = []
    for r in best:
        bal = next((x for x in results if x["faction"] == r["faction"] and x["variant"] == "balanced"), None)
        rows.append([r["army"], r["N"], r["side"], f"{r['efficiency']:.3f}", f"{r['efficiency'] * up.REF_RATING / r['N']:.3f}",
                     f"{bal['efficiency']:.3f}" if bal else "—",
                     f"{r['value']:,.0f}", f"{r['cost']:,.0f}", r["cards"],
                     f"{r['arms']['infantry']}/{r['arms']['cavalry']}/{r['arms']['artillery']}", f"{r['men']:,.0f}"])
    L += up.table(["army", "N", "side", "efficiency", "vs own rating", "balanced", "value", "cost", "cards",
                   "inf/cav/art", "men"], rows)
    L += ["", "- *efficiency*: stats per gold against a corps-8 reference. This is what 10 000 gold actually buys; "
          "a high corps number helps, because price scales with 8/N.",
          "- *vs own rating*: the same build's value measured at the army's own corps number (efficiency × N/8). "
          "This removes the 8/N effect and shows how well the army is priced *for its rating*: its army × class "
          "adjustments and the bargains in its roster. The best build is the same under both measures.",
          "- *balanced*: the best build with at least 4 cavalry and 2 artillery cards.", ""]
    neutral = sorted(best, key=lambda r: -r["efficiency"] * up.REF_RATING / r["N"])
    L += ["**Best priced for their rating** (vs own rating, top 10): " + "; ".join(
        f"{r['army']} {r['efficiency'] * up.REF_RATING / r['N']:.3f}" for r in neutral[:10]) + ".", "",
          "**Worst priced for their rating** (bottom 5): " + "; ".join(
        f"{r['army']} {r['efficiency'] * up.REF_RATING / r['N']:.3f}" for r in neutral[-5:]) + ".", "",
          "## 2. The builds", "",
          "Per army: the max-value build, then the balanced one if it differs. `×k` = copies; value/cost per card in "
          "brackets.", ""]
    for r in best:
        for v in ("max value", "balanced"):
            x = next((y for y in results if y["faction"] == r["faction"] and y["variant"] == v), None)
            if x is None:
                continue
            if v == "balanced" and sorted((c["key"], k) for c, k in x["chosen"]) == sorted((c["key"], k) for c, k in r["chosen"]):
                L += ["*(balanced build: the same)*", ""]
                continue
            L += [f"### {r['army']} — {v}: efficiency {x['efficiency']:.3f}, cost {x['cost']:,.0f}, "
                  f"value {x['value']:,.0f}, {x['cards']} cards, {x['men']:,.0f} men", "",
                  f"Staff general: {x['slot']}.", ""]
            L += [f"- {c['name']} ×{k} ({c['cost']:.0f} gold, value {c['value']:.0f}, ×{c['value'] / c['cost']:.2f})"
                  + (" — combat general" if c["kind"] == "commander" else "") for c, k in x["chosen"]]
            L += [""]
    L += [f"## 3. Units above {BIG_UNIT_MODELS} models (not valued)", "",
          "Possible bargains the models cannot value reliably: they overprice units this size, so the ratio "
          "below overstates their value, by up to ~70% for the largest.", ""]
    L += up.table(["army", "unit", "men", "cost", "model value (inflated)"],
                  [[a, c["name"], f"{c['men']:.0f}", f"{c['cost']:.0f}", f"{c['value']:.0f} (×{c['value'] / c['cost']:.2f})"]
                   for a, c in sorted(big_units, key=lambda t: -t[1]["men"])])
    L += ["", f"*Runtime {time.time() - started:.0f} s.*", ""]
    (OUT / "cost_effective_builds.md").write_text("\n".join(L), encoding="utf-8")
    with open(OUT / "cost_effective_builds.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["army_corps_name", "faction_key", "variant", "card", "unit_key", "kind", "unit_class", "copies",
                    "cost_each", "value_each", "value_per_cost"])
        for x in results:
            for c, k in x["chosen"]:
                w.writerow([x["army"], x["faction"], x["variant"], c["name"], c["key"], c["kind"], c["cls"], k,
                            f"{c['cost']:.0f}", f"{c['value']:.1f}", f"{c['value'] / c['cost']:.3f}"])
    up.log("done → analysis/output/cost_effective_builds.md, cost_effective_builds.csv", started)


if __name__ == "__main__":
    raise SystemExit(main())
