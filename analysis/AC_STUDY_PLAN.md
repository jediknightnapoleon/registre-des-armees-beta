# AC unit-pricing study — plan and progress

> **Resume here.** The plan for the Army Corps pricing study (approved by the user,
> 2026-10-10), with a progress checklist updated after every step. A fresh session
> reads this file and continues with the first unticked step. Python: `py -3.13`
> (a bare Python 3.14 sits first on PATH). Long runs: background, checkpoints in
> `analysis/.cache/ac/`. No commits unless the user asks.

## Progress

- [x] **0. Plan saved** here.
- [x] **1. Discount rule write-up** — `analysis/AC_DISCOUNT_RULES.md` (lane B, subagent).
- [x] **2. AC list-price model** — `analysis/ac_pricing.py`: 2a adopted + V4, 2b corps number, 2c AC vs ToW, 2d generals, 2e AC-only hold-out (lane A).
- [x] **3. Unit size forms** — AC and ToW, same folds (lane A).
- [x] **4. Natural experiment** — AC ↔ ToW pairs (lane C, subagent); fair-price residual test after step 2.
- [x] **5. Effective prices** — `analysis/ac_discounts.py`, `analysis/output/ac/ac_price_database.csv` (lane B, subagent).
- [x] **6. Blind study** — `analysis/ac_blind/` (lane D, blind subagent; comparison after step 2).
- [x] **7. Report and docs** — `analysis/AC_PRICING_REPORT.md`, HANDOFF, README.

### Log

**Study complete (2026-10-10).** Report: `analysis/AC_PRICING_REPORT.md`; tables: `analysis/output/ac/ac_pricing_results.md`; price database: `analysis/output/ac/ac_price_database.csv`. All model/size runs finished (the session hit a usage limit after the last run finished; nothing was lost). Blind study verified by re-running its `src/final.py` on a copy (identical predictions). Next (user request): a plan for adapting the optimiser to AC — which 4 corps give the most cost-effective builds at a fixed team total of corps numbers.

