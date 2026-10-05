"""Exp 11a-d: commander stage variants on top of 10b's stage 1:
slope a per base type / per unit type, and star-specific slopes."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

todo = sys.argv[1:] or ["11a", "11b", "11c", "11d"]
if "11a" in todo:
    e10.run("11a", "10b + commander slope a per base type", reg_lam=1e-5, slope_col="base_type")
if "11b" in todo:
    e10.run("11b", "10b + commander slope a per unit type", reg_lam=1e-5, slope_col="seg")
if "11c" in todo:
    e10.run("11c", "10b + commander star-specific slopes", reg_lam=1e-5, star_slopes=True)
if "11d" in todo:
    e10.run("11d", "10b + commander slope per unit type + star slopes", reg_lam=1e-5,
            slope_col="seg", star_slopes=True)
