"""Configurable per-arm log-price models (generalised ridge) used by experiments E03+.

A model = for each arm, a Design built from options, fitted on log(price) with
per-group ridge penalties; prediction = exp(linear predictor). Optional
per-army offsets (group "army") are shrunk ridge random effects: an unseen army
gets offset 0 automatically (its dummy column is 0 in training).
"""
from __future__ import annotations

import numpy as np

from common import Data
from features import Design, gridge_fit, STATS, BOOLS
from harness import arm_vec, ARMS, fold_vec

SPEED_LETTERS = ["C", "F", "G", "GS", "H", "L", "S"]


def split_speed(code: str) -> tuple[str, int]:
    i = len(code)
    while i > 0 and code[i - 1].isdigit():
        i -= 1
    return code[:i], int(code[i:]) if i < len(code) else 0


class Ctx:
    """Cached columns for the whole dataset."""

    def __init__(self, d: Data):
        self.d = d
        self.y = d.f("base_mp_cost")
        self.ly = np.log(self.y)
        self.arm = arm_vec(d)
        self.cls = d.s("unit_class")
        self.fold = fold_vec(d)
        self.men_raw = d.f("men_raw")
        self.men = d.f("men_display")
        self.guns = d.f("guns", 0)
        self.size = np.where(self.arm == "artillery", self.guns, self.men_raw)
        self.cn = d.f("corps_number")
        self.side = d.s("corps_side")
        self.fk = d.s("faction_key")
        sp = [split_speed(c) for c in d.s("speed_code")]
        self.sp_letter = np.array([s[0] for s in sp], dtype=object)
        self.sp_digit = np.array([s[1] for s in sp], dtype=float)
        self.stats = {s: d.f(s, 0) for s in STATS}
        self.bools = {b: d.b(b) for b in BOOLS}
        self.train = d.s("unit_training_level")
        self.speed = d.s("speed_code")
        self.pdmg = d.f("projectile_damage", 0)
        self.prel = d.f("projectile_reload_time", 0)
        self.rng = d.f("range", 0)
        self.rsm = d.s("range_selection_method")
        self.cap = d.f("unit_cap")
        self.div = d.s("division_id")
        # faction_key: ntw3_ac_<a|b><nn>_<x|r><k>_<nnn>
        parts = [k.split("_") for k in self.fk]
        self.fk_era = np.array([int(p[2][1:]) for p in parts], dtype=float)
        self.fk_xl = np.array([p[3][0] for p in parts], dtype=object)
        self.fk_xd = np.array([int(p[3][1:]) for p in parts], dtype=float)


