"""Commander variants: a general attached to a unit, priced from that unit's price.

Background: 5 238 of the ToW + Custom rows are commander variants
(`is_commander_variant`, `unit_class = general`): a named general leading a
regular unit. Each one has its regular counterpart in the same army — the same
unit key without `_com_<id>` — with the same men and speed, and stats boosted by
the general's command stars (morale +1 … +3, melee +0 … +2, accuracy +0 … +3).
A commander costs a median 0.86 × its regular unit.

Form (from the blind study, branch blind-pricing-study, exp 09–14):

    price_cmd = max(1, (a + a_s) · P + (b_s + army_f) · 8/N)

  P        price of the regular counterpart, scaled to the commander's unit size:
           P = P_regular · (S_cmd / S_regular)^p, S = models (guns for artillery),
           p = the adopted model's size power for the arm (1.09 / 0.75 / 1.3).
           70 commanders lead a bigger unit than their regular counterpart (e.g. a
           6-gun Guard battery against the regular 3-gun one); without the scaling
           their error is ~7× the rest.
  s        command stars, capped at 5 (6–7 stars: 12 rows); blank = 0
  a, a_s   price slope, and its change for s stars (a_0 = 0)
  b_s      gold per star level, scaled by the army divisor 8/N (blind: 10/N)
  army_f   optional per-army premium, ridge-shrunk (penalty 1e-3·n, as the blind study)

Unlike the blind study — which fitted these to its stage-1 *prediction* for the
commander's own (stat-boosted) row — the parameters here are learned from the
*true* counterpart price P, so they describe the game's commander pricing
without stage-1 error mixed in: stage 2 is a model of its own, "commander price
given the regular unit's price", and its parameters should be read that way. It
is then applied five ways:
  known      P = the counterpart's actual price
  FC seen    P = the adopted model's full-data fit of the counterpart (unit in the data)
  V4 seen    P = the same from the per-class model V4
  FC unseen  P = the adopted model's out-of-fold prediction (unit never seen)
  V4 unseen  P = the same from V4
"seen" matches the blind study's setting (its stage 1 had the regular unit in
training); "unseen" is stricter. Commanders share their counterpart's fold (the committed 500-seed splits),
so the stage-2 parameters for fold k are learned only from commanders whose
counterparts are outside fold k, and the regular-unit prediction is out-of-fold
too. Counterparts pinned to train have no out-of-fold prediction; their
commanders only ever train.

Variants (1-SE rule on the `known` errors, simplest within one SE of the best):
  S1  a + b_s                         (7 parameters)
  S2  S1 + star slopes a_s            (12)
  S3  S2 + per-army premium (ridge)   (12 + armies)

Inputs: the committed analysis/output/oof_predictions.csv (adopted model) and the
class_structure.py checkpoint for V4 (analysis/.cache/class_structure/).
Outputs: analysis/output/commander_stage_report.md, commander_coefficients.csv,
commander_predictions.csv.

    python analysis/commander_stage.py
"""

from __future__ import annotations

import csv
import pickle
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402
from blind_ideas import FINAL  # noqa: E402
from class_structure import segmented, with_class_p  # noqa: E402

OUT = up.ROOT / "analysis" / "output"
V4_CACHE = up.ROOT / "analysis" / ".cache" / "class_structure"
BLIND_OUT = up.ROOT / "blind_study" / "out"
MAX_STARS = 5
STARS = tuple(range(MAX_STARS + 1))
ARMY_RIDGE = 1e-3            # × number of training rows, as the blind study (exp 14a / 13c)
TINY_RIDGE = 1e-6
VARIANTS = ("S1", "S2", "S3")
LABELS = {"S1": "a·P + b_s·8/N", "S2": "(a + a_s)·P + b_s·8/N", "S3": "(a + a_s)·P + (b_s + army_f)·8/N"}
SOURCES = ("known", "FC seen", "V4 seen", "FC unseen", "V4 unseen")
SOURCE_LABELS = {"known": "actual regular price", "FC seen": "adopted model, unit seen",
                 "V4 seen": "V4, unit seen", "FC unseen": "adopted model, unit unseen",
                 "V4 unseen": "V4, unit unseen"}


