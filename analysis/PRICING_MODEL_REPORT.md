# NTW3 unit pricing model — final summary

*Theatre-of-War and Custom armies · branch `analysis/unit-pricing`, October 2026*

A readable formula that predicts the multiplayer price (`base_mp_cost`) of every
regular unit and staff general in NTW3's Theatre-of-War (ToW) and Custom armies
from the unit's stats, type, size and army. It is fitted on the game's own
data export, validated by 5-fold cross-validation, and written out below in
full. A unit's price can be reproduced by hand from
`analysis/output/coefficients.csv`.

---

## 1. Results at a glance

Cross-validated accuracy on units the model did not see. MAE is the mean
absolute error in gold; MAPE the mean absolute percentage error.

| Arm | Units | Median price | MAE | MAPE | R² (stats only) |
| --- | --- | --- | --- | --- | --- |
| Infantry | 4 370 | 358 | **27.4** | **7.7%** | 0.943 |
| Cavalry | 1 724 | 727 | **34.9** | **4.6%** | 0.958 |
| Artillery | 894 | 591 | **32.4** | **6.8%** | 0.955 |
| Staff generals | 288 | 202 | **8.6** (2.3 with faction modifier) | 2.2% | 0.989 |

How the error came down, MAE in gold (infantry / cavalry / artillery):

| Model | Infantry | Cavalry | Artillery |
| --- | --- | --- | --- |
| Class mean × unit size (baseline) | 143.9 | 252.4 | 163.1 |
| Linear stats, models, p = 1 (first model) | 38.5 | 60.6 | 74.6 |
| + size powers, stat powers, calibre curve | 34.6 | 59.2 | 49.7 |
| + one faction modifier per arm | 32.9 | 54.1 | 46.8 |
| **+ army × unit-class multiplier around 8/N (adopted)** | **27.4** | **34.9** | **32.4** |
| Per-class alternative V4: own formula and size power per class (§6) | 24.9 | 32.8 | 27.2 |
| Blind study's best model (13c), same units | 21.9 | 36.8 | 35.5 |

The blind study was an independent attempt in a fresh session that knew nothing
of this model (branch `blind-pricing-study`). Its key finding, a per-army
price adjustment per unit type, is what the adopted step brings over. The
adopted model now beats the blind study's best on cavalry and artillery; it
still trails on infantry.

**Two versions of the model:**
- **The adopted model** (§2–3) shares stat coefficients across the unit classes
  of an arm, so classes can be compared like for like.
- **The per-class alternative V4** (§6) gives each class its own formula. It is
  more accurate, especially for militia, grenadiers and horse artillery, but its
  classes can only be compared through their predicted prices.

---

## 2. The model

### 2.1 Regular units

For a unit of arm *a* (infantry, cavalry, artillery) in army *f* with corps
number *N*:

$$
\text{price} \;=\; \underbrace{\frac{8}{N}}_{\text{army divisor}}
\;\cdot\; \underbrace{m_{f,\,\text{class}}}_{\text{army}\times\text{class}}
\;\cdot\; \underbrace{M_a}_{\text{arm factor}}
\;\cdot\; S^{\,p_a}
\;\cdot\; \Bigl(b_0 + \sum_k \beta_k\,\phi_k(x)\Bigr)
\;+\; c_a
$$

| Symbol | Meaning |
| --- | --- |
| *N* | The corps number that opens the army name ("[1812] **7.** Danmark" → 7), i.e. the corps rating. Price scales with 1/N: identical units in armies with different N cost in proportion to 1/N (blind study: median ratio 0.999 over 85 pairs). The 8 only sets the scale; any constant gives the same prices. |
| *S* | Unit size: **models** (= men ÷ 2) for infantry and cavalry, **guns** for artillery (crew per gun is fixed by type, 10 foot / 6 horse, so models would misprice one artillery type against the other). |
| *p*ₐ | Size power: infantry 1.09, cavalry 0.75, artillery 1.3. |
| *b*₀ + Σβφ | Value of one size unit at rating 8, a linear sum over the unit's features: stats (some raised to a power), trait flags, unit class, speed tier and, for artillery, shot type and a calibre curve. |
| φₖ(x) | A stat enters as (stat ÷ 100)^aₖ. A flag is 0/1; class, speed and shot are one-hot. |
| *m*_{f, class} | Army × unit-class multiplier, one per (army, class) cell with units. It is fitted with a ridge pull towards 1 worth κ "pseudo-units" of average price (κ = 1 for infantry and cavalry, 0.5 for artillery, chosen by cross-validation). 1 means "priced as the rating alone predicts". A cell with no training data falls back to 1. |
| *M*ₐ | Arm-specific factor. Infantry: side (imperial ×0.884, coalition ×1). Cavalry: packing, 1 + δ·(rank depth − 11), δ = −0.0168. Artillery: none. |
| *c*ₐ | Flat per-unit constant outside the multipliers: artillery only, −161.5 gold. |