- Step 0 done.
- Resumed 2026-10-10. Lanes B (steps 1+5) and C (step 4) relaunched as subagents. Lane A: `analysis/ac_pricing.py` written (AC scope/side swapped in only while loading — `unit_pricing.py` untouched, so ToW is unaffected; κ grid extended to 0.05–30 for AC because κ hit the ToW grid's 0.5 edge). 500-seed model runs launched per arm (`--phase model --arm …`, logs in `analysis/.cache/ac/run_*.log`) + staff phase (T3 refit b 82.99, q 1.340). Lane D: `analysis/ac_blind/` (TASK.md, RULES.md, DATA_DICTIONARY.md, data/ac_units.csv with our folds + 17-corps unseen-army test) written by `--phase blind-data`; blind subagent launched.
- Lane D (blind) done: `analysis/ac_blind/REPORT.md` etc. M1 (per-arm log ridge, piecewise size curve, shrunk army + army×class offsets): CV MAE inf 26.4 / cav 47.1 / art 47.3 (overall 34.1, MAPE 5.73%); unseen armies 64.2. Its size finding (S-shaped infantry curve, not one power law) independently matches ours. Verification re-run of `src/final.py` running on a scratch copy (to avoid appending to its RESULTS.md). `--phase database` and the blind comparison (report §7) written; run after the infantry runs finish.
- Lane C done (verified: re-run of `analysis/experiments/ac_natural_experiment.py` gives byte-identical CSVs): ToW copies sit on the stats price curve, AC originals ~10% above it with corps × class scatter; ToW removes ~75–81% of that premium (R² 0.61–0.71); rebates play no part (corr ≤ 0.09); no exact rounding rule for regulars; staff ToW price = V(stars)/N reproduces 66.5% exactly. Rule C (N ratio^0.977 × k[side,class] × premium terms): median error 4.8%, P90 14.5% on held-out corps. Outputs: `analysis/output/ac/natural_experiment_{report.md,pairs.csv,effects.csv}`, `ac_only_tow_equivalent.csv`. To redo with step 2's AC model as the stats curve.
- Lane B done (verified by re-running `analysis/ac_discounts.py`: all self-checks pass, exit 0): `analysis/AC_DISCOUNT_RULES.md`, `analysis/output/ac/ac_discounts.csv` (13 116 cards), `ac_corps_discounts.csv` (238 corps). Rebates: brigade median 2.96%, division 8.97% (completable 7.99%), full corps 9.97%. Lua/app differ only in the 5 artillery divisions; 3 small groups would show it in game. 91 divisions can't be completed legally. Remaining for step 5: join model predictions + ToW prices into `ac_price_database.csv`.
- Lane A progress: artillery model phase done; AC staff (b 82.99, q 1.34) and commanders done (`--phase commanders`: FS7 refit CV MAE 11.40, ToW coefficients 17.36, ratio baseline 89.23). Size phase (`--phase size --dataset ac|tow --arm …`, forms F0–F6) done for artillery AC+ToW (F6 bands per class best: AC 44.84 vs F0 57.98; ToW 25.74 vs F0 32.36, beats committed V4 27.15); ToW cavalry and infantry size runs started; infantry/cavalry model phases still running (v0p/v4 stage). `--phase report` written (→ `analysis/output/ac/ac_pricing_results.md`).
- (earlier) **Paused by the user (2026-10-10)** right after the plan was approved. Lanes B (steps 1 + 5) and C (step 4) had just been launched as subagents and were stopped before writing anything; no study files exist yet. To resume: start lane A (parameterise `unit_pricing.py` scope/side, then `analysis/ac_pricing.py`), and relaunch lanes B and C with the same briefs (steps 1/5 and 4 above).

---


## Context

The pricing model (`analysis/PRICING_MODEL_REPORT.md`) explains Theatre-of-War and Custom prices; **Army Corps prices are not modelled**. AC is the game's flagship mode: 238 corps, 7 205 regular units, 5 628 combat-general versions and 283 staff generals, corps numbers N = 3–13. AC builds also earn **formation discounts**, so a unit's list price is not what it effectively costs.

**User's scope:**
- **every AC corps**, including those that never made it into a ToW army (e.g. 1814 Eugène);
- first the AC price model and the discount rule;
- then a blind study, compared on the same folds;
- also: *try to model unit size more accurately*. The current single size power per class leaves a U-shaped error by size, which forced the size harmonisation in `cost_effective_builds.py`.

## What we already know (exploration, read-only)

**The discount rule, from the game's Lua** (`source/original lua files/ntw3.lua`):
- **Army price** (`ArmyPrice`, 420–429): Σ `MPCost`, minus `AC_DivisionBrigade_Bonus` for factions with `_ac_`.
- **Rebate per completed group** (`AC_DivisionBrigade_PriceCut`): `floor(Group.Cost/100 × (NbUnits − 1))`. `Group.Cost` = Σ cap × MPCost over the group's *full roster* (generals excluded), and `NbUnits` = Σ cap.
- **Completion:** a group is complete when the selected cards (combat generals counted) reach `NbUnits`. A full division replaces its brigades' rebates.
- **No rebate:** division 0 and untagged units.
- **German States:** ×1.5, but this never matches a shipped corps.
- **No per-corps or per-rating price multiplier exists anywhere** in the Lua or the tables. `multiplayer_cost` is stored per unit, so any 1/N scaling is baked into each unit's price. The corps number is only used for lobby team points (`Faction_Points`).
- **Consequence:** completing a group of total cap n gives exactly **(n − 1)% off** that group. A full 11-card division is 10% off.

**The app** (`web/src/rules/rules.ts` `calculateArmyCost` / `groupDiscount`, `tools/army_builder_rules.py`) mirrors this, plus three rules that are not in the Lua:
- **The recruit-order affordability rule** (`priceBuild`), observed in game.
- **Support divisions earn nothing** (`supportDivisions`).
- **The Davout 1812 brigade exception.**

The one real disagreement with the Lua: **5 fully tagged artillery divisions** (`a11_x5_117` d7, `a11_x5_123` d4, `a11_x7_126` d3 and d7, `b17_x7_281` d7) get no rebate in the app but would in the Lua. The study will **flag this for in-game verification, not change it**: the app documents its support rule as in-game behaviour.

**Data facts:**
- **AC follows ~1/N.** log N has coefficient −0.91 in a stats regression; ToW has −0.99.
- **Corps × class cells** explain 54% of the remaining AC residual, the same hand-set pattern as ToW.
- **Natural experiment:** every one of the 12 032 ToW rows is a copy of an AC unit, with identical stats, size and cap.
  - 6 593 regular, 5 183 commander and 221 staff pairs.
  - P_ToW ≈ P_AC × N_AC/N_ToW × 0.91: slope 0.97, residual sd 0.13.
  - Source-corps × class means explain 84% of that residual.
- **Already rejected:** "ToW = AC minus the unit's own brigade rebate". The correlation is 0.07 and the factor barely moves with brigade size.
- **Staff generals:** T3 refit on AC gives b 83, q 1.34. Seven 0★ AC staff generals cost 2 gold, not 1.
- **AC-only corps:** 17 AC corps (612 regular units) have no ToW copy at all; every other AC corps is copied whole. They are the two Eugène / Italie corps (6. and 11.), Wellington / Pyrenees, Soult / Pyrénées, Bellegarde / Italien, Cathcart / Hanover, Schwarzenberg / Böhmen, Kindelán / Florida, Suchet / Alpes, Essen / PA, Hessen-Kassel / DK, Kienmayer / Aufstand, La Romana / D.N, Moore / Baltic, Donzelot / Sept-Îles, Marmont / XI.C and D'Este / VII.K. Mostly low corps numbers (3–5), where prices are highest. They are in every part of the study; only the natural experiment (step 4) cannot pair them.

## Study design

**New code:**
- `analysis/ac_pricing.py`, reusing `analysis/unit_pricing.py` (`load`, `make_slice`, `cv_spec`, `Spec`, `fclass_cv`, `parallel_map`, `table`, `log`) and `class_structure.py` (V4 pieces);
- `analysis/ac_discounts.py`.

**Outputs:** `analysis/output/ac/`. **Report:** `analysis/AC_PRICING_REPORT.md`.

**ToW defaults stay untouched.** The AC scope and the side mapping are parameters, so ToW runs reproduce exactly. AC `corps_side` empire/coalition maps to imperial/coalition.

**0. Saved progress.** Copy this plan to `analysis/AC_STUDY_PLAN.md` with a checklist, ticked after every step (the user asked for resumable work). Long runs go in the background with checkpoints in `analysis/.cache/ac/`. No commits unless asked.

**1. Discount rule write-up.** `analysis/AC_DISCOUNT_RULES.md` covers:
- the Lua formulas verbatim, with line numbers;
- the app's extra rules and where each comes from;
- the (n − 1)% consequence and a worked example (the verified 5 645-gold test build);
- the 5-division discrepancy list.

**2. AC list-price model (stats → price).** The same protocol as ToW: group folds, 5 folds, 500-seed search, MAE and MAPE per class.
- **2a. Refit on AC:**
  - the adopted form (fixed 8/N plus an army × class ridge, κ by nested CV);
  - V4, with per-class formulas and size powers.
- **2b. Corps number:** fixed 8/N against free per-N levels against N^−γ. N = 3, 4 and 13 occur only in AC.
- **2c. AC and ToW together:**
  - the ToW model applied to AC;
  - a joint fit with an AC/ToW indicator, per class.
  This shows whether the two use one pricing rule.
- **2d. Generals:**
  - staff generals: refit T3 on AC, and check the 2-gold 0★ case;
  - commanders: refit the FS7 commander model on AC pairs (`build_commander_pairs.py` with the AC scope).
- **2e. AC-only corps.** All 238 corps are in the fit. Additionally, a **corps-level hold-out**: fit on the 221 ToW-sourced corps and predict the 17 AC-only corps, unseen. This tests whether one pricing rule covers them and whether the extreme corps numbers (3–4) extrapolate. Accuracy is reported separately for the two groups and per AC-only corps.

**3. Unit size, modelled better (user request).** Run on AC and ToW, with the same folds as step 2. Size forms to compare:

| Form | What it allows |
|---|---|
| Single power S^p | today's adopted model |
| One power per class | V4 |
| Natural cubic spline in log S per arm (reuse `natural_spline_basis`, as the calibre curve does) | a smooth size curve |
| The same spline per class, shrunk toward the arm curve | class-specific size curves |
| Piecewise power with one knot | a break in the size–price relation |
| Size × training level | separates mass from mob and poorly trained (confounded today) |

- **Judged by:**
  - CV MAE overall;
  - the out-of-fold error by size stratum: the goal is the U-shape gone without losing mid-size accuracy;
  - the largest and smallest units.
- **Also reported:** how much of the size harmonisation in `cost_effective_builds.py` would then be unnecessary (re-run its stratum table on the new out-of-fold errors).
- **No automatic change.** The adopted ToW model is not changed; the report recommends.

**4. Natural experiment: what sets AC versus ToW prices.** Model log(P_ToW/P_AC) − log(N_AC/N_ToW) on the 6 593 / 5 183 / 221 pairs. Hypotheses for the ×0.91 and its corps × class spread:
- a corps-level expected rebate: the fraction a full-corps or full-division build saves;
- side and class effects;
- the ToW corps;
- price rounding (integer and multiples);
- whether AC prices sit above the stats model's fair price by a corps × class factor that ToW removes (using step 2's residuals);
- patch history, if the prices encode it.

