"""Exp 16a-c: 14a with a SPARSE army x type exceptions table (adaptive-ridge L1 on the
army offsets; cells with |offset| < 0.01 set to 0 and the rest refitted)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

base = dict(reg_lam=1e-5, star_slopes=True, weight="price", irls=10, cv_army_lam=1e-3)
todo = sys.argv[1:] or ["16a", "16b", "16c"]
for eid, l1 in [("16a", 1e-5), ("16b", 3e-5), ("16c", 1e-4)]:
    if eid in todo:
        e10.run(eid, f"14a with sparse army x type table (L1 {l1:g})", l1_f=l1, **base)
