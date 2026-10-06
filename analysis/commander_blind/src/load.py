"""Shared loader for the commander blind study (csv + numpy only)."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "pairs.csv"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

STATS = ["morale", "melee_attack", "melee_defense", "charge_bonus", "accuracy",
         "reload_skill", "ammo", "range"]
FLAGS = ["can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
         "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
         "scares_enemies", "can_build_barricades", "guard_mode", "skirmish",
         "can_snipe", "pike_square"]


def load() -> list[dict]:
    with open(DATA, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in list(r.items()):
            if k.startswith(("regular_", "commander_")) and k not in (
                    "regular_unit_key", "commander_unit_key", "commander_name"):
                r[k] = float(v) if v != "" else np.nan
        r["command_stars"] = int(r["command_stars"])
        r["corps_number"] = int(r["corps_number"])
    return rows


def col(rows, k):
    return np.array([r[k] for r in rows])


def group_folds(rows, k=5, seed=0):
    """Grouped k-fold on regular_unit_key, deterministic."""
    keys = sorted({r["regular_unit_key"] for r in rows})
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(keys))
    fold_of = {keys[i]: j % k for j, i in enumerate(perm)}
    return np.array([fold_of[r["regular_unit_key"]] for r in rows])
