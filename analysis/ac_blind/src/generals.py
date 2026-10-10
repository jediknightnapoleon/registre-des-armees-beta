"""Secondary targets: staff generals and combat-general (commander) variants.

G-ST (staff generals): price = T[stars] * (8 / corps_number)^b ; stars 0 -> fixed tiny price.
   T and b fitted in log space by least squares on the training folds.
G-CV (commander variants): log(price_cv / price_regular) = table[stars] + arm term
   + w . (stat differences variant - regular) [+ b log cn], fitted by ridge on training folds.
   Two versions: using the true regular price (allowed by TASK.md) and using the M1
   out-of-fold predicted regular price (fully model-based).
Writes out/generals_oof.csv and RESULTS.md rows.
"""
from __future__ import annotations

import csv
import os
import re

import numpy as np

from common import load_raw, boolc, num, OUT, metrics, append_results, regular_units
from features import STATS, gridge_fit


def fm(y, p, fold, mask):
    res = {"mae": [], "mape": [], "r2": []}
    for k in range(1, 6):
        m = mask & (fold == k)
        if m.sum() < 2:
            continue
        mm = metrics(y[m], p[m])
        for key in res:
            res[key].append(mm[key])
    return {k: (float(np.mean(v)), float(np.std(v))) for k, v in res.items()}


def log_row(rid, desc, seg, r, note=""):
    print(f"  {rid:8s} {seg:12s} MAE {r['mae'][0]:.1f} ± {r['mae'][1]:.1f} MAPE {r['mape'][0]:.2f}% R2 {r['r2'][0]:.4f}")
    append_results([rid, desc, seg, f"{r['mae'][0]:.1f} ± {r['mae'][1]:.1f}", f"{r['mape'][0]:.2f}", f"{r['r2'][0]:.4f}", "", note])


