"""Engineered features for the commander models."""
from __future__ import annotations

import numpy as np

from load import col, STATS
from harness import ROWS

R = ROWS
P = col(R, "regular_price").astype(float)
S = col(R, "command_stars").astype(float)
ARM = col(R, "arm")
INF = (ARM == "infantry").astype(float)
CAV = (ARM == "cavalry").astype(float)
ART = (ARM == "artillery").astype(float)
ARMS = {"infantry": INF, "cavalry": CAV, "artillery": ART}
ONE = np.ones(len(R))
MEN_R = col(R, "regular_men").astype(float)
MEN_C = col(R, "commander_men").astype(float)
SIZE = MEN_C / MEN_R                       # >1 for the 70 bigger commander units
GUN_R = np.nan_to_num(col(R, "regular_guns").astype(float), nan=0)
GUN_C = np.nan_to_num(col(R, "commander_guns").astype(float), nan=0)
SIZECH = (SIZE != 1).astype(float)
REG = {k: col(R, "regular_" + k).astype(float) for k in STATS}
COM = {k: col(R, "commander_" + k).astype(float) for k in STATS}
D = {k: COM[k] - REG[k] for k in STATS}
CORPS = col(R, "corps_number").astype(float)
SIDE = col(R, "side")
CLASS = col(R, "unit_class")
TRAIN = col(R, "training_level")
FAC = col(R, "faction_key")
SPEED = col(R, "speed_tag")
DSTATS = ["morale", "melee_attack", "melee_defense", "charge_bonus", "accuracy", "reload_skill"]


def dummies(v, levels=None, drop_first=False):
    levels = sorted(set(v.tolist())) if levels is None else levels
    if drop_first:
        levels = levels[1:]
    return np.column_stack([(v == l).astype(float) for l in levels]), levels
