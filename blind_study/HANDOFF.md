# HANDOFF — blind unit-pricing study (for an AI agent continuing this work)

This file is written for another AI agent that has the data and this repository and needs
to understand, verify or extend the study. It covers: what was done and why, what was
found, where every number comes from, how to reproduce it, and what not to break.

Read in this order: this file → `REPORT.md` (deliverable, models written out in full) →
`RESULTS.md` (one row per experiment) → `NOTES.md` (working notes) → `TASK.md` /
`DATA_DICTIONARY.md` (the original brief). Repo-root `CLAUDE.md` holds the session rules.

---

## 1. Status in one paragraph

The study is **complete**. Goal (from `TASK.md`): the most accurate *readable* model of
`base_mp_cost` for the 12 552 Theatre-of-War + Custom rows of
`data/ntw3_units_analysis.csv`. Result: a two-stage, per-unit-type log-linear model with an
army price divisor. Best model **13c**: CV MAE 27.4 ± 0.6 gold, **holdout MAE 27.8**,
MAPE 8.9%, R² 0.979. Compact **18a**: holdout MAE 31.0. Simplest **18b** (no lookup tables):
holdout MAE 43.1. Baselines: 287.2 (global mean) and 226.9 (per-class). The 20% holdout has
been **used once and is now consumed**. After the report, the user asked follow-up
questions about specific armies; those analyses are in section 7 and `out/army_audit.md`.

## 2. Hard rules (do not break)

1. **Never regenerate or re-split the holdout.** `data/holdout_ids.csv` (2 510 `row_id`s)
   and `data/dev_folds.csv` (fold 0–4 for the 10 042 development rows) are fixed.
   `src/00_make_split.py` refuses to run if the holdout file exists.
2. **The holdout is consumed.** `src/90_holdout.py` was run once and refuses to rerun
   (`out/holdout_done.json`). Any new model selection must use CV on the development folds
   only; numbers computed on holdout rows from now on are descriptive, not a fresh test.
3. `row_id` = 0-based row position in the original CSV (all 25 668 rows, before filtering).
   Holdout and fold files key on it.
4. Session rules (`CLAUDE.md`): work only inside `blind_study/`; scripts deterministic,
   write to `out/`; append a row to `RESULTS.md` after every experiment; commit/push often.
5. Allowed model families (`TASK.md`): linear/regularised-linear over engineered features,
   GAMs, depth ≤ 5 trees, ≤ 30-rule lists, model trees, compact lookup tables; ≈ 40
   coefficients per segment. No ensembles, boosting, kNN, NNs.

## 3. Environment and quick start

```bash
pip install -r blind_study/requirements.txt   # numpy, pandas, scikit-learn
pip install tabulate                           # only for markdown tables in reports
cd blind_study
python3 src/91_export_final.py   # refits 13c/18a/18b on dev, writes out/model_*, prints
                                 # "max |hand - model|" (~1e-11 = exported tables reproduce model)
python3 src/94_army_audit.py     # rebuilds out/army_audit.md (post-study army analysis)
python3 src/error_analysis.py out/oof_13c.csv   # rebuilds out/error_analysis_oof_13c.md
```

- Tested with Python 3.11, pandas 3.0, numpy 2.4, scikit-learn 1.9. The CSV is UTF-8 with
  BOM and CRLF: read with `encoding="utf-8-sig"` (done in `src/common.py`; path constant
  `DATA`).
- Most experiment scripts run in ~1 minute. **Exception:** `src/13_select_run.py` (nested
  feature selection) took ~3 h on 4 cores. Its results are cached in `out/sel/*.json`; it
  skips cached jobs, so rerunning it is instant unless you delete the cache.
- **Side effect:** experiment scripts (`01_…` to `17_…`, `13_selected_eval.py`) append a
  new row to `RESULTS.md` every time they run. Re-running one duplicates its row; use
  `git checkout RESULTS.md` if you only wanted to verify numbers.

## 4. Data facts the work relies on

- Scope: `faction_kind ∈ {theatre_of_war, custom}` → 12 552 rows (12 032 + 520).
  `army_corps` rows (13 116) are out of scope and were not used for fitting or features.
- **Exclusions (34 rows):** factions `aaa_lordz` ("1. Lordz" joke units, flat 9 500 gold;
  "Grumpy plebs" 500), `austria` (blank army name, exact copy of the Lordz units),
  `hannover` / `saxony` ("0. Placeholder B/A", one "Useless suicidal parasite" each at 3 360).
  Rule: `features.EXCLUDED_FACTIONS`. 28 in dev, 6 in holdout. Listed in `out/excluded_rows.md`.
