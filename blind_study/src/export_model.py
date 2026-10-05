"""Write a fitted TwoStage model out as readable markdown (formulas + lookup tables) and
CSVs. export(model, dev, path_prefix)"""
import numpy as np
import pandas as pd

from common import TARGET

DEFS = {
    "log_men": "ln(men_raw)",
    "train": "training level code (mob 0, poorly_trained 1, trained 2, well_trained 3, elite 4)",
    "range0": "range (0 if blank)", "projectile_damage0": "projectile_damage (0 if blank)",
    "projectile_reload_time0": "projectile_reload_time (0 if blank)",
    "guns0": "guns (0 if blank)", "speed_num": "digit of speed_code (e.g. L3 → 3)",
    "log_stars": "ln(command_stars)",
}


def term_def(name):
    if name in DEFS:
        return DEFS[name]
    if name.startswith("log_") and not name.startswith("log_men"):
        base = name[4:]
        return f"ln(1 + {DEFS.get(base, base).split(' (')[0]})"
    if name.endswith("^2"):
        return f"({name[:-2]})²"
    if "=" in name:
        c, v = name.split("=", 1)
        return f"1 if {c} = {v} else 0"
    if "*" in name:
        a, b = name.split("*")
        return f"{DEFS.get(a, a)} × {b}"
    return name


def stage1_tables(m1):
    """Per-segment coefficient tables with clamp ranges."""
    out = {}
    for s in m1.segs:
        rows = []
        for c in m1.cols:
            if not c.startswith(s + ":"):
                continue
            t = c.split(":", 1)[1]
            b = m1.coef[c]
            if t != "const" and abs(b) < 1e-12:
                continue
            rows.append({"term": t, "definition": "intercept" if t == "const" else term_def(t),
                         "coefficient": b,
                         "clamp_min": np.nan if t == "const" else m1.lo[c],
                         "clamp_max": np.nan if t == "const" else m1.hi[c]})
        out[s] = pd.DataFrame(rows)
    return out


def army_table(m1, armies):
    """army x segment offsets (log scale), as a wide table."""
    rows = []
    for c in m1.cols:
        if c.startswith("fac:"):
            fk, seg = c[4:].split("|")
            rows.append((fk, seg, m1.coef[c]))
    t = pd.DataFrame(rows, columns=["faction_key", "seg", "offset"])
    w = t.pivot(index="faction_key", columns="seg", values="offset")
    w.insert(0, "army", armies.reindex(w.index).values)
    return w


def cv_table(model):
    return pd.concat({g: c for g, c in model.cv_coef.items()}, axis=1)
