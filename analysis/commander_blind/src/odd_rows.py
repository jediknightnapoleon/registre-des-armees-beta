"""List odd rows: size/gun changes, near-free commanders, flag gains."""
from __future__ import annotations
import numpy as np
from load import load, col
rows = load()
P = col(rows, "regular_price"); C = col(rows, "commander_price"); s=col(rows,"command_stars")
mr=col(rows,"regular_men"); mc=col(rows,"commander_men"); gr=col(rows,"regular_guns"); gc=col(rows,"commander_guns")
# baseline star-arm model to show expected
arm=col(rows,"arm")
size = (mr!=mc)
guns = (~np.isnan(gr))&(gr!=gc)
print("size changes", size.sum(), "gun changes", guns.sum(), "both", (size&guns).sum())
print("pid arm stars P C men_r men_c guns_r guns_c C/P menratio name")
for i in np.where(size|guns)[0]:
    r=rows[i]
    print(r["pair_id"], arm[i][:3], s[i], int(P[i]), int(C[i]), int(mr[i]), int(mc[i]), gr[i], gc[i], round(C[i]/P[i],3), round(mc[i]/mr[i],3), r["commander_name"][:50], r["faction_key"][-6:])
print("rank depth change:")
for i in np.where(col(rows,"regular_rank_depth")!=col(rows,"commander_rank_depth"))[0]:
    print(" ", rows[i]["pair_id"], rows[i]["regular_rank_depth"], rows[i]["commander_rank_depth"], size[i], guns[i])
sc_r=col(rows,"regular_scares_enemies"); sc_c=col(rows,"commander_scares_enemies")
print("scare gained:")
for i in np.where(sc_c>sc_r)[0]:
    print(" ", rows[i]["pair_id"], arm[i], s[i], P[i], C[i], rows[i]["commander_name"][:50])
print("stamina lost:", [rows[i]["pair_id"] for i in np.where(col(rows,"commander_has_stamina")<col(rows,"regular_has_stamina"))[0]])
