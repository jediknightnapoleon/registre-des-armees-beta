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
the best. Faction modifiers are fitted on top of the final model; the adopted
army-level form (FCLASS_FORM, from the blind study) replaces the free rating
levels by the divisor 8/N and adds a ridge-shrunk faction × unit_class
multiplier fitted jointly with the stats (run "FC"). Staff generals:
price = b·stars^q·(8/N), 1 gold without stars (T3). See analysis/PRICING_MODEL_REPORT.md
for the model written out and analysis/HANDOFF.md for how to work on it.

Validation is 5-fold cross-validation where every fold is an 80/20 split built
to keep identical units together, stratify by unit type, cover every
categorical level in train, and spread each faction evenly.

Inputs:  data/generated/ntw3_units_analysis.csv  (tools/build_analysis_dataset.py)
         data/generated/army_corps_catalog.csv   (corps ratings)
Outputs: analysis/output/unit_pricing_report.md
         analysis/output/search_results.csv
         analysis/output/coefficients.csv
         analysis/output/oof_predictions.csv

Run from the repository root (~50 minutes with the default 6 worker processes):

    python analysis/unit_pricing.py [--seeds 500] [--workers 6] [--out DIR] [--artillery-cal …] [--linear]

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
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ARMS, CATALOG_CSV, DATA_CSV, ROOT, log, table  # noqa: E402  (re-exported as up.*)
from pricing import config  # noqa: E402
from pricing.config import Settings, configure  # noqa: E402,F401  (re-exported as up.*)

from pricing.constants import (  # noqa: E402,F401
    ABILITIES, ABLATIONS, CANDIDATES, CATEGORICAL, DEV_CORPS, EXTRA_ABILITIES, FINE_P_HALF, FINE_P_STEP, FINE_STAT_HALF, FINE_STAT_STEP, GROUPING, IMPERIAL_CUSTOM, MAX_RECENTRE, MIN_BALANCE_ROWS, MIN_FLAG_ROWS, MIN_POWER, MIN_STRATUM_GROUPS, MULT_CATEGORICAL, NUMERIC, N_SPLITS, POLAND, POWER_SCALE, P_WINDOW, RATE_SCALE, REF_RATING, SHAPE_DEFAULTS, SHOOT_STATS, SIDES, SIZE_KINDS, SPEED_TAG_RE, TEST_SHARE)
from pricing.data import (  # noqa: E402,F401
    Staff, Unit, in_scope, load, load_ratings, num, side_of)
from pricing.spec import (  # noqa: E402,F401
    Spec, with_powers)
from pricing.design import (  # noqa: E402,F401
    Design, build_design, design_for, factor_values, most_common_level, natural_spline_basis, prune_aliases, spline_knots)
from pricing.model import (  # noqa: E402,F401
    PriceModel, metrics)
from pricing.splits import (  # noqa: E402,F401
    Fold, SplitPlan, assign_folds, balance_scores, folds_from, group_ids, pinned_groups, repair, restrict, search_splits, unidentified)
from pricing.formatting import (  # noqa: E402,F401
    describe_factors, f1, f2, f3, pct_resid, pm, spearman)
from pricing.cv import (  # noqa: E402,F401
    CVRun, IRLS_FLOOR, IRLS_STEPS, PREVIOUS_FINAL, SIZE_WEIGHT_BANDS, Slice, SliceData, coverage_report, cv_baseline, cv_spec, data_for, fit_on, full_fit_prices, kish_ess, make_slice, predict_total, rich_design, side_spec, size_band_labels, size_of, size_weights, slice_data, slice_units, strata_for, sub)
from pricing.pool import (  # noqa: E402,F401
    parallel_map)
from pricing.search import (  # noqa: E402,F401
    ARTILLERY_CAL_KEYS, FineResult, PowerObjective, PowerResult, Profile, SearchResult, VariantResult, adopt_variant, descend_powers, enumerate_specs, line_search, local_profiles, nested_fine, nested_powers, power_floor, profile_p, refine_powers, screen_variants, shape_variants, structure_search, variant_details)
