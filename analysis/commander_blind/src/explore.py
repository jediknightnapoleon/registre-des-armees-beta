from __future__ import annotations
import collections
import numpy as np
from load import load, col, STATS, FLAGS

rows = load()
n = len(rows)
P = col(rows, "regular_price"); C = col(rows, "commander_price")
s = col(rows, "command_stars")
print("n", n, "unique regular", len({r['regular_unit_key'] for r in rows}))
print("ratio C/P quantiles", np.percentile(C/P, [0,1,5,25,50,75,95,99,100]).round(3))
print("diff C-P quantiles", np.percentile(C-P, [0,1,5,25,50,75,95,99,100]).round(1))
print("stars counts", collections.Counter(s.tolist()))
for st in range(8):
    m = s == st
    if m.sum():
        print(f"star {st}: n={m.sum():4d} ratio med {np.median(C[m]/P[m]):.3f} mean {np.mean(C[m]/P[m]):.3f} sd {np.std(C[m]/P[m]):.3f} diff med {np.median(C[m]-P[m]):.0f}")
for a in ["infantry","cavalry","artillery"]:
    m = col(rows,"arm")==a
    print(a, m.sum(), np.median(C[m]/P[m]).round(3))
men_r = col(rows,"regular_men"); men_c = col(rows,"commander_men")
print("men differ", (men_r!=men_c).sum(), "ratio quantiles", np.percentile((men_c/men_r)[men_r!=men_c],[0,25,50,75,100]))
g_r = col(rows,"regular_guns"); g_c = col(rows,"commander_guns")
gm = ~np.isnan(g_r)
print("guns differ", (g_r[gm]!=g_c[gm]).sum())
print("rank depth differ", (col(rows,"regular_rank_depth")!=col(rows,"commander_rank_depth")).sum())
for st_ in STATS:
    d = col(rows,"commander_"+st_)-col(rows,"regular_"+st_)
    print(f"{st_:14s} changed {np.sum(d!=0):5d} dist {collections.Counter(d.tolist()).most_common(8)}")
for fl in FLAGS:
    a = col(rows,"regular_"+fl); b = col(rows,"commander_"+fl)
    print(f"{fl:26s} reg {int(a.sum()):5d} com {int(b.sum()):5d} gained {int(((b==1)&(a==0)).sum())} lost {int(((b==0)&(a==1)).sum())}")
print("cheap commanders C<0.5P:")
for r in rows:
    if r["commander_price"] < 0.6*r["regular_price"] or r["commander_price"]<100:
        print(" ", r["pair_id"], r["faction_key"], r["commander_name"][:60], r["command_stars"], r["regular_price"], r["commander_price"], r["regular_men"], r["commander_men"])
