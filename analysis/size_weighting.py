"""Size-frequency weighting in the pricing fits (analysis/SIZE_WEIGHTING_PLAN.md).

The pricing models are fitted mostly to the commonest sizes (AC infantry: 2 005 units of 100–140 models
against 13 of 240+), so mid sizes fit well and the extremes poorly; today the optimiser compensates
downstream (cost_effective_builds.harmonise_by_size, the size-band model F6). Here each row's squared error
is weighted by the inverse frequency of its size band (unit_pricing.SIZE_WEIGHTING / size_weights), and the
two models the app uses are refitted on the same folds:
  V4  the per-class model (class_structure.run_variant: segmented formula + a size power per class);
      `fixed` keeps the cached unweighted size powers (a quick screen), `nested` searches them again under
      the weights;
  F6  the size-band model (ac_pricing.size_form_run with team_values.SB_BANDS_N, 240+ merged).
Baselines are the existing unweighted checkpoints (no unweighted re-run).

Each run (dataset × arm × model × mode × variant) is its own checkpoint in analysis/.cache/size_weighting/,
written as soon as it finishes and skipped when present, so an interrupted batch resumes. One variant per
process: the worker pool captures unit_pricing settings when it starts.

    py -3.13 analysis/size_weighting.py diagnostics
    py -3.13 analysis/size_weighting.py run --dataset tow --model V4 --mode nested --variant a1 [--arms infantry]
    py -3.13 analysis/size_weighting.py report
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac_pricing as ap  # noqa: E402
import class_structure as cs  # noqa: E402
import team_values as tv  # noqa: E402
import checkpoints as ckpt  # noqa: E402
import common  # noqa: E402
import unit_pricing as up  # noqa: E402
from blind_ideas import FINAL  # noqa: E402

CACHE = ckpt.SIZE_WEIGHTING_DIR
OUT = up.ROOT / "analysis" / "output"
ARMS = ("artillery", "cavalry", "infantry")
DATASETS = ("ac", "tow")
# The user's grid (2026-10-11): tempered and full inverse frequency capped at 10×, and full inverse uncapped.
VARIANTS = {
    "a0.5c10": {"alpha": 0.5, "cap": 10.0, "min_band": 20},
    "a1c10": {"alpha": 1.0, "cap": 10.0, "min_band": 20},
    "a1": {"alpha": 1.0, "cap": None, "min_band": 1},
}


def checkpoint(dataset: str, arm: str, model: str, mode: str, variant: str) -> Path:
    return ckpt.size_weighting(f"sw1_{dataset}_{arm}_{model}_{mode}_{variant}")


save = common.save_pickle


def baseline_v4(dataset: str, arm: str) -> tuple[up.CVRun, dict[str, float]]:
    return common.load_pickle(ckpt.v4_path(dataset, arm))


def baseline_f6(dataset: str, arm: str) -> tuple[up.CVRun, dict]:
    return common.load_pickle(ckpt.sb_path(dataset, arm))


def slice_checked(dataset: str, arm: str) -> up.Slice:
    """The cached slice, asserted to carry the baseline V4's folds (so every comparison is fold-paired)."""
    sl = tv.slice_of(dataset, arm)
    fold = np.zeros(len(sl.units), int)
    for k, (_, test) in enumerate(sl.plan.folds):
        fold[test] = k + 1
    base, _ = baseline_v4(dataset, arm)
    assert np.array_equal(fold, base.oof_fold), f"{dataset} {arm}: slice folds differ from the baseline V4"
    return sl


def run_one(dataset: str, arm: str, model: str, mode: str, variant: str) -> dict:
    sl = slice_checked(dataset, arm)
    kappa = tv.kappa_of(dataset, arm)
    weights, table = up.size_weights(np.array([up.size_of(u, FINAL[arm].size) for u in sl.units]),
                                     FINAL[arm].size, VARIANTS[variant])
    if model == "V4":
        v0 = up.joint_fclass_spec(FINAL[arm], kappa)
        design = cs.segmented(up.design_for(v0, sl.units, arm), sl.units)
        fixed = baseline_v4(dataset, arm)[1] if mode == "fixed" else None
        run, p_of = cs.run_variant(f"V4 {variant}", v0, design, sl, arm, True, fixed_p=fixed)
        extra = {"p_of": p_of}
    else:
        saved = ap.SIZE_BANDS["n"]
        ap.SIZE_BANDS["n"] = tv.SB_BANDS_N
        try:
            run, extra = ap.size_form_run("F6", up.joint_fclass_spec(FINAL[arm], kappa), sl.units, sl.plan.folds, arm)
        finally:
            ap.SIZE_BANDS["n"] = saved
    return {"run": run, "extra": extra, "weights": table, "ess": up.kish_ess(weights), "n": len(sl.units),
            "variant": variant, "setting": VARIANTS[variant]}