from pricing.fclass import (  # noqa: E402,F401
    FCLASS_FORM, FCLASS_GRID, FCLASS_LABEL, FCLASS_MAKERS, FclassResult, fclass_cv, fclass_multiplier, fold_run, inner_kappa, joint_fclass_spec, residual_fclass_spec, shared_faction_runs, shared_modifier)
from pricing.staff import (  # noqa: E402,F401
    STAFF_POWER_GRID, STAFF_RATING_NAMES, StaffRun, StaffSlice, make_staff_slice, staff_coverage, staff_cv, staff_faction_m, staff_full, staff_power_fit, staff_power_price, staff_rating_design)
from pricing.diagnostics import (  # noqa: E402,F401
    LB_PER, SHELL_WORDS, eastern_calibre_rows, firearm_range_overlap)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500, help="split seeds to search (default 500)")
    parser.add_argument("--linear", action="store_true",
                        help="fully linear run: size = models, p = 1, linear stats (no size or stat powers)")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default analysis/output)")
    parser.add_argument("--artillery-cal", choices=["auto", *ARTILLERY_CAL_KEYS], default="auto",
                        help="artillery calibre representations to screen: all (auto), or only F0 plus this one")
    parser.add_argument("--workers", type=int, default=config.settings.workers,
                        help="worker processes for the nested power searches "
                             f"(default {config.settings.workers}; 1 = serial)")
    args = parser.parse_args()
    if args.out is not None:
        configure(out_dir=args.out.resolve())
    configure(artillery_cal=args.artillery_cal, workers=args.workers)
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
    grid = (1.0,) if args.linear else config.settings.p_grid
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
    out_dir = config.settings.out_dir
    log(f"done → {out_dir.relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}", started)
    return 0


# --- Output -------------------------------------------------------------------

def write_outputs(res: Results) -> None:
    config.settings.out_dir.mkdir(parents=True, exist_ok=True)
    write_search(res)
    write_coefficients(res)
    write_oof(res)
    (config.settings.out_dir / "unit_pricing_report.md").write_text("\n".join(report_lines(res)) + "\n", encoding="utf-8")


def write_search(res: Results) -> None:
    with (config.settings.out_dir / "search_results.csv").open("w", encoding="utf-8", newline="") as handle:
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
    with (config.settings.out_dir / "coefficients.csv").open("w", encoding="utf-8", newline="") as handle:
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


def write_oof(res: Results) -> None:
    with (config.settings.out_dir / "oof_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
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
        for i, p in enumerate(config.settings.p_grid):
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
        cal = config.settings.artillery_cal
        if cal != "auto":
            add(f"**Artillery was restricted** (`--artillery-cal {cal}`): only F0 and "
                f"{ARTILLERY_CAL_KEYS[cal]} were screened, so this run fixes the calibre representation "
                "rather than choosing it.")
            add("")
        add("The adopted variant then goes through the stat-power comparison and fine search below.")
        add("")
    if res.powers:
        add(f"For each numeric stat, a power from {list(config.settings.power_grid)}, plus the size power p within ±{P_WINDOW}, is "
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


# --- Settings access for importers ---------------------------------------------
# The settings used to be module globals that importers reassigned (up.WORKERS = 4). Reading them under
# their old names still works; assigning one raises, because it would no longer reach the code.
SETTING_NAMES = {"WORKERS": "workers", "OUT_DIR": "out_dir", "P_GRID": "p_grid", "POWER_GRID": "power_grid",
                 "MAX_PASSES": "max_passes", "FINE_PASSES": "fine_passes", "MAX_ITER": "max_iter",
                 "TOLERANCE": "tolerance", "ARTILLERY_CAL": "artillery_cal", "SIZE_WEIGHTING": "size_weighting"}


def __getattr__(name: str) -> object:
    if name in SETTING_NAMES:
        return getattr(config.settings, SETTING_NAMES[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class _Module(type(sys)):
    def __setattr__(self, name: str, value: object) -> None:
        if name in SETTING_NAMES:
            raise AttributeError(f"{name} is a setting: use unit_pricing.configure({SETTING_NAMES[name]}=...)")
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _Module


if __name__ == "__main__":
    raise SystemExit(main())
