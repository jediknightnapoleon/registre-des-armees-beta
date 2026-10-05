"""Error analysis of out-of-fold (or holdout) predictions: python error_analysis.py <oof csv>
Writes a markdown summary to out/error_analysis_<name>.md"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import load_scope, TARGET, OUT  # noqa
from features import add_features  # noqa

path = sys.argv[1]
name = os.path.splitext(os.path.basename(path))[0]
o = pd.read_csv(path)
sc = add_features(load_scope()).set_index("row_id")
o = o.join(sc[["seg", "is_commander_variant", "army_corps_name", "faction_kind", "stars",
               "unit_training_level", "unit_name", "corps_n", "corps_side"]], on="row_id")
o["err"] = o.pred - o[TARGET]
o["ae"] = o.err.abs()
o["ape"] = o.ae / o[TARGET]
o["kind"] = np.where(o.seg == "staff", "staff general",
                     np.where(o.is_commander_variant == 1, "commander", "regular"))
o["band"] = pd.cut(o[TARGET], [0, 50, 200, 400, 700, 1000, 1500, 10000])
tot = o.ae.sum()


def tab(by, n=None, sort="share"):
    t = o.groupby(by, observed=True).agg(n=("ae", "size"), MAE=("ae", "mean"),
                                         median_AE=("ae", "median"),
                                         MAPE=("ape", lambda s: 100 * s.mean()),
                                         bias=("err", "mean"), share=("ae", "sum"))
    t["share"] = 100 * t["share"] / tot
    t = t.sort_values(sort, ascending=False)
    if n:
        t = t.head(n)
    return t.round(1).to_markdown()


lines = [f"# Error analysis: {name}", "", f"rows {len(o)}, MAE {o.ae.mean():.2f}, "
         f"MAPE {100*o.ape.mean():.2f}%, median AE {o.ae.median():.1f}", ""]
for title, by, n in [("By row kind", "kind", None), ("By unit type x kind", ["seg", "kind"], None),
                     ("By price band", "band", None), ("By faction kind", "faction_kind", None),
                     ("By army (top 15 by share)", "army_corps_name", 15),
                     ("By corps number N", "corps_n", None),
                     ("By command stars (commanders)", "stars", None),
                     ("By training level", "unit_training_level", None)]:
    lines += [f"## {title}", "", tab(by, n), ""]
worst = o.reindex(o.ae.sort_values(ascending=False).index).head(25)
lines += ["## 25 largest absolute errors", "",
          worst[["unit_name", "army_corps_name", "kind", "seg", TARGET, "pred", "err"]]
          .round(0).to_markdown(index=False), ""]
# residual by army within type: how much of the error is army-level?
g = o.groupby(["army_corps_name", "seg"]).err.transform("mean")
lines += [f"Share of squared error explained by army x type mean residual: "
          f"{1 - ((o.err - g) ** 2).sum() / (o.err ** 2).sum():.3f}", ""]
out = os.path.join(OUT, f"error_analysis_{name}.md")
open(out, "w").write("\n".join(lines))
print("\n".join(lines[:40]))