def run_batch(args, started: float) -> None:
    models = ["V4", "F6"] if args.model == "both" else [args.model]
    up.SIZE_WEIGHTING = VARIANTS[args.variant]            # before any pool exists
    up.WORKERS = args.workers
    for dataset in args.dataset:
        for model in models:
            mode = args.mode if model == "V4" else "full"
            for arm in args.arms:
                path = checkpoint(dataset, arm, model, mode, args.variant)
                if path.exists():
                    up.log(f"skip {path.name} (done)", started)
                    continue
                result = run_one(dataset, arm, model, mode, args.variant)
                save(path, result)
                run = result["run"]
                up.log(f"{path.name}: MAE {run.mean('mae'):.2f} ± {run.se('mae'):.2f}, MAPE {run.mean('mape'):.2f}%"
                       f"{'  p ' + json.dumps(result['extra'].get('p_of')) if model == 'V4' else ''}", started)


# --- per-band errors (diagnostics and report share these) -----------------------------------------

def bands_of(units: list[up.Unit], kind: str) -> tuple[np.ndarray, list[str]]:
    size = np.array([up.size_of(u, kind) for u in units])
    return np.searchsorted(np.array(up.SIZE_WEIGHT_BANDS[kind]), size, side="right"), up.size_band_labels(kind)


def band_errors(units: list[up.Unit], kind: str, oof: np.ndarray) -> list[dict]:
    """Per size band: units, median signed residual % (bias), MAPE, MAE, share of the per-size squared error."""
    band, labels = bands_of(units, kind)
    cost = np.array([u.cost for u in units], float)
    size = np.array([up.size_of(u, kind) for u in units])
    ok = np.isfinite(oof) & (oof > 0)
    pct = 100 * (oof - cost) / cost
    sq = ((oof - cost) / size) ** 2
    total_sq = sq[ok].sum()
    rows = []
    for b, label in enumerate(labels):
        m = ok & (band == b)
        if m.sum() == 0:
            continue
        rows.append({"band": label, "units": int(m.sum()), "bias": float(np.median(pct[m])),
                     "mape": float(np.mean(np.abs(pct[m]))), "mae": float(np.mean(np.abs(oof[m] - cost[m]))),
                     "sq_share": float(sq[m].sum() / total_sq), "unit_share": float(m.sum() / ok.sum())})
    return rows


def diagnostics(started: float) -> None:
    """S1: where the current (unweighted) V4 error sits by size band, and the weights each variant gives."""
    lines = ["# Size weighting — diagnostics (generated by analysis/size_weighting.py)", "",
             "Baseline V4 out-of-fold errors by size band: share of units vs share of the fitted loss (per-size "
             "squared error), median residual % (bias, + = overpriced by the model) and MAPE. Then each "
             "variant's weight per band and the Kish effective sample size.", ""]
    for dataset in DATASETS:
        for arm in ARMS:
            sl = tv.slice_of(dataset, arm)
            kind = FINAL[arm].size
            run, _ = baseline_v4(dataset, arm)
            lines += [f"## {dataset.upper()} {arm} ({len(sl.units)} units)", "",
                      "| band | units | unit share | loss share | bias % | MAPE % |", "|---|---|---|---|---|---|"]
            for r in band_errors(sl.units, kind, run.oof):
                lines.append(f"| {r['band']} | {r['units']} | {100 * r['unit_share']:.1f}% | {100 * r['sq_share']:.1f}% "
                             f"| {r['bias']:+.1f} | {r['mape']:.1f} |")
            size = np.array([up.size_of(u, kind) for u in sl.units])
            lines += ["", "| variant | weights per band | weight share of top band | ESS |", "|---|---|---|---|"]
            for name, setting in VARIANTS.items():
                w, table = up.size_weights(size, kind, setting)
                top = max(table, key=lambda t: t["units"])
                lines.append(f"| {name} | " + ", ".join(f"{t['band']} ×{t['weight']:.2f}" for t in table)
                             + f" | {100 * top['weight_share']:.0f}% (was {100 * top['units'] / len(size):.0f}%) "
                             f"| {up.kish_ess(w):.0f} of {len(size)} |")
            lines.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "size_weighting_diagnostics.md").write_text("\n".join(lines), encoding="utf-8")
    up.log("diagnostics → analysis/output/size_weighting_diagnostics.md", started)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("diagnostics")
    r = sub.add_parser("run")
    r.add_argument("--dataset", nargs="+", choices=DATASETS, default=list(DATASETS))
    r.add_argument("--model", choices=("V4", "F6", "both"), default="both")
    r.add_argument("--mode", choices=("fixed", "nested"), default="fixed")
    r.add_argument("--variant", choices=tuple(VARIANTS), required=True)
    r.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    r.add_argument("--workers", type=int, default=up.WORKERS)
    sub.add_parser("report")
    args = parser.parse_args()
    started = time.time()
    if args.cmd == "diagnostics":
        diagnostics(started)
    elif args.cmd == "run":
        run_batch(args, started)
    else:
        import size_weighting_report as report
        report.main(started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