The fit is alternating least squares on price per size unit. The stat powers,
size power and model structure were chosen by nested cross-validation (§4).

### 2.2 Staff generals

$$
\text{price} \;=\;
\begin{cases}
1 & \text{no command stars}\\[2pt]
76.55\cdot \text{stars}^{1.39}\cdot \dfrac{8}{N} & \text{otherwise}
\end{cases}
$$

At N = 10 this is 61.2·stars^1.39, close to the blind study's 60.4·stars^1.4.
An optional per-army faction modifier on top (TF3) brings the error from 8.6
to 2.3 gold.

### 2.3 Worked example

*1. Jydske linje Infanterie 'Bauditz' [L3]*, 7. Danmark (N = 7, imperial),
line infantry, speed L3, 130 models; actual price **317**.

| Feature | φ(x) | β | β·φ |
| --- | --- | --- | --- |
| intercept b₀ | — | — | +3.453 |
| accuracy 19 | (0.19)^0.05 = 0.920 | 8.425 | +7.753 |
| reload skill 41 | (0.41)^3.1 = 0.063 | 1.427 | +0.090 |
| ammo 39 | (0.39)^0.05 = 0.954 | 0.854 | +0.815 |
| morale 5 | (0.05)^2.25 = 0.0012 | 122.5 | +0.145 |
| melee attack 12 | (0.12)^1.4 = 0.051 | 14.17 | +0.728 |
| melee defence 9 | (0.09)^1.15 = 0.063 | 5.161 | +0.324 |
| charge bonus 19 | (0.19)^0.05 = 0.920 | −3.700 | −3.405 |
| range 70 | (0.70)^4 = 0.240 | 0.026 | +0.006 |
| has a ranged weapon | 1 | −8.372 | −8.372 |
| **b₀ + Σβφ** | | | **1.538** |

Price = (8/7) × 0.918 (Danmark × line) × 0.884 (imperial) × 130^1.09 (= 201.5)
× 1.538 = **287.2**, against 317 actual (−9%).

---

## 3. Parameters

All values are the full-data fit, merged imperial + coalition. Complete
tables, including every army × class cell, are in
`analysis/output/coefficients.csv` (variant `FC`); the staff general rule is
variant `T3`.

### 3.1 Stat powers and the main stat coefficients

β is gold per size unit^p at rating 8, for the column (stat ÷ 100)^power.

| Stat | Infantry: power | Infantry: β | Cavalry (linear): β | Artillery: power | Artillery: β |
| --- | --- | --- | --- | --- | --- |
| morale | 2.25 | 122.5 | 0.955 | 3 | 32 029 |
| melee attack | 1.4 | 14.17 | 0.305 | 2.5 | 5 792 |
| melee defence | 1.15 | 5.161 | 0.287 | 3 | 99 220 |
| charge bonus | 0.05 | −3.700 | 1.331 | 0.25 | 1.29 |
| accuracy | 0.05 | 8.425 | 0.093 | 3 | 86.4 |
| reload skill | 3.1 | 1.427 | −0.027 | 2 | 72.6 |
| ammo | 0.05 | 0.854 | −0.053 | — | — |
| range | 4 | 0.026 | 0.157 | (calibre curve) | |
| intercept b₀ | | 3.453 | 4.725 | | −3 872 |

Cavalry stats are linear: the power search did not beat linear by more than
one SE. Artillery's large β values multiply tiny powered values, e.g.
(0.08)³ for morale 8, and are offset by its intercept, so read them only
jointly.

