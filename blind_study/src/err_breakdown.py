"""Print error breakdown of an experiment's out-of-fold predictions: python err_breakdown.py 06b"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, TARGET, OUT  # noqa
from features import add_features  # noqa

pd.set_option("display.width", 250)
eid = sys.argv[1]
o = pd.read_csv(os.path.join(OUT, f"oof_{eid}.csv"))
dev = add_features(load_dev()).set_index("row_id")
o = o.join(dev[["seg", "is_commander_variant", "army_corps_name"]], on="row_id")
o["ae"] = (o.pred - o[TARGET]).abs()
o["lr"] = np.log(o.pred / o[TARGET])
t = o.groupby(["seg", "is_commander_variant"]).agg(n=("ae", "size"), mae=("ae", "mean"),
                                                    med_ae=("ae", "median"), lsd=("lr", "std"),
                                                    tot=("ae", "sum"))
t["share"] = t.tot / t.tot.sum()
print(t.drop(columns="tot").round(3).sort_values("share", ascending=False).to_string())
print("overall MAE", o.ae.mean().round(2), " low-price (<50) rows MAE share",
      (o.ae[o[TARGET] < 50].sum() / o.ae.sum()).round(3))
