"""Exp 14a-b: 12c + a per-army additive commander premium (army[f]/d), ridge-shrunk."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

todo = sys.argv[1:] or ["14a", "14b"]
base = dict(reg_lam=1e-5, star_slopes=True, weight="price", irls=10)
if "14a" in todo:
    e10.run("14a", "12c + per-army commander premium (ridge 1e-3)", cv_army_lam=1e-3, **base)
if "14b" in todo:
    e10.run("14b", "12c + per-army commander premium (ridge 1e-2)", cv_army_lam=1e-2, **base)