### 3.2 Traits, class, speed

| Feature | Infantry | Cavalry | Artillery |
| --- | --- | --- | --- |
| has a ranged weapon | −8.37 | −9.01 | — |
| stamina | +0.18 | +7.17 | +31.3 |
| shock resistant | +0.23 | +10.59 | — |
| inspire | +0.51 | +9.39 | +39.7 |
| guerrilla deployment | +2.04 | +11.16 | +59.0 |
| can snipe | +2.27 | — | — |
| solid square / stakes / mines / guard mode | +0.33 / +0.06 / −0.32 / −0.08 | — | — |
| camel | — | −19.08 | — |
| class (vs line / light / foot) | grenadiers −0.06, light −0.09, militia −0.02, irregulars +0.01 | heavy −2.80, lancers −1.47, missile −1.19, standard −0.96 | horse +175.5 |
| speed tiers (vs L3 / C4 / F3) | G1 −0.30 … G6 +1.15; L1 −0.21 … L6 +0.52; S1 −1.37, S2 −0.21, S3 +1.92 | C1 −3.20, C3 −2.42, C5 −1.73 | F1 −52.8 … F6 +124.1; H1 −144.1, H2 −85.0 |

### 3.3 Artillery calibre and shot

The calibre effect is a natural cubic spline in log(range) with 5 degrees of
freedom. Its knots are at range 250, 336, 394, 479, 655 and 1 400, unit-weighted
quantiles, and it is linear beyond the end knots. Coefficients cal_r1…cal_r5:
+691.6, −3 238.1, +10 083.1, −8 574.2, +1 723.9 (basis defined in
`natural_spline_basis`).

- **Shot type** (vs round shot): howitzer shell +26.3, unicorn shell +23.5.
- **Why range:** every projectile has exactly one range and damage, so calibre
  determines both. The spline in log range matches a free one-hot per cannon
  type (49.7 vs 49.4 MAE) with 9 fewer parameters, and also prices a calibre
  that never appears in the data.
- **The one-hot version** is kept in `analysis/calibre_onehot_results/`.

### 3.4 Army × unit-class multipliers

| Arm | Cells | Median | 10th–90th percentile | Range |
| --- | --- | --- | --- | --- |
| Infantry | 261 | 0.994 | 0.888 – 1.083 | 0.628 – 1.417 |
| Cavalry | 192 | 1.003 | 0.905 – 1.075 | 0.570 – 1.261 |
| Artillery | 108 | 0.996 | 0.895 – 1.099 | 0.635 – 1.160 |

The most extreme cells, i.e. the clearest "hand-set" prices:

- **Cheapest:**
  - Polska lancers ×0.57 and Russkiy narod lancers ×0.77;
  - España irregulars ×0.63 and Piemonte-Sardegna militia ×0.65;
  - Danmark horse artillery ×0.64.
- **Dearest:**
  - Piemonte-Sardegna skirmishers ×1.42 and Osmanlı skirmishers ×1.34;
  - UK, España, Portugal heavy cavalry ×1.26 and HRE heavy cavalry ×1.21;
  - Rossiya horse artillery ×1.16.

The full lists are in `unit_pricing_report.md` §10.

---

## 4. How it was built and validated

- **Data.** `data/generated/ntw3_units_analysis.csv`, exported from the game's
  `.pack` tables. Scope: every ToW and Custom unit.
  - Excluded: the developer joke and placeholder corps (`aaa_lordz`, `austria`,
    `hannover`, `saxony`) and fixed artillery.
  - Out of scope: commander variants (a general attached to a unit; §5).
- **Validation.** 5-fold cross-validation, where each fold is an 80/20 split:
  - identical units are kept together;
  - folds are stratified by class and speed;
  - every categorical level is guaranteed in training;
  - every army is spread evenly across folds.
  - Model choices (structure, powers, κ) are made *inside* training folds
    (nested CV), so the reported errors are honest.
- **Adoption rule.** A more complex model is adopted only if it beats the
  simpler one by more than one standard error. Among models within one SE of
  the best, the simplest wins.
- **Tested and rejected** (details in the per-experiment reports in
  `analysis/output/`):

