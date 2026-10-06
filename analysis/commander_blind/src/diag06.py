"""Corps number vs regular price per man, and vs residual of the star premium."""
from __future__ import annotations
import numpy as np
from features import *
from harness import Y
for c in range(5, 13):
    for a, A in ARMS.items():
        m = (CORPS == c) & (A == 1)
        if m.sum() < 5: continue
        print(f"corps {c} {a:9s} n={m.sum():4d} median P {np.median(P[m]):6.0f}  median P/men {np.median(P[m]/MEN_R[m]):.2f}  median stars {np.median(S[m]):.1f} mean stars {S[m].mean():.2f}")
