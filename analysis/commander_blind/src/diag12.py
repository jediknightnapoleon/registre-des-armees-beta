"""Residuals of J8 by the source code inside the unit key (4th '_' field, e.g. ntw3_cav_lance_131_...)."""
from __future__ import annotations
import collections
import numpy as np
from harness import cv_linear, Y
from features import *
SRC = np.array([r["regular_unit_key"].split("_")[3] for r in ROWS])
print("distinct source codes", len(set(SRC.tolist())))
dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
X8 = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART])
p, b = cv_linear(X8, "lad")
r = Y - p
ok = SIZE == 1
stats = []
for s in sorted(set(SRC.tolist())):
    m = (SRC == s) & ok
    if m.sum() >= 15:
        stats.append((np.median(r[m]), s, m.sum(), np.mean(abs(r[m]))))
stats.sort()
meds = np.array([t[0] for t in stats])
print("n sources with >=15 rows", len(stats), "sd of medians", meds.std().round(2))
for t in stats[:8] + stats[-8:]:
    print(f"  src {t[1]} n={t[2]:4d} medres {t[0]:6.1f} MAE {t[3]:5.1f}")
# within-source residual MAE vs global
within = np.concatenate([r[(SRC == s) & ok] - np.median(r[(SRC == s) & ok]) for s in set(SRC.tolist()) if ((SRC == s) & ok).sum() > 0])
print("MAE of residuals after removing per-source median (in-sample upper bound):", np.mean(abs(within)).round(2), "vs", np.mean(abs(r[ok])).round(2))
fwithin = np.concatenate([r[(FAC == s) & ok] - np.median(r[(FAC == s) & ok]) for s in set(FAC.tolist()) if ((FAC == s) & ok).sum() > 0])
print("same with per-army median:", np.mean(abs(fwithin)).round(2))