def build(c: Ctx, m: np.ndarray, arm: str, o: dict) -> Design:
    D = Design()
    ls = np.log(c.size[m])
    cls = c.cls[m]
    # ---- size
    if o.get("size_mode", "loglin") == "loglin":
        D.add("log_size", ls)
    if o.get("size_spline") and arm != "artillery":
        knots = o["size_spline"].get(arm, []) if isinstance(o["size_spline"], dict) else o["size_spline"]
        for k in knots:
            D.add(f"hinge_log_size_{k}", np.maximum(0, ls - np.log(k)))
    if o.get("size_spline_by_class") and arm != "artillery":
        for k in o["size_spline_by_class"]:
            for cl in sorted(set(cls)):
                h = np.maximum(0, ls - np.log(k)) * (cls == cl)
                if h.std() > 0:
                    D.add(f"hinge_log_size_{k}:{cl}", h, group="inter")
    if o.get("size_quad"):
        D.add("log_size2", (ls - ls.mean()) ** 2)
    if o.get("size_by_class"):
        for cl in sorted(set(cls)):
            if (cls == cl).sum() > 0:
                D.add(f"log_size:{cl}", ls * (cls == cl), group="inter")
    if o.get("size_quad_by_class"):
        for cl in sorted(set(cls)):
            D.add(f"log_size2:{cl}", (ls - ls.mean()) ** 2 * (cls == cl), group="inter")
    if arm == "artillery" and o.get("art_size_onehot"):
        g = np.minimum(c.guns[m], 5).astype(int).astype(str)
        D.add_onehot("guns", g, drop="3")
    # ---- stats
    stat_mode = o.get("stat_mode", "lin")
    for s in STATS:
        v = c.stats[s][m]
        if v.std() == 0:
            continue
        if stat_mode in ("lin", "both"):
            D.add(s, v)
        if stat_mode in ("log", "both"):
            D.add(f"log1p_{s}", np.log1p(v))
    if o.get("stat_by_class"):
        for s in STATS:
            v = c.stats[s][m]
            for cl in sorted(set(cls)):
                mm = cls == cl
                if v[mm].std() > 0:
                    D.add(f"log1p_{s}:{cl}", np.log1p(v) * mm, group="inter3")
    # ---- abilities
    for b in BOOLS:
        v = c.bools[b][m]
        if 0 < v.sum() < m.sum():
            D.add(b, v)
    D.add_onehot("class", cls)
    if o.get("bool_by_class"):
        for b in BOOLS:
            v = c.bools[b][m]
            for cl in sorted(set(cls)):
                mm = cls == cl
                if 0 < (v & mm).sum() < mm.sum():
                    D.add(f"{b}:{cl}", v & mm, group="inter2")
    if o.get("train", True):
        D.add_onehot("train", c.train[m], group="cat")
    # ---- speed
    sm = o.get("speed_mode", "onehot")
    if sm == "onehot":
        D.add_onehot("speed", c.speed[m], group="cat")
    elif sm == "letter_digit":
        D.add_onehot("spL", c.sp_letter[m], group="cat")
        for L in sorted(set(c.sp_letter[m])):
            D.add(f"spD:{L}", c.sp_digit[m] * (c.sp_letter[m] == L))
    # ---- artillery specifics
    if arm == "artillery" and o.get("art_feats"):
        D.add("log_pdmg", np.log(np.maximum(c.pdmg[m], 1)))
        D.add("howitzer", np.isin(c.rsm[m], ["howitzer_shell", "unicorn_shell"]))
        D.add("log_range", np.log(np.maximum(c.rng[m], 1)))
        D.add("log_prel", np.log(np.maximum(c.prel[m], 1)))
    if arm == "artillery" and o.get("art_proj"):
        D.add_onehot("proj", c.d.s("projectile_key")[m], group="cat")
    if o.get("size_by_train"):
        for t in sorted(set(c.train[m])):
            D.add(f"log_size:{t}", ls * (c.train[m] == t), group="inter")
    if arm == "infantry" and o.get("inf_range"):
        D.add("log_range", np.log(np.maximum(c.rng[m], 1)))
        D.add("log_pdmg", np.log(np.maximum(c.pdmg[m], 0.1)))
    # ---- army
    cm = o.get("cn_mode", "onehot")
    if cm == "onehot":
        D.add_onehot("cn", c.cn[m].astype(int).astype(str))
    elif cm.startswith("log+"):
        k = float(cm[4:])
        D.add("log_cn_k", np.log(c.cn[m] + k))
    elif cm == "linear":
        D.add("cn", c.cn[m])
    if o.get("side", True):
        D.add("empire", c.side[m] == "empire")
    if o.get("fk_codes"):
        D.add_onehot("era", c.fk_era[m].astype(int).astype(str), group="cat")
        D.add_onehot("xd", c.fk_xd[m].astype(int).astype(str), group="cat")
        D.add("r_letter", c.fk_xl[m] == "r")
    if o.get("army"):
        D.add_onehot("army", c.fk[m], group="army")
    if o.get("placement"):
        D.add_onehot("cap", np.minimum(c.cap[m], 4).astype(int).astype(str), group="cat")
        D.add_onehot("div", c.div[m], group="cat")
    if o.get("geometry"):
        D.add("rank_depth", c.d.f("rank_depth", 0)[m])
        D.add_onehot("drill", c.d.s("unit_drill_set")[m], group="cat")
        for g in ["base_density", "close_formation_spacing_horizontal", "close_formation_spacing_vertical",
                  "loose_formation_spacing_horizontal", "loose_formation_spacing_vertical"]:
            v = c.d.f(g, 0)[m]
            if v.std() > 0:
                D.add(g, v, group="cat")
    if o.get("train_by_class"):
        tc = np.array([f"{a}|{k}" for a, k in zip(c.train[m], cls)], dtype=object)
        D.add_onehot("traincls", tc, group="cat")
    if o.get("army_arm"):
        D.add_onehot("armyarm", c.fk[m], group="armyarm")
    if o.get("army_class"):
        ac = np.array([f"{a}|{k}" for a, k in zip(c.fk[m], cls)], dtype=object)
        D.add_onehot("armycls", ac, group="armycls")
    return D


DEFAULT_PEN = {"main": 1e-3, "cat": 1.0, "inter": 1.0, "army": 1.0, "armycls": 5.0, "armyarm": 1.0, "inter2": 1.0, "inter3": 5.0}


def fit_arm(c: Ctx, arm: str, o: dict, tr: np.ndarray, pen: dict | None = None):
    """tr: global indices of training rows (all arms). Returns (names, a0, b, Design builder fn)."""
    pen = {**DEFAULT_PEN, **(pen or {}), **o.get("pen", {})}
    m = c.arm == arm
    D = build(c, m, arm, o)
    X = D.matrix()
    idx = np.where(m)[0]
    pos = np.full(len(c.y), -1)
    pos[idx] = np.arange(len(idx))
    trm = pos[tr][pos[tr] >= 0]
    p = np.array([pen[g] for g in D.groups])
    a0, b = gridge_fit(X[trm], c.ly[idx[trm]], p)
    return D, X, idx, pos, a0, b


def make_fp(c: Ctx, o: dict, pen: dict | None = None):
    def fp(tr, te):
        out = np.empty(len(te))
        for arm in ARMS:
            D, X, idx, pos, a0, b = fit_arm(c, arm, o, tr, pen)
            tem = pos[te]
            sel = tem >= 0
            out[sel] = np.exp(a0 + X[tem[sel]] @ b)
        return out
    return fp
