"""Shared data loading, grouping, folds and metrics for the blind pricing study.

All randomness uses SEED. The holdout ids (data/holdout_ids.csv) are created once by
00_make_split.py and never regenerated.
"""
import os
import hashlib
import datetime as dt

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "ntw3_units_analysis.csv")
HOLDOUT = os.path.join(ROOT, "data", "holdout_ids.csv")
FOLDS = os.path.join(ROOT, "data", "dev_folds.csv")
OUT = os.path.join(ROOT, "out")
RESULTS = os.path.join(ROOT, "RESULTS.md")
SEED = 20261005
TARGET = "base_mp_cost"

# Attributes that describe the unit itself (used to define "identical feature rows").
# Excludes identity, faction, roster placement and UI/icon columns.
FEATURE_COLS = [
    "unit_class", "men_raw", "men_display", "guns", "speed_code", "speed_entity_key",
    "rank_depth", "base_density", "close_formation_spacing_horizontal",
    "close_formation_spacing_vertical", "loose_formation_spacing_horizontal",
    "loose_formation_spacing_vertical", "unit_drill_set", "unit_training_level",
    "accuracy", "reload_skill", "ammo", "morale", "melee_attack", "melee_defense",
    "charge_bonus", "range", "weapon_key", "firearm", "projectile_key",
    "range_selection_method", "projectile_damage", "projectile_reload_time",
    "can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
    "has_guerrilla_deployment", "can_place_stakes", "can_place_mines", "scares_enemies",
    "can_build_barricades", "skirmish", "guard_mode", "can_snipe", "pike_square",
    "is_general", "is_commander_variant", "command_stars",
]


def load_scope():
    """All in-scope rows (theatre_of_war + custom), with a stable row_id and group id."""
    df = pd.read_csv(DATA, encoding="utf-8-sig", low_memory=False)
    df["row_id"] = np.arange(len(df))  # position in the original file
    df = df[df["faction_kind"].isin(["theatre_of_war", "custom"])].copy()
    parts = [df[c].map(lambda v: "NA" if pd.isna(v) else str(v)) for c in FEATURE_COLS]
    key = pd.concat(parts, axis=1).agg("|".join, axis=1)
    df["group_id"] = key.map(lambda s: hashlib.md5(s.encode()).hexdigest()[:12])
    return df.reset_index(drop=True)


def load_dev():
    """Development rows (scope minus holdout) with their fixed CV fold (0..4)."""
    df = load_scope()
    hold = set(pd.read_csv(HOLDOUT)["row_id"])
    dev = df[~df["row_id"].isin(hold)].copy()
    folds = pd.read_csv(FOLDS)
    dev = dev.merge(folds, on="row_id", how="left", validate="1:1")
    assert dev["fold"].notna().all()
    return dev.reset_index(drop=True)


def load_holdout():
    df = load_scope()
    hold = set(pd.read_csv(HOLDOUT)["row_id"])
    return df[df["row_id"].isin(hold)].reset_index(drop=True)


def metrics(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    mae = np.mean(np.abs(y - p))
    mape = 100 * np.mean(np.abs(y - p) / np.abs(y))
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return {"mae": mae, "mape": mape, "r2": 1 - ss_res / ss_tot}


def cross_validate(dev, fit_predict):
    """fit_predict(train_df, test_df) -> predictions for test_df (array).

    Returns (per-fold metrics DataFrame, out-of-fold predictions)."""
    oof = np.full(len(dev), np.nan)
    rows = []
    for k in sorted(dev["fold"].unique()):
        tr = dev[dev["fold"] != k]
        te = dev[dev["fold"] == k]
        p = np.asarray(fit_predict(tr, te), float)
        oof[te.index] = p
        m = metrics(te[TARGET], p)
        m["fold"] = k
        rows.append(m)
    return pd.DataFrame(rows), oof


def summarize(fm):
    return {c: (fm[c].mean(), fm[c].std(ddof=1)) for c in ["mae", "mape", "r2"]}


def append_result(exp_id, segment, model, fm, n_params, note):
    s = summarize(fm)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    row = (f"| {exp_id} | {now} | {segment} | {model} | "
           f"{s['mae'][0]:.1f} ± {s['mae'][1]:.1f} | "
           f"{s['mape'][0]:.2f} ± {s['mape'][1]:.2f} | "
           f"{s['r2'][0]:.4f} ± {s['r2'][1]:.4f} | {n_params} | {note} |")
    with open(RESULTS) as f:
        text = f.read()
    marker = "\n## Holdout"
    i = text.index(marker)
    head, tail = text[:i].rstrip("\n"), text[i:]
    text = head + "\n" + row + "\n" + tail
    with open(RESULTS, "w") as f:
        f.write(text)
    print(row)


def save_oof(exp_id, dev, oof):
    os.makedirs(OUT, exist_ok=True)
    out = dev[["row_id", "fold", "unit_class", TARGET]].copy()
    out["pred"] = oof
    out.to_csv(os.path.join(OUT, f"oof_{exp_id}.csv"), index=False)
