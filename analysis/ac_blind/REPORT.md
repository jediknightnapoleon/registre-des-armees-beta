# A readable model of Army Corps unit prices — report

*Blind study on `data/ac_units.csv` only. All numbers are out-of-fold (5 given folds) unless marked otherwise.*

## 1. Summary

- **Final model M1** (one formula per arm — infantry, cavalry, artillery — plus two small army lookup tables) predicts a
  regular unit's list price with a typical error of **34 gold (5.7 %)**, against 214 gold (42 %) for the best baseline.
  On **17 armies it never saw** it still gets **64 gold (8.0 %)**.
- The formula works on the **logarithm of the price**, so every term is a *multiplier*: a coefficient of +0.10 means
  "about 10.5 % dearer" (e^0.10 = 1.105), −0.10 means "about 9.5 % cheaper".
- **The army matters a lot, and almost entirely through its corps number**: price ∝ corps_number^−0.92 to ^−0.96 in all
  three arms (and ^−0.93 for staff generals). The same unit costs about 2.5× as much in a "3." army as in an "8." army,
  and about 0.63× as much in a "13." army. Empire armies are 4–6 % cheaper than coalition ones. What is left per army is
  a small, mostly army-specific factor (typically ±5 %).
- **Unit size is not a single power law.** Infantry price is almost flat in size below ~150 soldiers (men_raw), rises
  faster than proportionally between 150 and 200, roughly proportionally up to ~340, and is flat again above. Cavalry is
  flat below ~100 men_raw and then rises with an elasticity of about 0.5–0.9. Artillery is priced by gun count with a
  table: relative to 3 guns, 1 gun ≈ 0.11×, 2 guns ≈ 0.53×, 4 guns ≈ 1.5×, 5 guns ≈ 2.1× — a one-gun section is almost
  free, and from two guns on price is roughly linear in (guns − 1).
- Price follows **men_raw** (soldiers in the unit file), not the halved men_display: two otherwise identical Cossack
  units with 120 and 121 men_raw cost 752 and 764.
- **Staff generals** are priced by a 9-entry star table times the same corps-number factor (4.7 % error).
  **Combat-general versions** are best priced as "regular price + a star/stat surcharge scaled by the corps number"
  (36 gold, 10.6 %).

## 2. Data, scope and protocol

- Primary target: 7 198 regular units (7 205 non-general rows minus 7 fixed-artillery rows), 238 armies; 7 artillery
  rows with an empty fold are always kept in training and never scored. Arms: infantry 4 537 rows, cavalry 1 715,
  artillery 946.
- Every unit key is unique (one row per unit per army), so no "same unit in another army" price is used anywhere.
- Folds: exactly the given `fold` column. Every tuning choice (penalty strengths) was made by an inner cross-validation
  on the four training folds of each outer fold (nested CV), criterion MAE in gold. The chosen penalties were very
  stable across folds (army / army×class / class-specific stats: infantry 1 / 2 / 2; cavalry 1 / 1 / 2; artillery
  1 / 1 / 5). Feature choices were made on CV across experiments (logged in `RESULTS.md`).
- Unseen-army test: fit on every row of the 221 other armies, predict the 609 scored regular rows of the 17
  `corps_holdout` armies (penalties chosen by CV inside the 221 armies).
- Baselines: **B0** = mean price of the unit_class; **B1** = that mean × (unit size / class mean size), size =
  men_display (guns for artillery).
- Fitting: least squares on log(price) with a light ridge penalty (separate penalty per group of terms); prediction =
  e^(formula). About 45 experiments are logged in `RESULTS.md`; reasoning in `NOTES.md`.

## 3. Results

### 3.1 Cross-validation (mean ± sd over the 5 folds)

| model | segment | MAE (gold) | MAPE % | R² |
|---|---|---|---|---|
| B0 class mean | infantry | 197.7 ± 5.3 | 49.28 ± 1.22 | 0.128 ± 0.018 |
| | cavalry | 296.9 ± 19.0 | 40.73 ± 2.14 | 0.248 ± 0.021 |
| | artillery | 314.4 ± 21.7 | 73.91 ± 13.01 | 0.034 ± 0.031 |
| | **overall** | **236.6 ± 5.0** | **50.46 ± 1.81** | **0.323 ± 0.016** |
| B1 class mean × size | infantry | 182.0 ± 7.2 | 44.71 ± 2.08 | 0.237 ± 0.032 |
| | cavalry | 300.1 ± 8.8 | 38.30 ± 1.06 | 0.196 ± 0.070 |
| | artillery | 211.1 ± 8.8 | 38.18 ± 3.64 | 0.535 ± 0.061 |
| | **overall** | **214.0 ± 3.2** | **42.33 ± 1.55** | **0.421 ± 0.038** |
| M2 army-blind formula | infantry | 34.0 ± 1.3 | 7.00 ± 0.23 | 0.961 ± 0.009 |
| | cavalry | 71.3 ± 2.4 | 8.25 ± 0.95 | 0.949 ± 0.009 |
| | artillery | 69.3 ± 6.0 | 9.23 ± 0.69 | 0.918 ± 0.032 |
| | **overall** | **47.5 ± 1.3** | **7.59 ± 0.17** | **0.960 ± 0.005** |
| **M1 final** | infantry | 26.4 ± 0.4 | 5.65 ± 0.13 | 0.973 ± 0.012 |
| | cavalry | 47.1 ± 2.4 | 5.60 ± 0.61 | 0.973 ± 0.005 |
| | artillery | 47.3 ± 3.5 | 6.36 ± 0.65 | 0.958 ± 0.010 |
| | **overall** | **34.1 ± 0.9** | **5.73 ± 0.11** | **0.977 ± 0.005** |

