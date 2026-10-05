"""Exp 08a-c: separate coefficients for commander variants vs regular units within each unit
type (seg x cv = 22 segments + staff), and army offsets shared / per broad type / per type.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof, TARGET  # noqa
from features import add_features, is_excluded  # noqa
from linmodels import JointLogLinear  # noqa

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)

STATS = ["log_men", "train", "accuracy", "reload_skill", "ammo", "morale", "melee_attack",
         "melee_defense", "charge_bonus", "range0", "projectile_damage0",
         "projectile_reload_time0", "speed_num", "rank_depth", "guns0",
         "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
         "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
         "pike_square"]
CVT = ["cv_stars", ("cv_stars2", lambda d: d["cv_stars"] ** 2)]
STAFF = [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))]


def seg2(d):
    return np.where(d["seg"] == "staff", "staff",
                    d["seg"] + np.where(d["is_commander_variant"] == 1, "|cv", "|reg"))


SEGS = sorted(set(seg2(dev)))
SPECS = {s: STAFF if s == "staff" else (STATS + CVT if s.endswith("|cv") else STATS)
         for s in SEGS}
dev["army_all"] = dev["faction_key"] + np.where(dev["staff_general"] == 1, "|staff", "|unit")
dev["army_bt"] = dev["faction_key"] + "|" + dev["base_type"]
dev["army_seg"] = dev["faction_key"] + "|" + dev["seg"]


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


def run(eid, fcol, lam_f, desc, note=""):
    def mk():
        return JointLogLinear(seg2, SPECS, use_n=True, lam_f=lam_f, rule_fn=staff_rule,
                              faction_col=fcol)

    fm, oof = cross_validate(dev, lambda tr, te: mk().fit(tr[tr[TARGET] >= 50]).predict(te))
    save_oof(eid, dev, oof)
    m = mk().fit(dev[dev[TARGET] >= 50])
    npar = m.n_params_by_seg()
    append_result(eid, "11 types x (regular, commander) + staff, joint", desc, fm,
                  f"{max(npar[s] for s in m.segs)}/seg + {npar['faction']} army", note)


todo = sys.argv[1:] or ["08a", "08b", "08c"]
if "08a" in todo:
    run("08a", "army_all", 1e-2, "commander/regular split; army offsets: staff + units tables")
if "08b" in todo:
    run("08b", "army_bt", 1e-2, "commander/regular split; army offsets per base type (staff/inf/cav/art)")
if "08c" in todo:
    run("08c", "army_seg", 1e-2, "commander/regular split; army offsets per unit type (12 tables)")
if "08d" in todo:
    run("08d", "army_bt", 1e-4, "08b with weak army shrinkage (1e-4)")
if "08e" in todo:
    run("08e", "army_seg", 1e-4, "08c with weak army shrinkage (1e-4)")
