# Army Corps unit pricing

*The AC pricing study (`analysis/AC_STUDY_PLAN.md`), October 2026.* It covers all 238 AC corps,
including the 17 that never became a Theatre-of-War (ToW) army, e.g. 6. Eugène / Italie.

Every number comes from an output file:
- **Tables:** `analysis/output/ac/ac_pricing_results.md`
  (`python analysis/ac_pricing.py --phase report`).
- **Discounts:** `analysis/AC_DISCOUNT_RULES.md`.
- **AC vs ToW:** `analysis/output/ac/natural_experiment_report.md`.
- **Blind study:** `analysis/ac_blind/REPORT.md`.

MAE is in gold, cross-validated on the 500-seed group-fold plan the ToW model uses.

## Summary

1. **AC list prices follow the same pricing rule as ToW.** The adopted ToW form explains them about as
   well as it explains ToW: MAE infantry 29.7, cavalry 43.3, artillery 58.0, against 27.4 / 34.7 / 32.4
   on ToW. Like ToW, AC needs its hand-set army × class multipliers. Without them, MAE is 38–81.
2. **Price scales with the corps number almost as 8/N.** The free per-N factors give γ = 0.89
   (infantry), 0.94 (cavalry) and 0.70 (artillery) against 1 for 8/N. Corps 3 and 4 are cheaper than
   8/N predicts, especially artillery.
3. **The formation discount is a simple, exact rule.** Completing a group (a brigade or a whole
   division) whose cards total n gives (n − 1)% off that group's full-roster price. In practice that
   means:
   - a median 3% for a brigade;
   - 8% for a division you can actually complete;
   - 10% for a whole corps.
   No other per-corps price multiplier exists in the game files. The app matches the Lua everywhere
   except 5 artillery divisions; only 3 small groups there would show the difference in game.
4. **AC prices carry a premium of about 10% over the ToW price scale. ToW copies remove most of it.**
   Every ToW unit is a copy of an AC unit. The copy sits on the common stats curve, while its AC
   original sits about 10% above it, by an amount hand-set per corps × class. That premium is about what
   completing a division gives back. The rebates themselves don't set any price.
5. **Unit size: one size power per class is the wrong curve, on AC and ToW alike.** A free multiplier
   per size band per class removes the U-shaped error and cuts MAE by:
   - ToW: 10–20% (infantry 27.4 → 22.0, cavalry 34.7 → 31.4, artillery 32.4 → 25.7);
   - AC: 5–23%.
   This beats the committed per-class model V4 and the blind study, and it removes most of the reason
   for the size harmonisation in `cost_effective_builds.py`.
6. **The blind study agrees.** An independent agent, on the same folds, found the infantry price
   curve is S-shaped in size, not a power law.
   - Its best model's MAE: 26.4 / 47.1 / 47.3.
   - Ours with size bands: 25.2 / 41.0 / 44.9.
   - Its per-army offsets generalise better to unseen corps than our army × class cells, which fall
     back to 1 there.

## 1. The formation discount (`analysis/AC_DISCOUNT_RULES.md`)

The game's Lua (`ntw3.lua` `ArmyPrice`, `AC_DivisionBrigade_Bonus`, `AC_DivisionBrigade_PriceCut`):

- **Army price** = Σ list prices − rebates, for `_ac_` factions only.
- **Group rebate** = `floor(Cost/100 × (n − 1))`, where:
  - `Cost` = Σ cap × list price over the group's full roster, generals excluded;
  - n = Σ cap.
- **A full division replaces its brigades' rebates.** Division 0 and untagged units earn nothing.
- **Combat generals count towards completion**, but not in `Cost` or n.
- **German States ×1.5:** this never matches a shipped corps.

| Rebate, % of the group's roster price | Median | Range |
|---|---|---|
| Brigade (2 519 eligible) | 3.0 | 0–18 |
| Division (979 eligible; 888 can be completed in a legal build) | 9.0 (8.0 completable) | 0–64 (29 completable) |
| Whole corps (224 corps with eligible groups) | 10.0 | 2.6–35.9 |

