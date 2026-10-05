"""Exp 15a-d: accuracy/simplicity trade-off around 14a (RICH stage-1 spec, price-weighted
LAD, commander star slopes + per-army premium): replace the army x type offset table by
(a) army x broad type (staff/inf/cav/art), (b) one army table for units + one for staff,
(c) no army tables (army divisor = N/10 only) but keep the commander army premium,
(d) no army tables anywhere (N/10 only)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)

todo = sys.argv[1:] or ["15a", "15b", "15c", "15d"]
base = dict(reg_lam=1e-5, star_slopes=True, weight="price", irls=10)
if "15a" in todo:
    e10.run("15a", "14a with army offsets per broad type (55x4)", army_col="army_bt",
            cv_army_lam=1e-3, **base)
if "15b" in todo:
    e10.run("15b", "14a with one army table for units + one for staff (55x2)",
            army_col="army_one", cv_army_lam=1e-3, **base)
if "15c" in todo:
    e10.run("15c", "14a with no stage-1 army tables (N/10 only); commander army premium kept",
            lam_f=None, cv_army_lam=1e-3, **base)
if "15d" in todo:
    e10.run("15d", "no army tables at all: divisor N/10 only", lam_f=None, **base)