How the error came down (overall CV MAE): first log-linear formula 63.9 (E01) → artillery calibre + gun table 52.9
(E03f) → + per-army offsets 45.9 (E04a) → + army×class offsets 40.4 (E05f) → + class-specific stat weights 38.4 (E06a)
→ + piecewise size curve 36.2 (E07a) → + projectile table 35.0 (E08a) → in-range bends + nested tuning 34.1 (M1).

### 3.2 Unseen-army test (17 armies, 609 scored regular rows; single split)

| model | infantry MAE / MAPE | cavalry MAE / MAPE | artillery MAE / MAPE | overall MAE / MAPE / R² |
|---|---|---|---|---|
| B0 | 284.0 / 45.5 % | 495.9 / 33.7 % | 410.7 / 63.2 % | 335.4 / 45.8 % / 0.14 |
| B1 | 273.6 / 42.0 % | 555.9 / 42.6 % | 349.2 / 37.8 % | 330.1 / 41.6 % / 0.19 |
| M2 | 58.4 / 8.5 % | 108.4 / 7.9 % | 95.9 / 10.5 % | 71.5 / 8.7 % / 0.950 |
| **M1** (army tables = 0) | **50.8 / 7.8 %** | **100.4 / 7.2 %** | **91.0 / 10.1 %** | **64.2 / 8.0 % / 0.955** |

The holdout armies are dearer on average than the rest (8 of the 17 have corps number 3 or 4), which is why gold errors
are higher than in CV while percentage errors rise only from 5.7 % to 8.0 %. M1 with its army tables set to zero beats
M2, the model built for unseen armies: fitting the army tables while estimating the unit formula keeps army quirks out
of the unit coefficients, so the unit formula itself transfers better. **Use M1 for every army; for an army not in the
tables its offsets are 0.**

### 3.3 Secondary targets (generals)

| model | rows | MAE (gold) | MAPE % | R² | unseen-army MAE / MAPE |
|---|---|---|---|---|---|
| **G-ST1** staff generals: T[stars] × corps factor | 283 staff generals | **14.5 ± 3.1** | **4.71** | 0.994 | 18.8 / 7.8 % (33 rows) |
| G-CV2 combat general: regular price × e^(star table + stat changes + arm + log cn) | 5 624 | 49.4 ± 1.5 | 16.78 | 0.967 | 56.1 / 9.2 % |
| **G-CV4** combat general: regular price + corps factor × (star table + arm + stat changes) | 5 624 | **36.1 ± 1.6** | **10.60** | 0.974 | 57.8 / 10.5 % |
| G-CV5 = G-CV4 + regular price × stat changes | 5 624 | 31.0 ± 1.2 | 11.42 | 0.978 | 55.1 / 9.4 % |
| G-CV3 = G-CV2 using M1's *predicted* regular price | 5 624 | 62.6 ± 2.3 | 18.94 | 0.941 | 88.6 / 12.8 % |

Combat-general percentage errors are inflated by 144 versions priced under 100 gold. By arm, G-CV4 is 4.9 % on cavalry,
12 % on infantry and 21 % on artillery.

## 4. The final model M1, written out in full

### 4.1 How to price a unit by hand

1. Pick the arm table below (infantry, cavalry, artillery) and the column of the unit's class.
2. Add up: the class constant; the size terms (size = men_raw, or guns for artillery; "log" is the natural logarithm;
   `max(0, log(men_raw/150))` is 0 for units of 150 men_raw or fewer); each stat × its coefficient plus log(1 + stat) ×
   its coefficient; the coefficient of every ability the unit has; the training-level and speed-code entries; for
   artillery the gun-count, projectile and calibre terms; then the corps term (coefficient × log(corps_number)) and the
   empire term.
3. Add the army's offset (`out/army_offsets_M1.csv`, by army and arm) and the army×class offset
   (`out/army_class_offsets_M1.csv`); use 0 for an army that is not listed.
