"""Exp 06a-c: segment by unit type (commander variants join the segment of the unit they
are attached to), joint fit with a shared army offset (-log(N/10) + shrunk deviations).

06a: 11 type segments + staff, linear stats + commander terms (is_cv, cv_stars, cv_stars^2)
06b: as 06a but rows priced < 50 gold are left out of fitting (still predicted/scored)
06c: as 06b but segments by base type only (inf/cav/art), with speed letter + drill set
     dummies instead of the unit-type code (no use of unit_key)
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
CV = ["is_commander_variant", "cv_stars", ("cv_stars2", lambda d: d["cv_stars"] ** 2)]
STAFF = [("log_stars", lambda d: np.log(d["stars"].clip(lower=1)))]


def staff_rule(d):
    return np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, np.nan)


def make(eid):
    if eid in ("06a", "06b"):
        segs = sorted(set(dev["seg"]))
        specs = {s: (STAFF if s == "staff" else STATS + CV) for s in segs}
        seg_fn = lambda d: d["seg"].values  # noqa
    else:
        specs = {"staff": STAFF}
        for bt in ["inf", "cav", "art"]:
            specs[bt] = STATS + CV + [("cat", "speed_letter"), ("cat", "unit_drill_set")]
        seg_fn = lambda d: d["base_type"].values  # noqa
    return specs, seg_fn


desc = {"06a": "type segments; log-linear stats + commander terms; army offset",
        "06b": "06a, fit without rows < 50 gold",
        "06c": "base-type segments + speed-letter/drill dummies (no unit_key); fit w/o < 50 gold"}
for eid in sys.argv[1:] or ["06a", "06b", "06c"]:
    specs, seg_fn = make(eid)
    lowcut = 0 if eid == "06a" else 50

    def fp(tr, te):
        tr = tr[tr[TARGET] >= lowcut] if lowcut else tr
        trr = tr[~((tr["staff_general"] == 1) & (tr["has_stars"] == 0))] if lowcut else tr
        m = JointLogLinear(seg_fn, specs, use_n=True, lam_f=1e-3, rule_fn=staff_rule)
        return m.fit(trr if lowcut else tr).predict(te)

    fm, oof = cross_validate(dev, fp)
    save_oof(eid, dev, oof)
    m = JointLogLinear(seg_fn, specs, use_n=True, lam_f=1e-3, rule_fn=staff_rule).fit(dev)
    npar = m.n_params_by_seg()
    append_result(eid, f"{len(specs)} segments, joint", desc[eid], fm,
                  f"{max(npar[s] for s in m.segs)}/seg + {npar['faction']} army", "")
