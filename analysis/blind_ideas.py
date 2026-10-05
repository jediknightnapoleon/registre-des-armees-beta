"""Which findings of the blind pricing study improve analysis/unit_pricing.py?

Background: a "blind" study (branch blind-pricing-study, folder blind_study/) was
run in a fresh session that knew nothing of this model: the same analysis CSV,
the ToW + Custom rows, any readable model, cross-validated. Its best model (13c)
is a per-unit-type log-linear formula with an army × unit-type price table, a
fixed N/10 army divisor and a price-weighted least-absolute-deviation fit. Scored
on exactly our rows it beats our final model by a wide margin, while its
stat-only variant (18b, no army table) is on par with ours — so the candidates
to bring over are the army-level structure, the divisor, the loss and its staff
general rule, not its stat formulas.

This driver tests each of them on our model and our folds (same 500-seed split
search, so the numbers compare directly with analysis/output):

  B    rating as the fixed divisor 8/N instead of free per-rating levels
  RFC  residual faction × unit_class modifier on top of the faction modifier,
       shrunk towards it (stats fitted first, as now)
  JFC  joint faction × unit_class multiplier inside the ALS fit, around the fixed
       8/N divisor (the blind study's form); stat coefficients fitted net of it
  LAD  least absolute deviation on total price (IRLS), on F and on RFC / JFC
  T3   staff generals: b·stars^q·(8/N), 1 gold without stars

The ridge strength κ of RFC / JFC (pseudo-units of average price pulling a cell
to 1) is chosen by inner CV inside each outer training fold, so the reported MAE
is honest. Adoption: a candidate must beat its reference by more than one paired
standard error (SE of the per-fold MAE difference); between RFC and JFC the lower
pooled MAE wins, and the residual form wins ties (within one paired SE) because it
keeps the stat coefficients of the final model unchanged.

Output: analysis/output/blind_ideas_report.md

    python analysis/blind_ideas.py [--seeds 500]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

# The committed final models (analysis/output/coefficients.csv, 2026-10-05 run).
FINAL = {
    "infantry": up.Spec(mult=frozenset({"rating", "side"}), size="n", p=1.09, powers=tuple(sorted({
        "accuracy": 0.05, "ammo": 0.05, "charge_bonus": 0.05, "melee_attack": 1.4, "melee_defense": 1.15,
        "morale": 2.25, "range": 4.0, "reload_skill": 3.1}.items()))),
    "cavalry": up.Spec(mult=frozenset({"rank_depth", "rating"}), size="n", p=0.75),
    "artillery": up.Spec(mult=frozenset({"rating"}), const=True, size="guns", p=1.3,
                         extras=frozenset({"damage", "proj_reload"}),
                         shape=(("cal", "spline_r"), ("cal_df", "5")), powers=tuple(sorted({
                             "accuracy": 3.0, "charge_bonus": 0.25, "melee_attack": 2.5, "melee_defense": 3.0,
                             "morale": 3.0, "reload_skill": 2.0}.items()))),
}
COMMITTED_OOF = up.ROOT / "analysis" / "output" / "oof_predictions.csv"
BLIND_OUT = up.ROOT / "blind_study" / "out"
BLIND_DATA = up.ROOT / "data" / "generated" / "ntw3_units_analysis.csv"
REPORT = up.ROOT / "analysis" / "output" / "blind_ideas_report.md"


@dataclass
class Arm:
    arm: str
    sl: up.Slice
    design: up.Design
    runs: dict[str, up.CVRun]
    fclass: dict[str, up.FclassResult]       # variant (and variant·LAD) -> nested-κ result


def pooled_folds(arms: dict[str, Arm], key: str) -> np.ndarray:
    """Per-fold MAE pooled over the three arms (row-weighted)."""
    out = []
    for k in range(1, up.N_SPLITS + 1):
        errors = []
        for a in arms.values():
            run = a.runs[key]
            cost = np.array([u.cost for u in a.sl.units], float)
            mask = run.oof_fold == k
            errors.append(np.abs(run.oof[mask] - cost[mask]))
        out.append(float(np.concatenate(errors).mean()))
    return np.array(out)


def pooled_paired(arms: dict[str, Arm], a: str, b: str) -> tuple[float, float]:
    diff = pooled_folds(arms, a) - pooled_folds(arms, b)
    return float(diff.mean()), float(diff.std(ddof=1) / np.sqrt(len(diff)))


def check_regression(arm: str, sl: up.Slice, runs: dict[str, up.CVRun]) -> float:
    """Max |Δ| between our F / RF out-of-fold predictions and the committed ones
    (rounded to 3 decimals there): proves the folds and specs are identical."""
    committed = {}
    with open(COMMITTED_OOF, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["slice"] == "merged" and r["model"] == arm:
                committed[(r["unit_key"], r["faction_key"])] = r
    worst = 0.0
    for key, column in (("F", "oof_final"), ("RF", "oof_final_faction")):
        ref = np.array([float(committed[(u.key, u.faction)][column] or "nan") for u in sl.units])
        oof = runs[key].oof
        if not np.array_equal(np.isnan(ref), np.isnan(oof)):
            raise AssertionError(f"{arm} {key}: pinned rows differ from the committed run")
        ok = np.isfinite(oof)
        worst = max(worst, float(np.abs(oof[ok] - ref[ok]).max()))
    if worst > 1e-3:
        raise AssertionError(f"{arm}: out-of-fold predictions differ from the committed run by {worst:.4f}")
    return worst


def blind_comparison(arms: dict[str, Arm], adopted: str | None) -> list[str]:
    """MAE of the blind study's out-of-sample predictions on exactly our rows."""
    if not (BLIND_OUT / "oof_13c.csv").exists():
        return ["*(blind_study/out not found — check out branch `blind-pricing-study` to reproduce this table.)*"]
    with open(BLIND_DATA, encoding="utf-8-sig") as fh:
        row_of = {(r["unit_key"], r["faction_key"]): i for i, r in enumerate(csv.DictReader(fh))}
    blind: dict[str, dict[int, float]] = {}
    for m in ("13c", "18b"):
        with open(BLIND_OUT / f"oof_{m}.csv", encoding="utf-8") as fh:
            blind[m] = {int(r["row_id"]): float(r["pred"]) for r in csv.DictReader(fh)}
        with open(BLIND_OUT / "holdout_predictions.csv", encoding="utf-8") as fh:
            blind[m].update({int(r["row_id"]): float(r[m]) for r in csv.DictReader(fh)})
    keys = ["F", "RF"] + ([adopted] if adopted else [])
    header = ["arm", "rows"] + [f"ours {k}" for k in keys] + ["blind 18b (stats + N/10)", "blind 13c (best)"]
    rows = []
    for name, a in arms.items():
        cost = np.array([u.cost for u in a.sl.units], float)
        rid = [row_of[(u.key, u.faction)] for u in a.sl.units]
        ok = np.isfinite(a.runs["F"].oof) & np.array([all(i in blind[m] for m in blind) for i in rid])
        line = [name, int(ok.sum())]
        line += [f"{np.abs(a.runs[k].oof[ok] - cost[ok]).mean():.1f}" for k in keys]
        line += [f"{np.mean([abs(blind[m][i] - c) for i, c, o in zip(rid, cost, ok) if o]):.1f}" for m in ("18b", "13c")]
        rows.append(line)
    return up.table(header, rows)


