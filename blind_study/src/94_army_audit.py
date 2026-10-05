"""Post-study army audit (descriptive, run after the holdout was used).

Answers follow-up questions about per-army pricing: does N/10 apply to units, which armies'
generals deviate from N/10 and whether their units follow, and which armies' units are
cheap/dear relative to their stats. "Implied by stats" = model 18b (per-type stat formulas
+ N/10, no army-specific terms): out-of-fold predictions for development rows
(out/oof_18b.csv) and holdout predictions (out/holdout_predictions.csv). Uses ALL clean
in-scope rows. Writes out/army_audit.md."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import load_scope, TARGET, OUT  # noqa
from features import add_features, is_excluded  # noqa

sc = add_features(load_scope())
sc = sc[~is_excluded(sc)]
L = ["# Army audit (descriptive, all clean rows)", "",
     "Ratios are real price ÷ price implied by stats (model 18b: stat formulas + N/10, no "
     "army terms). 18b misses single units by ~11% on average; read army/type medians over "
     "many units, not single rows. Rows under 50 gold are left out of ratio medians.", ""]

# 1. N/10 on identical regular units in armies with different N
reg = sc[(sc.is_commander_variant == 0) & (sc.staff_general == 0)]
pairs = []
for _, g in reg.groupby("group_id"):
    if g.corps_n.nunique() < 2:
        continue
    g = g.sort_values("corps_n")
    a, b = g.iloc[0], g.iloc[-1]
    pairs.append((a[TARGET] / b[TARGET]) / (b.corps_n / a.corps_n))
pairs = pd.Series(pairs)
L += ["## 1. Does N/10 apply to units?", "",
      f"Identical regular units (same feature hash) priced in armies with different N: "
      f"{len(pairs)} pairs; (price ratio) ÷ (N ratio): median {pairs.median():.3f}, "
      f"within ±5%: {(pairs.sub(1).abs() < 0.05).mean():.0%}.", ""]

# predictions of 18b for all clean rows
o = pd.read_csv(os.path.join(OUT, "oof_18b.csv"))[["row_id", "pred"]]
h = pd.read_csv(os.path.join(OUT, "holdout_predictions.csv"))
h = h[~h.excluded][["row_id", "18b"]].rename(columns={"18b": "pred"})
cols = ["army_corps_name", "corps_n", "seg", "is_commander_variant", "staff_general",
        "unit_name", "stars", TARGET]
p = pd.concat([o, h]).join(sc.set_index("row_id")[cols], on="row_id", how="inner")
p["r"] = p[TARGET] / p.pred
p["gap"] = p[TARGET] - p.pred
p["kind"] = np.where(p.staff_general == 1, "staff",
                     np.where(p.is_commander_variant == 1, "commander", "regular"))
q = p[(p[TARGET] >= 50) & (p.kind != "staff")]

# 2. general-derived divisor per army vs unit level
st = sc[(sc.staff_general == 1) & (sc.has_stars == 1)]
base = st[st.corps_n == 10].groupby("stars")[TARGET].agg(lambda s: s.mode().iloc[0])
dg = (st.stars.map(base) / st[TARGET]).groupby(st.army_corps_name).median()
t = pd.DataFrame({"N/10": sc.groupby("army_corps_name").corps_n.first() / 10,
                  "generals' divisor": dg})
t["generals vs N/10"] = t["N/10"] / t["generals' divisor"]
t["units vs stats"] = q[q.kind == "regular"].groupby("army_corps_name").r.median()
t["commanders vs stats"] = q[q.kind == "commander"].groupby("army_corps_name").r.median()
normal = t[(t["generals' divisor"] - t["N/10"]).abs() <= 0.02]["units vs stats"]
L += ["## 2. Armies whose standalone generals deviate from N/10", "",
      f"Standalone-general price at N = 10 by stars: {base.astype(int).to_dict()}.",
      f"Armies whose generals follow N/10: units vs stats median {normal.median():.3f}, "
      f"IQR {normal.quantile(.25):.3f}–{normal.quantile(.75):.3f}.", "",
      t[(t["generals' divisor"] - t["N/10"]).abs() > 0.02].round(3).to_markdown(), ""]

# 3. all armies ranked by unit level
A = q.groupby(["army_corps_name", "kind"]).r.median().unstack()
A["n"] = q.groupby("army_corps_name").size()
A["share below stats"] = q.groupby("army_corps_name").r.apply(lambda s: (s < 1).mean())
A["gold vs stats"] = q.groupby("army_corps_name").gap.sum()
A["rank (1 = cheapest units)"] = A.regular.rank().astype(int)
L += ["## 3. All armies: units and commanders vs stats", "",
      f"Across armies, regular-unit level: median {A.regular.median():.3f}, 10th–90th "
      f"percentile {A.regular.quantile(.1):.3f}–{A.regular.quantile(.9):.3f}.", "",
      A.sort_values("regular").round(3).to_markdown(), ""]

# 4. focus armies
for army in ["[1809] 10. UK, España, Portugal", "[1811] 9. UK, Portugal",
             "[1809] 7. Polska, sojusznicy"]:
    s = q[q.army_corps_name == army]
    by = s.groupby(["seg", "kind"]).agg(n=("r", "size"), median=("r", "median"),
                                        gold=("gap", "sum")).round(3)
    stf = p[(p.army_corps_name == army) & (p.kind == "staff")]
    L += [f"## 4. {army}", "", by.to_markdown(), "",
          "Standalone generals:", "",
          stf[["unit_name", "stars", TARGET, "pred", "r"]].round(2).to_markdown(index=False), "",
          "Cheapest units vs stats:", "",
          s.sort_values("r")[["unit_name", "kind", "seg", TARGET, "pred", "r"]].head(8)
          .round(2).to_markdown(index=False), ""]

# 5. cross-army comparisons for the flagged unit kinds
for title, mask in [
        ("Cossacks (name contains 'kazaki')", q.unit_name.str.contains("kazaki", case=False)),
        ("All lancers (cav_lance)", q.seg == "cav_lance"),
        ("British/Portuguese line + light infantry",
         q.seg.isin(["inf_line", "inf_light"]) &
         q.unit_name.str.contains(r"\bFoot\b|Infantaria|Caçadores|Light Infantry", regex=True))]:
    c = q[mask].groupby("army_corps_name").r.agg(n="size", median="median")
    L += [f"## 5. {title}, by army (n ≥ 3)", "",
          c[c.n >= 3].sort_values("median").round(3).to_markdown(), ""]

# 6. Wellington everywhere
w = st[st.unit_name.str.contains("Wellington")].copy()
w["standard price"] = (w.stars.map(base) * 10 / w.corps_n).round(0)
w["ratio"] = (w[TARGET] / w["standard price"]).round(3)
L += ["## 6. Wellington in every army", "",
      w[["army_corps_name", "stars", TARGET, "standard price", "ratio"]].to_markdown(index=False), ""]

open(os.path.join(OUT, "army_audit.md"), "w").write("\n".join(L))
print("\n".join(L[:12]))