- **91 divisions can't be completed:**
  - 74 cost more than 10 000;
  - 7 need more than 31 cards;
  - 10 break an artillery or heavy-cavalry cap.
- **No trend with corps number.**
- **The extremes:** cavalry reserve corps have the smallest rebate (Pajol I.RC 2.6%); Dorsenne / Nord
  the largest (35.9%, inflated by an oversized division).

**App versus Lua.** The app adds three rules: support divisions earn nothing, the Davout 1812 brigade
exception, and the recruit-order affordability rule. They differ from the Lua only in 5 fully tagged
artillery divisions:
- `a11_x5_117` d7;
- `a11_x5_123` d4;
- `a11_x7_126` d3 and d7;
- `b17_x7_281` d7.

Caps make most of those moot. Three groups would show it in game:

| Group | Lua price | App price |
|---|---|---|
| Reynier VII.C d4, both foot batteries | 1 437 | 1 451 |
| Reynier VII.C d4, whole division | 2 116 | 2 181 |
| Macdonald X.C d3 | 1 699 | 1 733 |
| Macdonald X.C d7 brigade 3 | 1 066 | 1 087 |

**For in-game verification.** The app is not changed.

## 2. AC list prices from unit stats

`analysis/ac_pricing.py`. It uses the ToW model code unchanged: AC's scope and side rules are swapped
in only while loading, the committed stat powers are kept, and κ is chosen by nested CV on an extended
grid.

| Model | Infantry (4 537) | Cavalry (1 715) | Artillery (946) |
|---|---|---|---|
| Free factor per corps number, no army × class | 38.5 | 81.4 | 79.5 |
| Fixed 8/N, no army × class | 40.2 | 84.1 | 93.0 |
| **Adopted form**: 8/N × army × class | **29.7** | **43.3** | **58.0** |
| V4: formula + size power per class | 28.1 | 42.4 | 51.8 |
| **Size bands per class (F6; F2 for cavalry)** | **25.2** | **41.0** | **44.8** |
| *ToW, adopted form / V4 (reference)* | *27.4 / 24.9* | *34.7 / 32.8* | *32.4 / 27.2* |

- **One rule or two?** The adopted form fitted on ToW + Custom, then applied to AC, is the ToW stat
  formula × 8/N. AC prices sit above that rule by:
  - ×1.09 for infantry (grenadiers and skirmishers ×1.12);
  - ×1.04 for cavalry;
  - ×1.01 for artillery (horse artillery ×1.15).
  The same rule with AC's own army × class cells halves the error. So the stat formula is shared, and
  the difference lies in the hand-set army × class layer.
- **The 17 AC-only corps, unseen:** fitted on the other 221 corps.

  | Arm | Units | Hold-out MAE (adopted) | CV MAE, army seen |
  |---|---|---|---|
  | Infantry | 430 | 57.5 | 37.1 |
  | Cavalry | 101 | 113.6 | 66.1 |
  | Artillery | 78 | 143.0 | 89.1 |

  - The large corps price well unseen: Eugène / Italie, Soult / Pyrénées, Wellington / Pyrenees
    (infantry 12–43).
  - The corps numbered 3–4 do not. Most are priced too dear by the unseen fit: median residuals run
    from −6% to −50% per arm, worst for Suchet / Alpes artillery (−50%) and Moore / Baltic (−16% to
    −27%). Kindelán / Florida's single cavalry unit is the exception, 23% too cheap. This is the
    γ < 1 flattening at low N, plus their own hand-set factors.
- **Generals:**

  | | Fit | MAE |
  |---|---|---|
  | Staff generals | T3 refitted on AC: b = 83.0, q = 1.34 (ToW 76.6, 1.39) | 17.3 (4.1%) on full grouped folds |
  | Staff generals | ToW T3 unchanged | 20.2 |
  | Combat-general versions | the ToW commander model refitted | 11.4 (3.4%) |
  | Combat-general versions | ToW coefficients unchanged | 17.4 |
  | Combat-general versions | a plain price ratio | 89.2 |

  Seven 0★ AC staff generals cost 2 gold, not 1.