The output is either a readable rule or an honest variance decomposition.

**For the 17 AC-only corps** there are no pairs. Using the fitted rule (N ratio, side, class, and the corps × class spread as an interval), they get an estimated *ToW-equivalent price*: what each unit would cost in a ToW army of a given corps number. This is clearly marked as model-based.

**5. Effective prices with discounts** (`analysis/ac_discounts.py`).
- **Per unit:**
  - list price;
  - effective price with its brigade complete, and with its division complete;
  - support divisions get no rebate.
  - Built from `tools/army_builder_rules.py` (`build_roster_totals`, `group_discount`, `support_divisions`), so it matches the app.
- **Per corps:** the discount potential, i.e. what full brigades or divisions save.
- **Comparison:** how much of AC's premium over ToW the rebates give back.
- **Output:** `analysis/output/ac/ac_price_database.csv`, covering all 238 corps (AC-only corps flagged), with list, predicted, brigade-effective and division-effective prices, plus the ToW price (paired units) or the estimated ToW-equivalent price (AC-only units).

**6. Blind study** (after steps 2–5), as for ToW.
- **The folder:** `analysis/ac_blind/` with `TASK.md` (neutral: predict AC list prices from stats, readable models only), `RULES.md` (the discount rule), `DATA_DICTIONARY.md`, and the AC units with stats, N, side, placement, cap and the fold ids from step 2.
- **The agent:** a fresh-context subagent that sees only that folder.
- **Afterwards:**
  - compare on identical folds;
  - re-run its final script to verify;
  - adopt anything better.

