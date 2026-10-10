"""Render the final M1 model (all-data fit, coefs_M1_<arm>.csv from analysis.py) as markdown
tables a reader can price a unit from by hand: out/model_M1.md. Also verifies that the
rendered formula reproduces the model's predictions (worked examples)."""
from __future__ import annotations

import csv
import os

import numpy as np

from common import OUT, regular_units
from features import STATS, BOOLS
from models import Ctx

ARMS = ["infantry", "cavalry", "artillery"]


def load(arm):
    with open(os.path.join(OUT, f"coefs_M1_{arm}.csv"), encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        return {r["term"]: float(r["coef"]) for r in rd}


def fmt(v, nd=3):
    return "" if v is None else (f"{v:+.{nd}f}" if v != 0 else "0")


def main():
    d = regular_units()
    c = Ctx(d)
    L = []
    for arm in ARMS:
        cf = load(arm)
        classes = sorted({k.split("=")[1] for k in cf if k.startswith("class=")})
        L.append(f"\n### {arm.capitalize()} (M1)\n")
        L.append("log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed"
                 + (" + gun table + calibre terms" if arm == "artillery" else "")
                 + " + corps terms + army offset + army×class offset\n")
        hdr = "| term | " + " | ".join(cl.replace(arm + "_", "") for cl in classes) + " |"
        L.append(hdr)
        L.append("|---|" + "---|" * len(classes))

        def row(label, vals, nd=3):
            L.append(f"| {label} | " + " | ".join(fmt(v, nd) if v is not None else "–" for v in vals) + " |")
        row("constant (intercept + class)", [cf["intercept"] + cf.get(f"class={cl}", 0) for cl in classes])
        row("× log(size)" + (" [size = men_raw]" if arm != "artillery" else " [size = guns]"),
            [cf.get("log_size", 0) + cf.get(f"log_size:{cl}", 0) for cl in classes], 4)
        for k in [t for t in cf if t.startswith("hinge_log_size_")]:
            kn = k.split("_")[-1]
            row(f"× max(0, log(men_raw/{kn}))", [cf[k]] * len(classes), 4)
        for s in STATS:
            lin = cf.get(s)
            lg = cf.get(f"log1p_{s}")
            if lin is None and lg is None:
                continue
            if lin is not None:
                row(f"× {s}", [lin] * len(classes), 4)
            if lg is not None:
                row(f"× log(1+{s})", [lg + cf.get(f"log1p_{s}:{cl}", 0) for cl in classes], 4)
        for b in BOOLS:
            if b in cf:
                row(f"if {b}", [cf[b]] * len(classes))
        L.append("")
        # lookup tables
        tr = {k.split("=")[1]: v for k, v in cf.items() if k.startswith("train=")}
        L.append("Training level: " + ", ".join(f"{k} {fmt(v)}" for k, v in sorted(tr.items(), key=lambda t: t[1])) + "\n")
        sp = {k.split("=")[1]: v for k, v in cf.items() if k.startswith("speed=")}
        L.append("Speed code: " + ", ".join(f"{k} {fmt(v)}" for k, v in sorted(sp.items())) + "\n")
        if arm == "artillery":
            g = {k.split("=")[1]: v for k, v in cf.items() if k.startswith("guns=")}
            L.append("Gun-count table (add; 3 guns = 0; 5 = 5 or more): " + ", ".join(f"{k} guns {fmt(v)}" for k, v in sorted(g.items())) + "\n")
            pj = {k.split("=")[1]: v for k, v in cf.items() if k.startswith("proj=")}
            L.append("Projectile table: " + ", ".join(f"{k.replace('_shot', '').replace('cannon_', '').replace('_shell', ' shell')} {fmt(v)}"
                                                    for k, v in sorted(pj.items(), key=lambda t: t[1])) + "\n")
            L.append(f"Calibre/ballistics: × log(projectile_damage) {fmt(cf['log_pdmg'], 4)}; if howitzer/unicorn shell {fmt(cf['howitzer'])}; "
                     f"× log(range) {fmt(cf['log_range'], 4)}; × log(projectile_reload_time) {fmt(cf['log_prel'], 4)}\n")
        L.append(f"Army terms: × log(corps_number) {fmt(cf['log_cn_k'], 4)}; if empire {fmt(cf['empire'])}; "
                 f"plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.\n")
    with open(os.path.join(OUT, "model_M1.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    # ---- verification: rebuild prediction from the tables for a few units, compare to stored model
    off = {}
    with open(os.path.join(OUT, "army_offsets_M1.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            off[(r["faction_key"], r["arm"])] = float(r["offset_log"])
    offc = {}
    with open(os.path.join(OUT, "army_class_offsets_M1.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            offc[(r["faction_key"], r["unit_class"])] = float(r["offset_log"])
    rng = np.random.default_rng(0)
    print("\nWorked-example check (rebuilt from tables):")
    for i in rng.choice(len(c.y), 6, replace=False):
        arm = c.arm[i]; cl = c.cls[i]; cf = load(arm)
        v = cf["intercept"] + cf.get(f"class={cl}", 0)
        ls = np.log(c.size[i])
        v += (cf.get("log_size", 0) + cf.get(f"log_size:{cl}", 0)) * ls
        for k in [t for t in cf if t.startswith("hinge_log_size_")]:
            v += cf[k] * max(0.0, ls - np.log(float(k.split("_")[-1])))
        for s in STATS:
            x = c.stats[s][i]
            v += cf.get(s, 0) * x + (cf.get(f"log1p_{s}", 0) + cf.get(f"log1p_{s}:{cl}", 0)) * np.log1p(x)
        for b in BOOLS:
            if c.bools[b][i]:
                v += cf.get(b, 0)
        v += cf.get(f"train={c.train[i]}", 0) + cf.get(f"speed={c.speed[i]}", 0)
        if arm == "artillery":
            v += cf.get(f"guns={int(min(c.guns[i], 5))}", 0) + cf.get(f"proj={d.s('projectile_key')[i]}", 0)
            v += cf["log_pdmg"] * np.log(max(c.pdmg[i], 1)) + cf["howitzer"] * (c.rsm[i] in ("howitzer_shell", "unicorn_shell"))
            v += cf["log_range"] * np.log(max(c.rng[i], 1)) + cf["log_prel"] * np.log(max(c.prel[i], 1))
        v += cf["log_cn_k"] * np.log(c.cn[i]) + cf["empire"] * (c.side[i] == "empire")
        v_noarmy = v
        v += off.get((c.fk[i], arm), 0) + offc.get((c.fk[i], cl), 0)
        print(f"  {d.s('unit_name')[i][:40]:40s} {cl:20s} true {c.y[i]:6.0f}  rebuilt {np.exp(v):7.1f}  (without army tables {np.exp(v_noarmy):7.1f})")


if __name__ == "__main__":
    main()
