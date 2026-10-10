"""Add the G-CV4 / G-CV5 (additive) combat-general OOF predictions to out/generals_oof.csv."""
import csv, os
import numpy as np
from common import load_raw, boolc, OUT
raw = load_raw()
cvi = np.where(boolc(raw["is_commander_variant"]))[0]
p4 = np.load(os.path.join(OUT, "pred_G-CV4.npy")); p5 = np.load(os.path.join(OUT, "pred_G-CV5.npy"))
m4 = {(raw["faction_key"][i], raw["unit_key"][i]): p4[j] for j, i in enumerate(cvi)}
m5 = {(raw["faction_key"][i], raw["unit_key"][i]): p5[j] for j, i in enumerate(cvi)}
path = os.path.join(OUT, "generals_oof.csv")
rows = list(csv.reader(open(path, encoding="utf-8")))
hdr = ["faction_key", "unit_key", "fold", "kind", "base_mp_cost", "pred_GST1_staff_or_GCV2_mult", "pred_GCV3_mult_on_M1_pred", "pred_GCV4_additive", "pred_GCV5_additive"]
out = [hdr]
for r in rows[1:]:
    k = (r[0], r[1])
    out.append(r[:7] + ([f"{m4[k]:.1f}", f"{m5[k]:.1f}"] if k in m4 else ["", ""]))
with open(path, "w", encoding="utf-8", newline="") as fh:
    csv.writer(fh).writerows(out)
print(len(out) - 1, "rows")
