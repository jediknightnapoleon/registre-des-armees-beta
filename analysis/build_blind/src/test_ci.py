"""Match-bootstrap 95% intervals on the TEST set for AUC / log-loss differences vs faction-only.

Uses the hyper-parameters chosen on validation (out/eval_test.csv).  Resamples
test MATCHES (teammates share a result).  Writes out/test_bootstrap.csv.
"""
from __future__ import annotations

import ast
import csv
import os

import numpy as np

from common import OUT, auc, logloss
from models import Data, run

D = Data()
rows = list(csv.DictReader(open(os.path.join(OUT, "eval_test.csv"), encoding="utf-8")))
preds = {}
for r in rows:
    tag = r["model"]
    model, skill = tag.replace("+elo", ""), tag.endswith("+elo")
    p, idx, _ = run(D, model, D.train, ~D.train, ast.literal_eval(r["hyperparams"]), skill)
    preds[tag] = p
y = D.y[idx]
matches = np.array([D.armies[i].match for i in idx])
um, inv = np.unique(matches, return_inverse=True)
groups = [np.flatnonzero(inv == g) for g in range(len(um))]
rng = np.random.default_rng(11)
B = 1000
samples = []
for _ in range(B):
    s = rng.integers(0, len(um), len(um))
    samples.append(np.concatenate([groups[g] for g in s]))
base = preds["faction"]
out = []
for tag, p in preds.items():
    da = [auc(y[s], p[s]) - auc(y[s], base[s]) for s in samples]
    dl = [logloss(y[s], p[s]) - logloss(y[s], base[s]) for s in samples]
    out.append([tag, round(auc(y, p), 4), round(float(np.percentile(da, 2.5)), 4), round(float(np.percentile(da, 97.5)), 4),
                round(logloss(y, p), 5), round(float(np.percentile(dl, 2.5)), 5), round(float(np.percentile(dl, 97.5)), 5)])
    print(f"{tag:14s} AUC {out[-1][1]:.4f} dAUC 95% [{out[-1][2]:+.4f},{out[-1][3]:+.4f}]  LL {out[-1][4]:.5f} dLL [{out[-1][5]:+.5f},{out[-1][6]:+.5f}]")
with open(os.path.join(OUT, "test_bootstrap.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["model", "test_auc", "dAUC_vs_faction_lo95", "dAUC_vs_faction_hi95", "test_logloss",
                "dLL_vs_faction_lo95", "dLL_vs_faction_hi95"])
    w.writerows(out)
