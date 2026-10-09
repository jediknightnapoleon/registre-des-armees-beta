# HANDOFF — NTW3 unit-pricing analysis (for an AI agent continuing this work)

Read this before touching anything under `analysis/`. Then read:

1. `analysis/PRICING_MODEL_REPORT.md`: the model written out, its parameters and
   its limitations.
2. `analysis/output/unit_pricing_report.md`: every table from the current run.
3. The repository-root `CLAUDE.md`: game context, and the rule that this repo is
   the source of truth for NTW3 facts.

`docs/HANDOFF.md` is about the *app*. This file is only about the offline
pricing analysis, which the app does not use.

---

## 1. Status

- **Goal.** A readable formula that predicts `base_mp_cost` for ToW + Custom
  regular units and staff generals. It is validated by cross-validation. No
  black-box models: the user wants explainable structure, and prefers power
  laws and multipliers to splines where they do equally well.
- **Branch and commits.** Branch `analysis/unit-pricing`. The last commits are
  local and not pushed.

  | Commit | What |
  | --- | --- |
  | `20296282` | First analysis: dataset builder, linear and power models |
  | `2c5d1f4f` | Fitted stat powers, shape variants, artillery calibre spline |
  | `3e2593c7` | Adopted joint faction × class multiplier, staff T3 rule, parallel power search |
  | `880dd653` | Class-structure experiment (not adopted yet) |
  | *(this commit)* | `PRICING_MODEL_REPORT.md`, this file, refreshed module docstring |

- **Adopted model:** `FCLASS_FORM = ("JFC", "ls")` in `unit_pricing.py`. CV
  MAE: infantry 27.4, cavalry 34.9, artillery 32.4. Staff generals use T3
  (8.6, or 2.3 with the faction modifier).
- **Two model versions, both reported (user decision, October 2026):**
  - **Adopted model** (`unit_pricing.py`): shared stat coefficients per arm, so
    unit classes are comparable. Kept as the main model because of that.
  - **V4, the per-class alternative** (`class_structure.py`): its own formula
    and size power per class. More accurate (24.9 / 32.8 / 27.2), reported
    beside the adopted model in `PRICING_MODEL_REPORT.md` §6. Coefficients are
    in `analysis/output/class_structure_coefficients.csv`; it is not wired into
    `unit_pricing.py`.
  - The user decided **not** to test fully independent models per class (own
    power and structure search): too much overfitting risk on small classes for
    little expected gain.
- **Blind study.** It lives on branch `blind-pricing-study`
  (`blind_study/`, with its own `HANDOFF.md`). An untracked copy sits in the
  working tree at `blind_study/`. **Don't commit it to this branch.**
  `blind_ideas.py` reads `blind_study/out/` only to build one comparison table.

## 2. Hard rules

1. **Repo facts win.** Game data comes from `data/generated/ntw3_units_analysis.csv`.
   Never "correct" a stat or price from the web (see root `CLAUDE.md` §1).
2. **Don't change the folds silently.**
   - Folds come from a 500-seed split search per slice (`make_slice(...,
     n_seeds=500)`; the CLI default `--seeds 500`).
   - Every experiment driver rebuilds them the same way and asserts that it
     reproduces the committed out-of-fold predictions (`blind_ideas.check_regression`).
   - With `--seeds 5` or any other count you get *different* folds, and
     nothing compares.
3. **Defaults must reproduce the committed outputs.**
   - New model options go in as off-by-default `Spec` fields or arguments.
     Existing examples: `fixed_rating`, `fclass`, `kappa`, `loss`, `"uclass"`
     in `mult`, `extra_pinned`.
   - After a change, rerun the regression check: `final` and `RF` out-of-fold
     predictions must match `analysis/output/oof_predictions.csv` to its
     3-decimal rounding.
   - The unweighted ALS path in `PriceModel.fit` keeps the *exact* original
     arithmetic order. Floating-point reassociation changes the last digits,
     and with them tie-breaks.
4. **The adoption rule is 1 SE.**
   - A more complex variant must beat its reference by more than one
     standard error (paired over folds where the folds are shared).
   - Among models within one SE of the best, take the simplest.
   - Choices (powers, κ, exponents) are made inside training folds (nested).
     Don't report a non-nested number as the headline.
5. **Confirm before pushing.** Commit locally; push or open PRs only when the
   user asks. End commit messages with the `Co-Authored-By` line from the
   session's system reminder.

## 3. Environment and commands

- **Python and packages.** Python 3.13 (Windows Store build), numpy,
  scikit-learn. No pandas, no psutil.
- **Run from the repository root** with `PYTHONIOENCODING=utf-8`, or
  non-ASCII army names crash prints on cp1252.

