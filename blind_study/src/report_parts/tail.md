## 5. Error analysis (model 13c)

Out-of-fold CV predictions (10 014 rows) and the holdout (2 504 rows); full tables in
`out/error_analysis_oof_13c.md` and `out/error_analysis_holdout_13c.md`
(`src/error_analysis.py`).

**By kind of row**

| kind | CV n | CV MAE | CV MAPE % | holdout n | holdout MAE | holdout MAPE % |
| --- | --- | --- | --- | --- | --- | --- |
| regular unit | 5 594 | 27.5 | 6.2 | 1 398 | 28.2 | 6.7 |
| commander variant | 4 191 | 28.7 | 8.5 | 1 047 | 28.9 | 12.3 |
| staff general | 229 | 3.5 | 0.4 | 59 | 0.9 | 0.9 |

**Where the misses are**

- **Price level.** Absolute error grows with price but relative error falls: CV MAE is
  17–18 gold below 400 gold, 38 at 700–1 000, 50 at 1 000–1 500 and 65 above 1 500, while
  MAPE drops from 13% (50–200 gold) to 3.6% (above 1 500). The 93 rows under 50 gold (mostly
  near-free commanders) have small absolute errors (median 2.7) but a MAPE of 89%; they
  inflate MAPE, not MAE.
- **Unit type.** Line and light infantry are priced best (regular `inf_line` CV MAE 17.5,
  5.1%; `inf_light` 21.3). The largest absolute misses are heavy cavalry (47 regular,
  42 commanders — but only 4% relative, they are expensive) and foot artillery (40, 8.4%).
  Skirmisher, militia and horse-artillery *commanders* have the worst relative errors
  (MAPE 16–57%): few rows, low prices, and the additive commander premium is least certain
  for them.
- **Commander stars.** Error grows with stars (CV MAE 26 at 0–1 star, 35 at 3, 47–49 at
  4–5) because high-star commanders are rare and expensive. The single largest holdout
  miss is a 5-star skirmisher commander, *Tecumseh* (`[1812] 7. UK (USA)`): predicted
  3 351, true 1 866 — the 5-star slope extrapolated onto an already expensive unit.
- **Training level.** `mob` and `poorly_trained` units are worst (CV MAE 40 and 34; holdout
  `mob` 58.5 with a +30 bias) — Cossack-type and irregular units whose stats spread widely.
- **Army.** Errors do cluster by army: `[1811] 7. España` is the worst army in both CV (MAE
  43.6) and holdout (41.4); the Russian armies are the best (`[1812] 10. Rossiya` 17.5).
  Armies with small N (5–7, i.e. prices ×1.4–2) have larger absolute errors simply because
  their prices are higher (N = 7: MAE 32.9; N = 10: 21.4). After the army table, the mean
  residual per army × type cell still explains 12% of the squared CV error, so army-level
  pricing quirks remain the largest structured source of error. Custom armies are slightly
  worse than Theatre-of-War ones (CV MAE 31.9 vs 27.3).
- **Unique units.** The biggest individual misses are one-of-a-kind units that sit outside
  their type's typical stats: the Ottoman mortar *Havan topu* (CV +874) and the Congreve
  rockets (holdout +581) — two of the four fixed-artillery `[F0]` units, which are priced with
  the foot-artillery formula, the *Württembergische Garde du Corps* (+540, and
  its commander +660), a camel regiment (*Régiment de dromadaires*, +514), and Wellington (a staff general whose army has a divisor of 0.64; −639 in CV).
- **No systematic bias** overall (CV mean error +0.4 gold; holdout +3.7), but some
  commander groups have a type-level bias (CV: light-infantry commanders −13.5, light/
  heavy-cavalry and lancer commanders +11 to +15), a sign that the commander slope differs
  a little by type; per-type commander slopes did not improve CV MAE (exp 11a/11b).

## 6. Limitations and judgment calls

- **`unit_key` type code.** Commander variants are labelled `general`, so the type of the
  unit they command is taken from the type code in `unit_key` (e.g. `inf_line`). Without
  it, CV MAE is ~8.5 worse (exp 06c). Nothing else is taken from `unit_key`, `unit_name`
  or other identifiers.
- **Army tables are lookups, not explanations.** They encode per-army price adjustments
  that no column explains. Model 18b shows what the stat formulas alone achieve (43 MAE,
  R² 0.96); 18a is the middle ground. The army tables can only price armies seen in
  training; an unseen army falls back to multiplier 1 and premium 0, i.e. model 18b.
- **Clamping.** Each input is clamped to the range seen in training for its type. This is
  part of the model (the ranges are in the tables) and is what keeps exp() from
  extrapolating wildly on rare units.
- **Out-of-scope rows.** The `army_corps` rows (13 116) were not used for fitting or
  features. A check on development data showed that Theatre-of-War prices are *not* a
  simple rescaling of the matching army-corps unit's price (log-ratio sd 0.17), so nothing
  is lost.
- **Selection.** Term selection per type was greedy (prune, then add), nested inside CV.
  Different folds picked overlapping but not identical terms; the final terms are those
  selected on all five development folds. Coefficients should be read jointly (log and
  linear versions of the same stat appear together), not one at a time.

## 7. Reproducing

Python 3 with numpy, pandas, scikit-learn (`requirements.txt`). All scripts are
deterministic and write to `out/`.

| step | script |
| --- | --- |
| holdout + folds (run once) | `src/00_make_split.py` |
| baselines | `src/01_baselines.py`, `src/02_clean_and_loglinear.py` |
| experiments 03–18 | `src/0x_…py`, `src/1x_…py` (one script per experiment group) |
| nested term selection (slow, ~3 h on 4 cores, resumable) | `src/13_select_run.py` |
| final candidates | `src/candidates.py`; CV: `src/13_selected_eval.py 13c 18a 18b` |
| holdout (once) | `src/90_holdout.py` |
| export written-out models + hand-pricing check | `src/91_export_final.py` |
| worked examples | `src/92_worked_example.py` |
| error analysis | `src/error_analysis.py out/oof_13c.csv` |
| this report | `src/93_build_report.py` |

Every experiment's CV row is in `RESULTS.md`; working notes are in `NOTES.md`.
