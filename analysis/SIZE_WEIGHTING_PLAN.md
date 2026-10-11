# Size-frequency weighting in the pricing fits — plan and progress

> **Resume here.** Approved 2026-10-11. Tick each step and add a log line after every step / finished run.
> Checkpoints: `analysis/.cache/size_weighting/` (re-runs skip finished ones). Python: `py -3.13`. No commits
> unless the user asks.

## Checklist

- [x] S0. Code: weights in unit_pricing (SIZE_WEIGHTING, size_weights, SliceData.w, fit_on), class_structure
      run_variant/fit_class_p args, team_values helpers, new analysis/experiments/size_weighting.py; sanity check (off = unchanged).
- [x] S1. Diagnostics: band share of current squared error vs share of units; weight + ESS tables.
- [x] S2. F6 × {a0.5c10, a1c10, a1} × {ac, tow} × 3 arms.
- [x] S3. V4 fixed-power screen × 3 variants × 2 datasets.
- [x] S4. V4 nested × 3 variants × 2 datasets (background, ~3 h).
- [x] S5. Report analysis/output/size_weighting_report.md (incl. ladder-replay test).
- [x] S6. Summary to the user.

## Log

- Plan approved. Variants: a0.5c10, a1c10, a1 (uncapped); baseline = existing cached V4/F6 (no unweighted re-run).

- S0 done: unit_pricing SIZE_WEIGHTING / SIZE_WEIGHT_BANDS / size_weights / kish_ess / SliceData.w (data_for) / fit_on weights (None when off → unchanged); class_structure.run_variant(fixed_p=); new analysis/experiments/size_weighting.py (diagnostics / run / report; checkpoints sw1_{ds}_{arm}_{model}_{mode}_{variant}.pkl; asserts slice folds = baseline V4 folds). Nested V4 checkpoints per arm (not per class: one parallel fold search per arm).
- S1 done → analysis/output/size_weighting_diagnostics.md. The per-size loss ALREADY over-weights the smallest units (AC artillery 1-gun: 4% of units, 24% of loss, bias +28%); uncapped a1 is extreme (AC cavalry 180-240 ×101, ESS 82 of 1715).
- S2+S3 launched (background, one process per variant, --workers 4): `run --model both --mode fixed --variant X`; logs analysis/.cache/size_weighting/logs/screen_X.log.

- S2+S3 done: 36 checkpoints (F6 + V4 fixed × 3 variants × 2 datasets × 3 arms). Report module analysis/experiments/size_weighting_report.py (+ team_values.v4_raw_and_oof(fitted=), replay_test(versions=)).
- S4 launched: `run --model V4 --mode nested --variant X --workers 5` (both datasets), logs analysis/.cache/size_weighting/logs/nested_X.log; resumable (re-run the same command; finished arms are skipped).

- Screen results (analysis/output/size_weighting_report.md, powers fixed): cavalry improves slightly everywhere (e.g. ToW V4 a1: balanced MAPE 6.86 → 5.84, MAE −0.3); infantry/artillery MAE worse (+1.5 … +8 gold) with modest balanced gains (best AC inf V4 a1: 13.03 → 11.64); F6 small balanced gains for artillery/cavalry; worst band bias (infantry 240+, ~30%) barely moves. a1c10 = a1 for artillery (no band hits the cap). Nested runs decide for V4.

- S4+S5 done (18 nested checkpoints; report rebuilt). Verdict: weighting does not fix the extremes. Nested V4: size powers barely move (only skirmishers 0.80 → 0.60); overall MAE worse for infantry (+2 … +6 gold) and artillery (+3 … +9), ~0 for cavalry; balanced MAPE gains small (best AC infantry a1 13.03 → 11.46, ToW cavalry a1 6.86 → 5.86; ToW infantry ≈ 0). Extreme bands' bias shrinks a few points (ToW inf 0-40 −7.7 → −3.9, 180-240 +9.4 → +3.9) at the cost of the 100-140 core (−2.7 → −5.4). 240+ militia stays ~+20–30% even uncapped: a form problem, not a weighting one. Replay: the removed part points the same way as harmonisation's (β +0.34 … +0.79), not significant (z 1.4–1.6). Not worth shipping; F6 (size bands) remains the better answer to the size problem.
- S6: summary given to the user.

