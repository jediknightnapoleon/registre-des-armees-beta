# Blind study: how a combat general's unit is priced

*Written by the blind-study agent; saved here by the main session, which could not
be done from the subagent. The verification note at the end was added by the main
session.*

**Data:** `data/pairs.csv`, 5 238 pairs, 4 776 distinct regular units, 55 armies
(5 189 rows from Theatre-of-War armies).

**Validation:**
- 5-fold CV, folds grouped on `regular_unit_key`, seed 0. Every row is scored.
- Predictions are clipped at a minimum of 1 gold.
- All models are fitted by least absolute deviation (median regression), because
  the target metric is MAE. It beat ordinary least squares on every model fitted
  both ways.
- One SE of the CV MAE ≈ 0.29 gold.

**Notation:**
- `P` = regular_price, `s` = command_stars, `corps` = corps_number, `men` = regular_men.
- `r` = commander_men / regular_men (the size ratio).
- `Δx` = commander_x − regular_x, for morale (mor), melee_defense (md),
  charge_bonus (cb), accuracy (acc) and reload_skill (rel).
- `Δ(x²)` = commander_x² − regular_x².
- `imp` = 1 for imperial armies.

## 1. Best model (26 parameters)

```
C = max(1,  a[arm]·P + b[arm] − 3.97·imp
          + P·( 0.045958·Δmor − 0.0037851·corps·Δmor + 0.020227·Δmd
              + 0.035952·Δcb − 0.00067449·Δ(cb²) + 0.011920·Δacc
              + 0.0011170·Δrel + 0.0000245·Δ(rel²) )
          + men·( 0.056932·Δmor + 0.0047895·Δ(mor²) + 0.0085454·Δrel )
          + s·( k[arm] + c[arm]·corps )
          + g[arm]·P·(r − 1) )
```

| Parameter | Infantry | Cavalry | Artillery |
|---|---|---|---|
| a | 0.87526 | 0.87888 | 0.91466 |
| b | −120.14 | −99.24 | −101.10 |
| k | 33.173 | 31.910 | 13.680 |
| c | −2.1774 | −0.4930 | +1.2029 |
| g | 0.43981 | 0.43981 | 1.8323 |

**CV MAE 8.58 ± 0.64 gold; median APE 1.08%; in-sample MAE 8.47.** Fold seeds 1,
2 and 3 give 8.61, 8.59 and 8.63.

**Worked example, pair 1:** cavalry, corps 8, 4 stars, 150 men, P = 1452. The
general adds morale 14→17, melee defence 19→21 and charge 8→9.
- Base: 0.8789·1452 − 99.24 = 1176.9
- Stat premium: 1452·(0.1379 − 0.0908 + 0.0405 + 0.0360 − 0.0115) = 162.6
- Per-man premium: 150·(0.1708 + 0.0048·93) = 92.4
- Star fee: 4·(31.91 − 0.493·8) = 111.9
- Total 1543.8, against a true price of 1540.

**How to read it:**
1. **Base.** A commander card starts at about 88% of the regular price minus
   about 100–120 gold. That is why 0★ and 1★ commanders are usually cheaper than
   the regular unit (median C/P 0.74 and 0.85), and why cheap units give
   near-free commanders.
2. **Stat premium.** The general's stat bonuses add a premium mostly
   proportional to P; morale, melee defence and charge are the largest parts.
   The morale part shrinks with corps number: one morale point adds about 2.7%
   of P at corps 5, 1.2% at corps 9 and almost nothing at corps 12.
3. **Per-man part.** Morale and reload bonuses are also worth a fixed amount per
   man: about 0.1–0.2 gold per man per morale point, more for units with higher
   morale. A big battalion pays more for the same general.
4. **Star fee.**
   - Infantry: about (33 − 2.2·corps) gold per star, so 15 gold at corps 8 and
     7 at corps 12.
   - Cavalry: about 28 gold per star.
   - Artillery: small.
5. **Size changes.** A bigger commander unit costs more; for artillery the rise
   is roughly quadratic in the gun count.
6. **Side.** Imperial armies are about 4 gold cheaper. The effect is tiny but
   consistent.

## 2. Simpler fallbacks

**Fallback (16 parameters): CV MAE 10.38 ± 0.64, median APE 1.38%.**

```
C = max(1, a[arm]·P + b[arm]
         + P·(0.028589·Δmor + 0.023803·Δmd + 0.016785·Δcb + 0.011662·Δacc + 0.0033894·Δrel)
         + 0.13545·men·Δmor + s·(41.230 − 2.0705·corps) + g·P·(r−1))
a = 0.88922 / 0.87017 / 0.90698 (inf/cav/art); b = −125.28 / −102.65 / −104.27
g = 0.43766 (inf, cav), 1.85304 (art)
```

**Minimal (11 parameters): CV MAE 11.90 ± 0.80, median APE 1.68%.**

```
C = max(1, 0.87940·P − 114.97
         + P·(0.037455·Δmor + 0.019650·Δmd + 0.010094·Δacc + 0.0052233·Δrel)
         + 0.093780·men·Δmor + s·(43.880 − 1.8271·corps) + g·P·(r−1))
g = 0.43942 (inf, cav), 1.89377 (art)
```

The fallback is about 6 SE worse than the best model, so the best model stands.
The fallback is the one to use by hand.

