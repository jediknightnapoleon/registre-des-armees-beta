"""Exp 12a-c: stage-1 loss: price-weighted least squares on log price, and IRLS towards
(price-weighted) least absolute deviation on log price. Otherwise as 11c."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

todo = sys.argv[1:] or ["12a", "12b", "12c"]
if "12a" in todo:
    e10.run("12a", "11c + stage-1 weights = price", reg_lam=1e-5, star_slopes=True,
            weight="price")
if "12b" in todo:
    e10.run("12b", "11c + stage-1 LAD on log (IRLS 10)", reg_lam=1e-5, star_slopes=True,
            irls=10)
if "12c" in todo:
    e10.run("12c", "11c + stage-1 price-weighted LAD on log (IRLS 10)", reg_lam=1e-5,
            star_slopes=True, weight="price", irls=10)
if "12d" in todo:
    e10.run("12d", "12c + commander stage by LAD", reg_lam=1e-5, star_slopes=True,
            weight="price", irls=10, cv_loss="l1")
