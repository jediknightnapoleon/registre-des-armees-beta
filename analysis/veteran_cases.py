"""Veteran's choice in practice: its optimal builds against Quantity and Formation discount only, and case
studies of the corps elite players field most.

Uses the Veteran's choice values of analysis/veteran_choice.py (the neural model, equal player weights:
analysis/local/veteran/veteran_values.csv, values as the optimiser uses them) and re-optimises every Army Corps
with them (ac_builds.solve_corps, the app's rules: 31 cards, formation rebates, recruit order). Quantity and
Formation discount only are the committed builds (analysis/output/teams/ac_builds_noise.csv / _price.csv).
Elite builds are the hand-picked players' legal builds (analysis/veteran_builds.py), aggregated per corps:
no player is named.

    py -3.13 analysis/veteran_cases.py [--workers 6] [--min-builds 25]
    → analysis/VETERAN_CASE_STUDIES.md
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac_builds as ab  # noqa: E402
import checkpoints as ckpt  # noqa: E402
import common  # noqa: E402
import cost_effective_builds as ceb  # noqa: E402
import veteran_choice as vc  # noqa: E402

sys.path.insert(0, str(common.ROOT))
from tools import army_builder_rules as abr  # noqa: E402

REPORT = common.ANALYSIS / "VETERAN_CASE_STUDIES.md"
VERSIONS = {"quantity": "Quantity", "price": "Formation discount only", "veteran": "Veteran's choice"}
DETAILED = 12                     # corps written up in full; the rest of the frequent ones in a summary table

_S: dict = {}


def _init() -> None:
    catalog, _, extra, _, _, t3 = ab.load_inputs()
    _S.update(catalog=catalog, extra=extra, t3=t3,
              command=ceb.Command(ab.LAMBDA["sb"], ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus()))


def _solve(job: tuple) -> tuple:
    faction, values = job
    res = ab.solve_corps(faction, _S["catalog"], values, _S["extra"], _S["t3"], _S["command"], common.MAX_CARDS)
    if res is None:
        return faction, None
    return faction, {"units": {c.unit_key: k for c, k in res["chosen"]}, "general": res["general"].unit_key,
                     "list": res["price"].base_cost, "rebate": res["price"].applied_discount,
                     "final": res["price"].final_cost, "groups": len(res["completed"])}


def veteran_builds(workers: int, started: float) -> dict[str, dict]:
    """Every AC corps' optimal build under the Veteran's choice (net) values, cached."""
    values: dict[str, dict] = defaultdict(dict)
    with (vc.LOCAL / "veteran_values.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            values[r["faction_key"]][(r["faction_key"], r["unit_key"])] = float(r["value_net"])
    def compute() -> dict:
        out = {}
        with ProcessPoolExecutor(workers, initializer=_init) as pool:
            for f, res in pool.map(_solve, sorted(values.items()), chunksize=4):
                if res:
                    out[f] = res
        common.log(f"veteran builds: {len(out)} corps", started)
        return out
    return common.cached(ckpt.veteran("case_builds"), compute)


def committed(version: str, staff: set) -> tuple[dict[str, Counter], dict[str, dict]]:
    """ac_builds.py's committed builds (units without the staff general) and their summary rows."""
    units: dict[str, Counter] = defaultdict(Counter)
    with (common.TEAMS_OUT / f"ac_builds_{version}.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r["faction_key"], r["unit_key"]) not in staff:
                units[r["faction_key"]][r["unit_key"]] += 1
    with (common.TEAMS_OUT / f"ac_build_summary_{version}.csv").open(encoding="utf-8") as fh:
        summary = {r["faction_key"]: r for r in csv.DictReader(fh) if r["cards"]}
    return units, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--min-builds", type=int, default=25, help="elite builds a corps needs for a case study")
    args = parser.parse_args()
    started = time.time()
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    card = {(c.faction_key, c.unit_key): c for c in catalog.cards}
    staff = {k for k, c in card.items() if abr.classify_general(c) == "staff"}
    with common.DATA_CSV.open(encoding="utf-8-sig") as fh:
        data = {(r["faction_key"], r["unit_key"]): r for r in csv.DictReader(fh)}
    vet = veteran_builds(args.workers, started)
    builds: dict[str, dict[str, Counter]] = {"veteran": {f: Counter(r["units"]) for f, r in vet.items()}}
    summary: dict[str, dict[str, dict]] = {"veteran": {f: {"list_cost": r["list"], "rebate": r["rebate"],
                                                           "final_cost": r["final"], "groups_completed": r["groups"]}
                                                       for f, r in vet.items()}}
    for v in ("quantity", "price"):
        builds[v], summary[v] = committed("noise" if v == "quantity" else v, staff)
    corps = sorted(set(builds["veteran"]) & set(builds["quantity"]) & set(builds["price"]))

    def arm(f: str, k: str) -> str:
        cls = data[(f, k)]["unit_class"]
        return "artillery" if cls.startswith("artillery") else "cavalry" if cls.startswith("cavalry") else "infantry"

    def overlap(a: Counter, b: Counter, f: str) -> float:
        """Share of a's list gold that b also fields, card by card."""
        tot = sum(card[(f, k)].mp_cost * n for k, n in a.items())
        return sum(card[(f, k)].mp_cost * min(n, b.get(k, 0)) for k, n in a.items()) / tot if tot else 0.0

    def stats(v: str) -> dict:
        gold, n_cards, inf_models, big, small, com, tot = Counter(), [], [], 0, 0, 0, 0
        for f in corps:
            b = builds[v][f]
            n_cards.append(sum(b.values()))
            for k, c in b.items():
                gold[arm(f, k)] += card[(f, k)].mp_cost * c
                tot += c
                com += c * ("_com_" in k)
                m = float(data[(f, k)]["men_raw"]) / 2
                if arm(f, k) == "infantry":
                    inf_models += [m] * c
                if arm(f, k) != "artillery":
                    big += c * (m >= 180)
                    small += c * (m <= 60)
        g = sum(gold.values())
        s = [summary[v][f] for f in corps]
        return {"unit cards": f"{np.mean(n_cards):.1f}", "infantry / cavalry / artillery (% of gold)":
                f"{100 * gold['infantry'] / g:.0f} / {100 * gold['cavalry'] / g:.0f} / {100 * gold['artillery'] / g:.1f}",
                "median infantry unit (models)": f"{np.median(inf_models):.0f}",
                "cards of 180+ models / ≤ 60 models": f"{100 * big / tot:.1f}% / {100 * small / tot:.1f}%",
                "commander variants": f"{100 * com / tot:.1f}%",
                "list value fielded (face)": f"{np.mean([float(x['list_cost']) for x in s]):.0f}",
                "formation rebate": f"{np.mean([float(x['rebate']) for x in s]):.0f}",
                "formations completed": f"{np.mean([float(x['groups_completed']) for x in s]):.2f}"}

    st = {v: stats(v) for v in VERSIONS}
    L = ["# Veteran's choice in practice — against Quantity and Formation discount only",
         "", "Generated by `analysis/veteran_cases.py` (method in its docstring). Aggregates only: no player is named.", "",
         f"## 1. Optimal builds over {len(corps)} Army Corps", "",
         "Each corps' best build under each valuation (31 cards, formation rebates and the recruit-order rule; "
         "unit cards exclude the staff general).", ""]
    L += common.table(["", *VERSIONS.values()], [[k, *(st[v][k] for v in VERSIONS)] for k in st["quantity"]])
    pairs = [("veteran", "price"), ("veteran", "quantity"), ("price", "quantity")]
    L += ["", "How much two optimal builds share (median over corps; share of the first build's list gold that the "
          "second also fields):", ""]
    L += common.table(["builds", "median shared", "quartiles"],
                      [[f"{VERSIONS[a]} ∩ {VERSIONS[b]}",
                        f"{np.median([overlap(builds[a][f], builds[b][f], f) for f in corps]):.2f}",
                        "{:.2f}–{:.2f}".format(*np.percentile([overlap(builds[a][f], builds[b][f], f) for f in corps],
                                                               [25, 75]))] for a, b in pairs])
    # What each favours: picks across all corps by class segment × size band.
    cell = {}
    with (vc.LOCAL / "veteran_values.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cell[(r["faction_key"], r["unit_key"])] = r["cell"]
    picks = {v: Counter() for v in VERSIONS}
    for v in VERSIONS:
        for f in corps:
            for k, c in builds[v][f].items():
                picks[v][cell.get((f, k), "?")] += c
    cells = sorted(set().union(*picks.values()),
                   key=lambda c: -(abs(picks["veteran"][c] - picks["price"][c]) + abs(picks["veteran"][c] - picks["quantity"][c])))
    L += ["", "Cards picked across all corps, by class segment and size band — the 16 cells where the three differ most:", ""]
    L += common.table(["class segment | size band", *VERSIONS.values()],
                      [[c, *(picks[v][c] for v in VERSIONS)] for c in cells[:16]])

    # --- 2. case studies ------------------------------------------------------------------------------------
    elite = defaultdict(list)
    for b in vc.elite_builds():
        elite[b.faction].append(b)
    frequent = sorted((f for f in elite if len(elite[f]) >= args.min_builds and f in corps), key=lambda f: -len(elite[f]))
    name = lambda f, k: data[(f, k)]["unit_name"]
    agree = {v: [] for v in VERSIONS}
    rows_summary = []
    detail = []
    for f in frequent:
        eb = elite[f]
        players = len({b.player for b in eb})
        obs = [Counter(b.units) for b in eb]
        per_v = {v: np.mean([overlap(o, builds[v][f], f) for o in obs]) for v in VERSIONS}
        for v in VERSIONS:
            agree[v] += [overlap(o, builds[v][f], f) for o in obs]
        corps_name = data[(f, next(iter(builds["quantity"][f])))]["army_corps_name"]
        best = max(per_v, key=per_v.get)
        rows_summary.append([corps_name, len(eb), players, *(f"{per_v[v]:.2f}" for v in VERSIONS), VERSIONS[best]])
        if len(detail) >= DETAILED:
            continue
        share = Counter(k for o in obs for k in o)                     # builds that field the card
        copies = Counter()
        for o in obs:
            copies.update(o)
        keys = {k for k, n in share.items() if n / len(eb) >= 0.25} | set().union(*(builds[v][f] for v in VERSIONS))
        keys = sorted(keys, key=lambda k: (-share[k] / len(eb), name(f, k)))
        D = [f"### {corps_name}", "",
             f"{len(eb)} elite builds by {players} players. Mean share of an elite build's list gold that each optimiser "
             "build also fields: " + ", ".join(f"{VERSIONS[v]} {per_v[v]:.2f}" for v in VERSIONS) + ".", ""]
        tab = []
        for k in keys:
            m = float(data[(f, k)]["men_raw"]) / 2
            size = f"{data[(f, k)]['guns']} guns" if arm(f, k) == "artillery" and data[(f, k)]["guns"] else f"{m:.0f}"
            tab.append([name(f, k)[:48], size, card[(f, k)].mp_cost,
                        f"{100 * share[k] / len(eb):.0f}% ({copies[k] / max(1, share[k]):.1f})",
                        *(builds[v][f].get(k, "") for v in VERSIONS)])
        D += common.table(["card", "size", "price", "elite: fielded in (copies when fielded)", *VERSIONS.values()], tab)
        s_e = np.mean([sum(card[(f, k)].mp_cost * n for k, n in o.items()) for o in obs])
        D += ["", f"Elite builds field {np.mean([sum(o.values()) for o in obs]):.1f} unit cards on average "
              f"({s_e:.0f} list gold); the optimiser builds field "
              + ", ".join(f"{VERSIONS[v]} {sum(builds[v][f].values())}" for v in VERSIONS) + ".", ""]
        detail += D
    L += ["", f"## 2. Case studies — the corps with at least {args.min_builds} elite builds", "",
          f"{len(frequent)} corps. For each: the mean share of an elite build's list gold that each optimiser's build "
          "also fields (higher = closer to what elite players actually field), and which valuation comes closest. "
          "Veteran's choice was fitted on these builds (in sample here; the held-out comparison is in "
          "VETERAN_CHOICE_REPORT.md: Quantity 0.376, Formation discount only 0.385, Veteran's choice 0.409).", ""]
    L += common.table(["corps", "elite builds", "players", *VERSIONS.values(), "closest"], rows_summary)
    wins = Counter(r[-1] for r in rows_summary)
    L += ["", "Closest valuation, count of corps: " + ", ".join(f"{k} {n}" for k, n in wins.most_common()) + ".",
          "", f"### The {min(DETAILED, len(frequent))} most-played corps in detail", "",
          "Every card fielded in at least a quarter of the elite builds or picked by any optimiser; the optimiser "
          "columns give its copies.", ""]
    L += detail
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    common.log(f"{len(corps)} corps compared, {len(frequent)} case studies → {REPORT}", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