**7. Report and docs.**
- `analysis/AC_PRICING_REPORT.md`: equations, accuracy, size findings, the natural experiment, effective prices, blind-study comparison, limitations.
- Updates to `analysis/HANDOFF.md` (status, commands) and the README branch note.

## Schedule: parallel lanes (machine: 16 cores)

**Estimate: about 3½–4½ hours of wall time with parallel processes and agents, against about 9–10 hours done serially.** The critical path is the model runs: step 2, then step 3. Everything else fits alongside.

**Compute-heavy runs** use `unit_pricing.parallel_map` process pools. HANDOFF recommends two 6-worker runs at once on this machine.

| Lane | Who | Work | Wall time |
|---|---|---|---|
| A. Compute | me, background processes | **2a** AC adopted model with ToW stat powers fixed (no full power search): ~15 min. **2a** V4 per class: ~40 min, run alongside (2 × 6 workers). Then **2b/2c/2e** on the same folds: ~30 min. Then **3** size forms (6 forms × 3 arms × AC and ToW), as parallel jobs: ~45–60 min | **~2–2½ h** |
| B. Discounts | subagent 1 (from the start) | **1** discount-rule write-up, **5** effective prices and the price-database scaffold (no model needed; uses `tools/army_builder_rules.py`) | ~1 h |
| C. Natural experiment | subagent 2 (from the start) | **4** pairs analysis, hypotheses for the ×0.91 (data only; the "fair-price residual" test waits for step 2's out-of-fold predictions) | ~1–1½ h |
| D. Blind study | blind subagent (launched early) | **6** It never sees our model, so it can run *in parallel*; only the *comparison* comes after our model, as you asked. It gets the AC data, rules and our fold ids (ready after step 2's fold search, ~15 min in) | ~2–3 h |
| E. Write-up | me | **7** report, as results land; the blind comparison and verification last | ~1 h after A and D finish |

**Caveats:**
- **Usage.** Three subagents cost noticeably more usage than working serially. If usage runs out mid-way, the checklist in `analysis/AC_STUDY_PLAN.md` (step 0) and the checkpoints in `analysis/.cache/ac/` let any session resume.
- **CPU contention.** Lane A's two 6-worker runs plus the agents' own scripts can slow things. I'd give the blind agent `--workers 2`.
- **Fixed stat powers in 2a.** The adopted AC model reuses ToW's stat powers to skip the ~50-minute power search. If AC fits clearly worse, a full search adds ~50 min to lane A.

## Files

- **New:** `analysis/ac_pricing.py`, `analysis/ac_discounts.py`, `analysis/AC_DISCOUNT_RULES.md`, `analysis/AC_STUDY_PLAN.md`, `analysis/AC_PRICING_REPORT.md`, `analysis/ac_blind/`, `analysis/output/ac/`.
- **Edited, small:**
  - `analysis/unit_pricing.py`: scope and side as parameters, defaults unchanged;
  - `analysis/build_commander_pairs.py`: an AC scope option;
  - `analysis/HANDOFF.md`, `README.md`.
- **Unchanged:** the app, `rules.ts` / `army_builder_rules.py` (no rule changes), the ToW outputs.

## Verification

1. **ToW unchanged.** After the `unit_pricing.py` parameterisation, a ToW run with the committed settings reproduces `analysis/output/oof_predictions.csv`. Spot-check one slice (`check_final.py` pattern: max |Δoof| ≈ 0).
2. **Discount code.** `ac_discounts.py` rebates equal `tools/army_builder_rules.calculate_army_cost` on sampled full-brigade and full-division builds, and on the verified 5 645-gold test build.
3. **Data.** AC loader counts match exploration: 7 205 regulars (minus 7 fixed artillery), 5 628 commanders, 283 staff, 238 corps. The 17 AC-only corps (612 regulars) are present in the model data, the price database and the blind-study data.
4. **CV.** Fixed seeds; the fold coverage report passes; out-of-fold predictions saved; metrics reproducible on re-run.
5. **Blind study.** Re-run its final script and match its reported numbers.
6. **Report.** Every number in the report comes from an output file written by the scripts.
