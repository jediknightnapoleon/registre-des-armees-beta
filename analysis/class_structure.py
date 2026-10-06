"""How should unit class enter the price: additive term, multiplier, own size curve, own formula?

Background: on the adopted model (joint faction × class around 8/N) infantry
residuals follow unit size in a wave shared by every class — tiny skirmisher
units cost more than models^1.09 predicts, 51–80-model units less, the 100–160
bulk is right, units above ~180 models are overpriced (up to −73% for a 487-model
militia). Under 60 models every unit is a skirmisher, and within skirmishers price
grows only weakly with size. A class effect that is really a multiplier — or a
class with its own size curve — fitted as an additive per-model term would leave
exactly such a size pattern, which one global exponent then tries to absorb. The
blind study fitted a separate formula per unit type.

Variants (per arm, merged slice, the adopted model with κ fixed at its full-grid
value so every variant is compared on equal terms):
  V0  adopted model: unit class as an additive one-hot in β·x
  V1  unit class as a multiplier in M (one factor per class); additive one-hot dropped
  V2  V1 + a size exponent per class segment, models^p_c (fitted inside each
      training fold: coordinate descent on the training objective)
  V3  a separate stat formula per class segment: every β·x column interacted with
      the segment (the blind study's segmentation), shared size exponent
  V4  V3 + a size exponent per segment
Segments follow the blind study: militia + irregulars, light + missile cavalry.

Adoption: a variant must beat V0 by more than one paired SE; among those, the
simplest (V1 < V2 < V3 < V4) within one SE of the best wins.

Output: analysis/output/class_structure_report.md. Each finished arm × variant is
checkpointed in analysis/.cache/class_structure/ (gitignored), so an interrupted
run resumes where it stopped; --fresh ignores the checkpoints.

    python analysis/class_structure.py [--seeds 500] [--fresh]
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402
from blind_ideas import FINAL  # noqa: E402

SEGMENT_OF = {"infantry_irregulars": "infantry_militia", "cavalry_missile": "cavalry_light"}
P_COARSE = tuple(round(0.2 + 0.1 * i, 1) for i in range(15))          # 0.2 … 1.6
P_FINE_STEP, P_FINE_HALF = 0.05, 1                                     # then ±0.05 around the best
P_PASSES = 2
MIN_SEGMENT_UNITS = 20          # smaller segments keep the arm's exponent
SIZE_BANDS = (0, 40, 60, 80, 100, 140, 180, 240, 1000)
ORDER = ("V0", "V1", "V2", "V3", "V4")
LABELS = {"V0": "adopted: class additive in β·x", "V1": "class as a multiplier",
          "V2": "class multiplier + size exponent per class", "V3": "separate formula per class",
          "V4": "separate formula + size exponent per class"}
REPORT = up.ROOT / "analysis" / "output" / "class_structure_report.md"
CACHE = up.ROOT / "analysis" / ".cache" / "class_structure"
CACHE_VERSION = 2          # bump when a variant's definition changes


def cached(name: str, compute, fresh: bool):
    """Load a checkpoint, or compute and save it."""
    path = CACHE / f"v{CACHE_VERSION}_{name}.pkl"
    if path.exists() and not fresh:
        return pickle.loads(path.read_bytes())
    value = compute()
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(value))
    tmp.replace(path)
    return value


def segment(u: up.Unit) -> str:
    return SEGMENT_OF.get(u.unit_class, u.unit_class)


def with_class_p(d: up.SliceData, units: list[up.Unit], spec: up.Spec, p_of: dict[str, float]) -> up.SliceData:
    """Per-row size exponent: g = size^(p_c − 1) instead of size^(p − 1)."""
    p_row = np.array([p_of.get(segment(u), spec.p) for u in units])
    return replace(d, g=d.g * d.size ** (p_row - spec.p))


def segmented(design: up.Design, units: list[up.Unit]) -> up.Design:
    """Every β·x column interacted with the class segment, plus segment intercepts;
    columns constant within a segment are left out (its intercept carries them)."""
    seg = np.array([segment(u) for u in units])
    levels = sorted(set(seg.tolist()))
    reference = max(levels, key=lambda s: ((seg == s).sum(), s))
    cols, names = [], []
    for s in levels:
        inside = seg == s
        if s != reference:
            cols.append(inside.astype(float))
            names.append(f"segment={s}")
        for j, name in enumerate(design.names):
            column = design.X[:, j] * inside
            if np.ptp(column[inside]) == 0:
                continue
            cols.append(column)
            names.append(f"{name} × {s}")
    return up.Design(np.column_stack(cols), names, {**design.references, "segment": reference},
                     design.dropped, design.aliases, design.power_keys)


def fit_class_p(spec: up.Spec, design: up.Design, units: list[up.Unit], rows: np.ndarray) -> dict[str, float]:
    """Coordinate descent over the segment exponents on the training objective."""
    d0 = up.data_for(spec, units)
    seg = np.array([segment(u) for u in units])
    segments = sorted(s for s in set(seg[rows].tolist()) if (seg[rows] == s).sum() >= MIN_SEGMENT_UNITS)
    p_of: dict[str, float] = {}

    def objective(trial: dict[str, float]) -> float:
        return up.fit_on(spec, design, with_class_p(d0, units, spec, trial), rows).sse

    for _ in range(P_PASSES):
        for s in segments:
            best = (np.inf, p_of.get(s, spec.p))
            for p in P_COARSE:                                  # coarse 0.1 grid …
                sse = objective({**p_of, s: p})
                if sse < best[0] - 1e-12:
                    best = (sse, p)
            centre = best[1]
            for k in range(-P_FINE_HALF, P_FINE_HALF + 1):      # … then ±0.05 around the best
                p = round(centre + k * P_FINE_STEP, 2)
                if k == 0 or p <= 0:
                    continue
                sse = objective({**p_of, s: p})
                if sse < best[0] - 1e-12:
                    best = (sse, p)
            p_of[s] = best[1]
    return p_of


def run_variant(label: str, spec: up.Spec, design: up.Design, sl: up.Slice, arm: str,
                class_p: bool) -> tuple[up.CVRun, dict[str, float]]:
    units, folds = sl.units, sl.plan.folds
    everything = np.arange(len(units))
    if class_p:
        fitted = up.parallel_map(fit_class_p, [(spec, design, units, train) for train, _ in folds]
                                 + [(spec, design, units, everything)])
    else:
        fitted = [{} for _ in range(len(folds) + 1)]
    d0 = up.data_for(spec, units)
    oof = np.full(len(units), np.nan)
    oof_fold = np.zeros(len(units), int)
    fold_metrics = []
    for k, (train, test) in enumerate(folds):
        d = with_class_p(d0, units, spec, fitted[k])
        model = up.fit_on(spec, design, d, train)
        pred = up.predict_total(model, design, d, test)
        oof[test], oof_fold[test] = pred, k + 1
        fold_metrics.append(up.metrics(d.cost[test], pred, d.size[test]))
    d = with_class_p(d0, units, spec, fitted[-1])
    full = up.fit_on(spec, design, d, everything)
    params = full.n_params(design.X) + len(fitted[-1])
    return up.CVRun(label, fold_metrics, oof, oof_fold, spec, full, design.names, design.references,
                    design.aliases, params), fitted[-1]


def paired(a: up.CVRun, b: up.CVRun) -> tuple[float, float]:
    diff = np.array([x["mae"] - y["mae"] for x, y in zip(a.fold_metrics, b.fold_metrics)])
    return float(diff.mean()), float(diff.std(ddof=1) / np.sqrt(len(diff)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--fresh", action="store_true", help="ignore checkpoints and recompute everything")
    args = parser.parse_args()
    started = time.time()
    if not up.FCLASS_FORM or up.FCLASS_FORM[0] != "JFC":
        raise SystemExit("expects the joint faction × class form (unit_pricing.FCLASS_FORM)")
    units, _, _, _ = up.load(up.load_ratings())
    out = ["# Unit class: additive term, multiplier, own size curve, own formula?", "",
           "Generated by `analysis/class_structure.py`. All variants build on the adopted model (joint faction × "
           "class multiplier around 8/N) with κ fixed at its full-grid value per arm, same folds as "
           "`analysis/output`. Stat powers stay at the committed values. Segments follow the blind study "
           "(militia + irregulars; light + missile cavalry). MAE in gold, mean ± sd over the 5 folds; Δ and SE "
           "paired over folds against V0.", ""]
    summary, details = [], []
    for arm, final in FINAL.items():
        sl = up.make_slice(arm, "merged", up.slice_units(units, arm, "merged"), args.seeds)
        kappa = cached(f"{arm}_kappa", lambda: up.fclass_cv("JFC", final, sl.units, sl.plan.folds, arm).full_kappa,
                       args.fresh)
        v0 = up.joint_fclass_spec(final, kappa)
        v1 = replace(v0, mult=v0.mult | {"uclass"})
        d0, d1 = up.design_for(v0, sl.units, arm), up.design_for(v1, sl.units, arm)
        d3 = segmented(d0, sl.units)
        specs = {"V0": (v0, d0, False), "V1": (v1, d1, False), "V2": (v1, d1, True),
                 "V3": (v0, d3, False), "V4": (v0, d3, True)}
        runs: dict[str, up.CVRun] = {}
        exps: dict[str, dict[str, float]] = {}
        for key, (spec, design, class_p) in specs.items():
            runs[key], exps[key] = cached(f"{arm}_{key}", lambda: run_variant(LABELS[key], spec, design, sl, arm, class_p),
                                          args.fresh)
            up.log(f"{arm:9} {key} {runs[key].mean('mae'):.2f}  {exps[key] or ''}", started)
        se_best = {}
        beats = {}
        for key in ORDER[1:]:
            delta, se = paired(runs[key], runs["V0"])
            beats[key] = delta < -se
            se_best[key] = (delta, se)
        winners = [k for k in ORDER[1:] if beats[k]]
        adopted = "V0"
        if winners:
            best = min(winners, key=lambda k: runs[k].mean("mae"))
            adopted = next(k for k in ORDER[1:] if k in winners and paired(runs[k], runs[best])[0] <= paired(runs[k], runs[best])[1])
        rows = []
        for key in ORDER:
            r = runs[key]
            delta, se = se_best.get(key, (0.0, 0.0))
            rows.append([f"`{key}`", LABELS[key], f"{r.mean('mae'):.2f} ± {r.sd('mae'):.2f}", f"{r.mean('mape'):.2f}",
                         "" if key == "V0" else f"{delta:+.2f}", "" if key == "V0" else f"{se:.2f}",
                         "" if key == "V0" else ("yes" if beats[key] else "no"), r.params,
                         "**adopted**" if key == adopted else ""])
        details += [f"## {arm}", ""] + up.table(["key", "variant", "MAE", "MAPE %", "Δ vs V0", "SE", "beats > 1 SE",
                                                  "params", ""], rows) + [""]
        m = runs["V1"].full.levels.get("uclass", {})
        details += ["Class multipliers (V1, full-data fit, reference = 1): "
                    + ", ".join(f"{c.split('_', 1)[1]} ×{v:.3f}" for c, v in sorted(m.items())) + "."]
        for key in ("V2", "V4"):
            details += [f"Size exponents per segment ({key}, full-data fit; others keep p = {final.p:g}): "
                        + ", ".join(f"{s.split('_', 1)[1]} {p:g}" for s, p in sorted(exps[key].items())) + "."]
        details += [""]
        # Residual by size band (median resid %, out-of-fold).
        cost = np.array([u.cost for u in sl.units], float)
        size = np.array([up.size_of(u, final.size) for u in sl.units])
        bands = [(lo, hi) for lo, hi in zip(SIZE_BANDS[:-1], SIZE_BANDS[1:])
                 if ((size > lo) & (size <= hi)).sum() >= 5] if arm != "artillery" else [(0, 2), (2, 3), (3, 4), (4, 6), (6, 100)]
        header = ["variant"] + [f"{lo + 1}–{hi}" if hi < 1000 else f">{lo}" for lo, hi in bands]
        band_rows = []
        for key in ORDER:
            oof = runs[key].oof
            line = [f"`{key}`"]
            for lo, hi in bands:
                mask = (size > lo) & (size <= hi) & np.isfinite(oof)
                line.append(f"{np.median((cost[mask] - oof[mask]) / oof[mask] * 100):+.1f}% ({mask.sum()})" if mask.any() else "")
            band_rows.append(line)
        details += [f"Median out-of-fold residual by size ({'guns' if final.size == 'guns' else 'models'}); "
                    "negative = model too dear:", ""] + up.table(header, band_rows) + [""]
        # Per segment MAE.
        seg = np.array([segment(u) for u in sl.units])
        seg_rows = []
        for s in sorted(set(seg.tolist())):
            mask = seg == s
            seg_rows.append([s, int(mask.sum())] + [
                f"{np.nanmean(np.abs(runs[k].oof[mask] - cost[mask])):.1f}" for k in ORDER])
        details += ["MAE per segment:", ""] + up.table(["segment", "units"] + list(ORDER), seg_rows) + [""]
        summary.append([arm] + [f"{runs[k].mean('mae'):.2f}" for k in ORDER] + [f"`{adopted}` {LABELS[adopted]}"])
    out += ["## Summary", ""] + up.table(["arm"] + list(ORDER) + ["adopted"], summary) + [""]
    out += [f"- `{k}`: {LABELS[k]}" for k in ORDER] + [""] + details
    out += [f"*Runtime {time.time() - started:.0f} s.*", ""]
    REPORT.write_text("\n".join(out), encoding="utf-8")
    up.log(f"done → {REPORT.relative_to(up.ROOT)}", started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
