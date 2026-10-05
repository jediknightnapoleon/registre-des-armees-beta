"""Does training on the extreme units help? Pinning edge units to the training set.

Background: rare extreme units sit at the edge of the data — the 64-pdr battery,
very large militia and irregular units, the fixed guns, the stat outliers. When
one lands in a test fold the model must extrapolate. The split search already pins
a group that alone holds a one-hot level (`pinned_groups`), but continuous extremes
(size, range/calibre, stats) are never pinned. The blind study met the same issue
(it clamps inputs to the training range because exp() extrapolation blew up rare
artillery and militia rows).

Schemes, per arm (merged slice, final adopted design):
  current  the committed folds (500-seed split search)
  P1       + every group holding the min or the max of a model column (continuous
           columns only; a tail shared by more than MAX_TIES groups is not "rare")
  P2       + every group beyond the 1% / 99% quantiles of a model column
Each scheme re-runs the same split search with those groups pinned to train.

Pinning removes the hardest rows from testing, so raw CV MAE would flatter it. The
report therefore gives
  (a) MAE on the rows that are test rows under every scheme — does training on the
      extremes help the typical unit;
  (b) the current scheme's out-of-fold error on the extreme rows themselves — how
      badly they are extrapolated today;
  (c) coefficient stability — the spread of each β across the five fold fits.
for the final model (F) and the adopted faction × class model (FC).

Adoption: pinning is a validation-design choice, not a model change. It is adopted
only if (a) improves the adopted model by more than one SE, or (c) shows clearly
more stable fits (median relative spread down by more than a quarter).

Output: analysis/output/extreme_pinning_report.md

    python analysis/extreme_pinning.py [--seeds 500]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402
from blind_ideas import FINAL  # noqa: E402

MAX_TIES = 3            # a tail value shared by more groups than this is not a rare extreme
TAIL = 0.01             # P2: quantile tails
STABLE_GAIN = 0.25      # (c): median relative β spread must drop by more than this share
SCHEMES = ("current", "P1", "P2")
REPORT = up.ROOT / "analysis" / "output" / "extreme_pinning_report.md"


def model_columns(arm: str, units: list[up.Unit], spec: up.Spec) -> list[tuple[str, np.ndarray]]:
    """Continuous model columns (more than two distinct values) plus unit size."""
    design = up.design_for(spec, units, arm)
    cols = [(name, design.X[:, j]) for j, name in enumerate(design.names) if len(np.unique(design.X[:, j])) > 2]
    size = np.array([up.size_of(u, spec.size) for u in units], float)
    return cols + [("size (" + ("guns" if spec.size == "guns" else "models") + ")", size)]


def extremes(arm: str, units: list[up.Unit], spec: up.Spec, groups: np.ndarray,
             scheme: str) -> tuple[set[int], dict[int, list[str]]]:
    """Group ids to pin, and for each the columns/tails that made it extreme."""
    why: dict[int, list[str]] = {}
    for name, x in model_columns(arm, units, spec):
        if scheme == "P1":
            tails = (("min", x == x.min()), ("max", x == x.max()))
        else:
            lo, hi = np.quantile(x, TAIL), np.quantile(x, 1 - TAIL)
            tails = (("low 1%", x < lo), ("high 1%", x > hi))
        for tail, mask in tails:
            holders = set(groups[mask].tolist())
            if scheme == "P1" and len(holders) > MAX_TIES:
                continue
            for g in holders:
                why.setdefault(g, []).append(f"{name} {tail}")
    return set(why), why


@dataclass
class SchemeRun:
    scheme: str
    sl: up.Slice
    pinned_extra: set[int]
    runs: dict[str, up.CVRun]
    betas: dict[str, np.ndarray]           # model -> fold × coefficient (stat part)


def fold_betas(spec: up.Spec, sl: up.Slice, arm: str, design: up.Design) -> np.ndarray:
    d = up.data_for(spec, sl.units)
    return np.array([np.concatenate([[m.b0], m.beta]) for m in
                     (up.fit_on(spec, design, d, train) for train, _ in sl.plan.folds)])


def relative_spread(betas: np.ndarray) -> np.ndarray:
    """sd across folds / |mean|, per coefficient with a non-negligible mean."""
    mean, sd = betas.mean(axis=0), betas.std(axis=0, ddof=1)
    keep = np.abs(mean) > 1e-6 * np.abs(mean).max()
    return sd[keep] / np.abs(mean[keep])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500)
    args = parser.parse_args()
    started = time.time()
    if not up.FCLASS_FORM:
        raise SystemExit("unit_pricing.FCLASS_FORM is not set")
    variant, loss = up.FCLASS_FORM
    units, _, _, _ = up.load(up.load_ratings())
    results: dict[str, dict[str, SchemeRun]] = {}
    why_by_arm: dict[str, dict[int, list[str]]] = {}
    for arm, spec in FINAL.items():
        arm_units = up.slice_units(units, arm, "merged")
        results[arm] = {}
        for scheme in SCHEMES:
            chosen: dict[int, list[str]] = {}

            def extra(groups: np.ndarray, scheme=scheme, chosen=chosen) -> set[int]:
                ids, why = extremes(arm, arm_units, spec, groups, scheme)
                chosen.update(why)
                return ids

            sl = up.make_slice(arm, "merged", arm_units, args.seeds, None if scheme == "current" else extra)
            if scheme == "P1":
                why_by_arm[arm] = dict(chosen)
            design = up.design_for(spec, sl.units, arm)
            runs = {"F": up.cv_spec(spec, sl.units, sl.plan.folds, arm, label="final", design=design,
                                    data=up.data_for(spec, sl.units))}
            fc = up.fclass_cv(variant, replace(spec, loss=loss), sl.units, sl.plan.folds, arm, design)
            runs["FC"] = fc.run
            betas = {"F": fold_betas(spec, sl, arm, design),
                     "FC": fold_betas(up.FCLASS_MAKERS[variant](replace(spec, loss=loss), fc.full_kappa),
                                      sl, arm, design)}
            results[arm][scheme] = SchemeRun(scheme, sl, set(chosen), runs, betas)
            up.log(f"{arm:9} {scheme:7} pinned rows {sl.plan.n_pinned_rows:4}; F {runs['F'].mean('mae'):.2f}, "
                   f"FC {runs['FC'].mean('mae'):.2f}", started)

    # (a) common test rows.
    out = ["# Pinning extreme units to the training set", "",
           "Generated by `analysis/extreme_pinning.py`. Final model `F` and the adopted faction × class model "
           f"`FC` ({up.FCLASS_LABEL[variant]}), merged slices, same 500-seed split search as `analysis/output`.",
           "",
           f"- **P1** pins every group holding the min or the max of a continuous model column or of unit size "
           f"(a tail shared by more than {MAX_TIES} groups is skipped).",
           f"- **P2** pins every group beyond the {TAIL:.0%} / {1 - TAIL:.0%} quantiles of those columns.", "",
           "## (a) Does training on the extremes help the typical unit?", "",
           "MAE on the rows that are test rows under all three schemes. Δ vs `current` with an approximate "
           "SE from the per-row paired differences.", ""]
    rows = []
    pooled: dict[tuple[str, str], list[np.ndarray]] = {}
    for arm, by in results.items():
        cost = np.array([u.cost for u in by["current"].sl.units], float)
        common = np.all([np.isfinite(by[s].runs["F"].oof) for s in SCHEMES], axis=0)
        for model in ("F", "FC"):
            errors = {s: np.abs(by[s].runs[model].oof[common] - cost[common]) for s in SCHEMES}
            line = [arm, model, int(common.sum()), f"{errors['current'].mean():.2f}"]
            for s in ("P1", "P2"):
                diff = errors[s] - errors["current"]
                line.append(f"{errors[s].mean():.2f} ({diff.mean():+.2f} ± {diff.std(ddof=1) / np.sqrt(len(diff)):.2f})")
                pooled.setdefault((model, s), []).append(diff)
            line += [by["P1"].sl.plan.n_pinned_rows - by["current"].sl.plan.n_pinned_rows,
                     by["P2"].sl.plan.n_pinned_rows - by["current"].sl.plan.n_pinned_rows]
            rows.append(line)
    out += up.table(["arm", "model", "common test rows", "current MAE", "P1 MAE (Δ ± SE)", "P2 MAE (Δ ± SE)",
                     "extra rows pinned P1", "extra rows pinned P2"], rows)
    verdict_a = {}
    lines = []
    for model in ("F", "FC"):
        for s in ("P1", "P2"):
            diff = np.concatenate(pooled[(model, s)])
            delta, se = diff.mean(), diff.std(ddof=1) / np.sqrt(len(diff))
            verdict_a[(model, s)] = delta < -se
            lines.append(f"`{model}` {s}: pooled Δ {delta:+.2f} ± {se:.2f} gold")
    out += ["", "Pooled over arms: " + "; ".join(lines) + ".", ""]

    # (b) extreme rows today.
    out += ["## (b) How badly are the extremes predicted today?", "",
            "Out-of-fold predictions under the **current** folds for the P1 extreme groups (rows pinned for "
            "coverage have no out-of-fold prediction and are left out).", ""]
    rows = []
    for arm, by in results.items():
        cur = by["current"]
        cost = np.array([u.cost for u in cur.sl.units], float)
        is_ext = np.isin(cur.sl.groups, list(why_by_arm[arm]))
        ok = np.isfinite(cur.runs["F"].oof)
        for model in ("F", "FC"):
            err = np.abs(cur.runs[model].oof - cost)
            rows.append([arm, model, int((is_ext & ok).sum()), f"{err[is_ext & ok].mean():.1f}",
                         f"{np.median(np.abs(err / cost)[is_ext & ok]) * 100:.1f}%",
                         f"{err[~is_ext & ok].mean():.1f}", f"{np.median(np.abs(err / cost)[~is_ext & ok]) * 100:.1f}%"])
    out += up.table(["arm", "model", "extreme rows tested", "MAE extreme", "median APE extreme",
                     "MAE other", "median APE other"], rows)
    out += ["", "Worst extreme units (current folds, adopted model `FC`):", ""]
    rows = []
    for arm, by in results.items():
        cur = by["current"]
        fc = cur.runs["FC"]
        for i, u in enumerate(cur.sl.units):
            g = int(cur.sl.groups[i])
            if g in why_by_arm[arm] and np.isfinite(fc.oof[i]):
                rows.append((abs(fc.oof[i] - u.cost), arm, u, fc.oof[i], cur.runs["F"].oof[i],
                             ", ".join(sorted(set(why_by_arm[arm][g])))[:90]))
    rows.sort(key=lambda t: -t[0])
    out += up.table(["arm", "unit", "corps", "size", "cost", "FC pred", "F pred", "extreme in"],
                    [[arm, u.name, u.corps, f"{up.size_of(u, FINAL[arm].size):g}", u.cost, f"{p:.0f}", f"{pf:.0f}", why]
                     for _, arm, u, p, pf, why in rows[:20]])

    # (c) stability.
    out += ["", "## (c) Coefficient stability across the five fold fits", "",
            "Relative spread of each coefficient (b0 and β) across the fold fits, sd / |mean|; median and 90th "
            "percentile over coefficients. Lower = more stable.", ""]
    rows = []
    verdict_c = {}
    for arm, by in results.items():
        for model in ("F", "FC"):
            spread = {s: relative_spread(by[s].betas[model]) for s in SCHEMES}
            line = [arm, model] + [f"{np.median(spread[s]):.3f} / {np.quantile(spread[s], 0.9):.3f}" for s in SCHEMES]
            rows.append(line)
            for s in ("P1", "P2"):
                verdict_c.setdefault((model, s), []).append(np.median(spread[s]) < (1 - STABLE_GAIN) * np.median(spread["current"]))
    out += up.table(["arm", "model"] + [f"{s} median / p90" for s in SCHEMES], rows)

    # Verdict.
    adopt = [s for s in ("P1", "P2") if verdict_a[("FC", s)] or all(verdict_c[("FC", s)])]
    out += ["", "## Verdict", ""]
    if adopt:
        out += [f"**Adopt {adopt[0]}**: " + ("it improves the adopted model on common rows by more than one SE"
                if verdict_a[("FC", adopt[0])] else "its fits are clearly more stable in every arm") + "."]
    else:
        out += ["**Keep the current folds.** Pinning the extremes neither improves the adopted model on the "
                "common test rows by more than one SE nor makes the fits clearly more stable. Table (b) stays "
                "the useful output: it says how far the model can be trusted on edge units."]
    out += ["", f"*Runtime {time.time() - started:.0f} s.*", ""]
    REPORT.write_text("\n".join(out), encoding="utf-8")
    up.log(f"done → {REPORT.relative_to(up.ROOT)}; adopt {adopt or 'none'}", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
