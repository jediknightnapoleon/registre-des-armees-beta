"""Print a step-by-step hand pricing of example rows with model 18b (no lookup tables) and
13c, from the exported CSV tables."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, TARGET  # noqa
from candidates import e13  # noqa
from linmodels import design  # noqa


def show(name, row):
    d = e13.dev.loc[[row]]
    r = d.iloc[0]
    s = r["seg"]
    tab = pd.read_csv(os.path.join(OUT, f"model_{name}_stage1_{s}.csv"))
    m = e13.mk("all", **CFG[name]).fit(e13.dev)
    X = design(d, m.stage1.fixed[s]).fillna(0)
    print(f"\n### {name}: {r['unit_name']} — {r['army_corps_name']} (true price {r[TARGET]})")
    print(f"type {s}, commander={r['is_commander_variant']}, stars={r['stars']}, N={r['corps_n']:.0f}")
    z = tab.loc[tab.term == "const", "coef"].iloc[0]
    print(f"| term | x | clamped | coef | coef·x |\n| --- | ---: | ---: | ---: | ---: |\n| const | | | {z:.5g} | {z:.4f} |")
    for _, t in tab[tab.term != "const"].iterrows():
        v = X[t.term].iloc[0]
        vc = v if np.isnan(t.lo) else min(max(v, t.lo), t.hi)
        z += t.coef * vc
        if vc != 0:
            print(f"| {t.term} | {v:.4g} | {vc:.4g} | {t.coef:.5g} | {t.coef*vc:.4f} |")
    ap = os.path.join(OUT, f"model_{name}_army_table.csv")
    off = 0.0
    if os.path.exists(ap):
        at = pd.read_csv(ap)
        hit = at[(at.faction_key == r["faction_key"]) & (at.seg == s)]
        off = hit.offset.iloc[0] if len(hit) else 0.0
    print(f"\nsum z = {z:.4f}; army×type multiplier = {np.exp(off):.3f}")
    p = np.exp(z + off) * 10 / r["corps_n"]
    print(f"regular price = exp(z) × multiplier × 10/N = {np.exp(z):.1f} × {np.exp(off):.3f} × 10/{r['corps_n']:.0f} = {p:.1f}")
    if r["is_commander_variant"] == 1:
        c = pd.read_csv(os.path.join(OUT, f"model_{name}_commander.csv"), index_col=0).iloc[:, 0]
        k = int(min(r["stars"], 5))
        a = c["a"] + c.get(f"a_star{k}", 0.0)
        b = c[f"b{k}"] + c.get(f"army[{r['faction_key']}]", 0.0)
        pc = max(1.0, a * p + b * 10 / r["corps_n"])
        print(f"commander price = max(1, a·p_reg + (b{k} + p_army)·10/N) = max(1, {a:.4f}×{p:.1f} + {b:.1f}×10/{r['corps_n']:.0f}) = {pc:.1f}")
        p = pc
    print(f"model prediction {m.predict(d)[0]:.1f}")


CFG = {"13c": dict(cv_army_lam=1e-3, l1_f=1e-5), "18b": dict(lam_f=None)}
if __name__ == "__main__":
    dev = e13.dev
    reg = dev[(dev.seg == "inf_line") & (dev.is_commander_variant == 0) &
              (dev.army_corps_name == "[1812] 10. Rossiya")].index[0]
    cmd = dev[(dev.seg == "cav_light") & (dev.is_commander_variant == 1) & (dev.stars == 2)].index[0]
    for nm in ["18b", "13c"]:
        show(nm, reg)
        show(nm, cmd)
