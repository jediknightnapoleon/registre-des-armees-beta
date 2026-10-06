"""Final models: full-data LAD fit, CV metrics, input evidence (paired fold diffs), failure analysis.

Writes out/final_params.json, out/final_predictions.csv, out/final_report.txt.
"""
from __future__ import annotations
import csv
import json
import numpy as np
from harness import fit_linear, Y, FOLDS
from features import *

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
mr, mc = REG["morale"], COM["morale"]
sz = P * (SIZE - 1)

IMP = (SIDE == "imperial").astype(float)
J8 = {
    "P*inf": P * INF, "P*cav": P * CAV, "P*art": P * ART, "inf": INF, "cav": CAV, "art": ART,
    "P*dmorale": P * dmo, "P*dmelee_def": P * dmd, "P*dcharge": P * dcb, "P*daccuracy": P * dac, "P*dreload": P * drl,
    "men*dmorale": MEN_R * dmo, "s": S, "corps*s": CORPS * S,
    "P(r-1)[inf,cav]": sz * (1 - ART), "P(r-1)[art]": sz * ART,
}
BEST = {k: v for k, v in J8.items() if k not in ("s", "corps*s")}
BEST.update({
    "P*d(charge^2)": P * (COM["charge_bonus"] ** 2 - REG["charge_bonus"] ** 2),
    "P*d(reload^2)": P * (COM["reload_skill"] ** 2 - REG["reload_skill"] ** 2),
    "P*corps*dmorale": P * CORPS * dmo,
    "men*d(morale^2)": MEN_R * (mc ** 2 - mr ** 2),
    "men*dreload": MEN_R * drl,
    "s[inf]": S * INF, "s[cav]": S * CAV, "s[art]": S * ART,
    "corps*s[inf]": CORPS * S * INF, "corps*s[cav]": CORPS * S * CAV, "corps*s[art]": CORPS * S * ART,
    "imperial": IMP,
})
MINIMAL = {"P": P, "1": ONE, "P*dmorale": P * dmo, "P*dmelee_def": P * dmd, "P*daccuracy": P * dac, "P*dreload": P * drl,
           "men*dmorale": MEN_R * dmo, "s": S, "corps*s": CORPS * S,
           "P(r-1)[inf,cav]": sz * (1 - ART), "P(r-1)[art]": sz * ART}
MODELS = {"BEST": BEST, "FALLBACK": J8, "MINIMAL": MINIMAL}


def cv(cols):
    X = np.column_stack(cols)
    pred = np.empty(len(Y))
    for f in range(5):
        tr = FOLDS != f
        b = fit_linear(X[tr], Y[tr], "lad")
        pred[~tr] = np.maximum(X[~tr] @ b, 1)
    ae = np.abs(pred - Y)
    return pred, np.array([ae[FOLDS == f].mean() for f in range(5)])


def summary(fm, pred):
    return f"CV MAE {fm.mean():.2f} ± {fm.std(ddof=1):.2f} (SE {fm.std(ddof=1)/np.sqrt(5):.2f}), median APE {np.median(np.abs(pred-Y)/Y*100):.2f}%"


