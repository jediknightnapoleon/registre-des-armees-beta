"""Exp 05a-c: how to model the per-army price divisor.

Joint log-linear model: per-segment (staff/inf/cav/art) linear terms in stats, plus a shared
army (faction) offset: (a) fixed -log(N/10) from the army name's corps number;
(b) (a) + per-army ridge-shrunk deviations; (c) free per-army lookup, no N.
Staff generals without command stars are priced by rule: 1 gold.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof  # noqa
from features import add_features, is_excluded  # noqa
from linmodels import JointLogLinear  # noqa

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)

STATS = ["log_men", "stars", "has_stars", "is_commander_variant", "train",
         "accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense",
         "charge_bonus", "range0", "projectile_damage0", "projectile_reload_time0",
         "speed_num", "rank_depth", "guns0",
         "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
         "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
         "pike_square", ("cat", "unit_class")]
SPECS = {"staff": [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))],
         "inf": STATS, "cav": STATS, "art": STATS}


def seg_fn(d):
    return d["base_type"].values


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


variants = {
    "05a": dict(use_n=True, lam_f=None, desc="army offset = -log(N/10) fixed"),
    "05b": dict(use_n=True, lam_f=1e-3, desc="-log(N/10) + per-army deviation (ridge 1e-3)"),
    "05c": dict(use_n=False, lam_f=1e-6, desc="free per-army lookup (no N)"),
}
for eid in sys.argv[1:] or variants:
    v = variants[eid]

    def fp(tr, te, v=v):
        m = JointLogLinear(seg_fn, SPECS, use_n=v["use_n"], lam_f=v["lam_f"], rule_fn=staff_rule)
        return m.fit(tr).predict(te)

    fm, oof = cross_validate(dev, fp)
    save_oof(eid, dev, oof)
    m = JointLogLinear(seg_fn, SPECS, use_n=v["use_n"], lam_f=v["lam_f"], rule_fn=staff_rule).fit(dev)
    npar = m.n_params_by_seg()
    append_result(eid, "staff / inf / cav / art, joint", "log-linear stats (as exp 04) + " + v["desc"],
                  fm, f"{max(npar[s] for s in m.segs)}/seg + {npar['faction']} army",
                  "faction divisor modelling")
