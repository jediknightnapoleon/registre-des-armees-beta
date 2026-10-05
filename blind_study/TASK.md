# Task: an explainable model of unit price

## Goal

Build the **most accurate model you can that a person can read**, predicting a unit's
price (`base_mp_cost`) from its other attributes. The data is
`data/ntw3_units_analysis.csv`, described in `DATA_DICTIONARY.md`.

Work only from the data. Don't rely on outside knowledge of the game, and don't search
the internet for its pricing rules.

## Scope

- Use every row with `faction_kind` equal to `theatre_of_war` or `custom`: 12 552 rows,
  generals included.
- You may split the data and fit **separate simple models per segment**, for example by
  unit type. Every in-scope row must still get a prediction.
- If you decide some rows are not real data and exclude them, justify it and list them in
  the report.

## What counts as "simple and readable"

**Allowed:**

- **Formulas.** Linear or regularised-linear models over engineered features, with any
  transforms (log, powers, splines, products, ratios, interactions).
- **GAMs.** Additive models made of 1-D or 2-D shape functions that can be shown as small
  tables or curves.
- **Trees and rules.** Decision trees of depth ≤ 5, rule lists of ≤ 30 rules, and model
  trees (a shallow tree with a small formula per leaf).
- **Lookup tables** for categorical features, kept compact.

As a rule of thumb, each segment's model should be writable on about one page: roughly
40 coefficients or fewer per segment, plus lookup tables.

**Not allowed:** neural networks; random forests, gradient boosting, bagging or any other
ensemble; kNN; kernel SVMs; anything else that can't be written down and read.

## Evaluation protocol

1. **Holdout.** At the very start, split off a **20% holdout** (fixed seed, stratified by
   `unit_class`), save the row ids to `data/holdout_ids.csv`, and **don't look at it again**
   until the end.
2. **Development.** Do all development with **5-fold cross-validation** on the remaining
   80%, using a fixed seed and the same folds for every experiment. Keep identical feature
   rows in the same fold, so a duplicate unit can't appear in both train and test.
3. **No leakage.** Any tuning (feature choice, hyperparameters, segment definitions) uses
   training folds only (nested CV), or is selected on CV and then confirmed on the holdout.
   The holdout is the final judge.
4. **Metrics.** Report **MAE in gold** (primary), **MAPE**, and **R²** on total price, as
   the mean ± sd over folds.
5. **Baselines.** Start with two:
   - the global mean;
   - the mean price per `unit_class`, scaled by unit size if that helps.
6. **Finish.** Evaluate your best 2–3 readable models **once** on the holdout.

## Checkpointing (required: the session may end abruptly)

- Keep every experiment's code in `src/` as rerunnable, deterministic scripts.
- **After every experiment**, append one row to `RESULTS.md`:
  - id and timestamp;
  - model and features (one line);
  - segment;
  - CV MAE ± sd, MAPE, R²;
  - number of parameters;
  - one-line note.
- **After every few experiments**, update `NOTES.md`: what you learned, what you'll try
  next, open questions.
- **Commit and push after every experiment, or at least every 15 minutes**, so nothing is
  lost.
- **On (re)start:** read `NOTES.md` and `RESULTS.md` first, and continue from where they
  stop. Never redo finished experiments.

## Deliverable: `REPORT.md`

- The best readable model(s), **written out in full** as formulas, trees and lookup tables,
  so a reader could price a unit by hand.
- CV and holdout metrics, compared with the baselines, and how accuracy trades off against
  simplicity across your candidates.
- An error analysis: where the model misses most, and whether misses cluster by faction,
  unit type or anything else.
- Any rows excluded, and why.