## 3. Models tried

The full log, about 150 experiments, is in `RESULTS.md`. Representative steps:

| ID | Model | Params | CV MAE | Median APE % |
|---|---|---|---|---|
| B0 | C = P | 0 | 94.0 | 19.1 |
| L1 | aP + b | 2 | 71.7 | 12.6 |
| L2 | P(a + c·s) + b + d·s | 4 | 33.9 | 5.0 |
| L4 | L2 per arm | 12 | 17.5 | 2.3 |
| L6 | arm × star lookup | 36 | 15.9 | 1.8 |
| D2 | stat-change linear | 14 | 16.2 | 1.9 |
| N1 | multiplicative exp form | 22 | 12.2 | 1.65 |
| Z7 | stars only, no stat changes | 7 | 24.4 | 3.1 |
| Z10 | minimal | 11 | 11.9 | 1.7 |
| J8 | fallback | 16 | 10.38 | 1.4 |
| W2 | per-arm star lookup | 45 | 10.0 | 1.3 |
| X1 | per-army premium scale | 69 | 10.1 | 1.3 |
| FS7 | best | 26 | 8.58 | 1.08 |
| FS10 | forward-selection minimum | 29 | 8.36 | – |

**Selection:** FS7 is the simplest model within one SE of the forward-selection
minimum (`out/forward_selection.txt`).

## 4. Evidence on each input, with regular_price known

Each row changes one block of the best model. Diff = the paired fold difference
against it (+ = worse).

| Change | Diff (gold) |
|---|---|
| Drop all stat changes | +13.46 ± 0.35 |
| Drop per-man terms | +4.40 |
| Drop star terms | +3.17 |
| Drop size-change terms | +2.09 |
| Replace stat changes with a 40-parameter arm × star lookup | +1.86 |
| Drop corps number entirely | +1.78 |
| Single slope/intercept instead of per arm | +1.44 |
| Drop the squared-change terms | +1.34 |
| Drop side | +0.22 ± 0.02 |
| Add corps main effect + P·corps | −0.01 |
| Add melee-attack change | 0.00 |
| Add men as its own term | 0.00 |
| Add training level | −0.02 |
| Add regular stats | −0.06 |
| Add class | −0.07 |
| Add s² | −0.07 |
| Add army multipliers (54) | −0.13 |
| Add ability flags | −0.15 |
| Add army intercepts (55) | −0.18 |

- **Stat changes:** the main driver; keep. Arm and stars almost fix them, but
  the small deviations still carry information.
- **Stars:** keep, as a flat fee per star on top of the stat changes.
- **Corps number:** keep, but only as a scale on the general's premium (the star
  fee and the morale premium). It adds nothing as a level once P is known.
- **Size changes:** keep (70 rows, but 12.8% of the absolute error).
- **Men:** keep, only inside the per-man stat premium.
- **Arm:** keep.
- **Army:** drop. 55 parameters gain under one SE. Side is kept at −4 gold.
- **Class, training, regular stats and flags:** drop; each improves CV by 0.15
  gold or less.

## 5. Odd rows and failures

- **Near-free commanders:** 33 rows have C ≤ 30, and 6 have C = 1. All are cheap
  units (P 83–136) where the −100 base reaches the floor. The clip at 1
  reproduces them: MAE on these 33 rows is 3.8.
- **Size-change rows:** 70 rows are modelled with g·P·(r−1). They have MAE 82,
  against 7.6 for same-size rows.
- **Remaining error:** MAE 7.6 and median absolute error 4.4 on same-size rows.
  The worst 5% of rows carry 34% of all absolute error.
- **Worst pairs:**
  - Diversanti 98→196 men: +411.
  - Otryad (skirmishers) 88→178 men: +385.
  - Tecumseh 194→294 men: +373.
  - Narodnoe vosstanie 974→1104 men: −332.
  - Sapeurs 152→211 men: +324.
  - Bedouin skirmishers 104→210 men: +300.
  - Sénarmont's battery, 2→4 guns: +299.
- **Patterns:**
  1. Size changes follow no single rule.
  2. High stars are under-predicted (mean error +8 at 4★, +23 at 5★).
  3. Very small cavalry units (76–82 men) are over-predicted by 60–115 gold.
  4. Horse artillery is biased by −12 gold.
  5. Corps 5–6 armies have a larger error (MAE 18.5 / 11.5).

---

## Verification (main session)

- **Reproduced:** `src/final.py`, re-run, gives exactly 8.58 ± 0.64 (best),
  10.38 (fallback) and 11.90 (minimal).
- **Stricter grouping:** the same unit or general can appear in several armies
  under different keys. Re-running all three models with folds grouped by
  commander name (4 974 groups) or by unit name (3 456 groups) gives the same
  results:

  | Model | By commander name | By unit name |
  | --- | --- | --- |
  | Best | 8.61 | 8.62 |
  | Fallback | 10.40 | 10.41 |
  | Minimal | 11.88 | 11.91 |

  So the CV is not flattered by duplicates across armies.
- **Comparison:** the earlier commander stage (`analysis/commander_stage.py`,
  `(a + a_s)·P + (b_s + army_f)·8/N`, stars only) scores 31.2 MAE on the same
  question, with the true regular price known. Pricing the general's actual
  stat changes is what makes the difference.