def staff_section(staff: list[up.Staff], seeds: int) -> tuple[list[str], dict[str, up.StaffRun], str]:
    ss = up.make_staff_slice("merged", staff, seeds)
    rows = []
    for key in ("T1", "T2", "TF1", "TF2", "T3", "TF3"):
        r = ss.runs[key]
        rows.append([f"`{key}`", r.label, f"{r.mean('mae'):.2f} ± {r.sd('mae'):.2f}", f"{r.mean('mape'):.2f}",
                     r.fallbacks])
    lines = up.table(["key", "model", "MAE", "MAPE % (starred)", "fallbacks"], rows)

    def pair(a: str, b: str) -> tuple[float, float]:
        diff = np.array([x["mae"] - y["mae"] for x, y in zip(ss.runs[a].fold_metrics, ss.runs[b].fold_metrics)])
        return float(diff.mean()), float(diff.std(ddof=1) / np.sqrt(len(diff)))

    d3, se3 = pair("T3", "T2")
    df3, sef3 = pair("TF3", "TF2")
    stars = np.array([g.stars for g in staff], float)
    cost = np.array([g.cost for g in staff], float)
    rating = np.array([g.rating for g in staff], float)
    b, q = up.staff_power_fit(stars, cost, rating)
    adopted = "T3" if d3 < -se3 else "T2"
    lines += ["", f"T3 vs T2: Δ MAE {d3:+.2f} (paired SE {se3:.2f}); TF3 vs TF2: Δ {df3:+.2f} (SE {sef3:.2f}).",
              f"Full-data fit: b = {b:.4f}, q = {q:g}, i.e. a starred general costs "
              f"{b:.1f}·stars^{q:g}·(8/N); at N = 10 that is {b * 0.8:.1f}·stars^{q:g} "
              f"(blind study: ≈ 60.4·stars^1.4·(10/N)).",
              f"**Verdict: {'adopt T3 (and TF3 as its faction-modifier version)' if adopted == 'T3' else 'keep T1/T2'}.**"]
    return lines, ss.runs, adopted


