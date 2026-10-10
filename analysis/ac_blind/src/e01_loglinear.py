"""E01/E02: log-linear model per arm (class, log size, stats, abilities, training,
speed code, corps_number one-hot, side), then + shrunk per-army offset."""
from __future__ import annotations
import numpy as np
from common import regular_units, OUT
from harness import run_cv, report, arm_vec, ARMS
from features import Design, gridge_fit, STATS, BOOLS

d = regular_units()
y = d.f("base_mp_cost"); ly = np.log(y)
arm = arm_vec(d)
size = np.where(arm == "artillery", d.f("guns", 0), d.f("men_display"))

def design(mask, army=False):
    D = Design()
    D.add("log_size", np.log(size[mask]))
    for s in STATS: D.add(s, d.f(s, 0)[mask])
    for b in BOOLS:
        v = d.b(b)[mask]
        if 0 < v.sum() < mask.sum(): D.add(b, v)
    D.add_onehot("class", d.s("unit_class")[mask])
    D.add_onehot("train", d.s("unit_training_level")[mask])
    D.add_onehot("speed", d.s("speed_code")[mask], group="cat")
    D.add_onehot("cn", d.s("corps_number")[mask])
    D.add("empire", d.s("corps_side")[mask] == "empire")
    if army:
        D.add_onehot("army", d.s("faction_key")[mask], group="army")
    return D

def make_fp(armflag, lam_army):
    def fp(tr, te):
        out = np.empty(len(te))
        for a in ARMS:
            m = arm == a
            D = design(m, armflag); X = D.matrix()
            idx = np.where(m)[0]; pos = {g: i for i, g in enumerate(idx)}
            trm = np.array([pos[i] for i in tr if m[i]]); tem = np.array([pos[i] for i in te if m[i]])
            pen = np.array([{"main": 1e-3, "cat": 1.0, "army": lam_army}[g] for g in D.groups])
            a0, b = gridge_fit(X[trm], ly[idx[trm]], pen)
            out[m[te]] = np.exp(a0 + X[tem] @ b)
        return out
    return fp

p = run_cv(make_fp(False, 0), d)
report("E01", d, y, p, "log-linear per arm: log size + 7 stats + abilities + class + training + speed + corps_number one-hot + side")
np.save(f"{OUT}/pred_E01.npy", p)
for lam in [1.0, 5.0]:
    p = run_cv(make_fp(True, lam), d)
    report(f"E02_l{lam:g}", d, y, p, "E01 + per-army offset (ridge)", f"lam_army={lam}")