4. Price = e^(sum).

The stat terms come in pairs (linear and log) and often have opposite signs: read them together. Together they give a
rising, saturating effect (the first points of melee attack or morale add more than later ones). The same holds for the
artillery calibre terms (projectile damage, reload time, range, projectile table and howitzer flag all describe the gun
type and must be read as one set).

**Worked example** — *Infantería de Alcázar de San Juan [L3]* (line infantry, army "7. Freire / 2-3°", coalition,
266 men_raw, trained, speed L3; accuracy 17, reload 35, ammo 35, morale 2, melee attack 7, defence 4, charge 12;
ability: skirmish):

| step | term | value | running sum |
|---|---|---|---|
| 1 | constant (line) | +2.9939 | 2.9939 |
| 2 | 0.3057 × log 266 | +1.7070 | 4.7009 |
| 3 | bends: 1.3876 × log(266/150) − 0.7072 × log(266/200) − 0.2195 × log(266/260) | +0.5882 | 5.2892 |
| 4 | stats (7 linear + 7 log terms) | +3.0055 | 8.2947 |
| 5 | ability skirmish | −1.0104 | 7.2842 |
| 6 | trained, speed L3 | +0.0070 − 0.0586 | 7.2326 |
| 7 | −0.9166 × log 7; coalition (0) | −1.7836 | 5.4490 → e^5.449 = **232 gold without army tables** |
| 8 | army offset +0.0313, army×class offset −0.0569 | −0.0256 | 5.4234 → e^5.423 = **227 gold** (true price 240) |

### 4.2 Coefficient tables (fit on all rows; log scale)

#### Infantry (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + corps terms + army offset + army×class offset

| term | grenadiers | irregulars | light | line | militia | skirmishers |
|---|---|---|---|---|---|---|
| constant (intercept + class) | +3.638 | +3.137 | +2.971 | +2.994 | +1.199 | +3.411 |
| × log(size) [size = men_raw] | +0.3312 | +0.4880 | +0.2800 | +0.3057 | +0.4087 | +0.6483 |
| × max(0, log(men_raw/150)) | +1.3876 | +1.3876 | +1.3876 | +1.3876 | +1.3876 | +1.3876 |
| × max(0, log(men_raw/200)) | -0.7072 | -0.7072 | -0.7072 | -0.7072 | -0.7072 | -0.7072 |
| × max(0, log(men_raw/260)) | -0.2195 | -0.2195 | -0.2195 | -0.2195 | -0.2195 | -0.2195 |
| × max(0, log(men_raw/340)) | -0.6908 | -0.6908 | -0.6908 | -0.6908 | -0.6908 | -0.6908 |
| × accuracy | -0.0075 | -0.0075 | -0.0075 | -0.0075 | -0.0075 | -0.0075 |
| × log(1+accuracy) | +0.4625 | +0.5021 | +0.5022 | +0.3515 | +0.5500 | +0.4548 |
| × reload_skill | +0.0053 | +0.0053 | +0.0053 | +0.0053 | +0.0053 | +0.0053 |
| × log(1+reload_skill) | -0.0970 | -0.0797 | +0.0567 | -0.0196 | +0.0364 | -0.1432 |
| × ammo | +0.0004 | +0.0004 | +0.0004 | +0.0004 | +0.0004 | +0.0004 |
| × log(1+ammo) | -0.0306 | -0.0727 | -0.0083 | -0.0310 | -0.1564 | -0.0412 |
| × morale | +0.0475 | +0.0475 | +0.0475 | +0.0475 | +0.0475 | +0.0475 |
| × log(1+morale) | -0.1277 | -0.0562 | -0.1231 | -0.0343 | +0.0950 | -0.1668 |
| × melee_attack | -0.0020 | -0.0020 | -0.0020 | -0.0020 | -0.0020 | -0.0020 |
| × log(1+melee_attack) | +0.3713 | +0.3265 | +0.3974 | +0.4701 | +0.7274 | +0.1467 |
| × melee_defense | -0.0205 | -0.0205 | -0.0205 | -0.0205 | -0.0205 | -0.0205 |
| × log(1+melee_defense) | +0.3177 | +0.1889 | +0.1741 | +0.2710 | +0.1568 | +0.2724 |
| × charge_bonus | -0.0084 | -0.0084 | -0.0084 | -0.0084 | -0.0084 | -0.0084 |
| × log(1+charge_bonus) | +0.1975 | +0.1096 | +0.2577 | +0.3207 | +0.4018 | +0.0694 |
| if can_form_square | +0.122 | +0.122 | +0.122 | +0.122 | +0.122 | +0.122 |
| if has_stamina | +0.089 | +0.089 | +0.089 | +0.089 | +0.089 | +0.089 |
| if is_shock_resistant | +0.096 | +0.096 | +0.096 | +0.096 | +0.096 | +0.096 |
| if can_inspire | +0.082 | +0.082 | +0.082 | +0.082 | +0.082 | +0.082 |
| if has_guerrilla_deployment | +0.497 | +0.497 | +0.497 | +0.497 | +0.497 | +0.497 |
| if can_place_stakes | +0.105 | +0.105 | +0.105 | +0.105 | +0.105 | +0.105 |
| if can_place_mines | -0.090 | -0.090 | -0.090 | -0.090 | -0.090 | -0.090 |
| if scares_enemies | -0.110 | -0.110 | -0.110 | -0.110 | -0.110 | -0.110 |
| if can_build_barricades | -0.052 | -0.052 | -0.052 | -0.052 | -0.052 | -0.052 |
| if skirmish | -1.010 | -1.010 | -1.010 | -1.010 | -1.010 | -1.010 |
| if guard_mode | -0.005 | -0.005 | -0.005 | -0.005 | -0.005 | -0.005 |
| if can_snipe | +0.519 | +0.519 | +0.519 | +0.519 | +0.519 | +0.519 |
| if pike_square | +0.032 | +0.032 | +0.032 | +0.032 | +0.032 | +0.032 |

