"""Final models for regular units, with nested penalty selection and the unseen-army test.

M1 "with army tables": per-arm log-price ridge model
    log price = unit formula (size spline + class size slopes, stats linear + log1p,
                class-specific log1p stat adjustments, abilities, class, training, speed,
                artillery calibre/projectile/range/reload + gun-count table)
              + corps term (b * log corps_number) + empire flag
              + army offset (shrunk) + army x class offset (shrunk)
M2 "army-blind": same unit formula + log corps_number + empire + faction-key codes, no army tables.

Penalties (army, army x class, stat x class) are chosen inside each outer fold by
an inner CV over the remaining given folds (criterion: MAE in gold).
Unseen-army test: fit on all rows of non-holdout armies (penalties chosen by CV on
those rows with the given folds), predict the 17 holdout armies.

Outputs: out/oof_predictions.csv, out/holdout_predictions.csv, out/final_metrics.json,
out/final_choice.json, out/pred_M1.npy, out/pred_M2.npy.
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import sys

import numpy as np

from common import regular_units, OUT, metrics, fold_metrics, append_results
from features import gridge_fit
from harness import ARMS, report
from models import Ctx, build, DEFAULT_PEN

BASE = dict(size_mode="loglin", stat_mode="both", size_quad=False, size_by_class=True,
            size_spline={"infantry": [150, 200, 260, 340], "cavalry": [100, 130, 170, 230]}, art_feats=True, art_size_onehot=True, art_proj=True,
            stat_by_class=True, speed_mode="onehot", cn_mode="log+0", side=True)
SPECS = {
    "M1": {**BASE, "army": True, "army_class": True},
    "M2": {**BASE, "fk_codes": True},
}
GRIDS = {
    "M1": [dict(army=a, armycls=ac, inter3=i3) for a, ac, i3 in itertools.product([0.3, 1.0], [1.0, 2.0, 4.0], [2.0, 5.0])],
    "M2": [dict(inter3=i3) for i3 in [1.0, 2.0, 5.0, 10.0]],
}


class ArmModel:
    """Design for one arm built once; fit on any subset of rows."""

    def __init__(self, c: Ctx, arm: str, o: dict):
        self.m = c.arm == arm
        self.idx = np.where(self.m)[0]
        self.D = build(c, self.m, arm, o)
        self.X = self.D.matrix()
        self.ly = c.ly[self.idx]
        self.pos = np.full(len(c.y), -1)
        self.pos[self.idx] = np.arange(len(self.idx))

    def fit(self, tr_global: np.ndarray, pen: dict):
        trm = self.pos[tr_global]
        trm = trm[trm >= 0]
        P = {**DEFAULT_PEN, **pen}
        p = np.array([P[g] for g in self.D.groups])
        return gridge_fit(self.X[trm], self.ly[trm], p)

    def predict(self, a0: float, b: np.ndarray, te_global: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        tem = self.pos[te_global]
        sel = tem >= 0
        return sel, np.exp(a0 + self.X[tem[sel]] @ b)


def fit_predict(models: dict, tr: np.ndarray, te: np.ndarray, pen: dict, n: int) -> np.ndarray:
    out = np.full(len(te), np.nan)
    for arm in ARMS:
        am = models[arm]
        a0, b = am.fit(tr, pen)
        sel, p = am.predict(a0, b, te)
        out[sel] = p
    return out


def choose_pen(models, c: Ctx, rows: np.ndarray, grid: list[dict], folds_avail: list[int]) -> tuple[dict, dict]:
    """Inner CV over the given folds within `rows`; returns best pen per arm (chosen per arm) and scores."""
    best = {}
    scores = {}
    for arm in ARMS:
        am = models[arm]
        res = []
        for pen in grid:
            errs = []
            for k in folds_avail:
                tr = np.where(rows & (c.fold != k))[0]
                te = np.where(rows & (c.fold == k) & (c.arm == arm))[0]
                if len(te) == 0:
                    continue
                a0, b = am.fit(tr, pen)
                sel, p = am.predict(a0, b, te)
                errs.append(np.abs(p - c.y[te][sel]))
            res.append(float(np.mean(np.concatenate(errs))))
        j = int(np.argmin(res))
        best[arm] = grid[j]
        scores[arm] = res
    return best, scores


def run_model(name: str, c: Ctx, d) -> tuple[np.ndarray, np.ndarray, dict]:
    o = SPECS[name]
    grid = GRIDS[name]
    models = {arm: ArmModel(c, arm, o) for arm in ARMS}
    n = len(c.y)
    allrows = np.ones(n, dtype=bool)
    pred = np.full(n, np.nan)
    choice = {}
    for k in range(1, 6):
        inner_folds = [f for f in range(1, 6) if f != k]
        rows = c.fold != k  # includes always-train rows (fold 0)
        best, _ = choose_pen(models, c, rows, grid, inner_folds)
        choice[k] = best
        tr = np.where(c.fold != k)[0]
        for arm in ARMS:
            te = np.where((c.fold == k) & (c.arm == arm))[0]
            a0, b = models[arm].fit(tr, best[arm])
            sel, p = models[arm].predict(a0, b, te)
            pred[te[sel]] = p
        print(name, "fold", k, "chosen", best, flush=True)
    # unseen-army test
    hold = d.s("corps_holdout") == "1"
    rows = ~hold
    best_h, _ = choose_pen(models, c, rows, grid, [1, 2, 3, 4, 5])
    tr = np.where(~hold)[0]
    hpred = np.full(n, np.nan)
    for arm in ARMS:
        te = np.where(hold & (c.arm == arm))[0]
        a0, b = models[arm].fit(tr, best_h[arm])
        sel, p = models[arm].predict(a0, b, te)
        hpred[te[sel]] = p
    choice["holdout"] = best_h
    # final all-data penalties (for the published coefficients)
    best_all, scores_all = choose_pen(models, c, allrows, grid, [1, 2, 3, 4, 5])
    choice["all"] = best_all
    return pred, hpred, choice


def main():
    d = regular_units()
    c = Ctx(d)
    hold = d.s("corps_holdout") == "1"
    names = [a for a in sys.argv[1:]] or ["M1", "M2"]
    allres = {}
    preds = {}
    for nm in names:
        pred, hpred, choice = run_model(nm, c, d)
        np.save(os.path.join(OUT, f"pred_{nm}.npy"), pred)
        np.save(os.path.join(OUT, f"hpred_{nm}.npy"), hpred)
        desc = ("M1 final: per-arm log ridge, unit formula + log cn + side + army & army x class offsets (nested pen)"
                if nm == "M1" else "M2 final army-blind: unit formula + log cn + side + faction-key codes (nested pen)")
        r = report(nm, d, c.y, pred, desc, params=json.dumps({str(k): v for k, v in choice.items()}).replace("|", "/"))
        sc = (c.fold > 0) & hold
        hm = {}
        for seg in ARMS + ["overall"]:
            mm = sc & ((c.arm == seg) if seg in ARMS else True)
            hm[seg] = metrics(c.y[mm], hpred[mm])
            print(f"  {nm} unseen-army {seg:10s} MAE {hm[seg]['mae']:.1f} MAPE {hm[seg]['mape']:.2f}% R2 {hm[seg]['r2']:.4f} n={hm[seg]['n']}")
            append_results([f"{nm}-unseen", f"{nm} fitted on 221 non-holdout armies, predicting 17 holdout armies", seg,
                            f"{hm[seg]['mae']:.1f}", f"{hm[seg]['mape']:.2f}", f"{hm[seg]['r2']:.4f}", "", "single split"])
        allres[nm] = {"cv": r, "unseen": hm, "choice": {str(k): v for k, v in choice.items()}}
        preds[nm] = (pred, hpred)
        with open(os.path.join(OUT, f"final_{nm}.json"), "w", encoding="utf-8") as fh:
            json.dump(allres[nm], fh, indent=1)


if __name__ == "__main__":
    main()
