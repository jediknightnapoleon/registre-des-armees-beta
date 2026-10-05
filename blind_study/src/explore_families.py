"""Exploration: add feature families to RICH per segment (regular units), CV MAE."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from explore_seg import get_dev  # noqa
from segsel import seg_cv_mae, n_coef  # noqa
import importlib.util  # noqa
spec = importlib.util.spec_from_file_location("e10", os.path.join(os.path.dirname(__file__),
                                                                  "10_stage1_features.py"))
e10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e10)
KEY = e10.KEY


def Q(c):
    return (f"{c}^2", lambda d, c=c: d[c].fillna(0) ** 2)


FAM = {
    "sq": [Q(c) for c in KEY],
    "speed": [("cat", "speed_code")],
    "trainlvl": [("cat", "unit_training_level")],
    "men2": [("log_men^2", lambda d: d["log_men"] ** 2)],
    "menx": [(f"log_men*{c}", lambda d, c=c: d["log_men"] * d[c].fillna(0)) for c in
             ["morale", "melee_attack", "melee_defense", "accuracy", "reload_skill"]],
    "prod": [("morale*melee_attack", lambda d: d["morale"] * d["melee_attack"]),
             ("morale*accuracy", lambda d: d["morale"] * d["accuracy"]),
             ("accuracy*reload", lambda d: d["accuracy"] * d["reload_skill"]),
             ("melee_attack*charge", lambda d: d["melee_attack"] * d["charge_bonus"]),
             ("melee_attack*defense", lambda d: d["melee_attack"] * d["melee_defense"])],
    "formation": ["base_density", "close_formation_spacing_horizontal",
                  "close_formation_spacing_vertical", "loose_formation_spacing_horizontal",
                  "loose_formation_spacing_vertical"],
    "drill": [("cat", "unit_drill_set")],
}

if __name__ == "__main__":
    d = get_dev()
    d = d.assign(army_seg=d.faction_key + "|" + d.seg)
    segs = sys.argv[1:] or sorted(set(d.seg) - {"staff"})
    for seg in segs:
        s = d[(d.seg == seg) & (d.is_commander_variant == 0)]
        base = seg_cv_mae(s, e10.RICH, [0, 1, 2, 3, 4])
        out = [f"{seg:10s} base {base:6.2f}"]
        for name, fam in FAM.items():
            m = seg_cv_mae(s, e10.RICH + fam, [0, 1, 2, 3, 4])
            out.append(f"{name} {100*(m/base-1):+5.1f}%")
        print(" | ".join(out), flush=True)