- Follow-up (user, 2026-10-11): residuals may be real strength, not error — does weighting make mid-sized units more cost-effective? Value shifts (report): infantry 0-40 +2…+4.5%, mid −1…−3%, 240+ −2…−11%; cavalry small +1…2%, 140+ −1…−7%. Running analysis/experiments/size_weighting_builds.py (optimiser picks by size band for raw / quantity / quality / sb / 3 weighted sets, ToW + AC; checkpoints builds_*.pkl; log logs/builds.log) → analysis/output/size_weighting_builds.md.

- Build comparison done → analysis/output/size_weighting_builds.md. Weighted values pick almost the same sizes as raw/quantity: ToW infantry 100-140 share raw 8.2%, weighted 8.6–10.1%, vs quality 22.1% and sb 21.6%; AC infantry 100-140: raw 37.0%, weighted 36.5–36.6%, quality 41.3%, sb 43.1%. Cavalry/artillery shifts within a few points. Conclusion: weighting does not make mid-sized units more cost-effective; Quality / size bands already do, far more.

- Report written: analysis/SIZE_WEIGHTING_REPORT.md (+ analysis/HANDOFF.md §8 item 7). Experiment closed.

## Plan (copy)

# Plan: size-frequency weighting in the pricing fits (analysis)

### Context

The pricing models are fitted mostly to the common sizes. For AC infantry, 2 005 units are 100–140 models
against 13 at 240+; for cavalry, 2 units are 180–240. The result is that mid-sized units fit well and the
extremes poorly. Today we compensate downstream:
- size harmonisation (`cost_effective_builds.harmonise_by_size`, full / noise);
- the AC size-band model (F6).

The user asks to weight each unit's error by the inverse frequency of its size, so the size distribution is
"regressed out" in training.

**User's decisions:**
- **Weightings to compare:** tempered (α = 0.5), full inverse (α = 1) capped at 10×, and full inverse
  **uncapped**. No unweighted run: the existing cached V4 / F6 results are the baseline.
- **Models:** the ones the app uses — V4 (ToW/Custom values, AC Quantity) and the size-band model F6
  (AC Quality), on AC and ToW data.
- **Outcome:** analysis first; whether to ship to the app is decided afterwards.

**Facts from exploration:**
- **One fit path.** Every fit goes through `unit_pricing.fit_on` → `PriceModel.fit(..., weights=None)`.
- **Weights exist but go unused.** The fitter already supports row weights; only the LAD/IRLS path uses
  them.
- **The current loss already weights by size.** It is LS on cost/size, i.e. total-price LS × 1/size².
- **CV.** The CV MAE is unweighted. Folds are stratified by class|speed. Every band with ≥ 20 units already
  appears in every fold, so the folds need no change.

### Weights

- **Bands.** Per arm, use the ac_pricing size bands: models 40/60/80/100/140/180/240, guns 2/3/4/5. They are
  defined once in `unit_pricing` as `SIZE_WEIGHT_BANDS`; `ap.SIZE_BANDS` is not reused, because team_values
  patches it.
- **Formula.** w = (median band count / own band count)^α, from the whole slice's counts (sizes are
  features, so there is no leakage). Weights are normalised to mean 1 on the training rows; this is
  cosmetic, since κ is scale-invariant.
- **Variants:**
  - `a0.5c10`;
  - `a1c10`;
  - `a1` uncapped.
- **Tiny bands.**
  - For the capped variants, bands under 20 units merge toward the middle (cavalry 180–240 into 140+,
    infantry 240+ into 180–240).
  - Uncapped keeps all bands as the user asked, with merging only where a band would be empty in a
    training fold.
- **Weights multiply the existing per-size loss.** The loss does not switch to total-price LS, which would
  weight rows by size² and favour big units.
- **Reported per variant:** a weight table per band — count, weight, and the effective sample size (Kish).

### Code changes

**`analysis/unit_pricing.py`**
- `SIZE_WEIGHTING = None | {"alpha", "cap", "min_band"}`, added to `SHARED_SETTINGS`.
- `size_weights(size, kind, setting)`, returning the weights and the band table.
- `SliceData.w`, set by `data_for` when the setting is on.
- `fit_on` passes `w[rows]` (and multiplies it into the LAD IRLS weights). With the setting off it passes
  `weights=None`, unchanged.
