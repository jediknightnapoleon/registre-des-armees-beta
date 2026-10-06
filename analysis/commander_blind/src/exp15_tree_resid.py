"""Exp 15: (a) can a depth<=4 tree find structure left in J8's residuals?  (b) tree-only models for comparison."""
from __future__ import annotations
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from harness import cv_linear, fit_linear, metrics, log_result, Y, FOLDS
from features import *
from load import FLAGS, col

dmo, dma, dmd, dcb, dac, drl = (D[k] for k in DSTATS)
X8 = np.column_stack([P * INF, P * CAV, P * ART, INF, CAV, ART, P * dmo, P * dmd, P * dcb, P * dac, P * drl, MEN_R * dmo, S, CORPS * S, P * (SIZE - 1) * (1 - ART), P * (SIZE - 1) * ART])
CD, _ = dummies(CLASS); TD, _ = dummies(TRAIN)
FL = np.column_stack([col(ROWS, "regular_" + f).astype(float) for f in FLAGS])
Z = np.column_stack([P, S, CORPS, MEN_R, SIZE, INF, CAV, ART, CD, TD, FL, (SIDE == "imperial")] + [REG[k] for k in STATS] + [D[k] for k in DSTATS])
pred = np.empty(len(Y))
for f in range(5):
    tr = FOLDS != f
    b = fit_linear(X8[tr], Y[tr], "lad")
    res_tr = Y[tr] - X8[tr] @ b
    t = DecisionTreeRegressor(max_depth=4, min_samples_leaf=30, criterion="absolute_error", random_state=0).fit(Z[tr], res_tr)
    pred[~tr] = X8[~tr] @ b + t.predict(Z[~tr])
log_result("T1", "J8 + depth-4 tree on residuals (diagnostic)", 16 + 15, metrics(np.maximum(pred, 1)), notes="tree leaves ~16")
# tree on ratio C/P alone
pred = np.empty(len(Y))
for f in range(5):
    tr = FOLDS != f
    t = DecisionTreeRegressor(max_depth=4, min_samples_leaf=20, random_state=0).fit(Z[tr], Y[tr] - P[tr])
    pred[~tr] = P[~tr] + t.predict(Z[~tr])
log_result("T2", "C = P + depth-4 tree(C-P)", 16, metrics(np.maximum(pred, 1)), notes="16 leaves")

# --- inspect the residual tree on the full data
from sklearn.tree import export_text
names = ["P", "stars", "corps", "men", "size_ratio", "inf", "cav", "art"] + [f"class={c}" for c in sorted(set(CLASS.tolist()))] + \
        [f"train={c}" for c in sorted(set(TRAIN.tolist()))] + [f"flag_{f}" for f in FLAGS] + ["imperial"] + [f"reg_{k}" for k in STATS] + [f"d_{k}" for k in DSTATS]
b = fit_linear(X8, Y, "lad")
t = DecisionTreeRegressor(max_depth=4, min_samples_leaf=30, criterion="absolute_error", random_state=0).fit(Z, Y - X8 @ b)
txt = export_text(t, feature_names=names, decimals=1)
print(txt)
open("../out/residual_tree_J8.txt", "w", encoding="utf-8").write(txt)
