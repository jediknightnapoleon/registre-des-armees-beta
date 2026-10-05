"""Exp 07a-c: army offsets estimated separately for staff generals and units, and the
amount of shrinkage. Model otherwise as 06b."""
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
CV = ["is_commander_variant", "cv_stars", ("cv_stars2", lambda d: d["cv_stars"] ** 2)]
STAFF = [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))]
SEGS = sorted(set(dev["seg"]))
SPECS = {s: (STAFF if s == "staff" else STATS + CV) for s in SEGS}
dev["fgroup"] = dev["faction_key"] + np.where(dev["staff_general"] == 1, "|staff", "|unit")


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


def run(eid, fcol, lam_f, desc):
    def mk():
        return JointLogLinear(lambda d: d["seg"].values, SPECS, use_n=True, lam_f=lam_f,
                              rule_fn=staff_rule, faction_col=fcol)

    def fp(tr, te):
        return mk().fit(tr[tr[TARGET] >= 50]).predict(te)

    fm, oof = cross_validate(dev, fp)
    save_oof(eid, dev, oof)
    m = mk().fit(dev[dev[TARGET] >= 50])
    npar = m.n_params_by_seg()
    append_result(eid, "12 segments, joint", desc, fm,
                  f"{max(npar[s] for s in m.segs)}/seg + {npar['faction']} army", "")


todo = sys.argv[1:] or ["07a", "07b", "07c"]
if "07a" in todo:
    run("07a", "fgroup", 1e-3, "06b with separate army offsets for staff generals and units")
if "07b" in todo:
    run("07b", "fgroup", 1e-4, "07a with weaker shrinkage (1e-4)")
if "07c" in todo:
    run("07c", "fgroup", 1e-2, "07a with stronger shrinkage (1e-2)")
