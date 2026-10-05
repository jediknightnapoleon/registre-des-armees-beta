"""Exp 01-02: baselines. Global mean; mean per unit_class; per-class price-per-man x men."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof, summarize, TARGET  # noqa

dev = load_dev()


def global_mean(tr, te):
    return np.full(len(te), tr[TARGET].mean())


def class_mean(tr, te):
    m = tr.groupby("unit_class")[TARGET].mean()
    return te["unit_class"].map(m).fillna(tr[TARGET].mean()).values


def class_per_man(tr, te):
    # ratio estimator: sum(price)/sum(men_raw) per class, times men_raw
    g = tr.groupby("unit_class")
    rate = g[TARGET].sum() / g["men_raw"].sum()
    p = te["unit_class"].map(rate) * te["men_raw"]
    return p.fillna(tr[TARGET].mean()).values


def class_best(tr, te):
    # per class, choose plain mean vs per-man scaling by training-fold MAE (inner choice on train)
    out = np.empty(len(te))
    for c, te_c in te.groupby("unit_class"):
        tr_c = tr[tr["unit_class"] == c]
        if len(tr_c) == 0:
            out[te.index.get_indexer(te_c.index)] = tr[TARGET].mean()
            continue
        mean = tr_c[TARGET].mean()
        rate = tr_c[TARGET].sum() / max(tr_c["men_raw"].sum(), 1)
        mae_mean = np.abs(tr_c[TARGET] - mean).mean()
        mae_rate = np.abs(tr_c[TARGET] - rate * tr_c["men_raw"]).mean()
        p = np.full(len(te_c), mean) if mae_mean <= mae_rate else rate * te_c["men_raw"].values
        out[te.index.get_indexer(te_c.index)] = p
    return out


for eid, fn, name, npar, note in [
    ("01", global_mean, "global mean", 1, "baseline 1"),
    ("02a", class_mean, "mean per unit_class", 15, "baseline 2"),
    ("02b", class_per_man, "per-class gold/man x men_raw", 15, "baseline 2, size-scaled"),
    ("02c", class_best, "per class: mean or gold/man x men (chosen on train fold)", 15,
     "baseline 2, best of both per class"),
]:
    fm, oof = cross_validate(dev, fn)
    save_oof(eid, dev, oof)
    append_result(eid, "all", name, fm, npar, note)
