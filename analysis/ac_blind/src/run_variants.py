"""Run named model variants (per-arm log ridge, see models.py) through 5-fold CV.

Usage: py -3.13 run_variants.py E03a E03b ...   (skips ids already in RESULTS.md)
OOF predictions saved to out/pred_<id>.npy.
"""
from __future__ import annotations

import os
import sys

import numpy as np

from common import regular_units, OUT, ROOT
from harness import run_cv, report
from models import Ctx, make_fp

BASE = dict(size_mode="loglin", stat_mode="lin", speed_mode="onehot", cn_mode="onehot", side=True)

VARIANTS: dict[str, tuple[str, dict]] = {
    "E03a": ("E01 with men_raw for size (art: guns)", dict(BASE)),
    "E03b": ("E03a + log1p stats instead of linear", {**BASE, "stat_mode": "log"}),
    "E03c": ("E03a + linear and log1p stats", {**BASE, "stat_mode": "both"}),
    "E03d": ("E03c + log size^2", {**BASE, "stat_mode": "both", "size_quad": True}),
    "E03e": ("E03d + class-specific log size slope", {**BASE, "stat_mode": "both", "size_quad": True, "size_by_class": True}),
    "E03f": ("E03e + artillery calibre/range/reload + guns one-hot", {**BASE, "stat_mode": "both", "size_quad": True, "size_by_class": True, "art_feats": True, "art_size_onehot": True}),
    "E03g": ("E03f + speed as letter + per-letter digit slope (instead of one-hot)", {**BASE, "stat_mode": "both", "size_quad": True, "size_by_class": True, "art_feats": True, "art_size_onehot": True, "speed_mode": "letter_digit"}),
}

