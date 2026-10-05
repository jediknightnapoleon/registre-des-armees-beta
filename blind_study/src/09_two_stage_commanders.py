"""Exp 09a-d: two-stage model. Stage 1 = regular units (11 type segments, log-linear stats,
army offset per unit type) + staff generals. Stage 2 = commander variants additive in the
stage-1 price: price = max(1, a*p_reg + b_stars/d)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof, TARGET  # noqa
from features import add_features, is_excluded  # noqa
from twostage import TwoStage  # noqa

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)

STATS = ["log_men", "train", "accuracy", "reload_skill", "ammo", "morale", "melee_attack",
         "melee_defense", "charge_bonus", "range0", "projectile_damage0",
         "projectile_reload_time0", "speed_num", "rank_depth", "guns0",
         "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
         "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
         "pike_square"]
STAFF = [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))]
SEGS = sorted(set(dev["seg"]))
SPECS = {s: STAFF if s == "staff" else STATS for s in SEGS}
dev["army_seg"] = dev["faction_key"] + "|" + dev["seg"]
dev["army_bt"] = dev["faction_key"] + "|" + dev["base_type"]


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


def run(eid, desc, note="", **kw):
    def mk():
        args = dict(reg_seg_fn=lambda d: d["seg"].values, reg_specs=SPECS,
                    army_col="army_seg", lam_f=1e-4, rule_fn=staff_rule)
        args.update(kw)
        return TwoStage(**args)

    fm, oof = cross_validate(dev, lambda tr, te: mk().fit(tr).predict(te))
    save_oof(eid, dev, oof)
    m = mk().fit(dev)
    n1 = m.stage1.n_params_by_seg()
    ncv = sum(len(c) for c in m.cv_coef.values())
    append_result(eid, "regular: 11 types + staff; commanders: stage 2", desc, fm,
                  f"{max(v for k, v in n1.items() if k != 'faction')}/seg + {n1['faction']} army"
                  f" + {ncv} cv", note)


todo = sys.argv[1:] or ["09a", "09b", "09c", "09d"]
if "09a" in todo:
    run("09a", "two-stage; commander adj. global (a, b0..b5), least squares")
if "09b" in todo:
    run("09b", "two-stage; commander adj. per base type, least squares",
        cv_group_fn=lambda d: d["base_type"].values)
if "09c" in todo:
    run("09c", "two-stage; commander adj. per unit type, least squares",
        cv_group_fn=lambda d: d["seg"].values)
if "09d" in todo:
    run("09d", "two-stage; commander adj. per unit type, least abs. deviation",
        cv_group_fn=lambda d: d["seg"].values, cv_loss="l1")
