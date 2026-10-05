"""Exp 17a-b: 14a with different ridge strength on the army x type offsets."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

base = dict(reg_lam=1e-5, star_slopes=True, weight="price", irls=10, cv_army_lam=1e-3)
todo = sys.argv[1:] or ["17a", "17b"]
for eid, lf in [("17a", 1e-5), ("17b", 1e-3)]:
    if eid in todo:
        e10.run(eid, f"14a with army-offset ridge {lf:g}", lam_f=lf, **base)
