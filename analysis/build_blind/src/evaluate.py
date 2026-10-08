"""Fixed evaluation protocol.

Stage 1 (model / hyper-parameter selection, training data only):
    fit on training armies before the validation cut (80th percentile of the
    training game times), score on the remaining training armies.
Stage 2 (reporting): refit on all training armies with the chosen
    hyper-parameters, score on the test armies (played_at >= cut).

Writes out/eval_validation.csv, out/eval_test.csv and appends to RESULTS.md.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys

import numpy as np

from common import OUT, append_results
from models import Data, run, score

GRID = {
    "faction": [{"prior_n": p} for p in (5.0, 20.0, 50.0, 100.0)],
    "paper": [{}],
    "comp": [{"lam": l} for l in (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0)],
    "cardEB": [{"k": k} for k in (5.0, 20.0, 50.0, 100.0, 200.0)],
    "hybrid": [{"lam": l, "lam_card": lc} for l in (1.0, 10.0, 30.0) for lc in (30.0, 100.0, 300.0, 1000.0, 3000.0)],
    "small": [{"lam": l} for l in (0.1, 1.0, 10.0, 100.0)],
    "hybsmall": [{"lam": 1.0, "lam_card": lc} for lc in (30.0, 100.0, 300.0, 1000.0, 3000.0)],
}


def paired_bootstrap(D, preds: dict, idx, B: int = 2000, seed: int = 7):
    """SE of the log-loss difference of every model vs the best one, resampling MATCHES."""
    from common import logloss
    y = D.y[idx]
    matches = np.array([D.armies[i].match for i in idx])
    um, inv = np.unique(matches, return_inverse=True)
    losses = {k: -(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))
              for k, p in preds.items()}
    best = min(losses, key=lambda k: losses[k].mean())
    rng = np.random.default_rng(seed)
    out = {}
    sums = {k: np.bincount(inv, weights=v, minlength=len(um)) for k, v in losses.items()}
    cnt = np.bincount(inv, minlength=len(um))
    draws = [rng.integers(0, len(um), len(um)) for _ in range(B)]
    for k in losses:
        d = sums[k] - sums[best]
        bs = [d[s].sum() / cnt[s].sum() for s in draws]
        out[k] = (float(losses[k].mean() - losses[best].mean()), float(np.std(bs)))
    return best, out


def main():
    only = sys.argv[1:] or list(GRID)
    if only[0] != "faction":
        only = ["faction"] + [m for m in only if m != "faction"]   # sets the faction prior
    D = Data()
    tr_dec_t = np.sort(D.t[D.train & D.dec])
    vcut = tr_dec_t[int(0.8 * len(tr_dec_t))]
    fit_m = D.train & (D.t < vcut)
    val_m = D.train & (D.t >= vcut)
    stamp = dt.date.today().isoformat()
    print("validation cut", vcut, "fit", (fit_m & D.dec).sum(), "val", (val_m & D.dec).sum())

    val_rows, test_rows, log = [], [], []
    val_best_pred = {}
    best_faction_prior = 20.0
    for model in only:
        for skill in (False, True):
            best = None
            for hp in GRID[model]:
                hp = dict(hp)
                hp.setdefault("prior_n", best_faction_prior)
                p, idx, _ = run(D, model, fit_m, val_m, hp, skill)
                a, ll, n = score(D, p, idx)
                tag = model + ("+elo" if skill else "")
                val_rows.append([tag, repr(hp), n, round(a, 4), round(ll, 5)])
                print(f"VAL  {tag:12s} {hp} AUC {a:.4f} LL {ll:.5f}")
                if best is None or ll < best[1]:
                    best = (hp, ll, a)
                    val_best_pred[tag] = (p, idx)
            if model == "faction" and not skill:
                best_faction_prior = best[0]["prior_n"]
            hp = best[0]
            p, idx, fit = run(D, model, D.train, ~D.train, hp, skill)
            a, ll, n = score(D, p, idx)
            ar, llr, nr = score(D, p, idx, rated_only=True)
            tag = model + ("+elo" if skill else "")
            test_rows.append([tag, repr(hp), n, round(a, 4), round(ll, 5), nr, round(ar, 4), round(llr, 5),
                              round(best[2], 4), round(best[1], 5)])
            print(f"TEST {tag:12s} {hp} AUC {a:.4f} LL {ll:.5f} | rated-only AUC {ar:.4f} LL {llr:.5f}")
            log.append(f"| {stamp} | {tag} {hp} | val (train-late) | {(val_m & D.dec).sum()} | {best[2]:.4f} | {best[1]:.5f} | best of grid on validation |")
            log.append(f"| {stamp} | {tag} {hp} | test | {n} | {a:.4f} | {ll:.5f} | refit on all training |")

    vidx = next(iter(val_best_pred.values()))[1]
    best_m, diffs = paired_bootstrap(D, {k: v[0] for k, v in val_best_pred.items()}, vidx)
    print("validation log-loss vs best (", best_m, "), match-bootstrap SE:")
    for k, (d, se) in sorted(diffs.items(), key=lambda kv: kv[1][0]):
        print(f"   {k:14s} +{d:.5f}  (SE {se:.5f})")
    os.makedirs(OUT, exist_ok=True)
    suffix = "" if len(only) == len(GRID) else "_" + "_".join(only)
    with open(os.path.join(OUT, f"eval_validation{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "hyperparams", "n", "auc", "logloss"])
        w.writerows(val_rows)
    with open(os.path.join(OUT, f"eval_test{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "hyperparams", "n_test", "test_auc", "test_logloss", "n_test_rated", "test_auc_rated", "test_logloss_rated", "val_auc", "val_logloss"])
        w.writerows(test_rows)
    with open(os.path.join(OUT, f"eval_val_bootstrap{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "val_logloss_minus_best", "match_bootstrap_se", "best"])
        for k, (d, se) in diffs.items():
            w.writerow([k, round(d, 5), round(se, 5), best_m])
    append_results(log)


if __name__ == "__main__":
    main()
