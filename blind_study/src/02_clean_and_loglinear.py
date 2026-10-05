"""Exp 02d-04: baselines on the cleaned dev set (34 joke/placeholder rows excluded),
then first log-linear models with the faction 'corps number' multiplier."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, cross_validate, append_result, save_oof, TARGET  # noqa
from features import add_features, is_excluded  # noqa
from linmodels import LogLinear, segmented  # noqa

dev = add_features(load_dev())
dev = dev[~is_excluded(dev)].reset_index(drop=True)
print("clean dev rows:", len(dev))

exps = sys.argv[1:] or ["02d", "02e", "03", "04"]


def class_best(tr, te):
    out = np.empty(len(te))
    for c, te_c in te.groupby("unit_class"):
        tr_c = tr[tr["unit_class"] == c]
        mean = tr_c[TARGET].mean()
        rate = tr_c[TARGET].sum() / max(tr_c["men_raw"].sum(), 1)
        mae_mean = np.abs(tr_c[TARGET] - mean).mean()
        mae_rate = np.abs(tr_c[TARGET] - rate * tr_c["men_raw"]).mean()
        p = np.full(len(te_c), mean) if mae_mean <= mae_rate else rate * te_c["men_raw"].values
        out[te.index.get_indexer(te_c.index)] = p
    return out


class StaffGeneral:
    """Standalone generals: 1 gold without command stars, else log-linear in stars and N."""

    def __init__(self, spec):
        self.spec = spec

    def fit(self, df):
        self.m = LogLinear(self.spec).fit(df[df["has_stars"] == 1])
        return self

    def predict(self, df):
        return np.where(df["has_stars"] == 1, self.m.predict(df), 1.0)


def staff_or(other):
    def seg(df):
        return np.where(df["staff_general"] == 1, "staff", other(df))
    return seg


if "02d" in exps:
    fm, oof = cross_validate(dev, lambda tr, te: np.full(len(te), tr[TARGET].mean()))
    save_oof("02d", dev, oof)
    append_result("02d", "all (clean)", "global mean", fm, 1,
                  "baseline 1 after excluding 34 joke/placeholder rows")
if "02e" in exps:
    fm, oof = cross_validate(dev, class_best)
    save_oof("02e", dev, oof)
    append_result("02e", "all (clean)", "per class: mean or gold/man x men (chosen on train)",
                  fm, 15, "baseline 2 on clean set")

if "03" in exps:
    spec = [("cat", "unit_class"), "log_men", "log_n", "stars"]
    models = {"staff": lambda: StaffGeneral(["log_n", ("ls", lambda d: np.log(d["stars"].clip(lower=1)))]),
              "rest": lambda: LogLinear(spec)}
    fp = segmented(staff_or(lambda d: np.full(len(d), "rest", dtype=object)), models)
    fm, oof = cross_validate(dev, fp)
    save_oof("03", dev, oof)
    append_result("03", "staff generals / rest", "log price ~ class + log men + log N + stars; "
                  "staff: 1 if no stars else log-linear(log stars, log N)", fm, 3 + 18,
                  "multiplicative structure; corps number N from army name")

if "04" in exps:
    base = ["log_men", "log_n", "stars", "has_stars", "is_commander_variant", "train",
            "accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense",
            "charge_bonus", "range0", "projectile_damage0", "projectile_reload_time0",
            "speed_num", "rank_depth", "guns0",
            "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
            "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
            "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
            "pike_square", ("cat", "unit_class")]
    models = {"staff": lambda: StaffGeneral(["log_n", ("ls", lambda d: np.log(d["stars"].clip(lower=1)))])}
    for bt in ["inf", "cav", "art"]:
        models[bt] = lambda: LogLinear(base)
    fp = segmented(staff_or(lambda d: d["base_type"].values), models)
    fm, oof = cross_validate(dev, fp)
    save_oof("04", dev, oof)
    append_result("04", "staff / inf / cav / art", "log-linear, all raw stats + flags + class + "
                  "log men + log N (linear in stats)", fm, "~40/seg",
                  "first full log-linear per base type")