| Command | Output | Time |
| --- | --- | --- |
| `python analysis/unit_pricing.py` | `analysis/output/` (spline artillery) | ~50 min with 6 workers |
| `python analysis/unit_pricing.py --artillery-cal projectile --out analysis/calibre_onehot_results` | cannon-type one-hot version | ~50 min |
| `python analysis/unit_pricing.py --linear --out analysis/linear_results` | historical fully linear model | shorter (no power search) |
| `python analysis/calibre_function.py` | `calibre_function_report.md` | ~12 min |
| `python analysis/blind_ideas.py` | `blind_ideas_report.md` | ~8 min |
| `python analysis/extreme_pinning.py` | `extreme_pinning_report.md` | ~5 min |
| `python analysis/class_structure.py [--fresh]` | `class_structure_report.md` | ~40 min; checkpoints in `analysis/.cache/`, resumable |
| `python analysis/export_optimiser_values.py` (then `tools/build_web_data.py`, then again with `--fixture`) | the in-app optimiser's data: `data/generated/ntw3_optimiser_values.csv`, `ntw3_optimiser_params.json`, the app's parity fixture (docs/HANDOFF.md §4.6) | ~15 s each |

- **Running two full runs.** Run them in parallel in the background: 2 × 6
  workers fits the 16-core machine. Watch the logs; the stages print
  `regression`, `profile`, `search`, `variant`, `adopted`, `fine`,
  `final models …`, `done`.
- **Use a quick smoke run before a long run** whenever report or output code
  changed. Monkeypatch the grids, then call `main`:

  ```python
  import sys; sys.path.insert(0, "analysis"); import unit_pricing as up
  up.POWER_GRID = (1.0,); up.MAX_PASSES = 1; up.FINE_PASSES = 0; up.P_GRID = (0.75, 1.0, 1.1, 1.3)
  sys.argv = ["x", "--seeds", "3", "--out", "<scratch dir>", "--artillery-cal", "spline"]
  up.main()
  ```

  This takes about 12 minutes and exercises every output path. It doesn't
  reproduce any number.

## 4. Data facts the code relies on

- **Scope.** ToW (`ntw3_tow_*`) and Custom factions.
  - Excluded factions: `aaa_lordz`, `austria`, `hannover` and `saxony`, which
    are joke or placeholder units.
  - `artillery_fixed` is excluded.
  - Commander variants (`unit_class = general` attached to a unit) are skipped by
    `unit_pricing.load`. They are priced separately by `commander_stage.py`, which
    pairs each with its regular counterpart (same army, unit key minus `_com_<id>`;
    all 5 238 match).
  - Staff generals are modelled separately.
- **Counts.** 4 370 infantry, 1 724 cavalry, 894 artillery and 288 staff
  generals (merged slice). Groups of identical feature rows are kept on one
  side of every split.
- **`rating` is the corps number N** that opens `army_corps_name`. It matches
  for every row; `load_ratings` reads it from the corps catalog. The 55
  factions in scope are 55 armies, so faction = army.
- **Size:**
  - Infantry and cavalry use models = `men_raw / 2`.
  - Artillery uses guns; crew per gun is fixed, 10 foot / 6 horse.
- **Speed** is parsed from the name tag (`[L3]`, `[GS2]`). GS is folded into
  S; camels are `DR` / `is_camel`. Four rows disagree with the pipeline's
  `speed_code` (listed in the report).
- **Artillery calibre:** use the projectile, never the name (root `CLAUDE.md`
  §4). The 64-pdr is a single unit and pinned to train, so it has no
  out-of-fold prediction.
- **Pinned rows.** A group that alone holds a one-hot level is pinned to train
  in every fold, so its out-of-fold prediction is NaN. Keep NaN handling when
  you add metrics.

## 5. Code map — `analysis/unit_pricing.py`