Training level: poorly_trained -0.012, mob -0.008, well_trained +0.004, trained +0.007, elite +0.009

Speed code: G1 -0.019, G2 -0.128, G3 -0.052, G4 +0.039, G5 +0.132, G6 +0.229, GS1 -0.391, GS2 -0.131, GS3 +0.134, L1 -0.322, L2 -0.172, L3 -0.059, L4 +0.009, L5 +0.091, L6 +0.138, S1 -0.131, S2 +0.159, S3 +0.473

Army terms: × log(corps_number) -0.9166; if empire -0.037; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.


#### Cavalry (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + corps terms + army offset + army×class offset

| term | heavy | lancers | light | missile | standard |
|---|---|---|---|---|---|
| constant (intercept + class) | +5.373 | +5.547 | +5.791 | +5.771 | +5.362 |
| × log(size) [size = men_raw] | +0.1563 | +0.1289 | +0.0908 | +0.1274 | +0.1285 |
| × max(0, log(men_raw/100)) | +0.7779 | +0.7779 | +0.7779 | +0.7779 | +0.7779 |
| × max(0, log(men_raw/130)) | -0.4656 | -0.4656 | -0.4656 | -0.4656 | -0.4656 |
| × max(0, log(men_raw/170)) | +0.2203 | +0.2203 | +0.2203 | +0.2203 | +0.2203 |
| × max(0, log(men_raw/230)) | -0.1673 | -0.1673 | -0.1673 | -0.1673 | -0.1673 |
| × accuracy | +0.0303 | +0.0303 | +0.0303 | +0.0303 | +0.0303 |
| × log(1+accuracy) | -0.5007 | -0.5007 | -0.5146 | -0.4938 | -0.4939 |
| × reload_skill | +0.0012 | +0.0012 | +0.0012 | +0.0012 | +0.0012 |
| × log(1+reload_skill) | -0.0421 | -0.0421 | -0.0545 | -0.0352 | -0.0367 |
| × ammo | -0.0206 | -0.0206 | -0.0206 | -0.0206 | -0.0206 |
| × log(1+ammo) | +0.5139 | +0.5139 | +0.5188 | +0.5016 | +0.5216 |
| × morale | +0.0033 | +0.0033 | +0.0033 | +0.0033 | +0.0033 |
| × log(1+morale) | +0.3181 | +0.3096 | +0.2527 | +0.2833 | +0.3190 |
| × melee_attack | -0.0233 | -0.0233 | -0.0233 | -0.0233 | -0.0233 |
| × log(1+melee_attack) | +0.4064 | +0.4193 | +0.4449 | +0.4191 | +0.4568 |
| × melee_defense | +0.0036 | +0.0036 | +0.0036 | +0.0036 | +0.0036 |
| × log(1+melee_defense) | +0.0303 | -0.0163 | +0.0591 | +0.0020 | +0.0306 |
| × charge_bonus | -0.0119 | -0.0119 | -0.0119 | -0.0119 | -0.0119 |
| × log(1+charge_bonus) | +0.3105 | +0.2738 | +0.2372 | +0.2670 | +0.2393 |
| if has_stamina | +0.231 | +0.231 | +0.231 | +0.231 | +0.231 |
| if is_shock_resistant | +0.302 | +0.302 | +0.302 | +0.302 | +0.302 |
| if can_inspire | +0.135 | +0.135 | +0.135 | +0.135 | +0.135 |
| if has_guerrilla_deployment | +0.285 | +0.285 | +0.285 | +0.285 | +0.285 |
| if skirmish | -0.137 | -0.137 | -0.137 | -0.137 | -0.137 |

