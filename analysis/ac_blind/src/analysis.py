"""Post-hoc analysis of the final models (needs out/pred_M1.npy etc. from final.py).

Writes:
  out/oof_predictions.csv, out/holdout_predictions.csv
  out/coefs_M1_<arm>.csv (all-data fit, penalties from final_M1.json "all")
  out/army_offsets_M1.csv, out/army_class_offsets_M1.csv
  out/analysis.txt (size curves, size-band errors, army findings, error analysis)
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

import numpy as np

from common import regular_units, OUT, metrics
from harness import ARMS
from models import Ctx
from final import SPECS, ArmModel

LOG = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def main():
    d = regular_units()
    c = Ctx(d)
    hold = d.s("corps_holdout") == "1"
    pr = {k: np.load(os.path.join(OUT, f"pred_{k}.npy")) for k in ["B0", "B1", "M1", "M2"]}
    hp = {k: np.load(os.path.join(OUT, f"hpred_{k}.npy")) for k in ["M1", "M2"]}
    choice = json.load(open(os.path.join(OUT, "final_M1.json"), encoding="utf-8"))["choice"]

    # ---------- baselines on the unseen-army split
    tr = ~hold
    size = np.where(c.arm == "artillery", c.guns, c.men)
    for nm in ["B0", "B1"]:
        h = np.full(len(c.y), np.nan)
        for cl in set(c.cls[hold]):
            mt = tr & (c.cls == cl)
            mh = hold & (c.cls == cl)
            h[mh] = c.y[mt].mean() if nm == "B0" else c.y[mt].mean() / size[mt].mean() * size[mh]
        hp[nm] = h
    sc = hold & (c.fold > 0)
    P("== Unseen-army test (17 armies, 609 scored regular rows)")
    for nm in ["B0", "B1", "M2", "M1"]:
        line = f"  {nm}:"
        for seg in ARMS + ["overall"]:
            mm = sc & ((c.arm == seg) if seg in ARMS else True)
            mt = metrics(c.y[mm], hp[nm][mm])
            line += f" {seg} MAE {mt['mae']:.1f} MAPE {mt['mape']:.2f}% R2 {mt['r2']:.3f} |"
        P(line)

    # ---------- CSV outputs
    scored = c.fold > 0
    with open(os.path.join(OUT, "oof_predictions.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "unit_key", "fold", "unit_class", "base_mp_cost", "pred_M1", "pred_M2", "pred_B0", "pred_B1"])
        for i in np.where(scored)[0]:
            w.writerow([c.fk[i], d.s("unit_key")[i], c.fold[i], c.cls[i], int(c.y[i]),
                        f"{pr['M1'][i]:.1f}", f"{pr['M2'][i]:.1f}", f"{pr['B0'][i]:.1f}", f"{pr['B1'][i]:.1f}"])
    with open(os.path.join(OUT, "holdout_predictions.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "unit_key", "fold", "unit_class", "base_mp_cost", "pred_M1", "pred_M2", "pred_B0", "pred_B1"])
        for i in np.where(sc)[0]:
            w.writerow([c.fk[i], d.s("unit_key")[i], c.fold[i], c.cls[i], int(c.y[i]),
                        f"{hp['M1'][i]:.1f}", f"{hp['M2'][i]:.1f}", f"{hp['B0'][i]:.1f}", f"{hp['B1'][i]:.1f}"])

    # ---------- all-data fit of M1, coefficient dump
    o = SPECS["M1"]
    allrows = np.arange(len(c.y))
    fits = {}
    for arm in ARMS:
        am = ArmModel(c, arm, o)
        pen = choice["all"][arm]
        a0, b = am.fit(allrows, pen)
        fits[arm] = (am, a0, b)
        with open(os.path.join(OUT, f"coefs_M1_{arm}.csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["term", "group", "coef"])
            w.writerow(["intercept", "main", f"{a0:.6f}"])
            for nm, g, bb in zip(am.D.names, am.D.groups, b):
                if g not in ("army", "armycls"):
                    w.writerow([nm, g, f"{bb:.6f}"])
        P(f"\n== M1 all-data fit {arm}: penalties {pen}; in-sample log resid sd "
          f"{np.std(am.ly - a0 - am.X @ b):.4f}")
    # army tables
    with open(os.path.join(OUT, "army_offsets_M1.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "army_corps_name", "corps_number", "corps_side", "arm", "offset_log", "factor"])
        names = dict(zip(c.fk, d.s("army_corps_name")))
        cnm = dict(zip(c.fk, c.cn))
        sdm = dict(zip(c.fk, c.side))
        for arm in ARMS:
            am, a0, b = fits[arm]
            for nm, bb in zip(am.D.names, b):
                if nm.startswith("army="):
                    k = nm[5:]
                    w.writerow([k, names[k], int(cnm[k]), sdm[k], arm, f"{bb:.4f}", f"{np.exp(bb):.4f}"])
    with open(os.path.join(OUT, "army_class_offsets_M1.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "unit_class", "offset_log", "factor"])
        for arm in ARMS:
            am, a0, b = fits[arm]
            for nm, bb in zip(am.D.names, b):
                if nm.startswith("armycls="):
                    k, cl = nm[8:].split("|")
                    w.writerow([k, cl, f"{bb:.4f}", f"{np.exp(bb):.4f}"])

    # ---------- army findings
    P("\n== Army dependence (M1 all-data fit)")
    offs = {}
    for arm in ARMS:
        am, a0, b = fits[arm]
        cf = dict(zip(am.D.names, b))
        ao = {nm[5:]: bb for nm, bb in cf.items() if nm.startswith("army=")}
        aco = np.array([bb for nm, bb in cf.items() if nm.startswith("armycls=")])
        offs[arm] = ao
        P(f"  {arm}: log_cn slope {cf['log_cn_k']:+.3f} (price ~ cn^{cf['log_cn_k']:.2f}); empire {cf['empire']:+.3f} "
          f"(x{np.exp(cf['empire']):.3f}); army offset sd {np.std(list(ao.values())):.3f}; army x class offset sd {aco.std():.3f}")
        for k in range(3, 14):
            P(f"     cn {k:2d}: factor vs cn 8 = {np.exp(cf['log_cn_k'] * (np.log(k) - np.log(8))):.3f}")
    common = sorted(set(offs["infantry"]) & set(offs["cavalry"]) & set(offs["artillery"]))
    M = np.array([[offs[a][k] for a in ARMS] for k in common])
    P("  corr of army offsets between arms (inf, cav, art):\n" + str(np.corrcoef(M.T).round(3)))
    # army offsets vs side/cn residual pattern
    cn_of = dict(zip(c.fk, c.cn))
    for arm in ARMS:
        ao = offs[arm]
        ks = list(ao)
        v = np.array([ao[k] for k in ks])
        cnv = np.array([cn_of[k] for k in ks])
        P(f"  {arm}: corr(army offset, cn) {np.corrcoef(v, cnv)[0, 1]:+.3f}; extreme armies: "
          + ", ".join(f"{k}({cn_of[k]:.0f}) {ao[k]:+.2f}" for k in sorted(ks, key=lambda k: ao[k])[:3])
          + " ... " + ", ".join(f"{k}({cn_of[k]:.0f}) {ao[k]:+.2f}" for k in sorted(ks, key=lambda k: ao[k])[-3:]))

    # ---------- size curves: elasticity per class & band (from all-data fit)
    P("\n== Size: local elasticity d log price / d log men_raw by class (M1), and price factor vs 100 men_raw")
    for arm in ["infantry", "cavalry"]:
        knots = o["size_spline"][arm]
        am, a0, b = fits[arm]
        cf = dict(zip(am.D.names, b))
        for cl in sorted(set(c.cls[c.arm == arm])):
            base = cf.get("log_size", 0) + cf.get(f"log_size:{cl}", 0)
            pts = [60, 80, 100, 120, 140, 180, 220, 280, 340, 440]

            def f(s):
                v = base * np.log(s)
                for k in knots:
                    v += cf[f"hinge_log_size_{k}"] * max(0.0, np.log(s) - np.log(k))
                return v
            el = []
            for s in pts:
                el.append(base + sum(cf[f"hinge_log_size_{k}"] for k in knots if s > k))
            fac = [np.exp(f(s) - f(100)) for s in pts]
            ms = c.men_raw[c.cls == cl]
            P(f"  {cl:22s} men_raw range {ms.min():.0f}-{ms.max():.0f}: elasticity at " +
              " ".join(f"{s}:{e:.2f}" for s, e in zip(pts, el)))
            P(f"  {'':22s} factor vs 100 men: " + " ".join(f"{s}:{x:.2f}" for s, x in zip(pts, fac)))
    am, a0, b = fits["artillery"]
    cf = dict(zip(am.D.names, b))
    for cl in ["artillery_foot", "artillery_horse"]:
        def g(n):
            v = (cf["log_size"] + cf.get(f"log_size:{cl}", 0)) * np.log(n)
            key = f"guns={min(n, 5)}"
            v += cf.get(key, 0.0)
            return v
        P(f"  {cl}: price factor vs 3 guns: " + " ".join(f"{n}:{np.exp(g(n) - g(3)):.2f}" for n in [1, 2, 3, 4, 5, 6, 8]))

    # ---------- size-band OOF errors
    P("\n== Out-of-fold error by size band (M1 / M2 / B1)")
    bands = [(0, 40), (40, 60), (60, 80), (80, 100), (100, 140), (140, 180), (180, 240), (240, 10000)]
    for arm in ["infantry", "cavalry"]:
        for lo, hi in bands:
            mm = scored & (c.arm == arm) & (c.men >= lo) & (c.men < hi)
            if mm.sum() == 0:
                continue
            r = {k: metrics(c.y[mm], pr[k][mm]) for k in ["M1", "M2", "B1"]}
            P(f"  {arm:9s} men_display {lo:3d}-{hi if hi < 10000 else '':<4} n={mm.sum():5d} "
              f"M1 MAE {r['M1']['mae']:6.1f} MAPE {r['M1']['mape']:5.2f}% | M2 MAE {r['M2']['mae']:6.1f} MAPE {r['M2']['mape']:5.2f}% "
              f"| B1 MAE {r['B1']['mae']:6.1f} | mean price {c.y[mm].mean():.0f}")
    for g in [1, 2, 3, 4, 5]:
        mm = scored & (c.arm == "artillery") & ((c.guns == g) if g < 5 else (c.guns >= 5))
        r = {k: metrics(c.y[mm], pr[k][mm]) for k in ["M1", "M2", "B1"]}
        P(f"  artillery guns {g}{'+' if g == 5 else ' '} n={mm.sum():4d} M1 MAE {r['M1']['mae']:6.1f} MAPE {r['M1']['mape']:5.2f}% "
          f"| M2 MAE {r['M2']['mae']:6.1f} MAPE {r['M2']['mape']:5.2f}% | B1 MAE {r['B1']['mae']:6.1f} | mean price {c.y[mm].mean():.0f}")

    # ---------- error analysis
    P("\n== Error analysis (M1 out-of-fold)")
    e = pr["M1"] - c.y
    ape = np.abs(e) / c.y
    lr = np.log(pr["M1"] / c.y)
    for cl in sorted(set(c.cls)):
        mm = scored & (c.cls == cl)
        P(f"  {cl:22s} n={mm.sum():5d} MAE {np.abs(e[mm]).mean():6.1f} MAPE {100 * ape[mm].mean():5.2f}% "
          f"median log ratio {np.median(lr[mm]):+.3f}  share |err|>20%: {100 * (ape[mm] > 0.2).mean():4.1f}%")
    for t in ["elite", "well_trained", "trained", "poorly_trained", "mob"]:
        mm = scored & (c.train == t)
        P(f"  train {t:15s} n={mm.sum():5d} MAE {np.abs(e[mm]).mean():6.1f} MAPE {100 * ape[mm].mean():5.2f}%")
    for k in range(3, 14):
        mm = scored & (c.cn == k)
        P(f"  cn {k:2d} n={mm.sum():5d} MAE {np.abs(e[mm]).mean():6.1f} MAPE {100 * ape[mm].mean():5.2f}%")
    # clustering by army: share of OOF log-residual variance explained by army means
    def anova_share(groups, r):
        mu = r.mean()
        ss_tot = ((r - mu) ** 2).sum()
        ss_b = 0.0
        for gv in set(groups):
            mm = groups == gv
            ss_b += mm.sum() * (r[mm].mean() - mu) ** 2
        return ss_b / ss_tot, len(set(groups))
    for nm in ["M1", "M2"]:
        rr = np.log(pr[nm] / c.y)
        s1, n1 = anova_share(c.fk[scored], rr[scored])
        ac = np.array([f"{a}|{k}" for a, k in zip(c.fk, c.cls)], dtype=object)
        s2, n2 = anova_share(ac[scored], rr[scored])
        s3, n3 = anova_share(c.cls[scored], rr[scored])
        P(f"  {nm}: share of OOF log-residual variance between armies {100 * s1:.1f}% ({n1} groups), "
          f"between army x class cells {100 * s2:.1f}% ({n2}), between classes {100 * s3:.1f}%")
    am_err = defaultdict(list)
    for i in np.where(scored)[0]:
        am_err[c.fk[i]].append(ape[i])
    names = dict(zip(c.fk, d.s("army_corps_name")))
    v = sorted(((np.mean(x), len(x), k) for k, x in am_err.items()), reverse=True)
    P("  worst armies (MAPE, n): " + "; ".join(f"{names[k]} [{k}] {100 * a:.1f}% n={n}" for a, n, k in v[:8]))
    P("  best armies (MAPE, n): " + "; ".join(f"{names[k]} {100 * a:.1f}% n={n}" for a, n, k in v[-4:]))
    o_ = np.argsort(-np.where(scored, ape, 0))[:20]
    P("  20 largest % misses:")
    for i in o_:
        P(f"    {d.s('unit_name')[i][:48]:48s} {c.cls[i]:20s} {names[c.fk[i]][:26]:26s} men_raw {c.men_raw[i]:4.0f} "
          f"guns {c.guns[i]:.0f} price {c.y[i]:5.0f} pred {pr['M1'][i]:6.0f} ({100 * (pr['M1'][i] / c.y[i] - 1):+.0f}%)")
    # unseen-army per-army errors
    P("\n== Unseen-army test, per army (M1)")
    for k in sorted(set(c.fk[sc]), key=lambda k: cn_of[k]):
        mm = sc & (c.fk == k)
        P(f"  {names[k][:32]:32s} cn {cn_of[k]:2.0f} {c.side[mm][0]:9s} n={mm.sum():3d} MAE {np.abs(hp['M1'][mm] - c.y[mm]).mean():6.1f} "
          f"MAPE {100 * np.mean(np.abs(hp['M1'][mm] - c.y[mm]) / c.y[mm]):5.2f}% median ratio pred/true {np.median(hp['M1'][mm] / c.y[mm]):.3f}")
    with open(os.path.join(OUT, "analysis.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
