# Working notes

## Status

- Holdout (20%, `data/holdout_ids.csv`) and 5 dev folds (`data/dev_folds.csv`) created by
  `src/00_make_split.py` — **fixed, never regenerate**. Both are stratified by `unit_class`
  and grouped by identical feature rows (`group_id` = hash of `FEATURE_COLS` in
  `src/common.py`).
- Experiments 01–14 done (see RESULTS.md). Best so far: **14a** (CV MAE 27.7, MAPE 7.3%,
  R² 0.985): two-stage model (`src/twostage.py`), stage 1 fitted by price-weighted LAD on
  log price (IRLS), commander stage with star slopes + per-army premium.
- Exp 13 (nested per-segment feature selection) is running/ran via
  `src/13_select_run.py` (cached per job in `out/sel/<seg>_<fold>.json`, resumable: just
  rerun it); evaluate with `src/13_selected_eval.py`.

## Findings so far

1. **Excluded rows (34 in scope):** factions `aaa_lordz` ("1. Lordz", joke units at a flat
   9500, "Grumpy plebs" at 500), `austria` (no army name; an exact copy of the Lordz units),
   `hannover`/`saxony` ("0. Placeholder A/B", one "Useless suicidal parasite" each at 3360).
   Rule: `faction_key in EXCLUDED_FACTIONS` (`src/features.py`). Baselines were rerun on the
   clean set (02d/02e).
2. **Army divisor.** Prices are multiplicative: price ≈ V(unit) / d(army). d is a single
   number per army, nearly always N/10 where N is the leading number of
   `army_corps_name` ("[1812] 7. ..." → 0.7). Exceptions seen on standalone generals:
   11.→1.10–1.15, 12.→1.30, HRE 0.79, France (Italie) 0.94, UK Portugal 0.955,
   Rossiya (Frantsiya) 0.875, France (Égypte) 0.855, Preußen (Frankreich) 0.785.
3. **Standalone ("staff") generals:** 1 gold if no command stars, else ≈ 60.4·stars^1.4 / d
   (almost exact).
4. **Commander variants** (general attached to a unit, `unit_class = general`, 42% of rows):
   stats are the attached unit's stats with boosts by stars (morale +1/+1/+2/+2/+3/+3/+4 for
   0..6 stars). Price ≈ a·(regular unit price) + b(stars), b ≈ −60, −30, +20, +65, +120 (×d).
   Some commanders are near-free (1–49 gold, ~90 dev rows); they wreck log fits.
5. The underlying unit type of a commander variant is only available from the `unit_key`
   token (`inf_line`, `cav_heavy`, …). Using it (06b) beats speed-letter/drill-set proxies
   (06c) by ~8.5 MAE.
6. Remaining error is not explained by unit_cap, weapon, roster placement, source corps
   number; exploratory GBM (not allowed as model) reaches log-resid sd ≈ 0.10 vs 0.15 linear
   on line infantry → some nonlinearity left, but much is unexplained noise.

7. **Two-stage model (exp 09+).** Stage 1 prices regular units with one log-linear formula per
   unit type (11 types) + `-log(N/10)` + an army×type offset table; staff generals by
   `log stars`. Stage 2 prices commander variants additively from the stage-1 price of the
   commander's own row: `price = max(1, a·p_reg + b_stars/(N/10))` with **one global set of 7
   coefficients** (a ≈ 0.9). This explains the near-free commanders.
8. Army effects are **type-specific** (army×type table 55×12 beats a shared army table by
   ~6 MAE). No roster-count/cap/year driver found — they look like hand-set adjustments.
9. log1p transforms of the main stats + raw men help most segments; predictions must clamp
   features to training range (exp() extrapolation blew up artillery/militia otherwise).
   Ridge 1e-4..1e-5 (× n) is right.

10. Fitting loss matters: price-weighted LAD on log price (IRLS) beats plain least squares on
    log price by ~3.5 MAE (12c). Commander stage: star-specific slopes small gain (11c),
    per-army additive premium −0.9 MAE (14a).
11. Effective coefficients per stage-1 segment with RICH spec: 17–36 (constant flags drop out).

12. Nested per-type greedy selection (exp 13; prune RICH then add squares / men
    interactions / stat products / dummies) keeps 10–31 terms per type and gives the best
    CV: 13b 27.3, 13c (sparse army table, 328 cells) 27.4.
13. Accuracy vs. army-table size (selected formulas): 579 cells 27.3 · 328 cells 27.4 ·
    241 cells 27.9 · 118 cells 30.7 · none (N/10 only) 43.0. Broad-type tables (55×4) are a
    worse use of cells (35.0 with RICH formulas).

## Next steps

- Holdout candidates (decided on CV): **13c** (best, sparse 328-cell table), **18a**
  (compact, 118 cells), **18b** (simplest, N/10 only). Baselines 01 and 02e are scored on the
  holdout too for comparison. `src/candidates.py` + `src/90_holdout.py` (one shot).
- Then: error analysis (CV OOF of 13c + holdout), export final model, write REPORT.md.

## Open questions

- Is using the unit_key type token acceptable? (It's a type code, not an id; reported both:
  06c shows the cost of not using it.)