Training level: mob -0.033, elite -0.000, well_trained +0.003, poorly_trained +0.015, trained +0.015

Speed code: C1 -0.005, C2 +0.011, C3 +0.072, C4 +0.066, C5 +0.117, L1 -0.262

Army terms: × log(corps_number) -0.9647; if empire -0.056; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.


#### Artillery (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + gun table + calibre terms + corps terms + army offset + army×class offset

| term | foot | horse |
|---|---|---|
| constant (intercept + class) | +4.358 | +4.893 |
| × log(size) [size = guns] | +1.2094 | +1.2520 |
| × accuracy | +0.0090 | +0.0090 |
| × log(1+accuracy) | -0.1591 | -0.1996 |
| × reload_skill | +0.0037 | +0.0037 |
| × log(1+reload_skill) | -0.0099 | -0.0352 |
| × morale | +0.0288 | +0.0288 |
| × log(1+morale) | -0.0547 | -0.0173 |
| × melee_attack | -0.0026 | -0.0026 |
| × log(1+melee_attack) | +0.1055 | +0.0903 |
| × melee_defense | -0.0791 | -0.0791 |
| × log(1+melee_defense) | +0.4462 | +0.4635 |
| × charge_bonus | +0.0852 | +0.0852 |
| × log(1+charge_bonus) | -0.1470 | -0.1355 |
| if has_stamina | +0.141 | +0.141 |
| if can_inspire | +0.188 | +0.188 |
| if has_guerrilla_deployment | +0.274 | +0.274 |

Training level: elite -0.045, poorly_trained +0.012, trained +0.015, well_trained +0.019

Speed code: F1 -0.289, F2 -0.273, F3 -0.169, F4 +0.031, F5 +0.253, F6 +0.447, H1 -0.257, H2 -0.026, H3 +0.283

Gun-count table (add; 3 guns = 0; 5 = 5 or more): 1 guns -0.900, 2 guns -0.142, 4 guns +0.060, 5 guns +0.124

Projectile table: 2_pounder -0.078, howitzer_7_pounder shell -0.070, unicorn_20_pounder shell -0.066, 6_pounder -0.048, 3_pounder -0.043, howitzer_6_In shell -0.022, 18_pounder -0.021, 10_pounder -0.017, 64_pounder -0.010, 8_pounder -0.003, 24_pounder +0.008, 9_pounder +0.035, 12_pounder +0.044, howitzer_5_In shell +0.059, 4_pounder +0.065, 5_pounder +0.070, unicorn_10_pounder shell +0.097

Calibre/ballistics: × log(projectile_damage) +0.2627; if howitzer/unicorn shell -1.004; × log(range) -0.5034; × log(projectile_reload_time) +1.3880

Army terms: × log(corps_number) -0.9427; if empire -0.046; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.


### 4.3 Army lookup tables

- `out/army_offsets_M1.csv`: one log-offset per army and arm (≈ 700 entries, shrunk towards 0; sd ≈ 0.05, i.e. about
  ±5 %; extremes −0.24 … +0.10).
- `out/army_class_offsets_M1.csv`: one log-offset per army × unit class (1 794 cells, shrunk; sd 0.04 for infantry,
  0.06 for cavalry and artillery).
- These two tables lower the CV error from 47.5 (M2, no tables) to 34.1 gold. They are idiosyncratic: the army offsets
  correlate only weakly between the arms of the same army (r ≈ 0.25–0.30), not at all with corps number, and neither
  table is explained by simple roster summaries (class share, number of units, mean stats, mean predicted value; all
  |r| < 0.25). They cannot be predicted for a new army.

### 4.4 M2 (army-blind variant)

Same unit formula as M1, plus small lookup tables for the faction-key codes (the two-digit number after a/b in
`faction_key`, the x-digit and the "r" letter), and no army tables. Reported for comparison only — M1 with zero offsets
is better on new armies. Coefficients are reproducible with `src/final.py`.

### 4.5 Staff generals (G-ST1)

price = T[stars] × (corps_number / 8)^−0.932, where T is the price in a corps-number-8 army:

| command stars | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| T (gold) | 80 | 209 | 365 | 546 | 746 | 935 | 1 131 | 1 315 | 1 522 |

Generals without stars cost 1–2 gold (use 1). A cavalry-general flag adds nothing (G-ST2). Each star adds ~130–200
gold at corps number 8, slightly more per star from 3 stars up.

### 4.6 Combat-general versions (G-CV4)

price_version = a_arm × price_regular + z × (S[stars] + c_arm + Σ w·Δstat), with z = (8 / corps_number)^0.93 and
Δstat = version stat − regular stat (least squares weighted by 1/price_regular). All-data coefficients:

