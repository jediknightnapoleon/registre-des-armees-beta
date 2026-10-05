"""Fit the final candidates (13c best, 18a compact, 18b simplest) on the full development
set — the exact models scored on the holdout — and write them out as readable markdown
(out/model_<name>.md) and CSV tables (out/model_<name>_*.csv). Also re-prices every dev
row "by hand" from the exported tables to check the write-up reproduces the model."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import TARGET, OUT  # noqa
from candidates import e13  # noqa

BOOL = {"can_form_square", "has_stamina", "is_shock_resistant", "can_inspire",
        "has_guerrilla_deployment", "can_place_stakes", "can_place_mines", "scares_enemies",
        "can_build_barricades", "skirmish", "guard_mode", "can_snipe", "pike_square"}
RAW = {"accuracy": "accuracy", "reload_skill": "reload_skill", "ammo": "ammo",
       "morale": "morale", "melee_attack": "melee_attack", "melee_defense": "melee_defense",
       "charge_bonus": "charge_bonus", "men_raw": "men_raw", "rank_depth": "rank_depth",
       "range0": "range", "projectile_damage0": "projectile_damage",
       "projectile_reload_time0": "projectile_reload_time", "guns0": "guns",
       "speed_num": "speed digit", "train": "training code",
       "close_formation_spacing_vertical": "close_formation_spacing_vertical"}
PROD = {"morale*accuracy": "morale × accuracy", "morale*melee_attack": "morale × melee_attack",
        "accuracy*reload": "accuracy × reload_skill",
        "melee_attack*charge": "melee_attack × charge_bonus",
        "melee_attack*defense": "melee_attack × melee_defense"}


def define(t):
    if t == "const":
        return "intercept"
    if t == "log_men":
        return "ln(men_raw)"
    if t == "log_men^2":
        return "ln(men_raw)²"
    if t == "log_stars":
        return "ln(command_stars)"
    if t.startswith("log_men*"):
        return f"ln(men_raw) × {RAW.get(t[8:], t[8:])}"
    if t in PROD:
        return PROD[t]
    if t.endswith("^2"):
        return f"{RAW.get(t[:-2], t[:-2])}²"
    if t.startswith("log_"):
        return f"ln(1 + {RAW.get(t[4:], t[4:])})"
    if "=" in t:
        c, v = t.split("=", 1)
        return f"[{c} = {v}]"
    if t in BOOL:
        return f"[{t}]"
    return RAW.get(t, t)


def export(name, kw):
    m = e13.mk("all", **kw).fit(e13.dev)
    st = m.stage1
    lines = [f"### Model {name}", ""]
    # stage 1 tables
    seg_tabs = {}
    for s in st.segs:
        rows = []
        for c in st.cols:
            if not c.startswith(s + ":"):
                continue
            t = c.split(":", 1)[1]
            b = st.coef[c]
            if t != "const" and abs(b) < 1e-12:
                continue
            binary = t in BOOL or "=" in t
            rows.append({"term": t, "x": define(t), "coef": b,
                         "lo": np.nan if (t == "const" or binary) else st.lo[c],
                         "hi": np.nan if (t == "const" or binary) else st.hi[c]})
        tab = pd.DataFrame(rows)
        seg_tabs[s] = tab
        tab.to_csv(os.path.join(OUT, f"model_{name}_stage1_{s}.csv"), index=False)
    # army offsets -> multipliers
    fac = [(c[4:].split("|")[0], c[4:].split("|")[1], st.coef[c]) for c in st.cols
           if c.startswith("fac:") and abs(st.coef[c]) > 1e-12]
    army_names = e13.dev.drop_duplicates("faction_key").set_index("faction_key")["army_corps_name"]
    if fac:
        ft = pd.DataFrame(fac, columns=["faction_key", "seg", "offset"])
        ft["multiplier"] = np.exp(ft["offset"])
        ft["army"] = ft["faction_key"].map(army_names)
        ft.to_csv(os.path.join(OUT, f"model_{name}_army_table.csv"), index=False)
        wide = ft.pivot(index="army", columns="seg", values="multiplier")
    else:
        ft, wide = None, None
    # commander stage
    cvc = m.cv_coef["all"]
    cvc.to_csv(os.path.join(OUT, f"model_{name}_commander.csv"))
    # ---- hand pricing check, purely from the exported tables ----
    d = e13.dev
    N = d["corps_n"].fillna(10).clip(lower=1).values
    z = np.zeros(len(d))
    from linmodels import design
    for s, tab in seg_tabs.items():
        msk = (d["seg"] == s).values
        if not msk.any():
            continue
        spec = st.fixed[s]
        X = design(d[msk], spec).fillna(0)
        zz = np.full(msk.sum(), tab.loc[tab.term == "const", "coef"].iloc[0])
        for _, r in tab[tab.term != "const"].iterrows():
            v = X[r.term].values
            if not np.isnan(r.lo):
                v = np.clip(v, r.lo, r.hi)
            zz += r.coef * v
        z[msk] = zz
    if ft is not None:
        off = ft.set_index(["faction_key", "seg"])["offset"]
        z += np.array([off.get((f, s), 0.0) for f, s in zip(d["faction_key"], d["seg"])])
    p = np.exp(z) * 10 / N
    p = np.where((d["staff_general"] == 1) & (d["has_stars"] == 0), 1.0, p)
    cvm = (d["is_commander_variant"] == 1).values
    st_ = d["stars"].clip(upper=5).values
    a = cvc["a"] + np.array([cvc.get(f"a_star{int(k)}", 0.0) for k in st_])
    b = np.array([cvc[f"b{int(k)}"] for k in st_]) + np.array(
        [cvc.get(f"army[{f}]", 0.0) for f in d["faction_key"]])
    pc = np.maximum(1.0, a * p + b * 10 / N)
    hand = np.where(cvm, pc, p)
    model = m.predict(d)
    print(name, "max |hand - model| over dev rows:", float(np.max(np.abs(hand - model))))
    return m, seg_tabs, ft, wide, cvc


def fmt(x, nd=4):
    if pd.isna(x):
        return ""
    return f"{x:.{nd}g}" if abs(x) < 1e4 else f"{x:.0f}"


def md_model(name, seg_tabs, ft, wide, cvc):
    L = [f"## Model {name}", ""]
    for s, tab in seg_tabs.items():
        L += [f"#### Stage 1, type `{s}`", "", "| term | x | coefficient | clamp x to |",
              "| --- | --- | ---: | --- |"]
        for _, r in tab.iterrows():
            rng = "" if np.isnan(r.lo) else f"[{fmt(r.lo)}, {fmt(r.hi)}]"
            L.append(f"| `{r.term}` | {r.x} | {r.coef:.6g} | {rng} |")
        L.append("")
    L += ["#### Commander stage", "", "| coefficient | value |", "| --- | ---: |"]
    for k, v in cvc.items():
        if not k.startswith("army["):
            L.append(f"| {k} | {v:.4g} |")
    arm = {k[5:-1]: v for k, v in cvc.items() if k.startswith("army[")}
    if arm:
        names = e13.dev.drop_duplicates("faction_key").set_index("faction_key")["army_corps_name"]
        L += ["", "Per-army commander premium `p_army` (gold, before dividing by N/10):", "",
              "| army | p_army |", "| --- | ---: |"]
        for k, v in sorted(arm.items(), key=lambda kv: str(names.get(kv[0]))):
            L.append(f"| {names.get(k, k)} | {v:.1f} |")
    if wide is not None:
        cols = list(wide.columns)
        L += ["", f"#### Army × type multiplier table ({len(ft)} non-blank cells; blank = 1)", "",
              "| army | " + " | ".join(cols) + " |", "| --- |" + " ---: |" * len(cols)]
        for army, r in wide.sort_index().iterrows():
            L.append(f"| {army} | " + " | ".join("" if pd.isna(r[c]) else f"{r[c]:.3f}"
                                                for c in cols) + " |")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    from candidates import CANDIDATES  # noqa
    cfg = {"13c": dict(cv_army_lam=1e-3, l1_f=1e-5), "18a": dict(cv_army_lam=1e-3, l1_f=1e-4),
           "18b": dict(lam_f=None)}
    for name, kw in cfg.items():
        m, seg_tabs, ft, wide, cvc = export(name, kw)
        open(os.path.join(OUT, f"model_{name}.md"), "w").write(md_model(name, seg_tabs, ft, wide, cvc))
