"""Final metrics table (mean ± sd over the 5 given folds) for B0, B1, M2, M1 -> out/final_table.md"""
import numpy as np
from common import regular_units, OUT, fold_metrics
from harness import fold_vec, arm_vec, ARMS
d = regular_units(); y = d.f("base_mp_cost"); fold = fold_vec(d); arm = arm_vec(d)
L = ["| model | segment | MAE (gold) | MAPE % | R² |", "|---|---|---|---|---|"]
for nm in ["B0", "B1", "M2", "M1"]:
    p = np.load(f"{OUT}/pred_{nm}.npy")
    for seg in ARMS + ["overall"]:
        m = ((arm == seg) if seg in ARMS else np.ones(len(y), bool)) & (fold > 0)
        f = fold_metrics(y, p, fold, m)
        L.append(f"| {nm} | {seg} | {f['mae'][0]:.1f} ± {f['mae'][1]:.1f} | {f['mape'][0]:.2f} ± {f['mape'][1]:.2f} | {f['r2'][0]:.3f} ± {f['r2'][1]:.3f} |")
open(f"{OUT}/final_table.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