| Idea | Result |
| --- | --- |
| Rating as a fixed 8/N divisor *without* the army × class cells | worse than free rating levels (+0.8 MAE) |
| Least-absolute-deviation loss | helps infantry, hurts cavalry; no overall gain |
| Army × class as a residual on top of the stat model | 32.0 pooled vs 29.9 for the joint fit |
| Shooting as a product (accuracy × reload × ammo …) | not better than the additive sum |
| Firearm one-hot instead of range | not better |
| Pinning extreme units into every training fold | no gain for typical units (+0.2 ± 0.1) |
| Blind study's per-type log-linear formulas *without* its army table | on par with ours (33.8 / 58.7 / 46.9) |

---

## 5. Limitations

1. **Very large units are overpriced.** Error grows with size above about 180
   models. Median residual (actual vs predicted):
   - 181–240 models: −9%;
   - 241–400 models: −28%;
   - the two 487-model units: −30% and −73%.

   Worst case: *Narodnoe gorodoskoe vosstanie* (Russkiy narod, 487 models)
   costs 608 but is predicted at ~2 200, and still ~1 900 when the model trains
   on it. Its smaller siblings cost more per man (118 models: 5.7 gold/model;
   218: 4.0; 487: 1.25). Almost every unit this big is mob or poorly trained
   militia, so size and quality are confounded. The game appears to discount
   very large units in a way one size power cannot follow.
2. **Tiny skirmisher units are underpriced** by about 16% (1–40 models), and
   51–80-model units overpriced by about 9%. Skirmishers scale with size at a
   power of about 0.8–0.9, not 1.09 (§6).
3. **The army × class table is descriptive, not explanatory.**
   - It is 561 cells. It captures what looks like hand-set balancing (e.g.
     Polska lancers at ×0.57), but says nothing about *why*.
   - A new army or a cell with no units is priced by the 8/N rule alone.
   - A cell with a single unit is shrunk about halfway towards 1, so its own price is only partly reproduced.
4. **Single coefficients are not always interpretable.**
   - Powers of 0.05 make accuracy, ammo and charge bonus nearly on/off flags.
     Together with "has a ranged weapon" they act as one "has a firearm"
     offset, so their individual signs (e.g. negative charge bonus) mean
     little.
   - Artillery's powered stats have very large, offsetting coefficients.
   - Read predictions, not single β.
5. **Stat powers were tuned before the army × class step** and not re-tuned
   after it. A joint re-tune could gain a little.
6. **Scope:**
   - Commander variants (about 42% of ToW + Custom rows) are not modelled.
   - Army Corps (non-ToW) prices are not modelled.
   - The 4 fixed artillery pieces are excluded.
7. **Accuracy varies by class.** Grenadiers (40 MAE), militia (38),
   skirmishers (39) and heavy cavalry (61) are fitted noticeably worse than
   line infantry (21) or lancers (28).
8. **Data snapshot.** The prices are from the v9.4/v9.6-era export in this
   repository; a balance patch would need a refit.

---

## 6. The per-class alternative (V4): one formula per unit class

There are two versions of the model, with a trade-off between them:

- **The adopted model (§2–3)** gives every class in an arm the *same* stat
  coefficients and size power. Classes differ only by an intercept shift and
  their army × class multipliers. This makes classes directly comparable: a
  point of morale is worth the same to a line regiment as to a grenadier
  regiment, so the model can say how much more a class costs for the same
  stats.
- **V4** gives each class its *own* formula and its *own* size power. It
  predicts better (below), but its coefficients live on different scales per
  class, so classes can only be compared through their predicted prices.

V4 was fitted by `analysis/class_structure.py` on the same folds. It isn't part
of `unit_pricing.py`; its coefficients are in
`analysis/output/class_structure_coefficients.csv`. Classes follow the blind
study's segments: militia and irregulars together, and light and missile
cavalry together, because irregulars (64 units) and missile cavalry (11) are
too small to stand alone.

### 6.1 Equation

For a unit of class *c*:

$$
\text{price} \;=\; \frac{8}{N}\;\cdot\; m'_{f,\,c}\;\cdot\; M_a\;\cdot\; S^{\,p_c}\;\cdot\;\Bigl(b_c + \sum_k \beta_{c,k}\,\phi_k(x)\Bigr) \;+\; c_a
$$

