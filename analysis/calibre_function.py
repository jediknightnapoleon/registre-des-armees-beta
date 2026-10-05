"""Can a smooth function of range and damage replace the artillery cannon-type one-hot?

Background: the cannon-type (projectile) one-hot cut artillery CV MAE from 58.4 to
49.4. Each of the 17 projectiles has exactly one (range, damage, gun reload, shot
type), so calibre fixes range and damage and any f(range, damage) is a function of
calibre. The one-hot is the most flexible such function (14-16 levels), but rare
cannon types (the single 64-pdr, five 18-pdrs, six 2-pdrs) estimate their level
from very few batteries; a smooth f with a handful of parameters borrows strength
across calibres and would also price a calibre that never appears in the data.

This driver reuses analysis/unit_pricing.py: the same merged artillery slice and
folds (same seeds), the adopted artillery structure (guns^1.2 × rating + c), and
the same nested coarse descent of stat powers. Variants replace only the calibre
representation (see the `cal` / `cal_df` / `shot` shape options there).

Adoption, preferring the simpler form: the best smooth function replaces the
one-hot if its nested MAE is within one SE of the one-hot's.

Output: analysis/output/calibre_function_report.md

    python analysis/calibre_function.py [--seeds 500]
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

# The adopted artillery structure from the last full run (unit_pricing.py): the
# structure-search headline guns^1.2 × rating + c, with the accepted ablation
# extras (damage, gun reload — dropped by every calibre shape). K0 is its
# cannon-type one-hot variant; its nested MAE in that run was 49.43.
PRE_POWER = up.Spec(mult=frozenset({"rating"}), const=True, size="guns", p=1.2,
                    extras=frozenset({"damage", "proj_reload"}))
EXPECTED_K0 = 49.43

VARIANTS = [
    ("K0", "cannon-type one-hot (current)", {"cal": "projectile"}),
    ("K1a", "power of damage (+ shot type)", {"cal": "calibre"}),
    ("K1", "powers of range and damage (+ shot type)", {"cal": "power2"}),
    ("K2·2", "spline in log range, df 2 (+ shot type)", {"cal": "spline_r", "cal_df": "2"}),
    ("K2·3", "spline in log range, df 3 (+ shot type)", {"cal": "spline_r", "cal_df": "3"}),
    ("K2·4", "spline in log range, df 4 (+ shot type)", {"cal": "spline_r", "cal_df": "4"}),
    ("K2·5", "spline in log range, df 5 (+ shot type)", {"cal": "spline_r", "cal_df": "5"}),
    ("K2·6", "spline in log range, df 6 (+ shot type)", {"cal": "spline_r", "cal_df": "6"}),
    ("K3·2", "spline in log damage, df 2 (+ shot type)", {"cal": "spline_d", "cal_df": "2"}),
    ("K3·3", "spline in log damage, df 3 (+ shot type)", {"cal": "spline_d", "cal_df": "3"}),
    ("K3·4", "spline in log damage, df 4 (+ shot type)", {"cal": "spline_d", "cal_df": "4"}),
    ("K4·2", "splines in log range + log damage, df 2+2, no shot type", {"cal": "spline_rd", "cal_df": "2", "shot": "none"}),
    ("K4·3", "splines in log range + log damage, df 3+3, no shot type", {"cal": "spline_rd", "cal_df": "3", "shot": "none"}),
    ("K5·2", "splines in log range + log damage, df 2+2 (+ shot type)", {"cal": "spline_rd", "cal_df": "2"}),
    ("K5·3", "splines in log range + log damage, df 3+3 (+ shot type)", {"cal": "spline_rd", "cal_df": "3"}),
    ("K6", "quadratic surface in (log range, log damage), no shot type", {"cal": "poly2", "shot": "none"}),
]

CALIBRE_PREFIXES = ("cal_", "calibre", "projectile=", "shot=")


@dataclass
class Result:
    key: str
    label: str
    spec: up.Spec
    power: up.PowerResult
    params: int
    levels: dict[str, float]          # projectile -> calibre term relative to the 6-pdr (full-data fit)
    calibre_columns: list[str]

    def mean(self) -> float:
        return self.power.nested.mean("mae")

    def se(self) -> float:
        return self.power.nested.se("mae")


def calibre_levels(spec: up.Spec, units, power: up.PowerResult) -> tuple[dict[str, float], list[str], dict]:
    """Full-data fit with the variant's fitted powers; the calibre term per
    projectile = Σ β·x over the calibre and shot-type columns (they depend only on
    the projectile), relative to the 6-pdr."""
    fitted = up.with_powers(spec, power.full_powers, power.full_p)
    design, d = up.design_for(fitted, units, "artillery"), up.data_for(fitted, units)
    model = up.fit_on(fitted, design, d, np.arange(len(units)))
    columns = [j for j, n in enumerate(design.names) if n.startswith(CALIBRE_PREFIXES)]
    row_of = {}
    for i, u in enumerate(units):
        row_of.setdefault(u.projectile, i)
    raw = {q: float(design.X[i, columns] @ model.beta[columns]) for q, i in row_of.items()}
    ref = raw["cannon_6_pounder_shot"]
    return ({q: v - ref for q, v in raw.items()}, [design.names[j] for j in columns],
            {"design": design, "model": model, "rows": row_of, "columns": columns})


def second_stage(target: dict[str, float], spec: up.Spec, power: up.PowerResult, units,
                 weights: Counter) -> tuple[float, dict[str, float]]:
    """How well a smooth form can represent the one-hot's calibre levels: weighted
    least squares of the 17 K0 levels on the form's calibre/shot columns evaluated
    at each projectile (weights = batteries per projectile). Returns (R², fitted)."""
    fitted = up.with_powers(spec, power.full_powers, power.full_p)
    design = up.design_for(fitted, units, "artillery")
    columns = [j for j, n in enumerate(design.names) if n.startswith(CALIBRE_PREFIXES)]
    row_of = {}
    for i, u in enumerate(units):
        row_of.setdefault(u.projectile, i)
    names = sorted(target)
    A = np.column_stack([np.ones(len(names))] + [[design.X[row_of[q], j] for q in names] for j in columns])
    y = np.array([target[q] for q in names])
    w = np.array([weights[q] for q in names], float)
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    fit = A @ coef
    mean = (w * y).sum() / w.sum()
    r2 = 1 - (w * (y - fit) ** 2).sum() / (w * (y - mean) ** 2).sum()
    return float(r2), dict(zip(names, (fit - fit[names.index("cannon_6_pounder_shot")]).tolist()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=500)
    args = parser.parse_args()
    started = time.time()
    log = lambda m: print(f"[{time.time() - started:5.0f}s] {m}", flush=True)

    ratings = up.load_ratings()
    units, _, _, _ = up.load(ratings)
    sl = up.make_slice("artillery", "merged", up.slice_units(units, "artillery", "merged"), args.seeds)
    weights = Counter(u.projectile for u in sl.units)
    info = {}
    for u in sl.units:
        info.setdefault(u.projectile, (u.shot, u.values["range"], u.values["proj_damage"]))

    results: list[Result] = []
    for key, label, shape in VARIANTS:
        spec = replace(PRE_POWER, shape=tuple(sorted(shape.items())))
        base = up.cv_spec(spec, sl.units, sl.plan.folds, "artillery", full_fit=False)
        power = up.nested_powers(spec, sl, base)
        design = up.design_for(spec, sl.units, "artillery")
        levels, columns, _ = calibre_levels(spec, sl.units, power)
        results.append(Result(key, label, spec, power, base.params + len(design.power_keys) + 1, levels, columns))
        log(f"{key:5} {label:58} nested MAE {power.nested.mean('mae'):6.2f} ± {power.nested.sd('mae'):.2f}")

    k0 = results[0]
    smooth = results[1:]
    best = min(smooth, key=lambda r: r.mean())
    simplest = min((r for r in smooth if r.mean() <= best.mean() + best.se()), key=lambda r: (r.params, r.mean()))
    adopted = best.mean() <= k0.mean() + k0.se()
    stage2 = {r.key: second_stage(k0.levels, r.spec, r.power, sl.units, weights) for r in smooth}

    # Hand-check: rebuild the best smooth form's spline columns for one 12-pdr
    # battery straight from the basis definition and compare with the design.
    check = ""
    if best.spec.shape_of("cal").startswith("spline"):
        fitted = up.with_powers(best.spec, best.power.full_powers, best.power.full_p)
        design = up.design_for(fitted, sl.units, "artillery")
        i = next(i for i, u in enumerate(sl.units) if u.projectile == "cannon_12_pounder_shot")
        df = int(best.spec.shape_of("cal_df"))
        diffs = []
        for prefix, field in (("cal_r", "range"), ("cal_d", "proj_damage")):
            cols = [j for j, n in enumerate(design.names) if n.startswith(prefix)]
            if not cols:
                continue
            x_all = np.log([u.values[field] for u in sl.units])
            basis = up.natural_spline_basis(np.log([sl.units[i].values[field]]), up.spline_knots(x_all, df))[0]
            design_values = design.X[i, cols]
            # alias pruning may drop a basis column; compare the ones kept
            names = [design.names[j] for j in cols]
            for name, value in zip(names, design_values):
                diffs.append(abs(basis[int(name[len(prefix):]) - 1] - value))
        check = f"max |basis − design| for a 12-pdr battery: {max(diffs):.1e}" if diffs else ""

    write_report(results, k0, best, simplest, adopted, stage2, info, weights, check, args.seeds,
                 time.time() - started, regression_ok=abs(k0.mean() - EXPECTED_K0) < 0.01)
    out = up.OUT_DIR / "calibre_function_report.md"
    log(f"done → {out.relative_to(up.ROOT) if out.is_relative_to(up.ROOT) else out}")
    return 0


def write_report(results, k0, best, simplest, adopted, stage2, info, weights, check, n_seeds, elapsed,
                 regression_ok) -> None:
    f1 = up.f1
    L: list[str] = []
    add = L.append
    add("# Artillery calibre — can a smooth f(range, damage) replace the cannon-type one-hot?")
    add("")
    add(f"Generated by `analysis/calibre_function.py` ({n_seeds} split seeds, {elapsed / 60:.0f} min). Merged "
        "artillery slice, with the same folds and nested coarse power descent as `unit_pricing.py`. Everything "
        "except the calibre representation is the adopted artillery model: guns^1.2 × rating + c, with "
        "additive crew stats and fitted powers.")
    add("")
    add("## 1. Does calibre alone fix range and damage?")
    add("")
    add("**Yes.** Each of the 17 projectiles has exactly one range, damage, gun reload and shot type, and "
        "canister is one per calibre too. So any f(range, damage) is a function of calibre, and the "
        "cannon-type one-hot is the most flexible such function.")
    add("")
    add("## 2. Smooth calibre functions vs the one-hot")
    add("")
    add(f"Regression check: K0 reproduces the full run's cannon-type nested MAE ({EXPECTED_K0}): "
        f"**{'yes' if regression_ok else 'NO'}** ({k0.mean():.2f}).")
    add("")
    rows = []
    for r in results:
        r2 = stage2.get(r.key)
        tag = " **(adopted)**" if adopted and r is best else (" (best smooth)" if r is best else "")
        rows.append([f"`{r.key}`", r.label + tag, up.pm(r.power.nested, "mae", f1), f"{r.mean() - k0.mean():+.2f}",
                     up.f2(k0.se()), f1(r.power.nested.mean("mape")), r.params,
                     f"{r2[0]:.3f}" if r2 else "—"])
    L += up.table(["variant", "calibre representation", "nested MAE", "Δ vs one-hot", "1 SE (one-hot)",
                   "MAPE %", "params", "R² vs one-hot levels"], rows)
    add("")
    add("*R² vs one-hot levels* is the second-stage check: how much of the one-hot's 17 calibre levels (weighted "
        "by battery count) this form can reproduce when fitted to them directly. A form can score a high R² "
        "and still lose out of fold, or the reverse, because the one-hot levels themselves are noisy for rare "
        "calibres.")
    add("")
    verdict = (f"**{best.key} is adopted:** {best.label}. Its nested MAE of {best.mean():.2f} is within one SE of "
               f"the one-hot's {k0.mean():.2f} (SE {k0.se():.2f}), using {best.params} parameters against "
               f"{k0.params}." if adopted else
               f"**The one-hot stays.** The best smooth form, {best.key} ({best.label}, {best.mean():.2f}), is more "
               f"than one SE worse than the one-hot ({k0.mean():.2f}, SE {k0.se():.2f}).")
    if best.mean() < k0.mean():
        verdict += " It is also **lower** than the one-hot outright, so it does better, not just simpler."
    add(verdict)
    if simplest is not best:
        add("")
        add(f"The simplest form within one SE of the best smooth form is `{simplest.key}` ({simplest.label}, "
            f"{simplest.mean():.2f}, {simplest.params} parameters).")
    add("")
    add("## 3. Calibre levels per projectile")
    add("")
    add("The calibre term from each full-data fit, in gold per gun^p **relative to the 6-pdr**, with the "
        "shot-type level included. The one-hot (K0) next to the best smooth form, its second-stage fit, and "
        "the simple power form for comparison.")
    add("")
    show = [r for r in results if r.key in {"K0", best.key, "K1a"}]
    rows = []
    for q in sorted(info, key=lambda q: (info[q][0], info[q][2])):
        shot, rng, dmg = info[q]
        rows.append([f"`{q}`", shot.replace("cannon_", ""), weights[q], f"{rng:g}", f"{dmg:g}"] +
                    [f"{r.levels[q]:+.0f}" for r in show] + [f"{stage2[best.key][1][q]:+.0f}"])
    L += up.table(["projectile", "shot", "batteries", "range", "damage"] + [f"{r.key} level" for r in show] +
                  [f"{best.key} fitted to K0 levels"], rows)
    add("")
    add("## 4. Fitted exponents per variant (full data)")
    add("")
    keys = sorted({k for r in results for k in r.power.full_powers})
    rows = [[f"`{k}`"] + [f"{r.power.full_powers[k]:g}" if k in r.power.full_powers else "—" for r in results]
            for k in keys] + [["size power p"] + [f"{r.power.full_p:g}" for r in results]]
    L += up.table(["exponent"] + [f"`{r.key}`" for r in results], rows)
    add("")
    if check:
        add(f"Spline hand-check ({best.key}): {check}.")
        add("")
    out = up.OUT_DIR / "calibre_function_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