- **Duplicates:** `group_id` = md5 of the 44 unit-attribute columns in `common.FEATURE_COLS`
  (no faction, name, placement or icon columns). 12 552 rows → 11 976 groups. Splits keep a
  group on one side.
- **Army number N:** regex `^(?:\[(\d{4})\]\s*)?(\d+)\.\s*(.*)$` on `army_corps_name`
  → `year`, `corps_n`. Blank only for the excluded `austria` rows (filled with 10).
- **Unit type:** `utype` = token 2–3 of `unit_key` (`ntw3_inf_line_…` → `inf_line`).
  Segments (`seg`) map `cav_missi→cav_light`, `art_fixed→art_foot`,
  `inf_irreg→inf_milit`, `gen_staff→staff`. Commander variants (`is_commander_variant`)
  have `unit_class = general`, so `seg` (from `unit_key`) is the only source of the type of
  the unit they lead. This was a deliberate judgment call (exp 06c: without it, +8.5 MAE).
- **Staff generals** = `is_general & !is_commander_variant` (229 dev rows). Without
  `command_stars` they cost 1 gold (rule, not fitted).
- `speed_code` is blank for the 4 `artillery_fixed` units (`[F0]`), so `speed_num` = 0 there.

## 5. Investigation process (what was tried, in order, and what it taught)

Experiment ids match `RESULTS.md` (CV MAE in gold on clean dev rows unless noted).

| step | exp | what | CV MAE | lesson |
| --- | --- | --- | --- | --- |
| 0 | 00 | fixed holdout + folds (stratified by class, grouped by duplicates) | – | – |
| 1 | 01–02c | baselines on all dev rows | 308 / 253 | Lordz/Placeholder rows distort everything |
| 2 | 02d–02e | baselines after excluding 34 sentinel rows | 284 / 229 | reference baselines |
| 3 | EDA | standalone general prices take a few exact values per star | – | price = V / d, d = N/10 from army name |
| 4 | 03 | log price ~ class + ln men + ln N | 212 | multiplicative structure confirmed |
| 5 | 04–05 | log-linear per base type, all stats, army offsets | 73 → 72 | stats matter; shared army offsets barely help |
| 6 | 06 | segment by `unit_key` type, commanders inside their unit's type | 51.2 | biggest structural gain |
| 7 | 07–08 | army offsets per type (army × type table) | 42.5 | army effect is type-specific |
| 8 | EDA | matched commander ↔ regular rows | – | commander price ≈ 0.9·regular + b(stars), additive |
| 9 | 09 | two-stage: regular model, then additive commander stage | 39.5 | explains near-free commanders; MAPE 13→9.5% |
| 10 | 10 | log1p stat transforms + men_raw + clamp inputs to train range | 32.0 | clamping stops exp() blow-ups (R² ±0.6 → 0.98) |
| 11 | 11 | commander slope per type / per star | 31.7 | star slopes small gain; per-type none |
| 12 | 12 | price-weighted least-absolute-deviation on log price (IRLS) | 28.6 | align loss with gold MAE |
| 13 | 14 | per-army additive commander premium | 27.7 | – |
| 14 | 15 | compact army tables (broad type / shared / none) | 35.0 / 38.3 / 41.8 | trade-off curve |
| 15 | 16–17 | sparse (L1) army × type table; ridge strength | 27.9 @ 308 cells | half the cells, same accuracy |
| 16 | 13 | nested greedy term selection per type (prune + add) | 27.3 / 27.4 | final formulas, 10–31 terms per type |
| 17 | 18 | compact variants on selected formulas | 30.7 (118 cells), 43.0 (none) | final candidates |
| 18 | holdout | 13c, 18a, 18b, 01, 02e scored once | 27.8 / 31.0 / 43.1 | CV and holdout agree |

