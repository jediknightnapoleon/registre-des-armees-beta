"""Exp 13: two-stage model with nested per-segment selected stage-1 specs (from
13_select_run.py). For outer fold k the specs selected without fold k are used; the
final-model specs ('all') are used only for the parameter count."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof  # noqa
from features import add_features, is_excluded  # noqa
from twostage import TwoStage  # noqa
import importlib.util  # noqa


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(__file__), fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sel = _load("sel13", "13_select_run.py")
e10 = _load("e10", "10_stage1_features.py")

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)
dev["army_seg"] = dev["faction_key"] + "|" + dev["seg"]
SEGS = sorted(set(dev["seg"]))


def specs_for(k):
    return {s: e10.STAFF if s == "staff" else sel.load_spec(s, k) for s in SEGS}


def mk(k, **kw):
    args = dict(reg_seg_fn=lambda d: d["seg"].values, reg_specs=specs_for(k),
                army_col="army_seg", lam_f=1e-4, rule_fn=e10.staff_rule, reg_lam=1e-5,
                star_slopes=True, weight="price", irls=10)
    args.update(kw)
    return TwoStage(**args)


def run(eid, desc, note="", **kw):
    fm, oof = cross_validate(dev, lambda tr, te: mk(int(te["fold"].iloc[0]), **kw).fit(tr).predict(te))
    save_oof(eid, dev, oof)
    m = mk("all", **kw).fit(dev)
    n1 = m.stage1.n_params_by_seg()
    ncv = sum(len(c) for c in m.cv_coef.values())
    nz = {s: int(sum(1 for c in m.stage1.cols if c.startswith(s + ":") and abs(m.stage1.coef[c]) > 1e-12))
          for s in m.stage1.segs}
    append_result(eid, "regular: 11 types + staff; commanders: stage 2", desc, fm,
                  f"≤{max(nz.values())}/seg + {n1['faction']} army + {ncv} cv", note)
    return m


if __name__ == "__main__":
    todo = sys.argv[1:] or ["13a", "13b", "13c"]
    if "13a" in todo:
        run("13a", "12c with per-type stage-1 terms chosen by nested greedy selection",
            note="selection nested inside CV")
    if "13b" in todo:
        run("13b", "13a + per-army commander premium (as 14a)", note="selection nested inside CV",
            cv_army_lam=1e-3)
    if "13c" in todo:
        run("13c", "13b with sparse army x type table (L1 1e-5, as 16a)",
            note="selection nested inside CV", cv_army_lam=1e-3, l1_f=1e-5)
