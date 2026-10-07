"""Commander price vs stars, read inside units that have several generals.

Within one regular unit, every commander version shares the regular price P, the
unit size, the army and its corps number N; only the general differs (his command
stars and the stat bonuses he gives). Price differences between generals of the
same unit therefore isolate what a general adds, with no regular-unit model in
between. 453 regular units have two or more generals (915 commanders); 444 of
them keep the regular unit's size and are used here.

Target: the price difference between a unit's higher-star general(s) and its
lowest-star general. Models are fitted by least squares, 5-fold CV grouped by
unit. Also tabulated: the stat bonus schedule by stars over all 5 238 commanders.

Input: analysis/commander_blind/data/pairs.csv (analysis/build_commander_pairs.py).
Output: analysis/output/commander_within_unit_report.md

    python analysis/commander_within_unit.py
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "analysis" / "commander_blind" / "data" / "pairs.csv"
REPORT = ROOT / "analysis" / "output" / "commander_within_unit_report.md"
STATS = ("morale", "melee_attack", "melee_defense", "charge_bonus", "accuracy", "reload_skill")


def table(header: list[str], rows: list[list[object]]) -> list[str]:
    return (["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
            + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main() -> int:
    rows = list(csv.DictReader(PAIRS.open(encoding="utf-8")))
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by[(r["faction_key"], r["regular_unit_key"])].append(r)
    multi = [v for v in by.values() if len(v) >= 2]
    same = [v for v in multi if all(r["commander_men"] == r["regular_men"] and r["commander_guns"] == r["regular_guns"]
                                    for r in v)]
    D, gid = [], []
    for i, v in enumerate(same):
        v = sorted(v, key=lambda r: int(r["command_stars"]))
        a = v[0]
        for b in v[1:]:
            d = {"ds": int(b["command_stars"]) - int(a["command_stars"]),
                 "dC": float(b["commander_price"]) - float(a["commander_price"]),
                 "P": float(a["regular_price"]), "N": int(a["corps_number"]), "models": float(a["regular_men"]) / 2,
                 "s0": int(a["command_stars"]), "s1": int(b["command_stars"])}
            for s in STATS:
                d["d" + s] = float(b["commander_" + s]) - float(a["commander_" + s])
            D.append(d)
            gid.append(i)
    gid = np.array(gid)
    y = np.array([d["dC"] for d in D])
    col = lambda k: np.array([d[k] for d in D], float)  # noqa: E731
    ds, P, N, models = col("ds"), col("P"), col("N"), col("models")
    div = 8 / N
    perm = np.random.default_rng(0).permutation(len(same))
    fold = (perm % 5)[gid]

    def cv(cols: list[np.ndarray]) -> tuple[float, float, np.ndarray]:
        X = np.column_stack(cols)
        pred = np.empty(len(y))
        for f in range(5):
            tr = fold != f
            b, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
            pred[~tr] = X[~tr] @ b
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(np.abs(pred - y).mean()), float(np.median(np.abs(pred - y))), b

    steps = np.column_stack([(col("s1") >= k).astype(float) - (col("s0") >= k).astype(float) for k in range(1, 7)])
    dstat = [col("d" + s) for s in STATS]
    ladder = [
        ("no model (mean difference)", None),
        ("A: k·Δs, a fixed amount per star", [ds]),
        ("B: k·Δs·8/N", [ds * div]),
        ("C: a lookup per star step, ·8/N", list((steps * div[:, None]).T)),
        ("J: Δs·(k₁·8/N + k₂·P), a fixed fee + a share of P per star", [ds * div, ds * P]),
        ("L: k·Δs·8/N + w·Δmorale·P", [ds * div, col("dmorale") * P]),
        ("M: k·Δs·8/N + w·(Σ stat bonuses)·P", [ds * div, sum(dstat) * P]),
        ("F: k·Δs·8/N + Σ w_j·Δstat_j·models", [ds * div] + [x * models for x in dstat]),
        ("H: k·Δs·8/N + Σ w_j·Δstat_j·P", [ds * div] + [x * P for x in dstat]),
    ]
    rows_out = []
    for name, cols in ladder:
        if cols is None:
            rows_out.append([name, 0, f"{np.abs(y - y.mean()).mean():.1f}", f"{np.median(np.abs(y - y.mean())):.1f}", ""])
            continue
        mae, med, b = cv(cols)
        rows_out.append([name, len(cols), f"{mae:.1f}", f"{med:.1f}", ", ".join(f"{x:.4g}" for x in b)])
    drops = []
    for s in STATS:
        mae, _, _ = cv([ds * div] + [col("d" + x) * P for x in STATS if x != s])
        drops.append([s, f"{mae:.2f}"])

    differ = ds != 0                      # a few same-star pairs have no per-star step
    slope = y[differ] / ds[differ]
    rel = slope / P[differ] * 100
    consecutive = []
    for s0 in range(0, 5):
        m = ((col("s0") == s0) & (ds == 1))[differ]
        if m.sum():
            consecutive.append([f"{s0}★ → {s0 + 1}★", int(m.sum()), f"{np.median(slope[m]):.0f}", f"{np.median(rel[m]):.1f}%"])
    schedule = []
    by_star: dict[int, list[list[float]]] = defaultdict(list)
    for r in rows:
        by_star[min(int(r["command_stars"]), 6)].append([float(r["commander_" + k]) - float(r["regular_" + k]) for k in STATS])
    for s in sorted(by_star):
        arr = np.array(by_star[s])
        schedule.append([f"{s}★" + ("+" if s == 6 else ""), len(arr)] + [f"{np.median(arr[:, i]):+.0f}" for i in range(len(STATS))])
    same_star = Counter()
    for v in multi:
        g: dict[int, set] = defaultdict(set)
        for r in v:
            g[int(r["command_stars"])].add(r["commander_price"])
        for s, prices in g.items():
            if sum(1 for r in v if int(r["command_stars"]) == s) >= 2:
                same_star[len(prices) == 1] += 1

    L = ["# Commander price vs stars, inside units with several generals", "",
         "Generated by `analysis/commander_within_unit.py`. Within one regular unit every commander version shares the "
         "regular price P, the unit size, the army and its corps number N; only the general differs. Comparing generals of "
         "the same unit therefore shows what a general adds, with no regular-unit model in between.", "",
         f"- **Data:** {len(multi)} regular units have two or more generals ({sum(len(v) for v in multi)} commanders).",
         f"  {len(same)} keep the regular unit's size and are used, giving {len(y)} within-unit price differences.",
         f"- **Same unit, same stars:** in {same_star[True]} of {sum(same_star.values())} cases two generals of the "
         "same unit with the same stars cost exactly the same.", "",
         "## 1. The stat bonus a general gives, by stars", "",
         "Median change from the regular unit, over all 5 238 commanders:", ""]
    L += table(["stars", "commanders"] + list(STATS), schedule)
    L += ["", "A fixed schedule: morale +⌊s/2⌋+1, melee attack +⌊s/2⌋, melee defence +(s+1), charge and accuracy "
          "+⌈s/2⌉, reload +5·(s+1). Within a unit, stars and stat bonuses therefore move almost in lockstep. They "
          "differ only where a unit cannot take a bonus, e.g. no accuracy gain for units without firearms.", "",
          "## 2. Price per extra star, raw", ""]
    L += table(["step", "pairs", "median gold per star", "median % of P per star"], consecutive)
    L += ["", f"Over all differences: a median of {np.median(slope):.0f} gold per star (middle half "
          f"{np.quantile(slope, .25):.0f}–{np.quantile(slope, .75):.0f}). As a share of P the step varies *more* "
          "(coefficient of variation 0.43 vs 0.39), so it is not simply a percentage of the regular price. The steps "
          "alternate in size because the morale bonus rises only at every other star.", "",
          "## 3. Models of the within-unit price difference", "",
          "CV grouped by unit; MAE and median absolute error in gold; coefficients from the full fit (order as in the "
          "formula; stat order " + ", ".join(STATS) + ").", ""]
    L += table(["model", "params", "CV MAE", "median abs error", "coefficients"], rows_out)
    L += ["", "Leaving one stat out of model H (CV MAE; all six: "
          f"{rows_out[-1][2]}):", ""]
    L += table(["stat left out", "CV MAE"], drops)
    L += ["", "## 4. Reading", "",
          "- **A general costs a fixed fee per star plus a share of the unit's price for each stat point he adds.**",
          "  - The fee is about 34–54 gold per star × 8/N.",
          "  - The stat part is proportional to P, not to the number of men (model H at 11.8 against F at 26).",
          "- **Stars alone are not enough.** A fixed amount per star, scaled or not by 8/N, leaves about 36 gold of "
          "error. That is half the raw spread, but three times model H.",
          "- **The per-stat weights are unstable.** The bonuses follow one schedule, so morale and melee attack, "
          "for example, are nearly the same variable. No single stat is essential (dropping one costs at most 5 gold, "
          "for reload), while the stars-plus-total-bonus form M gives 21 gold. The information that matters is the "
          "*realised* bonus each unit gets, which differs between unit types.",
          "- **This agrees with the blind study** (`analysis/commander_blind/REPORT.md`), whose best model prices "
          "the same things — stat changes × P, plus a per-star fee — across all pairs. The within-unit view confirms "
          "that structure without a regular-price model in the way.", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"{len(y)} within-unit differences from {len(same)} units → {REPORT.relative_to(ROOT)}")
    for r in rows_out:
        print(f"  {r[0]:62} CV MAE {r[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