if __name__ == "__main__":
    import sys
    out = []
    say = lambda s="": (print(s), out.append(s))
    res = {}
    for name, cols in MODELS.items():
        X = np.column_stack(list(cols.values()))
        b = fit_linear(X, Y, "lad")
        pred, fm = cv(list(cols.values()))
        res[name] = dict(params={k: float(v) for k, v in zip(cols, b)}, cv_mae=float(fm.mean()), cv_sd=float(fm.std(ddof=1)),
                         median_ape=float(np.median(np.abs(pred - Y) / Y * 100)), fold_mae=fm.round(3).tolist(),
                         insample_mae=float(np.mean(np.abs(np.maximum(X @ b, 1) - Y))))
        res[name]["_pred"] = pred; res[name]["_fm"] = fm
        say(f"== {name} (k={len(cols)}): {summary(fm, pred)}; in-sample MAE {res[name]['insample_mae']:.2f}")
        for k, v in zip(cols, b):
            say(f"     {k:18s} {v: .6g}")
    # input evidence relative to BEST: drop blocks / add blocks, paired fold differences
    best = MODELS["BEST"]; fb = res["BEST"]["_fm"]
    say("\n== Input evidence vs BEST (paired fold differences; + = worse than BEST)")
    def drop(keys):
        return [v for k, v in best.items() if k not in keys]
    from load import FLAGS, col
    STAR = {"s[inf]", "s[cav]", "s[art]", "corps*s[inf]", "corps*s[cav]", "corps*s[art]"}
    CORPSK = {"corps*s[inf]", "corps*s[cav]", "corps*s[art]", "P*corps*dmorale"}
    DELTA = {"P*dmorale", "P*dmelee_def", "P*dcharge", "P*daccuracy", "P*dreload", "P*d(charge^2)", "P*d(reload^2)",
             "P*corps*dmorale", "men*dmorale", "men*d(morale^2)", "men*dreload"}
    tests = {
        "drop all star terms (s, corps*s per arm)": drop(STAR),
        "drop corps entirely (corps*s, P*corps*dmorale)": drop(CORPSK) + [S * A for A in (INF, CAV, ART)],
        "drop all stat-change terms": drop(DELTA),
        "drop stat changes, use arm x star lookup instead": drop(DELTA) + [P * (np.minimum(S, 5) == k) * A for A in (INF, CAV, ART) for k in range(1, 6)] + [MEN_R * (np.minimum(S, 5) == k) * A for A in (INF, CAV) for k in range(1, 6)],
        "drop men-based terms (men*dmorale, men*d(morale^2), men*dreload)": drop({"men*dmorale", "men*d(morale^2)", "men*dreload"}),
        "drop convex terms (d(charge^2), d(reload^2), d(morale^2))": drop({"P*d(charge^2)", "P*d(reload^2)", "men*d(morale^2)"}),
        "drop size-change terms": drop({"P(r-1)[inf,cav]", "P(r-1)[art]"}),
        "drop side (imperial)": drop({"imperial"}),
        "single a,b instead of per arm": drop({"P*inf", "P*cav", "P*art", "inf", "cav", "art"}) + [P, ONE],
        "add corps (main) + P*corps": list(best.values()) + [CORPS, P * CORPS],
        "add army intercepts (55)": [v for k, v in best.items() if k not in {"inf", "imperial"}] + [dummies(FAC)[0]],
        "add army P-multipliers (54)": list(best.values()) + [P[:, None] * dummies(FAC)[0][:, 1:]],
        "add unit class dummies": list(best.values()) + [dummies(CLASS, drop_first=True)[0]],
        "add training level dummies": list(best.values()) + [dummies(TRAIN, drop_first=True)[0]],
        "add unit size (men)": list(best.values()) + [MEN_R],
        "add regular stats (8)": list(best.values()) + [np.column_stack([REG[k] for k in STATS])],
        "add regular flags (13)": list(best.values()) + [np.column_stack([col(ROWS, 'regular_' + f).astype(float) for f in FLAGS])],
        "add melee-attack change P*dma": list(best.values()) + [P * dma],
        "add star convexity s^2, P*s^2": list(best.values()) + [S ** 2, P * S ** 2],
    }
    ev = []
    for nm, cols in tests.items():
        cols = [c if c.ndim == 2 else c[:, None] for c in cols]
        X = np.hstack(cols); X = X[:, np.abs(X).sum(0) > 0]
        pred, fm = cv([X[:, j] for j in range(X.shape[1])])
        d = fm - fb
        ev.append((nm, X.shape[1], fm.mean(), d.mean(), d.std(ddof=1) / np.sqrt(5)))
        say(f"  {nm:52s} k={X.shape[1]:3d} CV MAE {fm.mean():6.2f}  diff {d.mean():+6.2f} ± {d.std(ddof=1)/np.sqrt(5):.2f}")
    say("\n== Robustness: CV MAE with other grouped-fold seeds (selection was done on seed 0)")
    from load import group_folds
    for name, cols in MODELS.items():
        X = np.column_stack(list(cols.values()))
        line = []
        for seed in (0, 1, 2, 3):
            fo = group_folds(ROWS, 5, seed=seed)
            pr = np.empty(len(Y))
            for f in range(5):
                tr = fo != f
                bb = fit_linear(X[tr], Y[tr], "lad")
                pr[~tr] = np.maximum(X[~tr] @ bb, 1)
            ae_ = np.abs(pr - Y)
            fm_ = np.array([ae_[fo == f].mean() for f in range(5)])
            line.append(f"seed{seed} {fm_.mean():.2f}±{fm_.std(ddof=1):.2f}")
        say(f"  {name:9s} " + "  ".join(line))
    # failure analysis for BEST
    pred = res["BEST"]["_pred"]; r = Y - pred; ae = np.abs(r)
    say("\n== BEST: worst 25 pairs (CV predictions)")
    for i in np.argsort(-ae)[:25]:
        rr = ROWS[i]
        say(f"  #{rr['pair_id']:>5} {FAC[i]:22s} c{int(CORPS[i]):2d} {CLASS[i]:22s} s={int(S[i])} men {int(MEN_R[i])}->{int(MEN_C[i])} P={int(P[i])} C={int(Y[i])} pred={pred[i]:.0f} err={r[i]:+.0f} | {rr['commander_name'][:60]}")
    sizech = SIZE != 1
    say(f"\n  size-change rows (n={sizech.sum()}): MAE {ae[sizech].mean():.1f}; share of total abs error {ae[sizech].sum()/ae.sum():.1%}")
    say(f"  other rows: MAE {ae[~sizech].mean():.2f}, median AE {np.median(ae[~sizech]):.2f}")
    say(f"  top 5% rows carry {np.sort(ae)[::-1][:len(ae)//20].sum()/ae.sum():.1%} of total abs error")
    for nm, v in [("arm", ARM), ("stars", S.astype(int)), ("class", CLASS), ("training", TRAIN), ("corps", CORPS.astype(int))]:
        say(f"  -- by {nm}")
        for k in sorted(set(v.tolist())):
            m = (v == k)
            say(f"     {str(k):24s} n={m.sum():5d} MAE {ae[m].mean():6.1f} mean err {r[m].mean():+6.1f}")
    # predictions file
    with open("../out/final_predictions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "regular_price", "commander_price", "cv_pred_best", "cv_pred_fallback", "err_best"])
        for i, rr in enumerate(ROWS):
            w.writerow([rr["pair_id"], int(P[i]), int(Y[i]), round(float(pred[i]), 1), round(float(res["FALLBACK"]["_pred"][i]), 1), round(float(r[i]), 1)])
    for v in res.values():
        v.pop("_pred"); v.pop("_fm")
    json.dump({"models": res, "evidence": [dict(test=e[0], k=e[1], cv_mae=e[2], diff=e[3], se=e[4]) for e in ev]},
              open("../out/final_params.json", "w", encoding="utf-8"), indent=1)
    open("../out/final_report.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
