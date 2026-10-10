"""E00: baselines - mean price per unit_class; that mean scaled by unit size."""
from __future__ import annotations
import numpy as np
from common import regular_units, OUT
from harness import run_cv, report, arm_vec

d = regular_units()
y = d.f("base_mp_cost")
cls = d.s("unit_class")
arm = arm_vec(d)
size = np.where(arm == "artillery", d.f("guns", 0), d.f("men_display"))

def class_mean(tr, te):
    out = np.empty(len(te))
    for c in set(cls[te]):
        out[cls[te] == c] = y[tr][cls[tr] == c].mean()
    return out

def class_mean_scaled(tr, te):
    out = np.empty(len(te))
    for c in set(cls[te]):
        m = cls[tr] == c
        out[cls[te] == c] = y[tr][m].mean() / size[tr][m].mean() * size[te][cls[te] == c]
    return out

p0 = run_cv(class_mean, d)
report("B0", d, y, p0, "baseline: mean price per unit_class", "", "")
p1 = run_cv(class_mean_scaled, d)
report("B1", d, y, p1, "baseline: class mean price x size / class mean size (size = men_display; guns for artillery)", "", "")
np.save(f"{OUT}/pred_B0.npy", p0); np.save(f"{OUT}/pred_B1.npy", p1)
