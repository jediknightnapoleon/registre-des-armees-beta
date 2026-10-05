"""Final candidates scored once on the holdout (chosen on CV before looking at it).
Each entry: name -> (description, make(dev) -> predict(df) function)."""
import os
import importlib.util

import numpy as np

from common import TARGET


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


e13 = _load("e13", "13_selected_eval.py")


def baseline_global(dev):
    mu = dev[TARGET].mean()
    return lambda df: np.full(len(df), mu)


def baseline_class(dev):
    """02e: per unit_class, mean price or gold-per-man x men (whichever fits train better)."""
    rules = {}
    for c, g in dev.groupby("unit_class"):
        mean = g[TARGET].mean()
        rate = g[TARGET].sum() / max(g["men_raw"].sum(), 1)
        if np.abs(g[TARGET] - mean).mean() <= np.abs(g[TARGET] - rate * g["men_raw"]).mean():
            rules[c] = ("mean", mean)
        else:
            rules[c] = ("rate", rate)
    mu = dev[TARGET].mean()

    def pred(df):
        out = np.full(len(df), mu)
        for i, (c, men) in enumerate(zip(df["unit_class"], df["men_raw"])):
            if c in rules:
                k, v = rules[c]
                out[i] = v if k == "mean" else v * men
        return out
    return pred


def two_stage(**kw):
    def make(dev):
        m = e13.mk("all", **kw).fit(dev)
        return m.predict
    return make


CANDIDATES = {
    "13c": ("best: selected formulas, sparse army x type table, commander army premium",
            two_stage(cv_army_lam=1e-3, l1_f=1e-5)),
    "18a": ("compact: as 13c with a 118-cell army table", two_stage(cv_army_lam=1e-3, l1_f=1e-4)),
    "18b": ("simplest: selected formulas, divisor N/10 only, no lookup tables",
            two_stage(lam_f=None)),
    "01": ("baseline: global mean", baseline_global),
    "02e": ("baseline: per-class mean or gold/man x men", baseline_class),
}