def extreme_cells(a: Arm, key: str, top: int = 8) -> list[str]:
    """Largest faction × class deviations of a variant's full fit, as the combined
    army multiplier relative to the 8/N divisor."""
    by_cell: dict[str, list[up.Unit]] = {}
    for u in a.sl.units:
        by_cell.setdefault(f"{u.faction}|{u.unit_class}", []).append(u)
    rows = sorted((up.fclass_multiplier(a.runs[key].full, us[0]), us[0].corps, us[0].unit_class, len(us))
                  for us in by_cell.values())
    pick = rows[:top] + rows[-top:]
    return up.table(["army", "unit class", "units", "price vs 8/N rule"],
                    [[c, uc, n, f"×{m:.3f}"] for m, c, uc, n in pick])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500)
    args = parser.parse_args()
    started = time.time()
    units, staff, _, _ = up.load(up.load_ratings())
    arms: dict[str, Arm] = {}
    for arm, spec in FINAL.items():
        sl = up.make_slice(arm, "merged", up.slice_units(units, arm, "merged"), args.seeds)
        design = up.design_for(spec, sl.units, arm)
        a = Arm(arm, sl, design, {}, {})

        def cv(label: str, s: up.Spec) -> up.CVRun:
            return up.cv_spec(s, sl.units, sl.plan.folds, arm, label=label, design=design, data=up.data_for(s, sl.units))

        a.runs["F"] = cv("final model", spec)
        a.runs["RF"] = cv("final × faction modifier", replace(spec, faction=True))
        worst = check_regression(arm, sl, a.runs)
        up.log(f"{arm:9} regression ok (max |Δoof| {worst:.1e}); F {a.runs['F'].mean('mae'):.2f}, "
               f"RF {a.runs['RF'].mean('mae'):.2f}", started)
        fixed = replace(spec, mult=spec.mult - {"rating"}, fixed_rating=True)
        a.runs["B"] = cv(f"rating fixed {up.REF_RATING}/N", fixed)
        a.runs["BRF"] = cv(f"rating fixed {up.REF_RATING}/N × faction modifier", replace(fixed, faction=True))
        a.runs["F·LAD"] = cv("final model, LAD", replace(spec, loss="lad"))
        for variant in up.FCLASS_MAKERS:
            ls = up.fclass_cv(variant, spec, sl.units, sl.plan.folds, arm, design)
            # LAD reuses the least-squares κ of each fold (re-selecting it costs ×10).
            lad = up.fclass_cv(variant, replace(spec, loss="lad"), sl.units, sl.plan.folds, arm, design,
                               kappas=ls.kappas)
            for key, result in ((variant, ls), (f"{variant}·LAD", lad)):
                a.fclass[key], a.runs[key] = result, result.run
            up.log(f"{arm:9} {variant}: κ per fold {ls.kappas} → {ls.run.mean('mae'):.2f}; "
                   f"LAD {lad.run.mean('mae'):.2f}", started)
        arms[arm] = a

    # Decisions.
    order = ["F", "B", "F·LAD", "RF", "BRF", "RFC", "RFC·LAD", "JFC", "JFC·LAD"]
    reference = {"B": "F", "F·LAD": "F", "BRF": "RF", "RFC": "RF", "JFC": "RF", "RFC·LAD": "RFC", "JFC·LAD": "JFC"}
    pooled = {key: pooled_folds(arms, key) for key in order}
    beats = {}
    for key, ref in reference.items():
        delta, se = pooled_paired(arms, key, ref)
        beats[key] = delta < -se
    fc_ok = [k for k in ("RFC", "JFC") if beats[k]]
    adopted_fc = None
    if fc_ok:
        adopted_fc = min(fc_ok, key=lambda k: pooled[k].mean())
        if adopted_fc == "JFC" and "RFC" in fc_ok:
            delta, se = pooled_paired(arms, "JFC", "RFC")
            if delta >= -se:
                adopted_fc = "RFC"
    adopted = adopted_fc
    if adopted_fc and beats[f"{adopted_fc}·LAD"]:
        adopted = f"{adopted_fc}·LAD"
    staff_lines, staff_runs, staff_adopted = staff_section(staff, args.seeds)
    up.log(f"adopted {adopted}; staff {staff_adopted}", started)

    # Report.
    out = ["# Blind-study ideas tested on the unit-pricing model", "",
           "Generated by `analysis/blind_ideas.py`. The blind study (branch `blind-pricing-study`, folder "
           "`blind_study/`) modelled the same ToW + Custom prices from scratch. This report tests which of its "
           "findings improve our model, on our folds (500-seed split search, identical to `analysis/output`; the "
           "final and faction-modifier runs reproduce the committed out-of-fold predictions — checked).", "",
           "MAE is total-price gold, mean ± sd over the 5 folds. Pooled = all three arms' test rows together. "
           "Δ and SE are paired over folds (SE of the per-fold difference). κ is the ridge strength of a "
           "faction × class cell: κ pseudo-units of average price pulling it to 1; it is chosen by inner CV "
           "inside each outer training fold.", "",
           "## 1. Where the blind model wins (scored on our rows)", "",
           "Out-of-sample predictions of the blind study (its CV for development rows, its one-shot holdout for "
           "holdout rows) against ours, on exactly the same units. Its stat-only model 18b is on par with our "
           "final model; the gap is its army × unit-type table.", ""]
    out += blind_comparison(arms, adopted)
    out += ["", "## 2. Unit models", ""]
    labels = {"F": "final model (committed)", "B": f"rating fixed at {up.REF_RATING}/N", "F·LAD": "final, LAD loss",
              "RF": "final × faction modifier (committed)", "BRF": f"{up.REF_RATING}/N × faction modifier",
              "RFC": "residual faction × class", "RFC·LAD": "residual faction × class, LAD",
              "JFC": f"joint faction × class around {up.REF_RATING}/N", "JFC·LAD": "joint faction × class, LAD"}
    rows = []
    for key in order:
        line = [f"`{key}`", labels[key]]
        for a in arms.values():
            r = a.runs[key]
            line.append(f"{r.mean('mae'):.2f} ± {r.sd('mae'):.2f}")
        line.append(f"{pooled[key].mean():.2f}")
        if key in reference:
            delta, se = pooled_paired(arms, key, reference[key])
            line += [f"`{reference[key]}`", f"{delta:+.2f}", f"{se:.2f}", "yes" if beats[key] else "no"]
        else:
            line += ["", "", "", ""]
        line.append(" / ".join(str(a.runs[key].params) for a in arms.values()))
        rows.append(line)
    out += up.table(["key", "model", "infantry", "cavalry", "artillery", "pooled", "vs", "Δ pooled", "SE",
                     "beats > 1 SE", "params (inf / cav / art)"], rows)
    out += ["", "κ chosen per outer fold (inner CV): " + "; ".join(
        f"{v} — " + ", ".join(f"{name} {a.fclass[v].kappas}" for name, a in arms.items())
        for v in up.FCLASS_MAKERS) + ".",
        "Full-data fits use the κ with the lowest (non-nested) CV MAE, from the grid below.", "",
        "Parameter counts include every faction × class cell (an upper bound: cells are ridge-shrunk). "
        "LAD runs reuse the least-squares κ of each fold.", "",
        "### κ grid (non-nested CV MAE, for reference)", ""]
    for variant in up.FCLASS_MAKERS:
        header = ["arm"] + [f"κ={kappa:g}" for kappa in up.FCLASS_GRID[variant]]
        out += [f"**{variant}**", ""]
        out += up.table(header, [[name] + [f"{r.mean('mae'):.2f}" for _, r in a.fclass[variant].grid]
                                 for name, a in arms.items()])
        out += [""]
    verdict = (f"**Verdict:** adopt `{adopted}`" if adopted else "**Verdict:** no faction × class form beats the "
               "faction modifier by more than one SE") + "."
    notes = []
    if fc_ok == ["RFC", "JFC"]:
        delta, se = pooled_paired(arms, "JFC", "RFC")
        notes.append(f"JFC vs RFC: Δ pooled {delta:+.2f} (paired SE {se:.2f}) — "
                     + ("the joint form is better by more than one SE." if delta < -se
                        else "within one SE, so the residual form (stats unchanged) is preferred."))
    if not beats["B"]:
        notes.append(f"The fixed {up.REF_RATING}/N divisor does not beat free rating levels (`B` vs `F`); the free "
                     "levels stay in the stats-only model. (The joint form uses 8/N because its faction × class "
                     "cells absorb the rest.)")
    if adopted_fc and "LAD" not in (adopted or ""):
        notes.append("LAD does not improve the adopted form by more than one SE (pooled); least squares stays. "
                     "Per arm it helps infantry and hurts cavalry. Under the residual form LAD degenerates: with "
                     "κ ≈ 0 a single-unit cell fits its unit exactly, so that row's IRLS weight explodes and "
                     "dominates the stat fit (artillery).")
    out += [verdict, ""] + [f"- {n}" for n in notes] + [""]
    if adopted:
        out += [f"### Largest army × class deviations (`{adopted}`, full-data fit)", "",
                "Combined army multiplier for the cell relative to the plain 8/N rule (1 = priced as the rating "
                "alone predicts).", ""]
        for name, a in arms.items():
            out += [f"**{name}**", ""] + extreme_cells(a, adopted) + [""]
    out += ["## 3. Staff generals", ""] + staff_lines + [""]
    out += ["## 4. Not taken over, and why", "",
            "- **Per-unit-type log-linear formulas, log1p transforms, input clamping** — the blind stat-only "
            "model 18b scores 33.8 / 58.7 / 46.9 on our rows vs our final 34.6 / 59.2 / 49.7: no material gain; "
            "clamping only guards exp() extrapolation, which our additive β·x does not have.",
            "- **Unit type from the unit_key token** — identical to our `unit_class` for every regular unit "
            "(it only matters for commander variants, which we do not model).",
            "- **Army number N parsed from the name** — identical to our `rating` for all rows.",
            "- **Lordz / placeholder exclusions** — already outside our scope.",
            "- **A one-shot holdout** — our validation is CV only, with coverage-guaranteed folds.", "",
            "## 5. Next step: commander variants", "",
            "Commander variants (a general attached to a unit, `unit_class = general`, about 42% of ToW + Custom "
            "rows) are outside this model. The blind study prices them in a second stage from the regular price "
            "of the unit they lead: `price ≈ max(1, a·p_reg + b(stars)·10/N)` with one global set of 7 "
            "coefficients (a ≈ 0.9; b ≈ −60, −30, +20, +65, +120 for 0–4 stars), plus an optional per-army "
            "premium. In its CV this cut commander-row error from about 51 to 39 gold (exp 09). With our "
            "regular-unit model as stage 1 this is the immediate next extension.", "",
            f"*Runtime {time.time() - started:.0f} s.*", ""]
    REPORT.write_text("\n".join(out), encoding="utf-8")
    up.log(f"done → {REPORT.relative_to(up.ROOT)}", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
