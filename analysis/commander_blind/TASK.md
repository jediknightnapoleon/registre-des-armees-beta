# Blind study: how is a combat general's unit priced?

## Background

NTW3 (Napoleonic: Total War III) is a mod for *Napoleon: Total War*. In its
multiplayer armies, a **combat general** ("commander") can lead a regular unit. The
game sells that as a separate card: the commander version of the unit, with its own
price. Every commander card has a **regular counterpart**, the same unit in the same
army without the general.

`data/pairs.csv` holds all 5 238 such pairs from the game's own data: one row per
commander, with the regular unit and the commander version side by side.

## Goal

Find the model that best explains `commander_price` given the pair's other columns,
above all `regular_price`. It must be **readable**: a formula a person could apply by
hand, with a small number of parameters. Report what the data say about how the
game prices a commander.

You decide which inputs matter. Do not assume any of them are needed, including:

- command stars;
- the army's corps number (`corps_number`), which is already reflected in
  `regular_price`;
- unit size changes;
- stat changes;
- the army itself.

Show the evidence for each input you keep or drop.

## Rules

- **Data.** Use only `data/pairs.csv` and the column meanings in `DATA_DICTIONARY.md`.
  Do not read anything else in this repository, especially not `analysis/output/`,
  `analysis/*.md` or any other `analysis/*.py`. This is a blind study, and other
  files contain earlier models of the same thing.
- **Models.**
  - **Allowed:** linear and regularised-linear models over engineered
    features, small lookup tables, piecewise or segmented formulas, and simple
    trees or rule lists (depth ≤ 4).
  - **Not allowed:** ensembles, boosting, kNN or neural networks.
  - About 30 coefficients at most, unless a lookup table is clearly justified.
- **Validation.** 5-fold cross-validation with a fixed seed.
  - Folds are grouped so that **pairs sharing a `regular_unit_key` stay in the
    same fold**, because the same unit can appear with several generals.
  - Report MAE in gold (mean ± sd over folds), median absolute % error, and the
    number of parameters.
  - Prefer the simpler model when two are within one standard error.
- **Rows.** Look for odd rows before modelling (near-free commanders, large size
  changes). Say how you treat them, and keep every row in the reported error
  unless you justify leaving it out.
- **Work location.** Work inside `analysis/commander_blind/`. Scripts go in `src/`,
  outputs in `out/`. Keep a running log in `RESULTS.md`, one row per experiment.

## Deliverable

`analysis/commander_blind/REPORT.md` containing:

1. the best model as a formula, with every parameter value;
2. a simpler fallback model, if it is close in accuracy;
3. a table of the models you tried, with CV MAE, median APE and parameters;
4. the evidence on each candidate input, including whether the corps number,
   stars, size changes and stat changes matter once `regular_price` is known;
5. where the model fails: the worst pairs, and any pattern in them.