| Section | Contents |
| --- | --- |
| Loading | `load_ratings`, `load` → `Unit` / `Staff` dataclasses |
| Model specification | `Spec` (frozen): `linear`, `mult`, `const`, `extras`, `size`, `p`, `powers`, `faction`, `shape`, `fixed_rating`, `fclass`, `kappa`, `loss` |
| Design matrix | `build_design` (features φ(x), shape options for firearm / calibre / shooting, `class_linear`), `natural_spline_basis`, `spline_knots`, `factor_values` |
| Model | `PriceModel.fit`: ALS with optional IRLS weights, ridge on `GROUPING` factors, residual faction × class; `predict`, `n_params` |
| Splits | `pinned_groups`, `assign_folds`, `search_splits(…, extra_pinned)`, `repair`, `restrict` |
| Cross-validation | `CVRun`, `fit_on` (LAD via IRLS when `loss="lad"`), `cv_spec`, `make_slice(…, extra_pinned)` |
| Structure search | `enumerate_specs`, `structure_search` (each variable out / in β·x / in M) |
| Parallel workers | `parallel_map`, `WORKERS`, `SHARED_SETTINGS` |
| Stat powers | `descend_powers` (coarse), `refine_powers` (fine), `nested_powers`, `nested_fine` |
| Shape variants | `shape_variants`, `screen_variants`, `adopt_variant` (summation default), `ARTILLERY_CAL` |
| Faction modifiers | `shared_modifier`, `shared_faction_runs` |
| Faction × class | `FCLASS_FORM`, `residual_fclass_spec`, `joint_fclass_spec`, `inner_kappa`, `fold_run`, `fclass_cv`, `fclass_multiplier` |
| Staff generals | `staff_cv` (S1…TF3), `staff_power_fit` / `staff_power_price` (T3), `staff_full` |
| Main | Steps 1–8, listed below |
| Output | `write_coefficients`, `write_oof`, `report_lines`, `fclass_report` |

**What `main()` does, step by step:**

1. Regression check against the first model's numbers: 38.4983 / 60.5637 / 74.5768.
2. Size-power profile.
3. Structure search; 3b, linear-part ablations.
4. Shape variants with nested coarse powers; 4b, nested fine refinement.
5. Final model on every slice, plus `RF` (per-arm faction modifier), `RFs`
   (shared) and `FC` (adopted faction × class); 5b, packing check.
6. Poland check.
7. Imperial → coalition transfer.
8. Staff generals.

**Experiment drivers** (each imports `unit_pricing as up`, writes one report
to `analysis/output/`, and never changes committed outputs):

| Driver | Purpose |
| --- | --- |
| `calibre_function.py` | Smooth calibre functions vs the cannon-type one-hot |
| `blind_ideas.py` | Blind-study ideas; holds the hard-coded `FINAL` specs the other drivers import |
| `extreme_pinning.py` | Pin extreme units to train |
| `class_structure.py` | Class as a multiplier, per-class size power, per-class formulas; checkpointed |

> `blind_ideas.FINAL` duplicates the committed final specs (powers, p, shape).
> If a full rerun ever changes a final spec, update `FINAL` too. The regression
> assert in `blind_ideas.py` catches a mismatch.

## 6. Verification checklist (expected values)

| Check | Expected |
| --- | --- |
| Log line `regression` | 38.4983 / 60.5637 / 74.5768 |
| Nested variant MAE, `F0·SH0` | infantry 34.73, cavalry 59.89, artillery 58.41 |
| Final MAE (merged, `final`) | 34.62 / 59.24 / 49.70 |
| `FC` (adopted) | 27.42 / 34.87 / 32.42 |
| Staff T3, full fit | b = 76.55, q = 1.39 |
| Infantry and cavalry identical in `output/` and `calibre_onehot_results/` | yes, except `oof_final_faction_shared`, which is fitted across arms |
| Hand check | Bauditz line infantry (7. Danmark) = 287.246 from `coefficients.csv` variant `FC`; formula in `PRICING_MODEL_REPORT.md` §2.3 |
| `fclass_cv` with κ → ∞ | equals the fixed-8/N model to ~1e-8 (κ only shrinks) |
| Parallel vs serial | identical powers and out-of-fold predictions (`--workers 1` vs 6) |

## 7. Findings to build on

- **Prices look hand-set per corps per unit class.** The army × class table is
  the largest single gain (MAE 39.9 → 29.9 pooled). Identical units in armies
  with a different N price at exactly 1/N.
- **Size curve:**
  - Price is roughly proportional to size for 100–160-model infantry.
  - Tiny skirmisher units cost more than proportional: skirmishers scale at
    a power of about 0.8–0.9.
  - Units above about 180 models get a growing discount: the 487-model militia
    are at −30% and −73%. They are misfit even when trained on (training error
    ≈ test error), so it's the formula, not extrapolation. Pinning doesn't help.
- **Per-class size powers:** infantry grenadiers 1.3, line and light 1.2,
  militia 1.0, skirmishers 0.8–0.9; artillery horse 1.35–1.4 vs foot 1.2;
  cavalry flat at 0.7–0.8.
- **Least-absolute-deviation loss:** no overall gain. Under the *residual*
  faction × class form it degenerates: a single-unit cell fits exactly, and its
  IRLS weight explodes.
- **Calibre:** a df-5 natural spline in log range matches the cannon-type
  one-hot. A single power of damage cannot follow the drop below about 5 pdr.

## 8. Open next steps, in suggested order

