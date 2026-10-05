"""Exploration (not a logged experiment): per-segment feature-transform comparison on
regular units, CV MAE with army dummies."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from explore_seg import cv_seg  # noqa

B = ["log_men", "train", "accuracy", "reload_skill", "ammo", "morale", "melee_attack",
     "melee_defense", "charge_bonus", "range0", "projectile_damage0",
     "projectile_reload_time0", "speed_num", "rank_depth", "guns0",
     "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
     "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
     "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
     "pike_square"]
KEY = ["accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense",
       "charge_bonus"]


def L(c):
    return (f"log_{c}", lambda d, c=c: np.log1p(d[c].fillna(0)))


def Q(c):
    return (f"{c}^2", lambda d, c=c: d[c].fillna(0) ** 2)


SETS = {
    "base": B,
    "+logs": B + [L(c) for c in KEY],
    "+sq": B + [Q(c) for c in KEY],
    "+logs+men": B + [L(c) for c in KEY] + ["men_raw"],
    "+logs+sq+men": B + [L(c) for c in KEY] + [Q(c) for c in KEY] + ["men_raw"],
    "+logs+men+catspeed+cattrain": B + [L(c) for c in KEY] + ["men_raw", ("cat", "speed_code"),
                                                          ("cat", "unit_training_level")],
    "+logs+men+art": B + [L(c) for c in KEY] + ["men_raw", L("guns0"), L("range0"),
                                              L("projectile_damage0"),
                                              L("projectile_reload_time0")],
}
if __name__ == "__main__":
    segs = sys.argv[1:] or ["inf_line", "art_foot", "art_horse", "cav_heavy", "inf_grena",
                            "inf_milit", "inf_skirm", "cav_light"]
    for seg in segs:
        for name, sp in SETS.items():
            m, lsd, _ = cv_seg(seg, sp, cvflag=0)
            print(f"{seg:10s} {name:30s} MAE {m:7.2f} lsd {lsd:.4f}")
