"""Create the fixed 20% holdout and the 5 development folds. Run once.

Holdout: stratified by unit_class, grouped by identical feature rows (so a duplicate
unit is never on both sides). Implemented as one fold of a 5-fold
StratifiedGroupKFold with a fixed seed. Dev folds: StratifiedGroupKFold(5) on the rest.
"""
import os
import sys

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, os.path.dirname(__file__))
from common import load_scope, HOLDOUT, FOLDS, SEED  # noqa: E402

if os.path.exists(HOLDOUT):
    sys.exit(f"{HOLDOUT} already exists; the holdout is fixed. Refusing to re-split.")

df = load_scope()
print("scope rows:", len(df), "groups:", df["group_id"].nunique())

sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
dev_idx, hold_idx = next(sgkf.split(df, df["unit_class"], df["group_id"]))
hold = df.iloc[hold_idx]
dev = df.iloc[dev_idx].reset_index(drop=True)
print("holdout rows:", len(hold), f"({len(hold)/len(df):.1%})")
pd.DataFrame({"row_id": hold["row_id"].sort_values()}).to_csv(HOLDOUT, index=False)

sgkf2 = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED + 1)
fold = pd.Series(-1, index=dev.index)
for k, (_, te) in enumerate(sgkf2.split(dev, dev["unit_class"], dev["group_id"])):
    fold.iloc[te] = k
assert (fold >= 0).all()
pd.DataFrame({"row_id": dev["row_id"], "fold": fold}).sort_values("row_id").to_csv(
    FOLDS, index=False)

print(pd.crosstab(dev["unit_class"], fold))
print("holdout class share vs scope:")
print(pd.concat([hold["unit_class"].value_counts(normalize=True).rename("hold"),
                 df["unit_class"].value_counts(normalize=True).rename("scope")], axis=1))
assert not set(hold["group_id"]) & set(dev["group_id"])