- a = 1.018 (infantry), 0.940 (cavalry), 0.997 (artillery)
- S[stars 0, 1, 2, 3, 4, 5, 6+] = −129, −134, −67, −53, +44, +81, +368 gold
- c_cavalry = +2, c_artillery = +50 gold
- w (gold per point of stat change): accuracy +30.0, reload −6.9, morale −8.0, melee attack +0.1, melee defence +58.6,
  charge −7.1

In words: a combat general's version costs about the regular unit's price, adjusted by a star-dependent amount — roughly
130 gold *less* at 0–1 stars, about the same at 3–4 stars once its stat bonuses are counted, and up to ~370 gold more
at 6+ stars — all scaled by the corps factor. A multiplicative form (G-CV2) is clearly worse (49 vs 36 gold).

## 5. How price depends on unit size

Local elasticity = % price change per 1 % more soldiers, holding everything else fixed (M1, all-data fit). Size is
men_raw for infantry and cavalry.

| infantry class | men_raw range | < 150 | 150–200 | 200–260 | 260–340 | > 340 |
|---|---|---|---|---|---|---|
| line | 128–452 | 0.31 | 1.69 | 0.99 | 0.77 | 0.08 |
| light | 140–422 | 0.28 | 1.67 | 0.96 | 0.74 | 0.05 |
| grenadiers | 116–442 | 0.33 | 1.72 | 1.01 | 0.79 | 0.10 |
| militia | 146–974 | 0.41 | 1.80 | 1.09 | 0.87 | 0.18 |
| irregulars | 128–974 | 0.49 | 1.88 | 1.17 | 0.95 | 0.26 |
| skirmishers | 46–272 | 0.65 | 2.04 | 1.33 | 1.11 | – |

| cavalry class | < 100 | 100–130 | 130–170 | 170–230 | > 230 |
|---|---|---|---|---|---|
| heavy | 0.16 | 0.93 | 0.47 | 0.69 | 0.52 |
| standard / lancers / missile | 0.13 | 0.91 | 0.44 | 0.66 | 0.49 |
| light | 0.09 | 0.87 | 0.40 | 0.62 | 0.46 |

| guns | 1 | 2 | 3 | 4 | 5 | 6 | 8 |
|---|---|---|---|---|---|---|---|
| foot artillery, price factor vs 3 guns | 0.11 | 0.53 | 1.00 | 1.50 | 2.10 | 2.62 | 3.71 |
| horse artillery, price factor vs 3 guns | 0.10 | 0.52 | 1.00 | 1.52 | 2.15 | 2.70 | 3.87 |

- **Not a single power law.** A single log-size slope (E01–E03c) and a quadratic in log size (E03d) were clearly worse
  than a piecewise curve with bends (E07, E10). For infantry the curve is S-shaped: shallow below 150 men_raw (a small
  company costs nearly as much as a 150-man unit), steep between 150 and 200, about proportional (elasticity ≈ 1)
  between 200 and 260, bending down above 260 and almost flat above 340 (the very large line and militia units are
  cheap per man). Cavalry: almost flat below 100 men_raw, then roughly elasticity 0.4–0.9.
- **Classes differ in steepness, not in shape.** The bends sit at the same sizes for all classes of an arm (separate
  bends per class did not help, E07b), but skirmishers (+0.34 vs line), irregulars (+0.18) and militia (+0.10) are
  steeper throughout; light infantry is the flattest. Cavalry classes are nearly identical, heavy cavalry a little steeper.
- **Training level** barely changes the slope (training-specific slopes gained 0.1 gold, E08b). Once the stats are in the
  formula, training level itself is worth only ±1–3 %.
- **Artillery**: price per gun rises with the number of guns; a 1-gun section costs ~10 % of a 3-gun battery, and from
  2 guns up each extra gun adds about half the 3-gun price. Calibre enters through the projectile (table and ballistic
  terms) rather than through crew size; horse and foot follow the same gun-count curve.

Out-of-fold error by size band (M1 final, with M2 and baseline B1 for comparison):