## 3. Unit size, modelled better

The forms are compared on the same folds and the same base (the adopted form, κ fixed). Every size
parameter is fitted on training folds only.

| Form | AC inf | AC cav | AC art | ToW inf | ToW cav | ToW art |
|---|---|---|---|---|---|---|
| F0 one size power (adopted) | 29.65 | 43.27 | 57.98 | 27.38 | 34.71 | 32.36 |
| F1 power per class | 30.13 | 43.14 | 55.87 | 27.51 | 34.59 | 30.90 |
| F2 + size-band multipliers | 25.55 | **41.03** | 48.58 | 22.60 | 33.20 | 26.66 |
| F3 one knot in the power | 27.46 | 43.54 | 57.64 | 25.68 | 34.63 | 30.81 |
| F4 power per training level | 30.23 | 43.27 | 59.23 | 27.32 | 34.71 | 32.56 |
| F5 per-class power + bands | 25.81 | 41.06 | 48.02 | 22.42 | 32.53 | 27.25 |
| F6 bands per class | **25.21** | **41.03** | **44.84** | **22.04** | **31.38** | **25.74** |

Bands are models 0–40, 40–60, 60–80, 80–100, 100–140, 140–180, 180–240, 240+ (guns 1, 2, 3, 4, 5+).

- **The size error is a curve shape, not a class or training effect.**
  - A power per class (F1) or per training level (F4) changes nothing: every training level picks the
    same power.
  - A free factor per size band (F2) removes most of it. Its median out-of-fold error per band is
    within ±3% where F0 was:
    - ToW infantry: +20% at 0–40 models, −9% at 60–80, −30% above 240;
    - artillery: −25% for single guns.
  - A knot at 160 models (F3) captures only the large-unit bend.
- **The blind study saw the same curve independently.** Infantry price elasticity is about 0.3 below
  150 men, 1.7 at 150–200, then falls to about 0.1 above 340. Artillery follows a gun-count table, not
  a power.
- **Caveat: the 240+ band holds only 13 AC and 17 ToW units.** Their band factor is poorly pinned.
  With bands the model is now *too cheap* there: +10–12% on AC, +27–42% on ToW. A smoothed or
  monotone size curve would fix that edge.

**Recommendation.** Adopt size-band multipliers per class (F6) in the ToW pricing model
(`unit_pricing.py` / `class_structure.py`), with the top band smoothed. Then:
1. re-run `commander_model.py` and the price database;
2. re-check `cost_effective_builds.py`: its size harmonisation existed to correct exactly this error.

That is a change to the adopted model, so it is left for your decision.

## 4. AC versus ToW: the natural experiment (`natural_experiment_report.md`)

- **What makes ToW copies cheaper.** A ToW copy costs ×0.896 of its AC original at the median.
  - The corps-number ratio explains 78% of the variance in the price ratio, but not the average cut.
  - The cut is AC's hand-set corps × class premium:
    - AC units sit about 10% above the common stats curve, and ToW copies sit on it;
    - ToW removes 75–81% of each corps' premium (R² 0.61–0.71).
- **Formation rebates play no part** (|correlation| ≤ 0.09). Their average size, about 11% for a
  division, matches the premium. That fits a design intent: a player who completes divisions in AC
  pays roughly ToW-scale prices.
- **No exact generating rule exists for regular units.**
  - There is no rounding or quantised factor.
  - Within an AC corps × class cell the ratio still scatters by 5%.
- **Staff generals are exact:** price × N is a fixed value per star level in each mode, and it
  reproduces 66.5% of ToW staff prices exactly.