It is the adopted equation with three things made per class: the size power
*p*_c, the intercept *b*_c and every stat, trait and speed coefficient
β_{c,k}. Still shared by all classes of an arm:

- the stat powers inside φ(x), kept at the adopted values (not re-tuned);
- the 8/N divisor;
- the arm factor *M*ₐ;
- the artillery constant *c*ₐ.

The army × class multipliers *m*′ are refitted along with V4. The ridge κ
is the same as in the adopted model.

### 6.2 Accuracy

Cross-validated MAE in gold, same folds as the adopted model:

| | Adopted | V4 | Change (paired SE) |
| --- | --- | --- | --- |
| Infantry | 27.38 | **24.92** | −2.46 (0.25) |
| Cavalry | 34.71 | **32.77** | −1.95 (0.68) |
| Artillery | 32.36 | **27.15** | −5.21 (0.83) |

Per class:

| Class | Units | Adopted | V4 |
| --- | --- | --- | --- |
| Infantry line | 2 295 | 20.8 | 20.0 |
| Infantry light | 755 | 26.5 | 23.9 |
| Infantry grenadiers | 585 | 40.4 | 34.1 |
| Infantry skirmishers | 368 | 39.0 | 37.7 |
| Infantry militia + irregulars | 367 | 38.3 | 30.1 |
| Cavalry light + missile | 702 | 30.3 | 27.0 |
| Cavalry standard | 387 | 26.9 | 28.2 |
| Cavalry lancers | 326 | 28.3 | 27.7 |
| Cavalry heavy | 309 | 61.2 | 57.1 |
| Artillery foot | 631 | 27.4 | 24.3 |
| Artillery horse | 263 | 44.3 | 33.9 |

**Size-related fixes:**
- **Tiny skirmisher units (≤ 40 models):** the median residual falls from +16%
  to +7%.
- **The largest batteries (7+ guns):** from −8.6% to −1.9%.
- **Not fixed:** units above 240 models only improve from −30% to −23.5%. The
  giant militia stay overpriced.

For cavalry the 1-SE adoption rule would pick a simpler version: class as a
multiplier plus a size power per class (33.03). V4 is shown here for all
three arms so the two versions can be compared like for like.

### 6.3 Size power per class

| Arm | Adopted (shared) | V4 per class |
| --- | --- | --- |
| Infantry | 1.09 | grenadiers 1.3 · line 1.2 · light 1.2 · militia 1.0 · skirmishers 0.8 |
| Cavalry | 0.75 | heavy 0.8 · standard 0.8 · lancers 0.7 · light 0.7 |
| Artillery | 1.3 | foot 1.2 · horse 1.4 |

Skirmisher prices grow much more slowly with unit size than line infantry
prices, and horse artillery faster than foot. The shared power of the adopted
model sits between them, which is where its size-related errors come from.

### 6.4 Main coefficients per class

β is gold per size unit^p_c at rating 8, before the army × class multiplier;
stats enter as (stat ÷ 100)^power, with the powers as in §3.1. "—" means the
feature is constant within that class, so its intercept carries it.

**Infantry**

| Feature | Adopted (all) | Grenadiers | Light | Line | Militia | Skirmishers |
| --- | --- | --- | --- | --- | --- | --- |
| size power | 1.09 | 1.3 | 1.2 | 1.2 | 1.0 | 0.8 |
| intercept | 3.36–3.45 | −4.93 | −4.56 | −5.24 | 3.08 | 2.93 |
| morale ^2.25 | 122.5 | 32.5 | 63.6 | 84.9 | 230.0 | 437.2 |
| melee attack ^1.4 | 14.17 | 5.09 | 8.82 | 6.92 | 30.16 | 17.09 |
| melee defence ^1.15 | 5.16 | 3.06 | 2.32 | 1.97 | 6.87 | 115.2 |
| reload skill ^3.1 | 1.43 | 0.61 | 0.78 | 0.63 | 3.78 | 4.28 |
| accuracy ^0.05 | 8.43 | 6.87 | 2.66 | 4.91 | 8.98 | 38.2 |
| charge bonus ^0.05 | −3.70 | −0.73 | 0.66 | 0.76 | −7.92 | −12.64 |

