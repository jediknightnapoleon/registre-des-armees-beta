"""Do size-weighted values change which unit sizes the optimiser picks? (analysis/SIZE_WEIGHTING_PLAN.md)

The user's point (2026-10-11): a pricing residual is not only error — it can be a unit's real strength or
weakness, so fitting the extreme sizes better (analysis/experiments/size_weighting.py) may make mid-sized units look
more cost-effective. This reruns the optimisers on each set of values and counts the picked cards by size
band of their base unit:
  raw, quantity (noise), quality (full), sb (size bands)       the values the app and the study use;
  w:a0.5c10, w:a1c10, w:a1                                     the weighted V4 (nested) at corps 8.
ToW + Custom: cost_effective_builds.army_builds "max value" (31 cards); AC: ac_builds.solve_corps (rebates
included). Weighted / raw values use the noise λ of the command correction (unharmonised scale).
One checkpoint per dataset × value set in analysis/.cache/size_weighting/builds_*.pkl (resumable).

    py -3.13 analysis/experiments/size_weighting_builds.py            # → analysis/output/size_weighting_builds.md
"""

from __future__ import annotations

import csv
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # analysis/
sys.path.insert(0, str(Path(__file__).resolve().parent))       # sibling experiments
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # repository root
import ac_builds as ab  # noqa: E402
import ac_pricing as ap  # noqa: E402
import cost_effective_builds as ceb  # noqa: E402
import size_weighting as sw  # noqa: E402
import team_values as tv  # noqa: E402
import common  # noqa: E402
import unit_pricing as up  # noqa: E402
from pricing.final import FINAL  # noqa: E402

WEIGHTED = tuple(f"w:{v}" for v in sw.VARIANTS)
SETS = ("raw", "quantity", "quality", "sb") + WEIGHTED


def band_lookup(dataset: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(faction, base unit key) → (arm, size band)."""
    out = {}
    for arm in sw.ARMS:
        kind = FINAL[arm].size
        units = tv.slice_of(dataset, arm).units
        band, labels = sw.bands_of(units, kind)
        out.update({(u.faction, u.key): (arm, labels[b]) for u, b in zip(units, band)})
    return out


def weighted_unit_values(dataset: str, variant: str) -> dict[tuple[str, str], float]:
    vals = {}
    for arm in sw.ARMS:
        res = pickle.loads(sw.checkpoint(dataset, arm, "V4", "nested", variant).read_bytes())
        units = tv.slice_of(dataset, arm).units
        vals.update(tv.v4_raw_and_oof(dataset, arm, units, (res["run"], res["extra"]["p_of"]))[0])
    return vals


def tow_counts(value_set: str, started: float) -> Counter:
    mode = "full" if value_set == "quality" else "noise"
    by_faction, staff_of, top_star, _ = ceb.load_cards(started, size_mode=mode)
    if value_set == "sb" or value_set.startswith("w:"):
        if value_set == "sb":
            with open(tv.OUT / "values_tow_sb.csv", encoding="utf-8") as fh:
                new = {(r["faction_key"], r["unit_key"]): float(r["value_sb"]) for r in csv.DictReader(fh)}
        else:
            units = weighted_unit_values("tow", value_set[2:])
            new = {**units, **tv.commander_values(None, None, units)}
        for f, cards in by_faction.items():
            for c in cards:
                c["value"] = new.get((f, c["key"]), c["value_raw"])
    elif value_set == "raw":
        for cards in by_faction.values():
            for c in cards:
                c["value"] = c["value_raw"]
    lam = ceb.COMMAND_LAMBDA["full" if value_set in ("quality", "sb") else "noise"]
    command = ceb.Command(lam, ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus())
    bands = band_lookup("tow")
    counts: Counter = Counter()
    for f, cards in by_faction.items():
        for _, chosen, _ in ceb.army_builds(cards, staff_of[f], top_star[f], command, ("max value",)):
            for c, k in chosen:
                counts[bands.get((f, c["base"]), ("?", "?"))] += k
    return counts


def ac_counts(value_set: str) -> Counter:
    catalog, values, extra, _, _, t3 = ab.load_inputs()
    if value_set.startswith("w:"):
        units = weighted_unit_values("ac", value_set[2:])
        coef = json.loads((ap.OUT / "ac_commanders.json").read_text(encoding="utf-8"))["coefficients_ac"]
        vals = {**units, **tv.commander_values(ap.OUT / "ac_commander_pairs.csv", coef, units)}
    elif value_set == "raw":
        with open(tv.OUT / "values_ac.csv", encoding="utf-8") as fh:
            vals = {(r["faction_key"], r["unit_key"]): float(r["value_raw"]) for r in csv.DictReader(fh)}
    else:
        vals = values[{"quantity": "noise", "quality": "full", "sb": "sb"}[value_set]]
    vals = {k: v for k, v in vals.items() if not common.is_wip(k[0])}
    lam = ceb.COMMAND_LAMBDA["full" if value_set in ("quality", "sb") else "noise"]
    command = ceb.Command(lam, ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus())
    bands = band_lookup("ac")
    counts: Counter = Counter()
    for f in sorted({f for f, _ in vals}):
        res = ab.solve_corps(f, catalog, vals, extra, t3, command, 31)
        if res is None:
            continue
        for c, k in res["chosen"]:
            counts[bands.get((f, c.cap_group_key), ("?", "?"))] += k
    return counts


def main() -> int:
    started = time.time()
    results: dict[str, dict[str, Counter]] = {"tow": {}, "ac": {}}
    for dataset in ("tow", "ac"):
        for value_set in SETS:
            path = sw.CACHE / f"builds_{dataset}_{value_set.replace(':', '_')}.pkl"
            if not path.exists():
                counts = tow_counts(value_set, started) if dataset == "tow" else ac_counts(value_set)
                sw.save(path, counts)
                up.log(f"{dataset} {value_set}: {sum(counts.values())} cards", started)
            results[dataset][value_set] = pickle.loads(path.read_bytes())
    L = ["# Which unit sizes the optimiser picks, by value set (generated by analysis/experiments/size_weighting_builds.py)", "",
         "Picked cards (copies) of every army's max-value build, by size band of the base unit, as a share of "
         "that arm's picked cards. ToW + Custom: 55 armies; AC: 223 corps with formation rebates. `w:` = the "
         "size-weighted V4 (nested refit), unharmonised.", ""]
    for dataset, by_set in results.items():
        for arm in sw.ARMS:
            labels = up.size_band_labels(FINAL[arm].size)
            L += [f"## {dataset.upper()} {arm}", "", "| values | cards | " + " | ".join(labels) + " |",
                  "|---|---|" + "---|" * len(labels)]
            for value_set, counts in by_set.items():
                n = sum(k for (a, _), k in counts.items() if a == arm)
                L.append(f"| {value_set} | {n} | " + " | ".join(
                    f"{100 * counts.get((arm, b), 0) / n:.1f}%" if n else "" for b in labels) + " |")
            L.append("")
    (sw.OUT / "size_weighting_builds.md").write_text("\n".join(L), encoding="utf-8")
    up.log("→ analysis/output/size_weighting_builds.md", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