def main():
    raw = load_raw()
    isg = boolc(raw["is_general"])
    cv = boolc(raw["is_commander_variant"])
    y_all = num(raw["base_mp_cost"])
    fold_all = np.array([int(v) if v else 0 for v in raw["fold"]])
    stars_all = num(raw["command_stars"], 0)
    cn_all = num(raw["corps_number"])
    hold_all = raw["corps_holdout"] == "1"
    out_rows = []

    # ------------------------------------------------------------ staff generals
    st = np.where(isg & ~cv)[0]
    y = y_all[st]; s = stars_all[st].astype(int); cn = cn_all[st]; fold = fold_all[st]
    cav = np.array([c.startswith("C") for c in raw["speed_code"][st]])

    def fit_staff(tr, use_cav=False):
        pos = s[tr] > 0
        X = [np.log(cn[tr][pos])]
        names = ["log_cn"]
        if use_cav:
            X.append(cav[tr][pos].astype(float)); names.append("cav")
        levels = sorted(set(s[s > 0]))
        for lv in levels:
            X.append((s[tr][pos] == lv).astype(float))
        X = np.column_stack(X)
        b, *_ = np.linalg.lstsq(X, np.log(y[tr][pos]), rcond=None)
        zero = float(np.median(y[tr][s[tr] == 0])) if (s[tr] == 0).any() else 1.0
        return b, levels, zero

    def pred_staff(model, te, use_cav=False):
        b, levels, zero = model
        out = np.full(len(te), zero)
        off = 2 if use_cav else 1
        for j, i in enumerate(te):
            if s[i] == 0:
                continue
            v = b[0] * np.log(cn[i])
            if use_cav:
                v += b[1] * cav[i]
            if s[i] in levels:
                v += b[off + levels.index(s[i])]
            out[j] = np.exp(v)
        return out

    for use_cav, rid in [(False, "G-ST1"), (True, "G-ST2")]:
        p = np.full(len(st), np.nan)
        for k in range(1, 6):
            tr = np.where(fold != k)[0]; te = np.where(fold == k)[0]
            p[te] = pred_staff(fit_staff(tr, use_cav), te, use_cav)
        desc = "staff generals: T[stars] x cn^b (log LSQ), stars 0 -> median price" + (" + cavalry-general flag" if use_cav else "")
        log_row(rid, desc, "staff", fm(y, p, fold, fold > 0))
        m0 = fold > 0
        log_row(rid, desc, "staff stars>0", fm(y, p, fold, m0 & (s > 0)))
        # unseen-army
        tr = np.where(~hold_all[st])[0]; te = np.where(hold_all[st])[0]
        hp = pred_staff(fit_staff(tr, use_cav), te, use_cav)
        mt = metrics(y[te], hp)
        print(f"  {rid} unseen-army MAE {mt['mae']:.1f} MAPE {mt['mape']:.2f}% n={mt['n']}")
        append_results([f"{rid}-unseen", desc, "staff (17 holdout armies)", f"{mt['mae']:.1f}", f"{mt['mape']:.2f}", f"{mt['r2']:.4f}", "", "single split"])
        if rid == "G-ST1":
            model_all = fit_staff(np.arange(len(st)))
            b, levels, zero = model_all
            print("  staff all-data: b(log cn) = %.3f ; T[stars] at cn=8: " % b[0] +
                  ", ".join(f"{lv}:{np.exp(b[0] * np.log(8) + b[1 + i]):.0f}" for i, lv in enumerate(levels)) + f" ; stars 0 -> {zero:.0f}")
            for j, i in enumerate(st):
                out_rows.append([raw["faction_key"][i], raw["unit_key"][i], fold[j], "staff", int(y[j]), f"{p[j]:.1f}", ""])

    # ------------------------------------------------------------ commander variants
    regidx = {(f, k): i for i, (f, k) in enumerate(zip(raw["faction_key"], raw["unit_key"])) if not isg[i]}
    cvi = np.where(cv)[0]
    J = np.array([regidx[(raw["faction_key"][i], re.sub(r"_com_\d+$", "", raw["unit_key"][i]))] for i in cvi])
    y = y_all[cvi]; yr = y_all[J]; fold = fold_all[cvi]
    s = stars_all[cvi].astype(int)
    cls_r = raw["unit_class"][J]
    arm = np.array(["artillery" if c.startswith("artillery") else ("cavalry" if c.startswith("cavalry") else "infantry") for c in cls_r])
    dstats = np.column_stack([num(raw[x], 0)[cvi] - num(raw[x], 0)[J] for x in STATS])
    dmen = np.log(num(raw["men_raw"])[cvi] / num(raw["men_raw"])[J])
    cn = cn_all[cvi]
    # M1 OOF predicted regular price for the matched regular unit
    d = regular_units(raw)
    pM1 = np.load(os.path.join(OUT, "pred_M1.npy"))
    pos = {g: i for i, g in enumerate(d.idx)}
    yr_hat = np.array([pM1[pos[j]] if j in pos and np.isfinite(pM1[pos[j]]) else np.nan for j in J])

    def design(rows, with_cn, with_inter):
        cols = []; names = []
        for lv in range(0, 7):
            cols.append((np.minimum(s[rows], 6) == lv).astype(float)); names.append(f"stars={lv}")
        for a in ["cavalry", "artillery"]:
            cols.append((arm[rows] == a).astype(float)); names.append(f"arm={a}")
        for j, x in enumerate(STATS):
            cols.append(dstats[rows, j]); names.append(f"d_{x}")
        cols.append(dmen[rows]); names.append("dlog_men")
        if with_cn:
            cols.append(np.log(cn[rows])); names.append("log_cn")
        if with_inter:
            for a in ["cavalry", "artillery"]:
                cols.append(np.minimum(s[rows], 6) * (arm[rows] == a)); names.append(f"stars*{a}")
        return np.column_stack(cols), names

    variants = [("G-CV1", False, False, "true"), ("G-CV2", True, True, "true"), ("G-CV3", True, True, "pred")]
    for rid, with_cn, with_inter, base in variants:
        basev = yr if base == "true" else yr_hat
        ok = np.isfinite(basev)
        tgt = np.log(y / basev)
        p = np.full(len(cvi), np.nan)
        for k in range(1, 6):
            tr = np.where(ok & (fold != k))[0]; te = np.where(ok & (fold == k))[0]
            X, names = design(tr, with_cn, with_inter)
            a0, b = gridge_fit(X, tgt[tr], np.full(X.shape[1], 1e-3))
            Xt, _ = design(te, with_cn, with_inter)
            p[te] = basev[te] * np.exp(a0 + Xt @ b)
        desc = (f"commander variant: {'true' if base == 'true' else 'M1-OOF-predicted'} regular price x exp(stars table + arm + stat diffs"
                + (" + log cn + stars x arm" if with_cn else "") + ")")
        mask = ok & (fold > 0)
        log_row(rid, desc, "cmd variants", fm(y, p, fold, mask))
        for a in ["infantry", "cavalry", "artillery"]:
            log_row(rid, desc, f"cmd {a}", fm(y, p, fold, mask & (arm == a)))
        # unseen-army (true-regular-price version only meaningful with true regular price of that army)
        tr = np.where(ok & ~hold_all[cvi])[0]; te = np.where(ok & hold_all[cvi] & (fold > 0))[0]
        X, names = design(tr, with_cn, with_inter)
        a0, b = gridge_fit(X, tgt[tr], np.full(X.shape[1], 1e-3))
        Xt, _ = design(te, with_cn, with_inter)
        if base == "pred":
            hM1 = np.load(os.path.join(OUT, "hpred_M1.npy"))
            hb = np.array([hM1[pos[j]] if j in pos else np.nan for j in J[te]])
            hp = hb * np.exp(a0 + Xt @ b)
        else:
            hp = basev[te] * np.exp(a0 + Xt @ b)
        okh = np.isfinite(hp)
        mt = metrics(y[te][okh], hp[okh])
        print(f"  {rid} unseen-army MAE {mt['mae']:.1f} MAPE {mt['mape']:.2f}% n={mt['n']}")
        append_results([f"{rid}-unseen", desc, "cmd variants (17 holdout armies)", f"{mt['mae']:.1f}", f"{mt['mape']:.2f}", f"{mt['r2']:.4f}", "", "single split"])
        if rid in ("G-CV2", "G-CV3"):
            X, names = design(np.where(ok)[0], with_cn, with_inter)
            a0, b = gridge_fit(X, tgt[ok], np.full(X.shape[1], 1e-3))
            print(f"  {rid} all-data coefficients: intercept {a0:+.4f}; " + "; ".join(f"{n} {v:+.4f}" for n, v in zip(names, b)))
            # report the stars multipliers relative to an infantry variant with unchanged stats
            print("   stars multiplier (infantry, no stat change, cn 8): " + ", ".join(
                f"{lv}:{np.exp(a0 + b[lv] + (b[names.index('log_cn')] * np.log(8) if with_cn else 0)):.3f}" for lv in range(7)))
            if rid == "G-CV2":
                for j, i in enumerate(cvi):
                    pass
        if rid == "G-CV2":
            for j, i in enumerate(cvi):
                out_rows.append([raw["faction_key"][i], raw["unit_key"][i], fold[j], "commander_variant", int(y[j]), f"{p[j]:.1f}", ""])
        if rid == "G-CV3":
            pmap = {raw["unit_key"][i] + "|" + raw["faction_key"][i]: p[j] for j, i in enumerate(cvi)}
            for r in out_rows:
                if r[3] == "commander_variant":
                    r[6] = f"{pmap[r[1] + '|' + r[0]]:.1f}"
    with open(os.path.join(OUT, "generals_oof.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "unit_key", "fold", "kind", "base_mp_cost", "pred_GST1_or_GCV2", "pred_GCV3_model_based"])
        for r in out_rows:
            if r[2] > 0:
                w.writerow(r)


if __name__ == "__main__":
    main()