**Cavalry** (linear stats)

| Feature | Adopted (all) | Heavy | Lancers | Light + missile | Standard |
| --- | --- | --- | --- | --- | --- |
| size power | 0.75 | 0.8 | 0.7 | 0.7 | 0.8 |
| intercept | 1.92–4.72 | 3.60 | 4.04 | 6.11 | 6.20 |
| morale | 0.955 | 0.979 | 1.395 | 1.031 | 0.656 |
| melee attack | 0.305 | 0.257 | 0.276 | 0.352 | 0.314 |
| melee defence | 0.287 | 0.131 | 0.316 | 0.408 | 0.136 |
| charge bonus | 1.331 | 0.711 | 1.541 | 2.028 | 0.713 |
| stamina | 7.17 | 7.25 | 7.45 | 8.36 | 6.15 |
| shock resistant | 10.59 | 10.56 | 11.23 | 13.33 | 8.27 |

**Artillery**

| Feature | Adopted (all) | Foot | Horse |
| --- | --- | --- | --- |
| size power | 1.3 | 1.2 | 1.4 |
| accuracy ^3 | 86.4 | 115.1 | 43.0 |
| reload skill ^2 | 72.6 | 77.0 | 81.1 |
| howitzer shell | 26.3 | 28.1 | 44.7 |
| unicorn shell | 23.5 | 30.4 | — |

The full per-class tables, with traits, speed tiers, the calibre spline and the
artillery intercepts, are in `analysis/output/class_structure_report.md`. Every
value is in `class_structure_coefficients.csv`.

**Reading these coefficients:**
- **Compare classes through predicted prices, not β.** Each class has its own
  intercept and size power, so a larger β does not by itself mean a dearer unit.
- **Skirmishers' large β values** (morale 437, melee defence 115, accuracy 38)
  come from a small class with a narrow stat range. They are partly offset by
  its negative ammo and charge-bonus terms (−23.5 and −12.6), so read them
  together.
- **Columns identical within a class share their effect equally.** For example,
  two skirmisher flags held by exactly the same units get the same coefficient.

### 6.5 Worked example

The same Bauditz line infantry as §2.3 (7. Danmark, 130 models, actual price
317): the adopted model gives 287.2 and V4 gives **293.3**. This reproduces
exactly from `class_structure_coefficients.csv`: line intercept and β, line
size power 1.2, V4's army × class cell and side factor.

### 6.6 Status

V4 is fully specified and reproducible, but `unit_pricing.py` still computes the
adopted model only. To make V4 the pipeline's model:
- add per-class size powers and per-class designs to `Spec`
  (`class_structure.segmented` and `fit_class_p` are the reference);
- re-run the full model (~50 minutes).

Keeping both versions is reasonable:
- the adopted model for comparing classes and explaining prices;
- V4 when the best price prediction is what matters.

---

## 7. Files

| File | What |
| --- | --- |
| `analysis/unit_pricing.py` | The full pipeline: structure search, powers, variants, final models, report |
| `analysis/output/unit_pricing_report.md` | Full technical report of the current run, every table |
| `analysis/output/coefficients.csv` | Every coefficient; variants `final`, `RF` (faction modifier), `FC` (adopted), staff `T1`–`T3` |
| `analysis/output/oof_predictions.csv` | Out-of-fold and full-fit predictions per unit, for checks |
| `analysis/output/blind_ideas_report.md` | Which blind-study ideas helped, and the comparison on the same units |
| `analysis/output/calibre_function_report.md` | Smooth calibre functions vs the cannon-type one-hot |
| `analysis/output/extreme_pinning_report.md` | Extreme units: pinning, and how badly they are priced |
| `analysis/output/class_structure_report.md` | §6: class structure variants, per-class V4 tables |
| `analysis/output/class_structure_coefficients.csv` | Every V4 coefficient (per-class β, size powers, army × class cells) |
| `analysis/output/faction_class_multipliers*.csv`, `.md` | The adopted model's army × class multipliers as tables (`analysis/fclass_table.py`) |
| `analysis/calibre_onehot_results/`, `analysis/linear_results/` | The same pipeline with the cannon-type one-hot, and the fully linear model |
| `analysis/HANDOFF.md` | How to work on this further |