@dataclass
class Commander:
    row_id: int              # row index in the analysis CSV
    key: str
    name: str
    faction: str
    corps: str
    rating: int
    arm: str
    stars: int               # capped at MAX_STARS
    raw_stars: int
    cost: float
    reg_index: int           # counterpart's index in its arm's merged slice
    fold: int                # counterpart's fold (0 = pinned to train)
    size_ratio: float        # commander's unit size / counterpart's (models; guns for artillery)


def design(c: list[Commander], p: np.ndarray, variant: str, armies: list[str]) -> tuple[np.ndarray, list[str]]:
    divisor = np.array([up.REF_RATING / x.rating for x in c])
    s = np.array([x.stars for x in c])
    cols, names = [p], ["a"]
    for level in STARS:
        cols.append((s == level) * divisor)
        names.append(f"b_{level}")
    if variant in ("S2", "S3"):
        for level in STARS[1:]:
            cols.append(p * (s == level))
            names.append(f"a_{level}")
    if variant == "S3":
        f = np.array([x.faction for x in c])
        for army in armies:
            cols.append((f == army) * divisor)
            names.append(f"army={army}")
    return np.column_stack(cols), names


def fit(c: list[Commander], p: np.ndarray, variant: str, armies: list[str]) -> tuple[np.ndarray, list[str]]:
    X, names = design(c, p, variant, armies)
    y = np.array([x.cost for x in c])
    pen = np.array([ARMY_RIDGE * len(y) if n.startswith("army=") else TINY_RIDGE for n in names])
    beta = np.linalg.solve(X.T @ X + np.diag(pen), X.T @ y)
    return beta, names


def predict(c: list[Commander], p: np.ndarray, variant: str, armies: list[str], beta: np.ndarray) -> np.ndarray:
    X, _ = design(c, p, variant, armies)
    return np.maximum(1.0, X @ beta)


def load_commanders(regs: dict[str, list[up.Unit]], folds: dict[str, np.ndarray]) -> list[Commander]:
    ratings = up.load_ratings()
    index = {arm: {(u.faction, u.key): i for i, u in enumerate(us)} for arm, us in regs.items()}
    out = []
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row_id, row in enumerate(csv.DictReader(fh)):
            if not (up.in_scope(row) and row["faction_key"] in ratings and row["is_general"] == "true"
                    and row["men_raw"] not in ("32", "122")):
                continue
            arm = {"inf": "infantry", "cav": "cavalry", "art": "artillery"}[row["unit_key"].split("_")[1]]
            base = re.sub(r"_com_\d+", "", row["unit_key"])
            i = index[arm].get((row["faction_key"], base))
            if i is None:
                raise SystemExit(f"no regular counterpart for {row['unit_key']} in {row['faction_key']}")
            raw = int(up.num(row["command_stars"]))
            reg = regs[arm][i]
            size = up.num(row["guns"]) if arm == "artillery" else int(row["men_raw"]) / 2
            out.append(Commander(row_id, row["unit_key"], row["unit_name"], row["faction_key"], row["army_corps_name"],
                                 ratings[row["faction_key"]], arm, min(raw, MAX_STARS), raw,
                                 float(row["base_mp_cost"]), i, int(folds[arm][i]),
                                 size / up.size_of(reg, FINAL[arm].size)))
    return out


def metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    err = np.abs(pred - y)
    ape = err / y
    return {"mae": float(err.mean()), "mape": float(ape.mean() * 100), "medape": float(np.median(ape) * 100)}


