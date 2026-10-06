"""Exp 18: greedy forward selection of small feature blocks on top of J8 (LAD, grouped CV).

Reports, for each step, the block added, CV MAE, and the paired fold-difference
SE versus the previous step, so 'within one standard error' can be judged on the
paired difference.  Stops when no block improves CV MAE by > 0.05.
"""
from __future__ import annotations
import numpy as np
from harness import fit_linear, Y, FOLDS
from features import *
from load import FLAGS, col

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
J8 = {"P*inf": P * INF, "P*cav": P * CAV, "P*art": P * ART, "inf": INF, "cav": CAV, "art": ART,
      "P*dmo": P * dmo, "P*dmd": P * dmd, "P*dcb": P * dcb, "P*dac": P * dac, "P*drl": P * drl,
      "men*dmo": MEN_R * dmo, "s": S, "corps*s": CORPS * S,
      "P(r-1)infcav": P * (SIZE - 1) * (1 - ART), "P(r-1)art": P * (SIZE - 1) * ART}
pool = {}
for k in ["morale", "melee_defense", "charge_bonus", "accuracy", "reload_skill"]:
    pool[f"P*d({k}^2)"] = [P * (COM[k] ** 2 - REG[k] ** 2)]
pool["men*d(morale^2)"] = [MEN_R * (COM["morale"] ** 2 - REG["morale"] ** 2)]
pool["s^2"] = [S ** 2]; pool["P*s^2"] = [P * S ** 2]; pool["P*s"] = [P * S]
pool["men*s"] = [MEN_R * S]; pool["men"] = [MEN_R]
pool["corps"] = [CORPS]; pool["P*corps"] = [P * CORPS]; pool["corps*P*dmo"] = [CORPS * P * dmo]
pool["corps*men*dmo"] = [CORPS * MEN_R * dmo]
pool["per-arm s,corps*s"] = [S * CAV, S * ART, CORPS * S * CAV, CORPS * S * ART]
pool["per-arm men*dmo"] = [MEN_R * dmo * CAV, MEN_R * dmo * ART]
pool["P*dma"] = [P * dma]; pool["men*dmd"] = [MEN_R * dmd]; pool["men*drl"] = [MEN_R * drl]
for k in STATS:
    pool[f"reg_{k}"] = [REG[k]]
    pool[f"P*reg_{k}"] = [P * REG[k]]
for f in ["can_inspire", "has_guerrilla_deployment", "can_place_stakes", "guard_mode", "can_snipe", "pike_square", "has_stamina", "is_shock_resistant", "can_form_square", "skirmish"]:
    pool[f"flag_{f}"] = [col(ROWS, "regular_" + f).astype(float)]
    pool[f"P*flag_{f}"] = [P * col(ROWS, "regular_" + f).astype(float)]
pool["imperial"] = [(SIDE == "imperial").astype(float)]
for c in sorted(set(CLASS.tolist())):
    pool[f"class={c}"] = [(CLASS == c).astype(float)]
for t in sorted(set(TRAIN.tolist())):
    pool[f"train={t}"] = [(TRAIN == t).astype(float)]

def cv_folds(cols):
    X = np.column_stack(cols)
    fm = np.empty(5)
    pred = np.empty(len(Y))
    for f in range(5):
        tr = FOLDS != f
        b = fit_linear(X[tr], Y[tr], "lad")
        pred[~tr] = np.maximum(X[~tr] @ b, 1)
    ae = np.abs(pred - Y)
    return np.array([ae[FOLDS == f].mean() for f in range(5)])

cur = list(J8.values()); chosen = []
cur_f = cv_folds(cur)
log = [f"start J8: CV MAE {cur_f.mean():.3f} (k={len(cur)})"]
print(log[-1], flush=True)
for step in range(10):
    best = None
    for name, blk in pool.items():
        if name in chosen: continue
        f = cv_folds(cur + blk)
        if best is None or f.mean() < best[1].mean():
            best = (name, f)
    name, f = best
    d = cur_f - f
    line = f"step {step+1}: + {name:28s} CV MAE {f.mean():.3f}  gain {d.mean():.3f}  paired SE {d.std(ddof=1)/np.sqrt(5):.3f}  k={len(cur)+len(pool[name])}"
    print(line, flush=True); log.append(line)
    if d.mean() < 0.05:
        break
    cur += pool[name]; chosen.append(name); cur_f = f
open("../out/forward_selection.txt", "w", encoding="utf-8").write("\n".join(log) + "\n")
