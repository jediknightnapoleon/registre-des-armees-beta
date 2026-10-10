"""G-CV4: additive commander-variant model.
price_cv = a_arm * price_regular + z * (T[stars] + w . stat differences + c_arm),  z = (8 / corps_number)^0.93
(linear least squares, weights 1/price_regular; folds as given). Appends to RESULTS.md."""
from __future__ import annotations
import re, os
import numpy as np
from common import load_raw, boolc, num, metrics, append_results, OUT
from features import STATS

raw = load_raw()
isg = boolc(raw["is_general"]); cv = boolc(raw["is_commander_variant"])
y_all = num(raw["base_mp_cost"]); fold_all = np.array([int(v) if v else 0 for v in raw["fold"]])
regidx = {(f, k): i for i, (f, k) in enumerate(zip(raw["faction_key"], raw["unit_key"])) if not isg[i]}
cvi = np.where(cv)[0]
J = np.array([regidx[(raw["faction_key"][i], re.sub(r"_com_\d+$", "", raw["unit_key"][i]))] for i in cvi])
y = y_all[cvi]; yr = y_all[J]; fold = fold_all[cvi]
s = np.minimum(num(raw["command_stars"], 0)[cvi], 6).astype(int)
cls_r = raw["unit_class"][J]
arm = np.array(["artillery" if c.startswith("artillery") else ("cavalry" if c.startswith("cavalry") else "infantry") for c in cls_r])
dst = np.column_stack([num(raw[x], 0)[cvi] - num(raw[x], 0)[J] for x in STATS])
z = (8.0 / num(raw["corps_number"])[cvi]) ** 0.93
hold = raw["corps_holdout"][cvi] == "1"
ARMS = ["infantry", "cavalry", "artillery"]
def X_of(rows, inter):
    cols, names = [], []
    for a in ARMS:
        cols.append(yr[rows] * (arm[rows] == a)); names.append(f"price_reg x [{a}]")
    for lv in range(7):
        cols.append(z[rows] * (s[rows] == lv)); names.append(f"z x [stars={lv}]")
    for a in ARMS[1:]:
        cols.append(z[rows] * (arm[rows] == a)); names.append(f"z x [{a}]")
    for j, x in enumerate(STATS):
        cols.append(z[rows] * dst[rows, j]); names.append(f"z x d_{x}")
    if inter:
        for j, x in enumerate(STATS):
            cols.append(yr[rows] * dst[rows, j] / 10); names.append(f"price_reg x d_{x}/10")
    return np.column_stack(cols), names
def fit(rows, inter):
    X, names = X_of(rows, inter); w = 1 / yr[rows]
    b, *_ = np.linalg.lstsq(X * np.sqrt(w)[:, None], y[rows] * np.sqrt(w), rcond=None)
    return b, names
for rid, inter in [("G-CV4", False), ("G-CV5", True)]:
    p = np.full(len(cvi), np.nan)
    for k in range(1, 6):
        tr = np.where(fold != k)[0]; te = np.where(fold == k)[0]
        b, _ = fit(tr, inter); p[te] = X_of(te, inter)[0] @ b
    p = np.maximum(p, 1)
    desc = "commander variant additive: a_arm x true regular price + (8/cn)^0.93 x (stars table + arm + stat diffs)" + (" + regular price x stat diffs" if inter else "")
    for seg in ["all"] + ARMS:
        res = {"mae": [], "mape": [], "r2": []}
        for k in range(1, 6):
            m = (fold == k) & ((arm == seg) if seg != "all" else True)
            mm = metrics(y[m], p[m]); [res[q].append(mm[q]) for q in res]
        r = {q: (np.mean(v), np.std(v)) for q, v in res.items()}
        print(f"  {rid} {seg:10s} MAE {r['mae'][0]:.1f} ± {r['mae'][1]:.1f} MAPE {r['mape'][0]:.2f}% R2 {r['r2'][0]:.4f}")
        append_results([rid, desc, f"cmd {seg}", f"{r['mae'][0]:.1f} ± {r['mae'][1]:.1f}", f"{r['mape'][0]:.2f}", f"{r['r2'][0]:.4f}", "", ""])
    tr = np.where(~hold)[0]; te = np.where(hold & (fold > 0))[0]
    b, names = fit(tr, inter); hp = np.maximum(X_of(te, inter)[0] @ b, 1)
    mt = metrics(y[te], hp)
    print(f"  {rid} unseen-army MAE {mt['mae']:.1f} MAPE {mt['mape']:.2f}% n={mt['n']}")
    append_results([f"{rid}-unseen", desc, "cmd variants (17 holdout armies)", f"{mt['mae']:.1f}", f"{mt['mape']:.2f}", f"{mt['r2']:.4f}", "", "single split"])
    b, names = fit(np.arange(len(cvi)), inter)
    print("   all-data coefs: " + "; ".join(f"{n} {v:+.3f}" for n, v in zip(names, b)))
    # where is it bad?
    ape = np.abs(p - y) / y
    for lv in range(7):
        m = s == lv; print(f"     stars {lv}: n={m.sum()} MAPE {100*ape[m].mean():.1f}%  median price {np.median(y[m]):.0f}")
    small = y < 100; print(f"     price<100: n={small.sum()} MAPE {100*ape[small].mean():.1f}% ; price>=100 MAPE {100*ape[~small].mean():.1f}%")
    np.save(os.path.join(OUT, f"pred_{rid}.npy"), p)