def main() -> int:
    started = time.time()
    units, _, _, _ = up.load(up.load_ratings())
    regs, folds, p_src = {}, {}, defaultdict(dict)
    with open(OUT / "oof_predictions.csv", encoding="utf-8") as fh:
        committed = {(r["model"], r["faction_key"], r["unit_key"]): r for r in csv.DictReader(fh) if r["slice"] == "merged"}
    for arm in FINAL:
        sl = up.make_slice(arm, "merged", up.slice_units(units, arm, "merged"), 500)
        regs[arm] = sl.units
        fc_oof = np.array([float(committed[(arm, u.faction, u.key)]["oof_final_faction_class"] or "nan") for u in sl.units])
        v4_run, _ = pickle.loads((V4_CACHE / f"v2_{arm}_V4.pkl").read_bytes())
        folds[arm] = np.where(np.isfinite(fc_oof), np.array([int(committed[(arm, u.faction, u.key)]["fold"] or 0)
                                                             for u in sl.units]), 0)
        if not np.array_equal(np.isfinite(fc_oof), np.isfinite(v4_run.oof)):
            raise SystemExit(f"{arm}: adopted and V4 out-of-fold rows differ — different folds?")
        # Full-data ("seen") fits of both models; κ and V4's size powers from the class_structure checkpoints.
        kappa = pickle.loads((V4_CACHE / f"v2_{arm}_kappa.pkl").read_bytes())
        _, p_of_class = pickle.loads((V4_CACHE / f"v2_{arm}_V4.pkl").read_bytes())
        spec = up.joint_fclass_spec(FINAL[arm], kappa)
        d0 = up.design_for(spec, sl.units, arm)
        data = up.data_for(spec, sl.units)
        everything = np.arange(len(sl.units))
        fc_seen = up.predict_total(up.fit_on(spec, d0, data, everything), d0, data, everything)
        v4_seen = up.predict_total(v4_run.full, segmented(d0, sl.units),
                                   with_class_p(data, sl.units, spec, p_of_class), everything)
        p_src[arm] = {"known": np.array([u.cost for u in sl.units], float), "FC seen": fc_seen, "V4 seen": v4_seen,
                      "FC unseen": fc_oof, "V4 unseen": v4_run.oof}
        up.log(f"{arm:9} {len(sl.units)} regular units; folds and out-of-fold predictions loaded", started)
    cmds = load_commanders(regs, folds)
    up.log(f"{len(cmds)} commanders, every one matched to its regular counterpart", started)

    def p_of(c: list[Commander], source: str) -> np.ndarray:
        """Counterpart price from `source`, scaled to the commander's unit size."""
        return np.array([p_src[x.arm][source][x.reg_index] * x.size_ratio ** FINAL[x.arm].p for x in c])

    armies = sorted({x.faction for x in cmds})
    y = np.array([x.cost for x in cmds])
    fold = np.array([x.fold for x in cmds])
    tested = fold > 0
    oof = {(v, s): np.full(len(cmds), np.nan) for v in VARIANTS for s in SOURCES}
    fold_mae = {(v, s): [] for v in VARIANTS for s in SOURCES}
    for k in range(1, up.N_SPLITS + 1):
        train = np.flatnonzero(fold != k)
        test = np.flatnonzero(fold == k)
        ctrain, ctest = [cmds[i] for i in train], [cmds[i] for i in test]
        for v in VARIANTS:
            beta, _ = fit(ctrain, p_of(ctrain, "known"), v, armies)
            for s in SOURCES:
                pred = predict(ctest, p_of(ctest, s), v, armies, beta)
                oof[(v, s)][test] = pred
                fold_mae[(v, s)].append(float(np.abs(pred - y[test]).mean()))
    full = {v: fit(cmds, p_of(cmds, "known"), v, armies) for v in VARIANTS}

    def se_diff(a: tuple[str, str], b: tuple[str, str]) -> tuple[float, float]:
        d = np.array(fold_mae[a]) - np.array(fold_mae[b])
        return float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d)))

    best = min(VARIANTS, key=lambda v: np.mean(fold_mae[(v, "known")]))
    adopted = next(v for v in VARIANTS if se_diff((v, "known"), (best, "known"))[0] <= se_diff((v, "known"), (best, "known"))[1])
    up.log("CV: " + "; ".join(f"{v} " + ", ".join(f"{s} {np.mean(fold_mae[(v, s)]):.2f}" for s in SOURCES)
                              for v in VARIANTS) + f" → adopted {adopted}", started)

    # ---- Report.
    L = ["# Commander variants: priced from their regular unit", "",
         "Generated by `analysis/commander_stage.py`. Functional form from the blind study (branch "
         "`blind-pricing-study`):", "",
         "    price_cmd = max(1, (a + a_s) · P + (b_s + army_f) · 8/N)", "",
         "P = the price of the commander's regular counterpart (same army, same unit key without `_com_<id>`), "
         "scaled to the commander's unit size by the model's size law, P_regular · (S_cmd / S_regular)^p; "
         "s = command stars, capped at 5; N = corps number.", "",
         "> **How to read this model.** The blind study fitted these parameters to its stage-1 *prediction* "
         "of the commander's own row, so its commander parameters also absorbed its regular-unit model's errors. "
         "Here they are learned from the **true price of the regular counterpart** instead. Stage 2 is therefore "
         "a model in its own right (*commander price given the regular unit's price*) and should be "
         "interpreted on its own, independently of either regular-unit model. The regular-unit models only "
         "enter when stage 2 is *applied* to a predicted P (the \"seen\" and \"unseen\" columns below).", "",
         "Commanders take their counterpart's fold (the committed 500-seed splits); stage-2 parameters for fold k "
         "are learned only from commanders outside fold k. P comes from: the actual regular price (*known*); a "
         "model's full-data fit of the regular unit (*seen*: the unit is in the data, as in the blind study); or "
         "its out-of-fold prediction (*unseen*: the unit was never seen, the strictest case). MAE in gold, mean "
         "over folds. "
         f"{int(tested.sum())} of {len(cmds)} commanders are tested; the rest belong to units pinned to train.", "",
         "## Accuracy", ""]
    rows = []
    for v in VARIANTS:
        line = [f"`{v}`", LABELS[v], len(full[v][1])]
        for s in SOURCES:
            m = metrics(y[tested], oof[(v, s)][tested])
            line.append(f"{np.mean(fold_mae[(v, s)]):.1f} ({m['medape']:.1f}%)")
        if v != "S1":
            prev = VARIANTS[VARIANTS.index(v) - 1]
            d, se = se_diff((v, "known"), (prev, "known"))
            line.append(f"{d:+.2f} ± {se:.2f} vs `{prev}`")
        else:
            line.append("")
        line.append("**adopted**" if v == adopted else "")
        rows.append(line)
    L += up.table(["key", "form", "params"] + [f"P = {SOURCE_LABELS[s]}" for s in SOURCES]
                  + ["Δ known (paired SE)", ""], rows)
    L += ["", "Cells: MAE (median absolute % error). The *known* column is stage 2 on its own. The other columns "
          "add the regular-unit model's error for the counterpart (regular units: MAE 27.4 / 34.9 / 32.4 adopted, "
          "24.9 / 32.8 / 27.2 V4, out of fold), scaled by a ≈ 0.9.", ""]

    # Blind comparison on the same rows.
    if (BLIND_OUT / "oof_13c.csv").exists():
        blind = {}
        with open(BLIND_OUT / "oof_13c.csv", encoding="utf-8") as fh:
            blind.update({int(r["row_id"]): float(r["pred"]) for r in csv.DictReader(fh)})
        with open(BLIND_OUT / "holdout_predictions.csv", encoding="utf-8") as fh:
            blind.update({int(r["row_id"]): float(r["13c"]) for r in csv.DictReader(fh)})
        both = np.array([tested[i] and cmds[i].row_id in blind for i in range(len(cmds))])
        bp = np.array([blind.get(x.row_id, np.nan) for x in cmds])
        L += ["**Against the blind study's best model (13c)** on the same commander rows "
              f"({int(both.sum())} rows; its own CV or holdout predictions): blind 13c MAE "
              f"{np.abs(bp[both] - y[both]).mean():.1f}; ours with `{adopted}`: "
              + ", ".join(f"{SOURCE_LABELS[s]} {np.abs(oof[(adopted, s)][both] - y[both]).mean():.1f}" for s in SOURCES)
              + ". The blind study's setting corresponds to *seen*.", ""]

    # Breakdown by arm and stars.
    L += [f"### By arm and by stars (`{adopted}`)", ""]
    arm_of = np.array([x.arm for x in cmds])
    rows = []
    for arm in FINAL:
        mask = tested & (arm_of == arm)
        rows.append([arm, int(mask.sum())] + [f"{np.abs(oof[(adopted, s)][mask] - y[mask]).mean():.1f}" for s in SOURCES])
    L += up.table(["arm", "commanders tested"] + [f"MAE, P = {s}" for s in SOURCES], rows) + [""]
    stars = np.array([x.stars for x in cmds])
    rows = []
    for level in STARS:
        mask = tested & (stars == level)
        if mask.any():
            ratio = np.median(y[mask] / p_of([cmds[i] for i in np.flatnonzero(mask)], "known"))
            rows.append([f"{level}{'+' if level == MAX_STARS else ''}", int(mask.sum()), f"{ratio:.3f}"]
                        + [f"{np.abs(oof[(adopted, s)][mask] - y[mask]).mean():.1f}" for s in SOURCES])
    L += up.table(["stars", "commanders", "median price ÷ regular price (size-scaled)"] + [f"MAE, P = {s}" for s in SOURCES],
                  rows) + [""]

    # Coefficients.
    beta, names = full[adopted]
    coef = dict(zip(names, beta))
    L += [f"## Parameters (`{adopted}`, full-data fit on actual regular prices)", ""]
    rows = []
    for level in STARS:
        slope = coef["a"] + coef.get(f"a_{level}", 0.0)
        rows.append([f"{level}{'+' if level == MAX_STARS else ''}", f"{slope:.4f}", f"{coef[f'b_{level}']:+.1f}",
                     f"{coef[f'b_{level}'] * up.REF_RATING / 10:+.1f}"])
    L += up.table(["stars", "price slope a + a_s", "b_s (gold at N = 8)", "b_s at N = 10"], rows)
    if adopted == "S3":
        army = sorted(((coef[n], n.split("=", 1)[1]) for n in names if n.startswith("army=")))
        corps = {x.faction: x.corps for x in cmds}
        L += ["", f"Per-army premium (gold at N = 8; ridge {ARMY_RIDGE:g}·n): median {np.median([a for a, _ in army]):+.1f}; "
              "lowest " + ", ".join(f"{corps[f]} {a:+.0f}" for a, f in army[:4]) + "; highest "
              + ", ".join(f"{corps[f]} {a:+.0f}" for a, f in army[-4:]) + "."]
    L += ["", f"Worked reading: a 2-star commander of a regular unit costing 500 in a rating-8 army costs about "
          f"{coef['a'] + coef.get('a_2', 0):.3f} × 500 + {coef['b_2']:.0f}"
          + (" + army premium" if adopted == "S3" else "")
          + f" = {(coef['a'] + coef.get('a_2', 0)) * 500 + coef['b_2']:.0f} gold.", ""]

    # Worst misses (known P).
    err = np.abs(oof[(adopted, "known")] - y)
    worst = [i for i in np.argsort(-np.nan_to_num(err)) if tested[i]][:10]
    L += ["## Largest misses (P = actual regular price)", ""]
    L += up.table(["commander", "corps", "stars", "size vs regular", "regular price", "commander price", "predicted"],
                  [[cmds[i].name, cmds[i].corps, cmds[i].raw_stars, f"×{cmds[i].size_ratio:.2f}",
                    f"{p_src[cmds[i].arm]['known'][cmds[i].reg_index]:.0f}",
                    f"{y[i]:.0f}", f"{oof[(adopted, 'known')][i]:.0f}"] for i in worst])
    L += ["", f"*Runtime {time.time() - started:.0f} s.*", ""]
    (OUT / "commander_stage_report.md").write_text("\n".join(L), encoding="utf-8")

    with open(OUT / "commander_coefficients.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["variant", "feature", "coefficient", "note"])
        for v in VARIANTS:
            for n, b in zip(*reversed(full[v])):
                note = {"a": "slope on the regular price P"}.get(n, "")
                if n.startswith("b_"):
                    note = "gold × 8/N for this star level"
                elif n.startswith("a_"):
                    note = "added to the slope for this star level"
                elif n.startswith("army="):
                    note = f"gold × 8/N, ridge {ARMY_RIDGE:g}·n"
                w.writerow([v, n, f"{b:.10g}", note + (" (adopted)" if v == adopted else "")])
    with open(OUT / "commander_predictions.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit_key", "faction_key", "army_corps_name", "arm", "stars", "cost", "regular_price",
                    "size_ratio", "fold"] + [f"oof_{adopted}_{s.replace(' ', '_')}" for s in SOURCES])
        for i, x in enumerate(cmds):
            w.writerow([x.key, x.faction, x.corps, x.arm, x.raw_stars, int(x.cost),
                        f"{p_src[x.arm]['known'][x.reg_index]:.0f}", f"{x.size_ratio:.4g}", x.fold or ""]
                       + [f"{oof[(adopted, s)][i]:.3f}" if np.isfinite(oof[(adopted, s)][i]) else "" for s in SOURCES])
    up.log("done → analysis/output/commander_stage_report.md, commander_coefficients.csv, commander_predictions.csv",
           started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