Exploration that did **not** pan out (documented so you don't repeat it): residuals are not
explained by `unit_cap`, weapon/firearm, roster placement (`division_*`, `brigade_id`),
`year`, source corps number, roster counts per army × type, or formation columns. ToW
prices are not a rescaling of the matching `army_corps` unit price (log-ratio sd 0.17).
Exploratory gradient boosting (not allowed as a model) only reached log-residual sd ≈ 0.10
vs 0.15 linear on line infantry at the time, i.e. much of the remaining error looks like
unrecorded per-unit or per-army choices rather than missing non-linearity.

## 6. Final model structure (13c; 18a/18b share the form)

```
z      = c[type] + Σ_k β[type,k] · clamp(x_k, lo[type,k], hi[type,k])        # stage 1
p_reg  = exp(z) · M[army, type] · 10 / N                                   # M = 1 if absent
staff general without stars: price = 1;  with stars: z = c + β·ln(stars)
commander (s = min(stars, 5)):
price  = max(1, (a + a_star[s]) · p_reg + (b[s] + p_army[army]) · 10 / N)
```

- Stage-1 terms per type are in `out/model_<name>_stage1_<seg>.csv` (term, definition,
  coefficient, clamp range); army × type multipliers in `out/model_<name>_army_table.csv`
  (`offset` = ln M); commander coefficients in `out/model_<name>_commander.csv`.
  `REPORT.md` §4.3–4.5 has all of them as markdown.
- Fitting (`src/twostage.py`, `src/linmodels.JointLogLinear`): stage 1 is one joint
  ridge-penalised regression on log price with a fixed offset −ln(N/10), per-segment
  coefficient blocks, army × segment dummies (ridge `lam_f = 1e-4·n`; 13c/18a add an
  adaptive-ridge L1 so small cells become exactly 0), weights ∝ price, 10 IRLS iterations
  towards least absolute deviation. Rows < 50 gold are left out of stage-1 fitting.
  Stage 2 is least squares of commander price on [p_reg, star dummies / (N/10),
  p_reg × star dummies, army dummies / (N/10)], with p_reg from stage 1 on the commander's
  own row.
- Final configs: `src/candidates.py` and `src/91_export_final.py`
  (13c: `cv_army_lam=1e-3, l1_f=1e-5`; 18a: `l1_f=1e-4`; 18b: `lam_f=None`, no army terms).
  Specs per type: `out/sel/<seg>_all.json`; for CV fold k, `out/sel/<seg>_<k>.json`
  (selected without fold k).

## 7. Post-study follow-up analyses (asked by the user after the report)

All in `src/94_army_audit.py` → `out/army_audit.md`. Method: ratio = real price ÷ price
implied by stats, using **model 18b** (stat formulas + N/10, no army terms): out-of-fold
CV predictions for dev rows, holdout predictions for holdout rows, all 12 518 clean rows.
Single units are noisy (18b misses ~11% per unit); only army/type medians are meaningful.
These are descriptive and used the holdout rows after the holdout was consumed.

1. **N/10 applies to all rows, not only generals.** 85 pairs of identical regular units in
   armies with different N: (price ratio)/(N ratio) median 0.999; 52% within ±5%.
2. **General-level deviations from N/10 only sometimes carry to units** (armies whose
   generals follow N/10: regular-unit median 0.99, IQR 0.97–1.01):

   | army | generals vs N/10 | regular units vs stats | reading |
   | --- | --- | --- | --- |
   | 9. Heiliges Römisches Reich | ×1.14 | ×1.12 | whole army dearer (divisor 0.79 not 0.9) |
   | [1814] 9. Rossiya (Frantsiya) | ×1.03 | ×1.05 | whole army, slightly |
   | [1809] 10. UK, España, Portugal | ×1.58 | ×0.98 | **generals only** |
   | [1798] 8. France (Égypte) | ×0.94 | ×0.98 | generals only |
   | [1811] 9. UK, Portugal | ×0.94 | ×0.90 | units even cheaper |
   | France (Italie), France (Allemagne) 11., France (Prusse) 12. | ×0.92–0.96 | ×0.95–0.99 | partial / noise |

3. **[1809] 10. UK, España, Portugal:** all four standalone generals cost ×1.57–1.58 the
   standard N = 10 price (Wellington 1 746 vs 1 109; Beresford 250 vs 159; Cuesta and
   Silveira 95 vs 60). Wellington elsewhere: 1 022 in `[1815] 9. UK, Nederlanden` (×1.00),
   1 161 in `[1811] 9. UK, Portugal` (×0.94). Units: ×0.977, mid-pack among N = 10 armies
   (France (Espagne) ×0.969 is cheaper). Heavy cavalry ×1.17, line infantry ×0.955.
4. **[1811] 9. UK, Portugal:** regular units 3rd cheapest of 55 armies vs stats (×0.904;
   across armies median 0.99, 10th–90th pct 0.93–1.04), commanders 2nd cheapest (×0.884);
   84% of rows below stats; −10 900 gold vs stats over 253 rows, of which −10 700 from line
   + light infantry. British/Portuguese infantry by army: ×0.875 here vs 0.95–1.12 in every
   other British army. Cavalry, artillery, skirmishers normal.
5. **[1809] 7. Polska, sojusznicy:** overall ×0.97 (15th of 55), generals at formula, but
   lancers ×0.58 (next cheapest army ×0.84; most armies 0.95–1.03) and Cossacks ×0.50
   (other armies 0.85–1.23); 21 lancer rows carry −7 600 of the army's −9 300 gold gap.
   Dragoons slightly dear (×1.08–1.13).
6. Whether these are "unfair" or intentional balancing cannot be decided from the data;
   the data only shows price relative to listed stats.

## 8. Code map

| file | role |
| --- | --- |
| `src/common.py` | paths, `SEED`, `FEATURE_COLS`, `load_scope/load_dev/load_holdout`, `metrics`, `cross_validate`, `append_result`, `save_oof` |
| `src/features.py` | `add_features` (all engineered columns), `EXCLUDED_FACTIONS`, `is_excluded` |
| `src/linmodels.py` | `design` (feature spec → matrix), `LogLinear`, `ridge_solve`, `JointLogLinear` (segments, army offsets, clamping, weights, IRLS, L1) |
| `src/twostage.py` | `TwoStage` = stage 1 `JointLogLinear` + additive commander stage |
| `src/segsel.py`, `src/13_select_run.py` | greedy per-segment selection; nested job runner with cache `out/sel/` |
| `src/explore_*.py`, `src/err_breakdown.py` | exploration helpers (not logged experiments) |
| `src/00_…`–`src/18` (`13_selected_eval.py` holds 13a–c, 18a–c) | experiments; each appends to `RESULTS.md` and writes `out/oof_<id>.csv` |
| `src/candidates.py`, `src/90_holdout.py` | final candidates; one-shot holdout → `out/holdout_predictions.csv`, `out/holdout_done.json` |
| `src/91_export_final.py` | refit finals, write `out/model_*`, hand-pricing check |
| `src/92_worked_example.py` | `out/worked_example.md` |
| `src/93_build_report.py` | `REPORT.md` from `src/report_parts/{head,tail}.md` + `out/model_*.md` + `out/excluded_rows.md` |
| `src/94_army_audit.py` | post-study army analysis → `out/army_audit.md` |
| `src/error_analysis.py` | error tables for any oof/holdout csv |
| `src/export_model.py` | early helper, superseded by `91_export_final.py` |

`out/oof_<id>.csv` columns: `row_id, fold, unit_class, base_mp_cost, pred` (out-of-fold
prediction from that experiment). `out/holdout_predictions.csv`: one column per candidate
plus `excluded`.

## 9. Gotchas met along the way

- pandas 3: `df.astype(str)` keeps NaN as NaN (string dtype); build string keys per column
  with an explicit NaN → "NA" map (see `load_scope`).
- Log-linear fits extrapolate exponentially: always clamp inputs to the training range
  (`JointLogLinear(clip=True)`), and use a small ridge (`lam ≈ 1e-5·n`); with near-zero
  ridge, collinear log/linear pairs gave predictions of 30 000+ gold.
- Near-free commanders (1–49 gold) wreck log-scale fits; they are excluded from stage-1
  fitting (`lowcut=50`) but always predicted and scored.
- Early `RESULTS.md` rows report "41/seg" parameter counts that include columns constant
  within a segment; later rows count non-zero coefficients (≤ 36, final ≤ 31).
- In shell wait loops, `pgrep -f <script>` also matches the waiting shell's own command
  line; it never exits. Use a pid or a done-file instead.
- Stage-1 penalties are scaled by the number of rows (`pen = lam·n`); a 1e-2 army penalty
  over-shrinks small army × type cells (exp 08 vs 08e).

## 10. Open questions / possible next steps

- Commander stage: per-type slopes with shrinkage (bias by type: light-infantry
  commanders −13.5, cavalry commanders +11 to +15 gold in CV); cap star slopes so 5-star
  commanders on expensive units don't overshoot (holdout miss: Tecumseh +1 485).
- A small rule set for the 4 fixed-artillery `[F0]` units (largest CV miss, Havan topu +874).
- Whether the army × type effects (and the UK Portugal / Polska patterns) are deliberate
  balancing: needs information outside this dataset (game balance notes, gameplay data).
- Any new modelling must be validated on the development folds only; the holdout can no
  longer serve as an unbiased test.

## 11. Verification checklist (expected values)

| check | command | expected |
| --- | --- | --- |
| scope / split sizes | `python3 -c "import sys; sys.path.insert(0,'src'); from common import *; print(len(load_scope()), len(load_dev()), len(load_holdout()))"` | 12552 10042 2510 |
| exported tables reproduce models | `python3 src/91_export_final.py` | three lines, max diff ≈ 1e-11 |
| holdout results | `cat out/holdout_done.json` | 13c MAE 27.82, 18a 31.00, 18b 43.12 (clean rows) |
| CV of 13c (appends a row) | `python3 src/13_selected_eval.py 13c` | 27.4 ± 0.6, MAPE 7.04, R² 0.9849 |
| army audit | `python3 src/94_army_audit.py` | 85 pairs, median 0.999; tables as in §7 |
