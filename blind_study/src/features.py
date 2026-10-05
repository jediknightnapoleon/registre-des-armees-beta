"""Feature engineering shared by all experiments."""
import numpy as np
import pandas as pd

# Custom factions whose rows are not real price data (see NOTES.md / REPORT.md):
# '1. Lordz' joke units (flat 9500 / 500), an unnamed 'austria' copy of the same units,
# and the two '0. Placeholder' units (flat 3360).
EXCLUDED_FACTIONS = ["aaa_lordz", "austria", "hannover", "saxony"]

TRAIN_ORD = {"mob": 0, "poorly_trained": 1, "trained": 2, "well_trained": 3, "elite": 4}
BOOL_COLS = ["can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
             "has_guerrilla_deployment", "can_place_stakes", "can_place_mines",
             "scares_enemies", "can_build_barricades", "skirmish", "guard_mode", "can_snipe",
             "pike_square", "is_general", "is_commander_variant", "is_tow_variant"]
NUM_COLS = ["men_raw", "guns", "accuracy", "reload_skill", "ammo", "morale", "melee_attack",
            "melee_defense", "charge_bonus", "range", "projectile_damage",
            "projectile_reload_time", "rank_depth", "base_density",
            "close_formation_spacing_horizontal", "close_formation_spacing_vertical",
            "loose_formation_spacing_horizontal", "loose_formation_spacing_vertical",
            "command_stars"]


def is_excluded(df):
    return df["faction_key"].isin(EXCLUDED_FACTIONS)


def add_features(df):
    df = df.copy()
    x = df["army_corps_name"].str.extract(r"^(?:\[(\d{4})\]\s*)?(\d+)\.\s*(.*)$")
    df["year"] = pd.to_numeric(x[0])
    df["corps_n"] = pd.to_numeric(x[1])
    for c in BOOL_COLS:
        df[c] = df[c].astype(str).str.lower().eq("true").astype(int)
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["stars"] = df["command_stars"].fillna(0)
    df["has_stars"] = df["command_stars"].notna().astype(int)
    df["guns0"] = df["guns"].fillna(0)
    df["train"] = df["unit_training_level"].map(TRAIN_ORD)
    sc = df["speed_code"].fillna("")
    df["speed_letter"] = sc.str.extract(r"^([A-Z]+)")[0]
    df["speed_num"] = pd.to_numeric(sc.str.extract(r"(\d+)$")[0])
    df["staff_general"] = ((df["is_general"] == 1) & (df["is_commander_variant"] == 0)).astype(int)
    drill = df["unit_drill_set"].fillna("")
    df["base_type"] = np.where(drill.str.contains("artillery"), "art",
                      np.where(drill.str.contains("cavalry"), "cav", "inf"))
    df.loc[df["staff_general"] == 1, "base_type"] = "staff"
    # unit type code from unit_key (e.g. inf_line); for commander variants this is the type
    # of the unit the general is attached to
    df["utype"] = df["unit_key"].str.extract(r"^ntw3_([a-z]+_[a-z]+)_")[0]
    seg = df["utype"].replace({"cav_missi": "cav_light", "art_fixed": "art_foot",
                               "inf_irreg": "inf_milit", "gen_staff": "staff"})
    df["seg"] = seg
    df["cv_stars"] = df["stars"] * df["is_commander_variant"]
    df["log_men"] = np.log(df["men_raw"].clip(lower=1))
    df["log_n"] = np.log(df["corps_n"].fillna(10).clip(lower=1))
    for c in ["accuracy", "reload_skill", "ammo", "range", "projectile_damage",
              "projectile_reload_time"]:
        df[c + "0"] = df[c].fillna(0)
    return df
