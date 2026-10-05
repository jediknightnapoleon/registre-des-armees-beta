"""FINAL: evaluate the chosen candidates ONCE on the 20% holdout.

Each candidate is fitted on the full development set (all 5 folds) and scored on the
holdout. Refuses to run if out/holdout_done.json exists. Excluded (joke/placeholder) rows
are identified by the same rule as in development and scored separately."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import load_dev, load_holdout, metrics, TARGET, OUT, RESULTS  # noqa
from features import add_features, is_excluded  # noqa
from candidates import CANDIDATES  # noqa

FLAG = os.path.join(OUT, "holdout_done.json")
if os.path.exists(FLAG):
    sys.exit("holdout already evaluated; see " + FLAG)

dev = add_features(load_dev())
hold = add_features(load_holdout())
for d in (dev, hold):
    d["army_seg"] = d["faction_key"] + "|" + d["seg"]
    d["army_bt"] = d["faction_key"] + "|" + d["base_type"]
    d["army_one"] = d["faction_key"] + np.where(d["staff_general"] == 1, "|staff", "|unit")
dev = dev[~is_excluded(dev)].reset_index(drop=True)
exc = is_excluded(hold).values
print("holdout rows", len(hold), "excluded", exc.sum())

res, preds = {}, hold[["row_id", "unit_class", TARGET]].copy()
for name, (desc, make) in CANDIDATES.items():
    model = make(dev)
    p = np.asarray(model(hold), float)
    preds[name] = p
    m_clean = metrics(hold[TARGET][~exc], p[~exc])
    m_all = metrics(hold[TARGET], p)
    res[name] = {"desc": desc, "clean": m_clean, "all_in_scope": m_all}
    print(name, {k: round(v, 3) for k, v in m_clean.items()})

preds["excluded"] = exc
preds.to_csv(os.path.join(OUT, "holdout_predictions.csv"), index=False)
with open(FLAG, "w") as f:
    json.dump(res, f, indent=1)

rows = []
for name, r in res.items():
    c, a = r["clean"], r["all_in_scope"]
    rows.append(f"| {name}: {r['desc']} | {c['mae']:.1f} | {c['mape']:.2f} | {c['r2']:.4f} | "
                f"{a['mae']:.1f} / {a['mape']:.1f} / {a['r2']:.3f} |")
text = open(RESULTS).read()
text = text.replace("| model | holdout MAE | MAPE % | R² |\n| --- | --- | --- | --- |",
                    "| model | holdout MAE | MAPE % | R² | incl. excluded rows: MAE / MAPE / R² |\n"
                    "| --- | --- | --- | --- | --- |")
text = text.rstrip("\n") + "\n" + "\n".join(rows) + "\n"
open(RESULTS, "w").write(text)