| arm | size band | n | M1 MAE | M1 MAPE | M2 MAE | M2 MAPE | B1 MAE | mean price |
|---|---|---|---|---|---|---|---|---|
| infantry | men_display < 40 | 93 | 28.2 | 9.4 % | 34.1 | 11.3 % | 100.1 | 272 |
| infantry | 40–60 | 214 | 30.4 | 9.5 % | 31.7 | 9.8 % | 110.3 | 305 |
| infantry | 60–80 | 230 | 41.7 | 9.7 % | 43.2 | 10.2 % | 132.8 | 418 |
| infantry | 80–100 | 719 | 22.8 | 5.1 % | 28.9 | 6.5 % | 131.5 | 418 |
| infantry | 100–140 | 2 005 | 20.5 | 4.0 % | 29.0 | 5.4 % | 175.1 | 523 |
| infantry | 140–180 | 1 042 | 29.2 | 6.0 % | 39.5 | 7.5 % | 234.0 | 573 |
| infantry | 180–240 | 221 | 57.3 | 11.5 % | 60.1 | 12.3 % | 309.2 | 578 |
| infantry | > 240 | 13 | 34.2 | 8.9 % | 61.3 | 14.4 % | 354.4 | 360 |
| cavalry | men_display < 40 | 22 | 79.7 | 36.5 % | 104.5 | 46.2 % | 348.0 | 745 |
| cavalry | 40–60 | 596 | 39.9 | 5.5 % | 57.9 | 8.0 % | 241.2 | 701 |
| cavalry | 60–80 | 542 | 46.7 | 5.2 % | 73.6 | 8.2 % | 275.1 | 875 |
| cavalry | 80–100 | 324 | 50.4 | 5.1 % | 73.6 | 7.0 % | 318.8 | 1 023 |
| cavalry | 100–140 | 203 | 59.3 | 4.8 % | 95.4 | 7.5 % | 446.2 | 1 289 |
| cavalry | 140–180 | 26 | 55.9 | 3.5 % | 88.5 | 5.2 % | 678.2 | 1 655 |
| cavalry | 180–240 | 2 | 51.0 | 5.7 % | 1.5 | 0.2 % | 1 287.9 | 879 |
| artillery | 1 gun | 41 | 15.7 | 13.9 % | 16.8 | 15.3 % | 201.4 | 123 |
| artillery | 2 guns | 337 | 33.3 | 6.1 % | 44.6 | 8.6 % | 163.7 | 541 |
| artillery | 3 guns | 418 | 51.1 | 5.9 % | 80.5 | 9.2 % | 222.8 | 867 |
| artillery | 4 guns | 114 | 71.6 | 6.0 % | 105.2 | 9.1 % | 294.0 | 1 222 |
| artillery | 5+ guns | 29 | 105.7 | 6.9 % | 129.1 | 9.2 % | 279.8 | 1 359 |

The model is most reliable at the common sizes (infantry 80–180 men_display, cavalry 40–180, 2–4 guns) and weakest at
the extremes: small infantry (< 80 men_display — mostly skirmishers and detachments), the largest infantry (180–240),
tiny cavalry (< 40, only 22 units, one of them a 43-gold outlier) and single guns (large percentages on small prices:
16 gold average error).

## 6. How price depends on the army

- **Corps number is the dominant army effect.** Without it, army-level price levels span a factor of about 3. In M1,
  log(price) falls by 0.917 (infantry), 0.965 (cavalry) and 0.943 (artillery) per unit of log(corps_number): price is
  close to inversely proportional to the corps number. Factor relative to a corps-number-8 army:

  | corps number | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | infantry | 2.46 | 1.89 | 1.54 | 1.30 | 1.13 | 1.00 | 0.90 | 0.82 | 0.75 | 0.69 | 0.64 |
  | cavalry | 2.58 | 1.95 | 1.57 | 1.32 | 1.14 | 1.00 | 0.89 | 0.81 | 0.74 | 0.68 | 0.63 |
  | artillery | 2.52 | 1.92 | 1.56 | 1.31 | 1.13 | 1.00 | 0.90 | 0.81 | 0.74 | 0.68 | 0.63 |

  One log(corps_number) slope fits as well as a separate factor per corps number (E07d vs E07a) and better than a
  straight line in corps number (E04e) or 1/corps_number. Staff generals follow the same law (exponent −0.93). In the
  data, the list value of a full roster (Σ unit_cap × price) shows no trend with corps number (about 26 000–39 000 gold)
  while high-numbered armies have bigger rosters — the corps number acts like a divisor that keeps whole rosters at a
  similar total.
- **Side**: empire armies are 3.7 % (infantry), 5.5 % (cavalry) and 4.5 % (artillery) cheaper than coalition armies with
  the same corps number and units.
- **The army itself**: after corps number and side, each army keeps its own factor (sd ≈ 5 % per arm, extremes −21 % …
  +10 %) plus an army×class factor of similar size. These are only weakly shared between arms of the same army
  (r 0.24–0.30), unrelated to corps number, and not explained by roster summaries; the faction-key codes explain a
  little (E04b vs E03f: 51.1 vs 52.9 gold) but not enough to beat M1 with zero offsets on new armies. For a new army
  expect about ±8 % error (unseen-army test), of which roughly 5 points are this unpredictable army factor.

## 7. Error analysis (M1, out-of-fold)

- **By class**: best for line infantry (4.6 %), light infantry (4.9 %), light cavalry (5.2 %), foot artillery (5.4 %);
  worst for skirmishers (10.3 %), irregulars (11.0 %), militia (9.1 %) and horse artillery (8.8 %; 10 % of horse
  batteries are off by more than 20 %). Bias is negligible everywhere (median log ratio within ±0.012).