- **A compact rule** for corps without a ToW copy (leave-corps-out median error 4.8%, 90th percentile
  14.5%):

  `P_ToW = P_AC × (N_AC/N_ToW)^0.977 × k[side, class] × exp(−0.122·e_A − 0.459·e_A,cell)`

- **The 17 AC-only corps** get estimated ToW-equivalent prices at their own N and at N = 8, with
  ±10–12% bands. These are model-based, and N = 3–4 lies outside anything ToW uses.
- **Caveat:** that study used its own stats curve. Re-running its premium test with this study's AC
  model is a cheap follow-up.

## 5. The price database (`analysis/output/ac/ac_price_database.csv`)

One row per AC card: 13 116 cards in 238 corps, AC-only corps flagged. For each:
- list price, and the effective price with its brigade or division complete (rebate %, support
  division);
- out-of-fold model prices: the adopted form, and the arm's best size form;
- for generals, the commander refit or T3;
- the ToW price where a copy exists (12 032 cards), or the ToW-equivalent estimate with its band
  (1 070 cards in the 17 AC-only corps).

## 6. The blind study (`analysis/ac_blind/REPORT.md`)

A fresh agent saw only the AC data, the rebate rule and our folds. Its numbers were verified by
re-running its final script on a copy, which gave identical predictions.

| On identical rows | Infantry | Cavalry | Artillery | Unseen corps (inf / cav / art) |
|---|---|---|---|---|
| Blind M1 (log ridge, piecewise size, shrunk army and army × class offsets) | 26.4 | 47.1 | 47.4 | **50.8 / 100.4 / 91.0** |
| Blind M2 (army-blind) | 34.0 | 71.3 | 69.4 | — |
| Ours, adopted form | 29.7 | 43.3 | 58.1 | 57.5 / 113.6 / 143.0 |
| Ours, V4 | 28.1 | 42.4 | 51.9 | 49.9 / 111.9 / 128.6 |
| **Ours, best size form** | **25.2** | **41.0** | **44.9** | (not run unseen) |

- **Where it confirms us:**
  - the S-shaped size curve;
  - price ∝ N^−0.92…0.96, and staff N^−0.93;
  - empire 4–6% cheaper;
  - a residual per-army factor of about 5%, plus army × class of similar size.
- **What it does better:** unseen corps, especially artillery (91 against 129–143). Its additive per-army
  offsets on a log scale transfer, while our multiplicative army × class cells fall back to 1.
- **Worth adopting:** a per-army level shared across classes, so an unseen army keeps its army
  factor.

## 7. Limitations

- **Corps 3–4 are few and odd.** They are 3 and 8 corps, mostly AC-only, and all models price them
  worst.
- **The 240+ size band is thin.** See §3.
- **The size forms were not run on the unseen-corps test.**
- **Fixed stat powers.** AC reuses the committed ToW stat powers, chosen to skip the power search. AC
  fits as well as ToW, so a search was not needed.
- **List prices only.** The rebates are an exact rule (§1). No model predicts which groups a player
  completes.
- **Data snapshot:** v9.4 / v9.6-era tables.

## Commands

```bash
py -3.13 analysis/ac_pricing.py --phase model --arm infantry|cavalry|artillery --workers 4   # ~3–90 min per arm
py -3.13 analysis/ac_pricing.py --phase staff
py -3.13 analysis/ac_pricing.py --phase commanders
py -3.13 analysis/ac_pricing.py --phase size --dataset ac|tow --arm …                         # ~5–55 min each
py -3.13 analysis/ac_pricing.py --phase blind-data       # analysis/ac_blind/data
py -3.13 analysis/ac_discounts.py                        # rebates, self-checked (~1 min)
py -3.13 analysis/ac_natural_experiment.py               # AC vs ToW pairs (~4 min)
py -3.13 analysis/ac_pricing.py --phase database         # ac_price_database.csv
py -3.13 analysis/ac_pricing.py --phase report           # ac_pricing_results.md
```

Checkpoints live in `analysis/.cache/ac/` (gitignored), so runs resume.