1. **Only if the user asks: make V4 a pipeline model.** Add `Spec` support for
   per-class size powers (`class_p`) and per-class segmented designs. The
   `class_structure.py` functions `segmented` and `fit_class_p` are the
   reference.
   - Wire this into step 5 as an extra run *next to* `FC`, not replacing it: the
     user wants both versions.
   - Rerun both full outputs and update `PRICING_MODEL_REPORT.md`.
2. **Large-unit discount.** Militia above about 180 models need a size term that
   bends down. Test something readable before a spline, e.g. a capped or
   piecewise power on models, or a size knee for militia and mob. Judge it by
   the size-band residuals in `class_structure.py`'s table as well as MAE.
   Check whether `unit_cap` matters for these units: the Narod L3 is cap 1. The
   blind study found no overall cap effect.
3. **Re-tune the stat powers jointly with the adopted army × class form.** They
   were tuned before it.
4. **Commander variants: superseded by the commander blind study (October 2026).**
   `analysis/commander_blind/` (pairs from `build_commander_pairs.py`; brief `TASK.md`;
   result `REPORT.md`) was run by a fresh-context agent on unit ↔ commander pairs only.
   - Its best model prices commanders from the regular price **plus the general's
     actual stat changes** (morale, melee defence, charge, accuracy, reload).
   - It gets CV MAE 8.6 (fallback 10.4, minimal 11.9), against 31.2 for the
     stars-only form in `commander_stage.py`. Verified by re-running it and by
     stricter grouping.
   - Corps number matters only as a scale on the premium, not as a level.
   - The within-unit study (`commander_within_unit.py`) explains why stars alone
     fail (`PRICING_MODEL_REPORT.md` §7.3).
   - **Done (user's choice: the best 26-parameter model):** `commander_model.py`
     fits it on true regular prices (8.6) and, as the combined model, refits it on
     each base model's out-of-fold predicted price (V4 base 28.4, adopted 31.0;
     the refit gains only ~0.7 because base-model errors are unit-specific).
   - It also writes `analysis/output/price_database.csv`: every unit with its true
     price and every out-of-fold prediction. The user values this database.
   - `commander_stage.py` stays as the record of the rejected stars-only form.

   Earlier notes on `commander_stage.py`:
   - Its parameters are learned from *true* regular prices (the user's choice), so
     it is a standalone model; keep it that way.
   - The remaining chain error (40–46 vs 31 given the true price) is the
     regular-unit model's error carried through.
   - Commanders' individual stat boosts beyond their star level are not used. A
     natural extension: scale P by the regular-unit model's predicted ratio of
     the commander's boosted row to the regular row (this generalises the size
     scaling).
   - High-star commanders (4+) have large individual premiums.

   The original note, kept for reference: about 42% of ToW + Custom rows. Blind-study recipe:
   `price ≈ max(1, a·p_reg + b(stars)·10/N)`, with `p_reg` the regular price of
   the unit the general leads and one global set of 7 coefficients
   (a ≈ 0.9). Its CV error went 51 → 39 gold. Use our regular model as stage 1.
5. **Army Corps (non-ToW) prices.** They are out of scope so far. The blind
   study found ToW prices are not a rescaling of AC prices (log-ratio sd 0.17).

## 9. Gotchas

- **Windows multiprocessing uses spawn.**
  - Workers re-import the module and see only *default* globals.
    `SHARED_SETTINGS` copies the tunables into them. If you add a global that
    affects fitting and set it from the CLI or a monkeypatch, add it there.
  - Workers never open a pool of their own (`WORKERS = 1` inside a worker).
  - Driver scripts that use `parallel_map` need an `if __name__ == "__main__":`
    guard.
- **Line endings and edits.** `unit_pricing.py` uses CRLF line endings. Exact
  multi-line find-and-replace from LF strings fails silently on it; normalise,
  edit, write back CRLF. Keep the file all-CRLF.
- **The ALS iteration cap.** The joint faction × class fit with a free rating
  factor plus a faction factor converges slowly: nested factors with a weak
  ridge. The adopted `JFC` drops both, using the fixed 8/N divisor plus cells
  only, and converges in about 50–130 iterations.
- **Long runs.** `class_structure.py` V4 (per-class formulas plus per-class
  powers) is the slowest piece, about 35 minutes for infantry.
  - Checkpoints are versioned (`CACHE_VERSION`); bump it when a variant's
    definition changes, or pass `--fresh`.
  - A paused run (suspended processes) does not survive the end of a Claude
    Code session. Prefer checkpoints over pausing.
- **Comparing with the blind study.** It used its own holdout and folds. Compare
  on *our* rows via its `out/oof_*.csv` plus `holdout_predictions.csv`, keyed by
  CSV row index (`blind_ideas.blind_comparison`).
- **Watching runs.** Monitor or `tail -F` with a grep for the stage names *and*
  `Traceback|Error|exit`, so a crash is not silent.
