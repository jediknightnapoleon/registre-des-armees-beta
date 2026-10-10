# Task: a readable model of Army Corps unit prices

## Goal

Build the **most accurate model you can that a person can read**, predicting an Army
Corps unit's list price (`base_mp_cost`) from its other attributes. The data is
`data/ac_units.csv`, described in `DATA_DICTIONARY.md`. `RULES.md` explains how these
prices are used in the game (an army's total is reduced by formation rebates; the list
price itself is fixed per unit).

Work only from the files in this folder. Don't read anything else in the repository
(in particular nothing under `analysis/output/`, no other `analysis/*.py` or `*.md`, no
`docs/`), don't use outside knowledge of the game's pricing, and don't search the internet.

## Scope

- **Primary target:** regular units — rows with `is_general` = `false` (7 205 rows,
  238 armies). Rows with `unit_class` = `artillery_fixed` (7) are out of scope.
- **Secondary:** staff generals (`is_general` = `true`, `men_raw` 32 or 122; 283 rows) and
  combat-general versions of units (`is_commander_variant` = `true`; 5 628 rows). Model
  them if time allows; a combat general's price may use its regular unit's price (same key
  without the `_com_<n>` suffix, same army).
- You may split the data and fit **separate simple models per segment**, e.g. by unit type.

## What counts as "simple and readable"

**Allowed:** formulas (linear or regularised-linear over engineered features, any
transforms: logs, powers, splines, products, ratios, interactions); GAMs with 1-D or 2-D
shape functions shown as small tables or curves; decision trees of depth ≤ 5, rule lists of
≤ 30 rules, model trees (a shallow tree with a small formula per leaf); compact lookup
tables for categorical features, including per-army (or army × type) factors if you
regularise them. Rule of thumb: each segment's model fits on about one page (≈ 40
coefficients per segment plus lookup tables).

**Not allowed:** neural networks; random forests, gradient boosting or any ensemble; kNN;
kernel SVMs; anything that can't be written down and read.

## Evaluation protocol (fixed, so results compare with other work)

1. **Folds are given.** Column `fold` (1–5) holds the cross-validation fold of every
   in-scope row; use exactly these folds for every experiment (train on four, predict the
   fifth). Rows with an empty `fold` are out of scope or always-train rows: never score them.
2. **No leakage.** Any tuning (feature choice, hyperparameters, segment definitions,
   regularisation strength) uses the training folds only (nested CV), or is chosen on CV.
3. **Metrics.** Report **MAE in gold** (primary), **MAPE**, and **R²** on total price, mean ±
   sd over the 5 folds, per segment and overall (regular units: per arm — infantry, cavalry,
   artillery — and overall).
4. **Unseen-army test.** Column `corps_holdout` = 1 marks 17 armies (1 084 rows). For your
   final model(s), also fit on all rows of the *other* armies and predict these 17 armies'
   rows; report MAE / MAPE on them. This tests whether your model prices an army it has
   never seen.
5. **Baselines.** Start with the mean price per `unit_class`, and that mean scaled by unit
   size.

## Questions your report must answer

- The best readable model(s), **written out in full** so a reader could price a unit by hand.
- **How price depends on unit size** (number of soldiers / guns), class by class: is it a
  power law, does the curve bend, does it differ between unit types or training levels?
  Show the out-of-fold error by size band (e.g. < 40, 40–60, 60–80, 80–100, 100–140,
  140–180, 180–240, > 240 men_display; guns 1, 2, 3, 4, 5+) for your final model.
- **How price depends on the army** (`corps_number`, `corps_side`, the army itself).
- An error analysis: where the model misses most; whether misses cluster by army or type.

## Working rules

- **Folder:** work only in this folder — scripts in `src/`, outputs in `out/`. Use fixed
  seeds. Python: `py -3.13` with `PYTHONIOENCODING=utf-8` (numpy, scipy, scikit-learn;
  no pandas). Use at most 2 CPU processes at a time: the machine is shared.
- **Checkpoint as you go** (the session may end abruptly): after every experiment append a
  row to `RESULTS.md` (id, model and features in one line, segment, CV MAE ± sd, MAPE, R²,
  parameters, note); every few experiments update `NOTES.md` (what you learned, what's
  next). On (re)start, read both and continue; never redo finished experiments.
- **No git:** don't run git commands.

## Deliverables

- `REPORT.md` (written for a reader who knows the game but not statistics): the models in
  full, the metrics table (CV per arm and overall, plus the unseen-army test) against the
  baselines, the size and army findings, the error analysis, and limitations.
- `out/oof_predictions.csv`: one row per scored row — `faction_key`, `unit_key`, `fold`,
  and an out-of-fold prediction column per final model; plus `out/holdout_predictions.csv`
  for the unseen-army test.
