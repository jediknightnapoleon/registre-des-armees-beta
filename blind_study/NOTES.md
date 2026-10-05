# Working notes

## Status

- Holdout (20%, `data/holdout_ids.csv`) and 5 dev folds (`data/dev_folds.csv`) created by
  `src/00_make_split.py` — **fixed, never regenerate**. Both are stratified by `unit_class`
  and grouped by identical feature rows (`group_id` = hash of `FEATURE_COLS` in
  `src/common.py`).
- Experiments 01–06 done (see RESULTS.md). Best so far: **06b** (CV MAE 51.2).

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

## Next steps

- Feature engineering per segment: splines / log transforms of key stats, men interactions.
- Price additive vs multiplicative check for commander variants.
- Robust loss (fit on log but weight to MAE), calibration of exp() back-transform.
- Model trees (shallow tree + per-leaf formula) for artillery.
- Compact army table: N/10 + list of exceptions.

## Open questions

- Is using the unit_key type token acceptable? (It's a type code, not an id; reported both.)