- The worker pool captures settings when it starts, so the runs use one variant per process.

**`analysis/class_structure.py`**
- `run_variant(..., fixed_p=None, p_grid=None)` and `fit_class_p(..., grid=P_COARSE)`, passed through the
  job tuples. The defaults keep the cached results identical.

**`analysis/team_values.py`**
- `v4_raw_and_oof(..., run=None)` and `replay_test(..., versions=...)`, so a weighted run can be valued and
  replay-tested.

**New `analysis/experiments/size_weighting.py`**
- **CLI:** `--dataset ac|tow --arm --model V4|F6 --mode fixed|nested --variant a0.5c10|a1c10|a1 --workers`,
  plus `--report`.
- **Inputs:** slices and folds from the existing caches (AC `v1_s500_{arm}_slice`, ToW `..._tow_...`). It
  asserts the ToW folds equal those of the cs V4 checkpoint.
- **Baselines:** AC V4 `v1_s500_{arm}_v4`, ToW V4 `v2_{arm}_V4`, F6 `teams/sb_*`.
- **Checkpoints:** `analysis/.cache/size_weighting/sw1_{ds}_{arm}_{model}_{mode}_{variant}.pkl`. It never
  writes into the v1_/v2_ caches, and asserts `SIZE_WEIGHTING is None` in the old scripts' mains.

### Saving progress (in case a session limit hits)

- **First step:** copy this plan into `analysis/SIZE_WEIGHTING_PLAN.md` with a checklist and a log, before
  any code changes.
- **After every step and every finished run:** tick the checklist and add a log line with the numbers so
  far, so a fresh session can continue from the file alone.
- **Per-run checkpoints:** each run writes its own checkpoint (`analysis/.cache/size_weighting/sw1_*.pkl`)
  as soon as it finishes. A re-run skips finished checkpoints, so an interrupted batch resumes where it
  stopped.
- **Nested V4 runs:** these also save each class's fitted powers as they finish, so a run that dies midway
  keeps its finished classes.
- **Logs:** background runs write to `analysis/.cache/size_weighting/logs/`.
- **Report:** the report is built only from checkpoints, so it can be regenerated at any time.
- **No commits** unless the user asks.

### Run order (background; progress logged in `analysis/SIZE_WEIGHTING_PLAN.md`)

0. **Sanity check, not a run:** with the setting off, `fit_on` passes `weights=None` exactly as today. The
   baseline is the existing cached results; there is no separate unweighted run.
1. **Diagnostics** (no fitting): each band's share of the current squared error against its share of units,
   plus the weight and ESS tables.
2. **F6, the three variants** × 2 datasets × 3 arms. Minutes. F6's free band multipliers absorb band bias,
   so only the shared parameters move.
3. **V4 fixed-power screen,** the three variants (powers held at the cached unweighted values). Minutes.
4. **V4 nested** (powers re-searched under the weights) for all three weighted variants. ToW ≈ 40 min and
   AC ≈ 70 min per variant; two processes at a time, about 3 h in total.
5. **`--report`** → `analysis/output/size_weighting_report.md`, with per variant and model:
   - the per-band median out-of-fold residual % (bias) and MAPE — the table the user reads;
   - balanced MAPE (mean over bands) and the worst |band bias|, as fold-paired Δ ± SE against the cached
     unweighted baseline (same folds);
   - the overall unweighted MAE as a guardrail;
   - per-class size powers, the artillery constant, and the ESS;
   - corps-8 value ratios per band (weighted ÷ raw), beside full / noise / sb, to check whether weighting
     reproduces harmonisation;
   - the harmonisation still left on the weighted model's out-of-fold errors;
   - **the ladder-replay test, which decides:** full harmonisation's removed part predicted winning
     (+0.32, z 3.0), so a closer fit to price at the extremes might remove the same real signal.
6. **Summary:** the findings go to the user. Shipping a new value version to the app is a separate decision.

### Verification

- With weighting off, the code path is unchanged.
- The old caches and outputs are unchanged (git diff shows only new files plus the small API additions).
- `py -3.13 -m unittest tools.tests.test_build_web_data tools.tests.test_army_builder_rules` still pass.
- The report's baseline column equals the published V4 / F6 numbers.
- Every weighted run passes the paired-fold consistency asserts.
