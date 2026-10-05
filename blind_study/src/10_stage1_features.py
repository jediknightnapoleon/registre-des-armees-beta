"""Exp 10a-d: two-stage model (as 09a) with richer stage-1 features:
log1p of the main stats, men_raw, log1p of artillery stats; predictions clamp every
feature to its training range. Army offsets per unit type."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof  # noqa
from features import add_features, is_excluded  # noqa
from twostage import TwoStage  # noqa

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)

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


RICH = B + [L(c) for c in KEY] + ["men_raw", L("guns0"), L("range0"), L("projectile_damage0"),
                                  L("projectile_reload_time0")]
STAFF = [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))]
SEGS = sorted(set(dev["seg"]))
dev["army_seg"] = dev["faction_key"] + "|" + dev["seg"]
dev["army_bt"] = dev["faction_key"] + "|" + dev["base_type"]
dev["army_one"] = dev["faction_key"] + np.where(dev["staff_general"] == 1, "|staff", "|unit")


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


def run(eid, desc, note="", spec=RICH, **kw):
    specs = {s: STAFF if s == "staff" else spec for s in SEGS}

    def mk():
        args = dict(reg_seg_fn=lambda d: d["seg"].values, reg_specs=specs,
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


if __name__ == "__main__":
    todo = sys.argv[1:] or ["10a", "10b", "10c", "10d"]
    if "10a" in todo:
        run("10a", "09a + log1p stats, men_raw, log1p art stats; clamp; ridge 1e-4",
            reg_lam=1e-4)
    if "10b" in todo:
        run("10b", "10a with ridge 1e-5", reg_lam=1e-5)
    if "10c" in todo:
        run("10c", "10a with ridge 1e-3", reg_lam=1e-3)
    if "10d" in todo:
        run("10d", "10a but army offsets per base type (staff/inf/cav/art)", army_col="army_bt",
            reg_lam=1e-4)