- **By training**: well-trained 4.9 %, trained 5.6 %, poorly trained 7.3 %, mob 8.1 %; elite units have the largest gold
  errors (68 gold) because they are the dearest (6.5 %).
- **By corps number**: error falls as the corps number rises (corps 3: 13.4 %, 126 gold — only 40 units in 3 armies;
  corps 10–13: 4.5–5.7 %). Low-numbered armies are dear, rare and more irregular.
- **Clustering**: after M1, only 1.2 % of the remaining (log) error variance is a shared army effect, but 27 % is shared
  within army × class cells — misses cluster by army-and-type more than by army or type alone. For M2 (no tables) the
  shares are 15 % (army) and 62 % (army × class), which is what M1's tables capture.
- **Worst armies** (MAPE): 3. Kindelán / Florida 25 % (10 units), 5. Ibrahim / Ghugha 19 %, 7. Garde impériale
  (`ntw3_ac_a06_x4_105`) 19 %, 9. Soult / Sud 18 % (56 units), 6. Davidov / Narod 15 %. Best: 10. Tchitchagov / D.ZA
  2.5 %, 9. Konstantin / O.LG 2.6 %, 8. Toutchkov / III.K 2.7 %.
- **Largest single misses** look like special cases the attributes do not reveal: *1er lanciers d'Espagne* (Soult / Sud)
  costs 43 gold (predicted 311); *Simanó-li 'Seminole'* skirmishers cost 955 (predicted 2 430); *Gendarmes d'élite* in a
  Garde impériale army 416 (predicted 965); Portuguese *Ordenanças* militia 387 (predicted 136); *Lanciers de la
  Vistule* 1 036 (predicted 412); several 1-gun or 4-pounder horse batteries 50–80 % cheaper than predicted; the 18-pdr
  naval battery in Chabot / Corfou 1 473 (predicted 2 498).
- **Unseen armies**: 6–10 % error for most holdout armies; the two corps-number-3 armies are the worst (Suchet / Alpes
  over-predicted by 15 % on median, 17 % error; Kindelán / Florida 24 % error) — the thin data at corps number 3.

## 8. Limitations

- "Readable" but not tiny: per arm ~40 shared coefficients plus per-class columns, small lookup tables (training, speed
  code, projectile, gun count) and the two army tables (≈ 700 army and ≈ 1 800 army×class entries). Without the army
  tables accuracy drops from 5.7 % to 7.6 % (M2).
- Coefficients of related terms (linear vs log stats; the artillery calibre set; overlapping abilities) are not
  individually meaningful — only their sum is. Rare abilities (e.g. the infantry `skirmish` flag, −1.01) rest on few
  units and absorb class quirks.
- Size effects are estimated *holding stats fixed*; because size, class and stats are correlated, the S-shaped infantry
  curve partly reflects which kinds of units come in which sizes.
- Prices contain hand-set components (army × class factors, single exceptions such as a 43-gold lancer unit) that no
  attribute explains; most of the remaining 5–6 % error is of this kind.
- The unseen-army test is one split of 17 armies, 8 of them low-numbered; its figures are noisier than the CV ones.
- The combat-general models need the regular unit's true price; with M1's *predicted* regular price instead, the error
  grows (G-CV3: 63 gold vs 49 for the same model on the true price).

## 9. Files

- `src/common.py`, `src/harness.py`, `src/features.py`, `src/models.py` — data loading, CV over the given folds,
  generalised ridge, configurable per-arm model.
- `src/e00_baselines.py`, `src/e01_loglinear.py`, `src/run_variants.py` (experiments E03–E10), `src/eda*.py` (exploration).
- `src/final.py` — final M1/M2 with nested penalty selection and the unseen-army test; `src/analysis.py` — size curves,
  army and error analysis, CSV outputs; `src/writeout.py` — coefficient tables (section 4.2); `src/example.py` — worked
  example; `src/table.py` — metrics table; `src/generals.py`, `src/generals2.py`, `src/generals_csv.py` — staff and combat generals.
- `out/oof_predictions.csv` (faction_key, unit_key, fold, unit_class, price, pred_M1, pred_M2, pred_B0, pred_B1),
  `out/holdout_predictions.csv` (unseen-army test, same columns), `out/generals_oof.csv` (staff G-ST1; combat generals G-CV2, G-CV3, G-CV4, G-CV5), `out/coefs_M1_<arm>.csv`,
  `out/model_M1.md`, `out/army_offsets_M1.csv`, `out/army_class_offsets_M1.csv`, `out/analysis.txt`,
  `out/final_table.md`, `out/final_M1.json`, `out/final_M2.json`.
- `RESULTS.md` (every experiment), `NOTES.md` (running notes).