FULL = {**BASE, "stat_mode": "both", "size_quad": True, "size_by_class": True, "art_feats": True, "art_size_onehot": True}
VARIANTS.update({
    "E04a": ("E03f + per-army offset (ridge lam=1)", {**FULL, "army": True}),
    "E04b": ("E03f + faction_key codes (era nn, x-digit, r-letter)", {**FULL, "fk_codes": True}),
    "E04c": ("E03f + fk codes + per-army offset", {**FULL, "fk_codes": True, "army": True}),
    "E04d": ("E03f with corps_number as log(cn+2) instead of one-hot", {**FULL, "cn_mode": "log+2"}),
    "E04e": ("E03f with corps_number linear", {**FULL, "cn_mode": "linear"}),
    "E04f": ("E03f + per-army offset + per-army x class offset", {**FULL, "army": True, "army_class": True}),
    "E04g": ("E03f + stats x class interactions (log1p)", {**FULL, "stat_by_class": True}),
})
ARMY = {**FULL, "army": True}
VARIANTS.update({
    "E05a": ("E04a + unit_cap & division_id one-hot", {**ARMY, "placement": True}),
    "E05b": ("E04a + formation geometry (rank depth, drill set, density, spacings)", {**ARMY, "geometry": True}),
    "E05c": ("E04a + training x class one-hot", {**ARMY, "train_by_class": True}),
    "E05d": ("E04a + fk codes + side (already) ; army penalty 0.3", {**ARMY, "fk_codes": True, "pen": {"army": 0.3}}),
    "E05e": ("E04a, army penalty 3", {**ARMY, "pen": {"army": 3.0}}),
    "E05f": ("E04f with army x class penalty 2", {**ARMY, "army_class": True, "pen": {"armycls": 2.0}}),
    "E05g": ("E04f with army x class penalty 10", {**ARMY, "army_class": True, "pen": {"armycls": 10.0}}),
})
AC = {**ARMY, "army_class": True, "pen": {"armycls": 2.0}}
VARIANTS.update({
    "E06a": ("E05f + log1p stats x class (pen 5)", {**AC, "stat_by_class": True}),
    "E06b": ("E05f + abilities x class (pen 1)", {**AC, "bool_by_class": True}),
    "E06c": ("E05f with army x class penalty 1", {**ARMY, "army_class": True, "pen": {"armycls": 1.0}}),
    "E06d": ("E04a + army x arm offset (pen 1) instead of army x class", {**ARMY, "army_arm": True}),
    "E06e": ("E05f + geometry", {**AC, "geometry": True}),
    "E06f": ("no-army-table model: E03f + fk codes + abilities x class + stats x class", {**FULL, "fk_codes": True, "bool_by_class": True, "stat_by_class": True}),
})
AC2 = {**AC, "stat_by_class": True}
VARIANTS.update({
    "E07a": ("E06a + hinge spline in log men_raw (knots 60,100,150,220,320)", {**AC2, "size_spline": [60, 100, 150, 220, 320]}),
    "E07b": ("E06a + hinge spline (knots 60,100,150,220,320) + class-specific hinges (pen 1)", {**AC2, "size_spline": [60, 100, 150, 220, 320], "size_spline_by_class": [100, 220]}),
    "E07c": ("E07a without quadratic", {**AC2, "size_quad": False, "size_spline": [60, 100, 150, 220, 320]}),
    "E07d": ("E07a + cn as log(cn) instead of one-hot", {**AC2, "size_spline": [60, 100, 150, 220, 320], "cn_mode": "log+0"}),
})
S7 = {**AC2, "size_spline": [60, 100, 150, 220, 320], "cn_mode": "log+0"}
VARIANTS.update({
    "E08a": ("E07d + artillery projectile one-hot (pen 1)", {**S7, "art_proj": True}),
    "E08b": ("E07d + training-specific log size slope (pen 1)", {**S7, "size_by_train": True}),
    "E08c": ("E07d + infantry log range & log projectile damage", {**S7, "inf_range": True}),
    "E08d": ("E07d with stats x class pen 2 and army x class pen 1.5", {**S7, "pen": {"armycls": 1.5, "inter3": 2.0}}),
})
S8 = {**S7, "art_proj": True}
VARIANTS.update({
    "E09a": ("lean: E08a with log1p stats only (no linear stat terms)", {**S8, "stat_mode": "log"}),
    "E09b": ("lean: E08a without log size^2 (spline only)", {**S8, "size_quad": False}),
    "E09c": ("lean: E09a + E09b + no artillery guns one-hot", {**S8, "stat_mode": "log", "size_quad": False, "art_size_onehot": False}),
    "E09d": ("army-blind: E08a minus army tables, + fk codes", {**S8, "army": False, "army_class": False, "fk_codes": True}),
})
S9 = {**S8, "size_quad": False}
VARIANTS.update({
    "E10a": ("E09b with in-range knots per arm (inf 150,200,260,340; cav 100,130,170,230)",
             {**S9, "size_spline": {"infantry": [150, 200, 260, 340], "cavalry": [100, 130, 170, 230]}}),
    "E10b": ("E09b with in-range knots per arm (inf 120,150,180,220,280,360; cav 90,110,130,160,200,260)",
             {**S9, "size_spline": {"infantry": [120, 150, 180, 220, 280, 360], "cavalry": [90, 110, 130, 160, 200, 260]}}),
})


def done_ids() -> set[str]:
    p = os.path.join(ROOT, "RESULTS.md")
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as fh:
        return {ln.split("|")[1].strip() for ln in fh if ln.startswith("| E")}


def main(ids: list[str]) -> None:
    d = regular_units()
    c = Ctx(d)
    done = done_ids()
    for vid in ids:
        if vid in done and "--force" not in sys.argv:
            print("skip", vid)
            continue
        desc, o = VARIANTS[vid]
        p = run_cv(make_fp(c, o), d)
        report(vid, d, c.y, p, desc, params=str({k: v for k, v in o.items() if k not in BASE or BASE[k] != v}))
        np.save(os.path.join(OUT, f"pred_{vid}.npy"), p)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
