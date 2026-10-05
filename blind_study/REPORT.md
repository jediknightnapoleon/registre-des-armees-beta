# REPORT — an explainable model of NTW3 unit price

## 1. Summary

The price (`base_mp_cost`) of Theatre-of-War and Custom units can be written as a short,
hand-computable recipe:

1. **Army divisor.** Every army has a price divisor `N/10`, where `N` is the leading
   number of `army_corps_name` (`[1812] 7. España` → N = 7 → prices ×10/7). It applies to
   units and generals alike; a few armies deviate from it, some only for their generals
   (section 3). Together with
   the per-type stat formulas below, this alone takes MAE from 229 gold (per-class
   baseline) to 43.
2. **Regular units:** one log-linear formula per unit type (11 types, 10–31 coefficients
   each) over the unit's stats; price = exp(formula) × 10/N.
3. **Standalone ("staff") generals:** 1 gold if they have no command stars, otherwise
   ≈ 60.5·stars^1.40 × 10/N (almost exact).
4. **Commander variants** (a general attached to a unit, 42% of rows): price the row as a
   regular unit of its type, then `price = max(1, a_stars·p_reg + b_stars × 10/N)` — an
   *additive* general premium that is negative for 0–1 stars, which is why some
   commanders cost almost nothing.
5. Optional **lookup tables** that capture hand-set per-army adjustments: an army × unit-type
   multiplier table and a per-army commander premium.

| model | lookup tables | CV MAE (gold) | CV MAPE % | CV R² | **holdout MAE** | holdout MAPE % | holdout R² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline: global mean | – | 283.8 ± 2.5 | 331 | 0.00 | 287.2 | 149.4 | 0.000 |
| baseline: per-class mean or gold/man × men | – | 228.7 ± 4.8 | 306 | 0.27 | 226.9 | 125.9 | 0.303 |
| **18b — simplest** (formulas + N/10 only) | none | 43.0 ± 0.9 | 11.0 | 0.968 | **43.1** | 13.0 | 0.961 |
| **18a — compact** | 118 army×type cells + 55 commander premiums | 30.7 ± 0.6 | 7.5 | 0.982 | **31.0** | 9.9 | 0.974 |
| **13c — best** | 328 army×type cells + 55 commander premiums | 27.4 ± 0.6 | 7.0 | 0.985 | **27.8** | 8.9 | 0.979 |

All three share the same stage-1 formulas (232 coefficients over 11 unit types + staff,
≤ 31 per type) and a 12-coefficient commander stage. CV is 5-fold on the development 80%
(mean ± sd over folds); the holdout (20%, 2 504 clean rows) was scored once, at the end,
for the five rows of this table only. For the three candidate models, holdout MAE is within
one fold-sd of CV MAE; holdout MAPE is 1–2 points higher than CV, driven by a few cheap
commander variants (section 5). Median absolute error of 13c is 16 gold on both.

## 2. Data, scope and protocol

- Scope: the 12 552 rows with `faction_kind` ∈ {`theatre_of_war`, `custom`}.
- **Holdout**: 20% of rows (2 510), stratified by `unit_class` and *grouped by identical
  feature rows* so a duplicate unit never sits on both sides (`src/00_make_split.py`, seed
  20261005, ids in `data/holdout_ids.csv`). It was not looked at until the final
  evaluation (`src/90_holdout.py`, run once; its flag file `out/holdout_done.json` blocks
  reruns).
- **Development**: the other 10 042 rows, 5 fixed folds (`data/dev_folds.csv`), same
  stratification and grouping. Every experiment uses the same folds.
- **No leakage**: all tuning (feature choice, penalties, segmentation, army tables) was
  done on CV. The per-type feature selection of the final models was **nested**: for
  outer fold k, terms were selected by an inner CV on the other four folds only
  (`src/13_select_run.py`), so the reported CV of 13c/18a/18b is not optimistic about
  selection. Final candidates were then fitted on the full development set and scored once
  on the holdout.
- Metrics: MAE in gold (primary), MAPE, R² on total price.

### Excluded rows (34 in scope: 28 development, 6 holdout)

The rule was fixed on development data: drop the four custom factions `aaa_lordz`,
`austria`, `hannover`, `saxony`. Reasons:

- **`1. Lordz`** (16 rows): joke units named after players ("…Lordz: Kevin", "Grumpy
  plebs"). Every one costs a flat **9 500** gold whatever its class, size or stats
  (12-pounder battery, hussars and grenadiers alike), except the two "Grumpy plebs" at a
  flat 500. These are sentinel prices, not a pricing rule.
- **`austria`** (16 rows, blank `army_corps_name`): an exact copy of the Lordz units with
  the same unit keys, stats and sentinel prices.
- **`0. Placeholder A` / `0. Placeholder B`** (`saxony`, `hannover`; 1 row each): a
  placeholder unit called "Useless suicidal parasite", flat 3 360.

The six holdout rows caught by the rule are all Lordz copies at 9 500, consistent with the
decision. For transparency, the holdout table in `RESULTS.md` also gives metrics on all
2 510 holdout rows with these rows priced by the model as if they were real (13c: MAE
41.1, MAPE 9.0%, R² 0.70 — the six 9 500-gold rows dominate the R²). They would be
reproduced exactly by a three-line rule (Lordz → 9 500, "Grumpy plebs" → 500, Placeholder
→ 3 360), which is a lookup of the rows themselves and not a model.

<details><summary>Full list of excluded rows</summary>

|   row_id | faction_key   | army             | unit_class           | unit_name                                                            |   base_mp_cost | split   |
|---------:|:--------------|:-----------------|:---------------------|:---------------------------------------------------------------------|---------------:|:--------|
|        0 | aaa_lordz     | 1. Lordz         | artillery_foot       | Artillerie à pied de 12 livres 'Lordz: Liberalis' [F4]               |           9500 | dev     |
|        1 | aaa_lordz     | 1. Lordz         | cavalry_heavy        | Garde du Corps 'Lordz: The Nate Devourer' [C2]                       |           9500 | holdout |
|        2 | aaa_lordz     | 1. Lordz         | cavalry_lancers      | Donskie kazaki 'Lordz: Cosak' [C5]                                   |           9500 | dev     |
|        3 | aaa_lordz     | 1. Lordz         | cavalry_light        | 15th (the King's) Hussars 'the Tabs, Lordz: Uxbridge' [C4]           |           9500 | dev     |
|        4 | aaa_lordz     | 1. Lordz         | cavalry_light        | Chevaulegers Nr. 5 'Klenau, Lordz: MightyOwl' [C4]                   |           9500 | dev     |
|        5 | aaa_lordz     | 1. Lordz         | cavalry_standard     | 2° dragoni 'Napoleone, Lordz: Desaix' [C3]                           |           9500 | holdout |
|        6 | aaa_lordz     | 1. Lordz         | general              | Grumpy plebs                                                         |            500 | dev     |
|        7 | aaa_lordz     | 1. Lordz         | infantry_grenadiers  | ¤ 6. Grenadier-Garde 'Lange Kerls, Lordz: JC von Preußen' [G4]       |           9500 | dev     |
|        8 | aaa_lordz     | 1. Lordz         | infantry_light       | ¤ 52nd (Oxfordshire) Light Foot 'the Light Bobs, Lordz: Bogdan' [L6] |           9500 | holdout |
|        9 | aaa_lordz     | 1. Lordz         | infantry_line        | ¤ 42nd (Royal Highland) Foot 'the Black Watch, Lordz: Davn' [G4]     |           9500 | dev     |
|       10 | aaa_lordz     | 1. Lordz         | infantry_line        | ¤ Leyb-gvardyi Preobrajenskyi 'Lordz: Kevin' [G3]                    |           9500 | dev     |
|       11 | aaa_lordz     | 1. Lordz         | infantry_line        | ¤ Moushketyeri 'Apsheron, Lordz: Gerona' [L4]                        |           9500 | dev     |
|       12 | aaa_lordz     | 1. Lordz         | infantry_line        | ¤ Royal Marines 'the Bootnecks, Lordz: Commodore Wesley' [G3]        |           9500 | dev     |
|       13 | aaa_lordz     | 1. Lordz         | infantry_line        | ¤ Ungarische Linieninfanterie Nr. 19 'Alvinczy, Lordz: Avon' [L3]    |           9500 | dev     |
|       14 | aaa_lordz     | 1. Lordz         | infantry_militia     | Grumpy plebs [L3]                                                    |            500 | dev     |
|       15 | aaa_lordz     | 1. Lordz         | infantry_skirmishers | Voltigeurs de la ligne 'Lordz: Metjuhaumer' [S2]                     |           9500 | dev     |
|       16 | austria       | (blank)          | artillery_foot       | Artillerie à pied de 12 livres 'Lordz: Liberalis' [F4]               |           9500 | dev     |
|       17 | austria       | (blank)          | cavalry_heavy        | Garde du Corps 'Lordz: The Nate Devourer' [C2]                       |           9500 | holdout |
|       18 | austria       | (blank)          | cavalry_lancers      | Donskie kazaki 'Lordz: Cosak' [C5]                                   |           9500 | dev     |
|       19 | austria       | (blank)          | cavalry_light        | 15th (the King's) Hussars 'the Tabs, Lordz: Uxbridge' [C4]           |           9500 | dev     |
|       20 | austria       | (blank)          | cavalry_light        | Chevaulegers Nr. 5 'Klenau, Lordz: MightyOwl' [C4]                   |           9500 | dev     |
|       21 | austria       | (blank)          | cavalry_standard     | 2° dragoni 'Napoleone, Lordz: Desaix' [C3]                           |           9500 | holdout |
|       22 | austria       | (blank)          | general              | Grumpy plebs                                                         |            500 | dev     |
|       23 | austria       | (blank)          | infantry_grenadiers  | ¤ 6. Grenadier-Garde 'Lange Kerls, Lordz: JC von Preußen' [G4]       |           9500 | dev     |
|       24 | austria       | (blank)          | infantry_light       | ¤ 52nd (Oxfordshire) Light Foot 'the Light Bobs, Lordz: Bogdan' [L6] |           9500 | holdout |
|       25 | austria       | (blank)          | infantry_line        | ¤ 42nd (Royal Highland) Foot 'the Black Watch, Lordz: Davn' [G4]     |           9500 | dev     |
|       26 | austria       | (blank)          | infantry_line        | ¤ Leyb-gvardyi Preobrajenskyi 'Lordz: Kevin' [G3]                    |           9500 | dev     |
|       27 | austria       | (blank)          | infantry_line        | ¤ Moushketyeri 'Apsheron, Lordz: Gerona' [L4]                        |           9500 | dev     |
|       28 | austria       | (blank)          | infantry_line        | ¤ Royal Marines 'the Bootnecks, Lordz: Commodore Wesley' [G3]        |           9500 | dev     |
|       29 | austria       | (blank)          | infantry_line        | ¤ Ungarische Linieninfanterie Nr. 19 'Alvinczy, Lordz: Avon' [L3]    |           9500 | dev     |
|       30 | austria       | (blank)          | infantry_militia     | Grumpy plebs [L3]                                                    |            500 | dev     |
|       31 | austria       | (blank)          | infantry_skirmishers | Voltigeurs de la ligne 'Lordz: Metjuhaumer' [S2]                     |           9500 | dev     |
|      275 | hannover      | 0. Placeholder B | infantry_irregulars  | ¤ Useless suicidal parasite [L1]                                     |           3360 | dev     |
|    25667 | saxony        | 0. Placeholder A | infantry_irregulars  | ¤ Useless suicidal parasite [L1]                                     |           3360 | dev     |

</details>

## 3. What the data says about pricing

These findings come from development data only (experiments 01–18 in `RESULTS.md`).

1. **Prices are multiplicative in an army divisor.** For a standalone general, the price
   at each star level takes only a handful of values, and their ratios are exact:
   2-star generals cost 159 / 177 / 199 / 228 / 266 gold = 159 / {1.0, 0.9, 0.8, 0.7, 0.6}.
   The divisor is the army's `N/10`, with N the leading number of `army_corps_name`, and it
   applies to **all** rows, not only generals: identical regular units in armies with
   different N have price ratios centred on the N ratio (median 0.999 over 85 pairs; half of
   the pairs are within ±5%, the rest scatter because of the army × type effects below).
   For **standalone generals**, a few armies deviate from N/10 (HRE 9. → 0.79,
   France (Égypte) 8. → 0.855, Rossiya (Frantsiya) 9. → 0.875, France (Italie) 9. → 0.94,
   UK Portugal 9. → 0.955, the 11. armies → 1.10–1.15, France (Prusse) 12. → 1.3,
   UK España Portugal 10. → 0.64). These general-level deviations carry over to the army's
   units only in some cases (post-study check on all clean rows, regular units compared with
   the stats-only model 18b, `src/94_army_audit.py` → `out/army_audit.md`; armies whose
   generals follow N/10 have a median unit level of 0.99, IQR 0.97–1.01):
   - **whole army:** HRE units are ×1.12 (generals ×1.14 = 0.9/0.79); Rossiya (Frantsiya)
     units ×1.05 (generals ×1.03).
   - **generals only:** UK, España, Portugal — generals ×1.58, units ×0.98 (normal);
     France (Égypte) — generals ×0.94, units ×0.98.
   - **within noise / partial:** France (Italie), the 11. and 12. armies, UK Portugal (whose
     units are ×0.90, cheaper than its generals' ×0.94).
   The army tables pick these up per type (e.g. HRE light cavalry ×1.138 ≈ 0.9/0.79; the
   UK, España, Portugal staff-general cell ×1.37 on top of the general formula).
2. **The rest of the army effect is type-specific.** After the divisor, the residual
   army effect differs by unit type (e.g. heavy cavalry of `[1815] 9. France (Flandres)` and
   `[1815] 9. UK, Nederlanden` is ×0.82 of what their stats imply, while the HRE is ×1.09–1.18
   on every type — its divisor is 0.79, not 0.9). A single shared
   army table gains little (exp 07); the army tables together gain ~15.6 MAE (18b → 13c). No
   attribute in the data (unit cap, roster counts, year, source corps, weapon) explains it;
   it looks like hand-set balancing.
3. **Standalone generals:** 1 gold without command stars (presumably the army's own
   commander, included for free), otherwise price ≈ 60.5 · stars^1.40 × 10/N (fitted:
   60.5, 159.5, 281.3, 574.6, 1 307 for 1, 2, 3, 5, 9 stars at N = 10).
4. **Commander variants** carry the stats of the unit they lead, boosted by the general
   (morale exactly +1, +1, +2, +2, +3, +3, +4 for 0–6 stars, smaller boosts to melee and
   reload). Their price is **additive**, not multiplicative, in the plain unit's price:
   ≈ 0.9 × unit price + b(stars) with b ≈ −60, −30, +20, +65, +120 (×10/N) for 0–4 stars.
   The negative premium for 0–1 star commanders explains the 1–49 gold commanders attached
   to cheap units. Modelling this additively (exp 09a) cut CV MAE from 42.5 to 39.5 and MAPE
   from 13.3% to 9.5% (vs 08e, same stage 1).
5. **Unit type.** For commander variants `unit_class` is just `general`; the type of the
   unit they lead (line, light, grenadier, … cavalry, artillery) is only recoverable from the
   type code in `unit_key` (`ntw3_inf_line_…`). Using that code as a categorical attribute
   is worth ~8.5 MAE over proxies built from speed letter and drill set (exp 06b vs 06c).
   It is a type code, not an identifier; no other part of `unit_key` is used.
6. **Within a type**, price grows with ln(men) and with log-transforms of the main stats
   (morale, melee attack/defence, charge, accuracy, reload, ammo); a few products
   (ln men × morale, morale × accuracy) help infantry. Fitting by **price-weighted least
   absolute deviation on log price** (IRLS) matches the gold-MAE objective and gained ~3.5
   MAE over plain least squares (exp 12c). Predictions clamp every input to its training
   range; without clamping, exp() extrapolation blew up rare artillery and militia rows
   (exp 10).

## 4. The models

### 4.1 How to price a unit by hand

Notation: `N` = leading number of `army_corps_name`; type = the unit-type code from
`unit_key` mapped to 11 groups (`inf_line`, `inf_light`, `inf_grena`, `inf_skirm`,
`inf_milit` (= militia + irregulars), `cav_light` (incl. the 11 missile cavalry),
`cav_stand`, `cav_lance`, `cav_heavy`, `art_foot` (incl. the 4 fixed guns), `art_horse`),
or `staff` for a general that is not a commander variant.

**Step 1 — formula of the type.** Take the type's table in section 4.3–4.5. For every term,
compute x from the unit's columns (booleans are 1/0; blank range, projectile and gun
columns count as 0; "speed digit" is the number in `speed_code`, 0 if blank), clamp x to the "clamp x to" interval, multiply by the coefficient and
add everything to the intercept: `z = intercept + Σ coef · clamp(x)`.

**Step 2 — regular price.** `p_reg = exp(z) × M[army, type] × 10 / N`, where `M` is the
army × type multiplier (1 if blank or absent; model 18b has no table).
Standalone general without command stars: price = 1.
Standalone general with stars: the `staff` formula is `z = intercept + coef · ln(stars)`.

**Step 3 — commander variants only.** With `s = min(command_stars, 5)` (0 if blank):
`price = max(1, (a + a_star_s) · p_reg + (b_s + p_army) × 10 / N)`, where `p_reg` is
step 2 applied to the commander's own row and `p_army` is the army's commander premium
(0 in model 18b).

Worked example (model 13c), *Lineinaya pekhota 'Kexholm' [L3]*, `[1812] 10. Rossiya`, true
price 487: z = 6.1905 from the 21 `inf_line` terms (largest contributions: ln(men) 13.11,
ln(1+charge) 3.81, ln(men)×morale 1.79, men_raw −1.54); exp(z) = 488.1; army×type
multiplier 1.016; N = 10 → **496**.
Commander example, *Friedrich Carl zu Hohenlohe-Ingelfingen (Chevaulegers Nr. 31) [C4]*,
`9. Heiliges Römisches Reich`, 2 stars, true price 1 368: `cav_light` z = 7.1104, exp(z)
= 1 224.7, HRE light-cavalry multiplier 1.138, ×10/9 → p_reg = 1 548.7; commander stage
0.9309 × 1 548.7 + (−23.9) × 10/9 = **1 415**. With model 18b (no tables) the same two
units price at 494 and 1 213. Full step-by-step tables: `out/worked_example.md`
(`src/92_worked_example.py`). `src/91_export_final.py` re-prices every development row
from the exported tables alone and reproduces the model to 1e-11 gold.

### 4.2 Accuracy versus simplicity

Milestones (CV MAE on the clean development set; details in `RESULTS.md`):

| exp | model | CV MAE | MAPE % | size |
| --- | --- | --- | --- | --- |
| 02e | per-class mean or gold/man × men | 228.7 | 306 | 15 |
| 03 | log price ~ class + ln men + ln N | 212.3 | 64 | 21 |
| 04 | log-linear per base type (inf/cav/art/staff), raw stats | 73.3 | 18.1 | ~40/segment |
| 06b | 11 unit-type segments, commanders inside their type | 51.2 | 14.4 | 32/segment + 55 army |
| 08e | + army × type offsets | 42.5 | 13.3 | + 585 cells |
| 09a | commanders additive in regular price (two-stage) | 39.5 | 9.5 | + 7 commander |
| 10b | log1p stat transforms, clamping | 32.0 | 7.4 | ≤ 36/type |
| 12c | price-weighted LAD fit | 28.6 | 8.3 | |
| 14a | + per-army commander premium | 27.7 | 7.3 | + 55 |
| 13b | nested per-type term selection | 27.3 | 7.0 | ≤ 31/type, 579 cells |
| **13c** | 13b with sparse (L1) army table | **27.4** | 7.0 | 328 cells |

Trade-off on the final formulas (same 232 stage-1 coefficients):

| army × type cells | commander premiums | CV MAE | holdout MAE |
| --- | --- | --- | --- |
| 579 (full table, 13b) | 55 | 27.3 | – |
| **328 (13c)** | 55 | **27.4** | **27.8** |
| 241 (18c) | 55 | 27.9 | – |
| **118 (18a)** | 55 | **30.7** | **31.0** |
| **0 (18b)** | 0 | **43.0** | **43.1** |

With the earlier, unselected formulas, the alternatives "one army table for units + one
for staff generals" (105 cells, exp 15b) and "army × broad type" (215 cells, exp 15a) gave
38.3 and 35.0 —
a worse use of table cells than the sparse army × type table. Dropping the `unit_key` type
code costs ~8.5 MAE. The single biggest structural gains were the army divisor, the
unit-type segmentation, and the additive commander stage; the army tables are worth
~15.6 MAE (18b → 13c) but are the least "explanatory" part.

All three models use the same terms per type; the coefficients differ because each was fitted with its own army tables. Coefficients apply to the clamped x; `[flag]` means 1 if the flag is true. Commander coefficients: `a` and `a_star{s}` multiply p_reg; `b{s}` and `p_army` are in gold before the ×10/N divisor. CSV copies of every table are in `out/model_<name>_*.csv`.

### 4.3 Model 13c (best) — written out in full

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.02046 |  |
| `log_men` | ln(men_raw) | 1.81669 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00659277 | [6, 82] |
| `reload_skill` | reload_skill | 0.00415047 | [14, 100] |
| `morale` | morale | 0.0240201 | [2, 12] |
| `melee_defense` | melee_defense | -0.173334 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.22671 | [0, 2] |
| `range0` | range | 0.000971556 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0242142 | [17, 80] |
| `speed_num` | speed digit | 0.194696 | [0, 6] |
| `guns0` | guns | 0.0728113 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.212069 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.30008 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 0.848449 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.340579 | [0, 1.099] |
| `men_raw` | men_raw | -0.00794575 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.177165 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.77231 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -11.8421 |  |
| `log_men` | ln(men_raw) | 2.05799 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00580704 | [29, 85] |
| `reload_skill` | reload_skill | 0.00372279 | [35, 100] |
| `morale` | morale | 0.0976791 | [5, 14] |
| `range0` | range | 0.00203534 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0113838 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.15991 | [14, 40] |
| `speed_num` | speed digit | 0.382229 | [1, 3] |
| `guns0` | guns | -0.244221 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.205895 |  |
| `can_inspire` | [can_inspire] | 0.143613 |  |
| `log_morale` | ln(1 + morale) | -0.538554 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.27342 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.112185 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.12646 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000257387 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | 0.0168214 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | 0.00308421 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0240195 |  |
| `log_men^2` | ln(men_raw)² | 0.0471575 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.000590672 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.0134169 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.43985 |  |
| `log_men` | ln(men_raw) | 0.579515 | [4.382, 5.823] |
| `train` | training code | -0.0116897 | [1, 4] |
| `morale` | morale | 0.0221076 | [7, 18] |
| `melee_attack` | melee_attack | -0.0528365 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0139174 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.159837 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.333071 |  |
| `can_inspire` | [can_inspire] | 0.157611 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.3098 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.52721 |  |
| `log_men` | ln(men_raw) | 0.624105 | [4.357, 5.656] |
| `morale` | morale | 0.0420773 | [4, 16] |
| `melee_defense` | melee_defense | -0.0362097 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0724043 | [1, 9] |
| `rank_depth` | rank_depth | -0.0103408 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.256603 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.322324 |  |
| `can_inspire` | [can_inspire] | 0.0800484 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.186302 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.114133 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.440425 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.578031 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00311508 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.17577 |  |
| `log_men` | ln(men_raw) | 0.560629 | [4.331, 5.886] |
| `accuracy` | accuracy | 0.0183169 | [0, 34] |
| `reload_skill` | reload_skill | -0.0068121 | [0, 90] |
| `morale` | morale | -0.0224776 | [3, 15] |
| `melee_defense` | melee_defense | -0.0163701 | [3, 23] |
| `range0` | range | 0.0130256 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.233762 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.284086 |  |
| `can_inspire` | [can_inspire] | 0.127423 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.469323 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.39005 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.0485885 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.549779 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.435122 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.205906 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00589368 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -0.86945 |  |
| `log_men` | ln(men_raw) | 0.614151 | [4.357, 5.781] |
| `morale` | morale | 0.0699516 | [6, 13] |
| `melee_attack` | melee_attack | -0.0495852 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0219665 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.183772 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.341317 |  |
| `log_morale` | ln(1 + morale) | 0.563142 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.962623 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.140261 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.00607603 | [5, 9] |
| `morale^2` | morale² | -0.00458919 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -1.21904 |  |
| `log_men` | ln(men_raw) | 1.58712 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.0737049 | [9, 30] |
| `reload_skill` | reload_skill | 0.00462618 | [4, 99] |
| `morale` | morale | -0.0873833 | [4, 18] |
| `melee_attack` | melee_attack | 0.138177 | [12, 25] |
| `melee_defense` | melee_defense | -0.00589093 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.00658633 | [16, 33] |
| `range0` | range | 0.0046177 | [70, 100] |
| `projectile_damage0` | projectile_damage | 2.15702 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0883271 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.104251 |  |
| `has_stamina` | [has_stamina] | 0.0925669 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0969054 |  |
| `can_inspire` | [can_inspire] | 0.0894509 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.296646 |  |
| `can_place_stakes` | [can_place_stakes] | 0.06642 |  |
| `can_build_barricades` | [can_build_barricades] | 0.165793 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.328419 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -1.56281 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.179358 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.319742 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.00503684 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -3.47814 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0317859 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.0025665 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0228026 | [44.35, 168] |
| `morale^2` | morale² | 0.00295442 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00357443 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | -0.0674352 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | -0.00381048 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -9.59494 |  |
| `log_men` | ln(men_raw) | 2.38628 | [4.868, 6.114] |
| `train` | training code | 0.00370441 | [1, 4] |
| `reload_skill` | reload_skill | -0.0193203 | [23, 101] |
| `ammo` | ammo | -0.000781809 | [15, 70] |
| `melee_attack` | melee_attack | -0.0606724 | [6, 19] |
| `charge_bonus` | charge_bonus | -0.0262883 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0179023 | [14, 20] |
| `speed_num` | speed digit | 0.0476093 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.146471 |  |
| `has_stamina` | [has_stamina] | 0.105235 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0950384 |  |
| `can_inspire` | [can_inspire] | 0.0992868 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.530077 |  |
| `guard_mode` | [guard_mode] | 0.0550139 |  |
| `pike_square` | [pike_square] | 0.0238322 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.278309 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.182951 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.068573 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.535508 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.0070115 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | 0.543036 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00460842 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.0795356 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0516237 |  |
| `speed_code=L3` | [speed_code = L3] | -0.0689601 |  |
| `speed_code=L4` | [speed_code = L4] | -0.00254232 |  |
| `speed_code=L5` | [speed_code = L5] | 0.044352 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0522945 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0126233 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | 0.000978336 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -10.8174 |  |
| `log_men` | ln(men_raw) | 2.34546 | [4.852, 6.114] |
| `ammo` | ammo | 0.00357398 | [25, 70] |
| `morale` | morale | -0.0202729 | [0, 16] |
| `melee_attack` | melee_attack | 0.030699 | [6, 23] |
| `melee_defense` | melee_defense | -0.013725 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0524078 | [9, 30] |
| `projectile_damage0` | projectile_damage | 0.090755 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0735342 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.130494 |  |
| `has_stamina` | [has_stamina] | 0.0973369 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0849549 |  |
| `can_inspire` | [can_inspire] | 0.0903833 |  |
| `can_place_stakes` | [can_place_stakes] | 0.234749 |  |
| `pike_square` | [pike_square] | 0.0245962 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.00749093 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.223655 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.172419 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.219739 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.200912 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.19767 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00575423 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.18724 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0290598 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00276654 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000678208 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.00781 |  |
| `log_men` | ln(men_raw) | 1.252 | [4.852, 6.881] |
| `train` | training code | -0.0156601 | [0, 3] |
| `ammo` | ammo | 0.0070707 | [0, 70] |
| `morale` | morale | 0.0538464 | [0, 18] |
| `melee_defense` | melee_defense | 0.0400157 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.0981182 | [8, 29] |
| `range0` | range | 0.0084037 | [0, 100] |
| `projectile_damage0` | projectile_damage | 0.611061 | [0, 0.83] |
| `speed_num` | speed digit | 0.15691 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.149264 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0761999 |  |
| `can_inspire` | [can_inspire] | -0.429865 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.394447 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0891018 |  |
| `scares_enemies` | [scares_enemies] | 0.440117 |  |
| `skirmish` | [skirmish] | -1.20382 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.429669 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.145347 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.23588 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | 0.134276 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.06597 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.209037 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.35794 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00260315 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.671394 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.217308 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.0439756 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 7.65785 |  |
| `log_men` | ln(men_raw) | -0.59354 | [3.871, 5.606] |
| `train` | training code | 0.0130085 | [0, 4] |
| `accuracy` | accuracy | 0.0295479 | [15, 38] |
| `morale` | morale | 0.1369 | [3, 13] |
| `melee_attack` | melee_attack | -0.00200332 | [1, 23] |
| `charge_bonus` | charge_bonus | -0.026045 | [1, 32] |
| `speed_num` | speed digit | 0.332827 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0701637 |  |
| `can_inspire` | [can_inspire] | -0.0217118 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.699408 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0945971 |  |
| `guard_mode` | [guard_mode] | 0.0426935 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.551845 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | -0.00254475 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -0.796999 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.234947 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0386154 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.0128665 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.0313132 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.10295 |  |
| `log_stars` | ln(command_stars) | 1.3985 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.8989 |
| b0 | -81.44 |
| b1 | -58.71 |
| b2 | -35.42 |
| b3 | -17.49 |
| b4 | -1.301 |
| b5 | 39.16 |
| a_star1 | 0.01207 |
| a_star2 | 0.03208 |
| a_star3 | 0.06592 |
| a_star4 | 0.09 |
| a_star5 | 0.1228 |

Per-army commander premium `p_army` (gold, before dividing by N/10):

| army | p_army |
| --- | ---: |
| 7. Danmark | -13.4 |
| 8. Piemonte-Sardegna (1796) | 17.4 |
| 8. UK (Spain, 1808) | 12.8 |
| 9. France (1796) | 4.2 |
| 9. Heiliges Römisches Reich | 11.6 |
| [1798] 5. France (Irlande) | -5.9 |
| [1798] 5. UK (Ireland) | 27.2 |
| [1798] 8. France (Égypte) | -10.2 |
| [1798] 8. Mamālīk | -8.8 |
| [1799] 7. France (Hollande) | -1.2 |
| [1799] 7. UK, Russia (Helder) | 16.1 |
| [1799] 7. Österreich (Schwaben) | 7.8 |
| [1799] 9. France (Italie) | -3.6 |
| [1799] 9. France (Rhin) | -5.6 |
| [1799] 9. Österreich (Italien) | 0.3 |
| [1800] 8. Osmanlı, UK | 5.8 |
| [1804] 7. Irānshahr | -4.1 |
| [1804] 8. Rossiya (Kavkaz, Dunau) | -10.6 |
| [1805] 11. France (Allemagne) | -7.0 |
| [1805] 6. France (Tyrol) | 15.2 |
| [1805] 8. Österreich | 3.6 |
| [1805] 9. Rossiya, Österreich | -7.5 |
| [1806] 10. Preußen | -12.5 |
| [1806] 12. France (Prusse) | -19.3 |
| [1806] 9. Osmanlı | -8.5 |
| [1807] 9. Rossiya (Polsha) | -4.2 |
| [1808] 7. Rossiya (Finlyandiya) | -4.1 |
| [1808] 7. Sverige (Finska) | -6.9 |
| [1809] 10. France (Autriche) | -11.1 |
| [1809] 10. France (Espagne) | -17.1 |
| [1809] 10. UK, España, Portugal | 0.8 |
| [1809] 10. Österreich | -5.7 |
| [1809] 6. UK (Walcheren) | 20.7 |
| [1809] 7. Polska, sojusznicy | -0.5 |
| [1809] 8. Österreich (Tyrol) | 15.2 |
| [1809] 9. España | 0.5 |
| [1811] 7. España | 5.5 |
| [1811] 8. France (Espagne) | 0.9 |
| [1811] 9. UK, Portugal | -3.3 |
| [1812] 10. Rossiya | -16.2 |
| [1812] 11. France (Russie-Centre) | -17.6 |
| [1812] 6. France (Russie-Nord) | 12.8 |
| [1812] 7. France (Russie-Sud) | 7.5 |
| [1812] 7. UK (USA) | -9.4 |
| [1812] 7. United States | 11.4 |
| [1812] 8. Russkiy narod | -10.4 |
| [1814] 8. France | -1.7 |
| [1814] 8. Preußen (Frankreich) | 3.5 |
| [1814] 8. Österreich (Frankreich) | -0.7 |
| [1814] 9. Rossiya (Frantsiya) | -7.3 |
| [1815] 6. Napoli | 9.8 |
| [1815] 6. Österreich (Italien) | 14.6 |
| [1815] 7. Preußen (Flandern) | 12.2 |
| [1815] 9. France (Flandres) | -5.4 |
| [1815] 9. UK, Nederlanden | 2.2 |

#### Army × type multiplier table (328 non-blank cells; blank = 1)

| army | art_foot | art_horse | cav_heavy | cav_lance | cav_light | cav_stand | inf_grena | inf_light | inf_line | inf_milit | inf_skirm | staff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7. Danmark |  |  | 0.915 |  | 0.920 | 0.948 | 0.886 | 0.886 | 0.925 |  |  |  |
| 8. Piemonte-Sardegna (1796) |  |  | 0.971 |  |  | 1.111 |  | 0.910 | 1.027 |  |  |  |
| 8. UK (Spain, 1808) |  |  |  |  | 0.977 |  |  | 1.098 | 1.049 |  |  |  |
| 9. France (1796) |  |  | 0.981 |  | 1.030 | 1.031 | 0.888 | 0.968 | 0.915 |  |  |  |
| 9. Heiliges Römisches Reich | 1.144 |  | 1.176 |  | 1.138 |  | 1.112 | 1.093 | 1.131 | 1.088 | 1.130 | 1.132 |
| [1798] 5. France (Irlande) |  | 1.031 |  |  | 1.165 |  |  |  | 0.951 |  | 1.064 |  |
| [1798] 5. UK (Ireland) |  |  |  |  |  |  | 1.056 |  |  |  | 1.070 |  |
| [1798] 8. France (Égypte) |  |  |  |  | 0.968 | 0.924 | 0.900 |  | 0.924 |  |  | 0.937 |
| [1798] 8. Mamālīk |  |  | 1.026 | 0.933 | 0.896 |  |  |  | 0.925 |  | 0.904 |  |
| [1799] 7. France (Hollande) |  |  |  |  | 0.913 |  | 0.921 |  | 0.909 |  |  |  |
| [1799] 7. UK, Russia (Helder) | 0.971 |  |  | 1.055 | 0.936 |  |  | 1.087 | 1.140 |  |  |  |
| [1799] 7. Österreich (Schwaben) |  | 0.978 | 0.922 | 0.911 | 0.926 | 1.051 | 1.024 | 1.099 | 1.082 | 0.895 |  |  |
| [1799] 9. France (Italie) | 0.855 |  |  |  | 0.943 |  | 0.886 |  | 0.904 |  |  | 0.958 |
| [1799] 9. France (Rhin) | 1.026 |  | 1.042 |  | 0.932 | 0.966 | 0.936 |  | 1.026 |  |  |  |
| [1799] 9. Österreich (Italien) | 1.021 | 0.966 |  | 0.880 |  |  | 0.974 | 1.031 | 1.073 |  |  |  |
| [1800] 8. Osmanlı, UK | 0.951 |  | 1.070 |  | 0.973 |  |  | 1.086 | 1.036 |  |  |  |
| [1804] 7. Irānshahr |  |  | 1.059 | 1.075 | 0.915 |  |  |  | 1.028 |  |  |  |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  |  | 1.021 | 1.034 | 0.975 | 0.967 | 0.923 | 0.806 | 0.915 |  |  |  |
| [1805] 11. France (Allemagne) | 0.954 | 0.958 |  |  |  |  | 0.940 |  | 0.864 |  |  | 0.957 |
| [1805] 6. France (Tyrol) | 1.017 |  | 1.039 |  | 1.036 | 0.885 | 0.912 | 0.924 | 0.936 |  |  |  |
| [1805] 8. Österreich |  |  | 0.977 |  | 0.925 |  | 1.015 | 1.102 | 1.049 |  |  |  |
| [1805] 9. Rossiya, Österreich |  |  | 0.895 | 1.042 | 1.033 | 1.050 | 1.099 | 1.027 | 1.050 |  |  |  |
| [1806] 10. Preußen |  | 0.968 | 0.953 |  | 1.039 | 0.956 | 1.234 | 1.071 |  |  |  |  |
| [1806] 12. France (Prusse) | 0.935 | 0.929 | 0.900 |  | 0.964 | 0.965 | 0.907 | 0.952 | 0.885 |  |  | 0.924 |
| [1806] 9. Osmanlı | 1.078 |  |  | 0.908 | 1.046 |  |  |  | 0.969 | 0.909 | 1.187 |  |
| [1807] 9. Rossiya (Polsha) | 0.819 | 1.020 | 1.022 |  | 1.044 |  | 1.077 | 1.109 | 1.052 |  |  |  |
| [1808] 7. Rossiya (Finlyandiya) |  |  | 0.980 | 0.829 | 1.040 | 1.041 |  | 0.843 | 1.033 |  |  |  |
| [1808] 7. Sverige (Finska) | 1.022 |  | 1.032 |  | 0.937 |  | 1.102 | 0.972 | 1.098 |  | 1.077 |  |
| [1809] 10. France (Autriche) |  |  | 0.952 |  |  | 1.039 | 0.906 |  | 0.916 |  |  |  |
| [1809] 10. France (Espagne) | 0.918 |  |  | 1.047 | 1.027 | 0.858 | 0.958 | 0.935 | 0.949 |  | 1.044 |  |
| [1809] 10. UK, España, Portugal | 1.026 |  | 1.158 |  | 1.033 | 1.072 |  |  |  |  |  | 1.365 |
| [1809] 10. Österreich |  |  | 0.968 |  | 0.963 | 1.044 | 0.954 | 1.079 | 1.077 |  |  |  |
| [1809] 6. UK (Walcheren) | 0.914 |  | 1.045 |  | 1.088 |  |  |  | 1.140 |  | 0.912 |  |
| [1809] 7. Polska, sojusznicy |  |  | 0.984 | 0.673 |  | 1.065 | 0.971 | 0.919 | 0.926 |  | 0.941 |  |
| [1809] 8. Österreich (Tyrol) |  |  |  |  | 1.064 |  |  | 1.051 | 1.043 |  | 1.104 |  |
| [1809] 9. España | 0.895 |  | 1.032 |  |  | 1.109 |  | 1.093 | 1.077 | 0.963 |  |  |
| [1811] 7. España | 0.925 |  | 1.064 | 1.053 | 1.073 | 1.050 | 1.062 | 1.091 | 1.058 | 0.949 |  |  |
| [1811] 8. France (Espagne) | 0.915 |  | 1.042 | 1.028 | 0.970 | 0.949 | 0.911 |  | 0.952 |  | 0.949 |  |
| [1811] 9. UK, Portugal |  |  | 1.041 |  | 0.976 | 0.971 | 1.034 | 0.887 | 0.926 |  |  | 0.944 |
| [1812] 10. Rossiya | 0.961 |  | 0.978 | 1.036 | 1.081 | 0.971 | 1.031 | 1.063 | 1.016 |  | 0.951 |  |
| [1812] 11. France (Russie-Centre) | 0.777 |  | 0.932 |  |  |  | 0.937 |  | 0.958 |  | 0.969 |  |
| [1812] 6. France (Russie-Nord) |  | 0.917 | 1.053 | 1.097 | 0.900 | 1.059 | 0.962 | 0.894 | 0.968 |  |  |  |
| [1812] 7. France (Russie-Sud) | 0.982 |  | 1.038 |  | 0.957 | 0.971 |  | 0.917 | 0.924 |  |  |  |
| [1812] 7. UK (USA) | 0.945 |  | 1.027 |  |  |  | 1.058 | 0.948 |  | 1.063 |  |  |
| [1812] 7. United States | 1.034 |  |  |  |  | 1.105 | 1.063 | 1.048 | 0.913 | 0.706 |  |  |
| [1812] 8. Russkiy narod |  | 1.106 |  | 0.840 |  |  |  |  |  | 1.139 | 0.824 |  |
| [1814] 8. France | 0.767 | 0.979 | 0.855 |  | 1.077 | 0.965 | 0.898 | 0.821 | 0.863 | 0.943 | 1.058 |  |
| [1814] 8. Preußen (Frankreich) | 1.117 | 1.015 | 0.916 | 1.019 | 1.024 |  |  |  | 1.060 |  | 1.037 |  |
| [1814] 8. Österreich (Frankreich) |  |  | 0.898 | 1.045 | 0.878 |  | 1.106 | 0.988 | 1.101 |  |  |  |
| [1814] 9. Rossiya (Frantsiya) | 1.039 | 1.050 | 0.882 | 0.968 | 1.076 |  | 1.117 | 1.086 | 1.092 |  |  |  |
| [1815] 6. Napoli |  |  |  | 0.951 |  |  | 0.922 | 1.089 |  |  |  |  |
| [1815] 6. Österreich (Italien) | 1.040 |  | 1.050 | 0.961 | 1.049 |  | 1.048 | 0.925 | 1.020 |  |  |  |
| [1815] 7. Preußen (Flandern) | 0.895 |  |  |  | 0.925 | 0.955 |  | 1.144 |  | 1.026 |  |  |
| [1815] 9. France (Flandres) | 0.969 | 0.955 | 0.817 |  |  | 1.037 |  | 0.982 | 0.904 |  |  |  |
| [1815] 9. UK, Nederlanden |  |  | 0.818 |  | 0.966 |  | 1.078 |  | 1.080 |  | 1.038 |  |

### 4.4 Model 18a (compact) — written out in full

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.59494 |  |
| `log_men` | ln(men_raw) | 1.85383 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00665348 | [6, 82] |
| `reload_skill` | reload_skill | 0.00391873 | [14, 100] |
| `morale` | morale | 0.0253353 | [2, 12] |
| `melee_defense` | melee_defense | -0.258869 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.339231 | [0, 2] |
| `range0` | range | 0.000918587 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0255547 | [17, 80] |
| `speed_num` | speed digit | 0.192005 | [0, 6] |
| `guns0` | guns | 0.0599313 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.218526 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.294018 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 1.20361 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.522133 | [0, 1.099] |
| `men_raw` | men_raw | -0.00788456 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.194192 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.87916 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -11.6359 |  |
| `log_men` | ln(men_raw) | 2.0463 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00576789 | [29, 85] |
| `reload_skill` | reload_skill | 0.00353084 | [35, 100] |
| `morale` | morale | 0.0916088 | [5, 14] |
| `range0` | range | 0.0019252 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0115331 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.158227 | [14, 40] |
| `speed_num` | speed digit | 0.378688 | [1, 3] |
| `guns0` | guns | -0.244432 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.205333 |  |
| `can_inspire` | [can_inspire] | 0.154375 |  |
| `log_morale` | ln(1 + morale) | -0.502668 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.14613 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.124346 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.10807 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000239348 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | 0.0140589 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | 0.00452648 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0319835 |  |
| `log_men^2` | ln(men_raw)² | 0.0457574 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -8.96067e-05 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.00440016 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.840143 |  |
| `log_men` | ln(men_raw) | 0.553607 | [4.382, 5.823] |
| `train` | training code | -0.0163025 | [1, 4] |
| `morale` | morale | 0.0195228 | [7, 18] |
| `melee_attack` | melee_attack | -0.0460569 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0146388 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.158807 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.344419 |  |
| `can_inspire` | [can_inspire] | 0.163831 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.18251 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.88939 |  |
| `log_men` | ln(men_raw) | 0.612449 | [4.357, 5.656] |
| `morale` | morale | 0.0408833 | [4, 16] |
| `melee_defense` | melee_defense | -0.0255011 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0595644 | [1, 9] |
| `rank_depth` | rank_depth | -0.016745 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.255601 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.309268 |  |
| `can_inspire` | [can_inspire] | 0.0489301 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.170675 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.16089 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.351373 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.5146 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00381028 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.23602 |  |
| `log_men` | ln(men_raw) | 0.53718 | [4.331, 5.886] |
| `accuracy` | accuracy | 0.0102149 | [0, 34] |
| `reload_skill` | reload_skill | -0.00601341 | [0, 90] |
| `morale` | morale | -0.0256014 | [3, 15] |
| `melee_defense` | melee_defense | -0.015994 | [3, 23] |
| `range0` | range | 0.0134142 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.249287 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.288206 |  |
| `can_inspire` | [can_inspire] | 0.150702 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.455477 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.321745 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.0265152 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.573094 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.44371 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.187334 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00478495 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.340264 |  |
| `log_men` | ln(men_raw) | 0.605129 | [4.357, 5.781] |
| `morale` | morale | 0.177628 | [6, 13] |
| `melee_attack` | melee_attack | -0.0491242 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0311136 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.18014 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.351815 |  |
| `log_morale` | ln(1 + morale) | -0.103003 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.897054 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0582503 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.000475724 | [5, 9] |
| `morale^2` | morale² | -0.00701509 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -1.77697 |  |
| `log_men` | ln(men_raw) | 1.51217 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.124753 | [9, 30] |
| `reload_skill` | reload_skill | 0.00412115 | [4, 99] |
| `morale` | morale | -0.0875631 | [4, 18] |
| `melee_attack` | melee_attack | 0.126014 | [12, 25] |
| `melee_defense` | melee_defense | -0.0132544 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.0163161 | [16, 33] |
| `range0` | range | 0.00393881 | [70, 100] |
| `projectile_damage0` | projectile_damage | 3.55695 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0800051 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.0973624 |  |
| `has_stamina` | [has_stamina] | 0.0950211 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.103988 |  |
| `can_inspire` | [can_inspire] | 0.0946074 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.309547 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0713295 |  |
| `can_build_barricades` | [can_build_barricades] | 0.122801 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.13631 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -1.60498 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.224937 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.591153 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.0052713 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -6.02321 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0309351 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.0021427 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0285781 | [44.35, 168] |
| `morale^2` | morale² | 0.00142379 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00220042 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | -0.0307866 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | 0.0142839 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -7.39087 |  |
| `log_men` | ln(men_raw) | 2.28069 | [4.868, 6.114] |
| `train` | training code | 0.00454276 | [1, 4] |
| `reload_skill` | reload_skill | -0.0266861 | [23, 101] |
| `ammo` | ammo | -0.000298063 | [15, 70] |
| `melee_attack` | melee_attack | -0.0216368 | [6, 19] |
| `charge_bonus` | charge_bonus | 0.00405909 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0279625 | [14, 20] |
| `speed_num` | speed digit | 0.0558398 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.152435 |  |
| `has_stamina` | [has_stamina] | 0.114272 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.104404 |  |
| `can_inspire` | [can_inspire] | 0.104997 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.528597 |  |
| `guard_mode` | [guard_mode] | 0.0583106 |  |
| `pike_square` | [pike_square] | 0.0215184 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.367304 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.195959 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0123521 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.0716949 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.00677348 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -1.2134 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00583427 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.130345 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0753115 |  |
| `speed_code=L3` | [speed_code = L3] | -0.0962241 |  |
| `speed_code=L4` | [speed_code = L4] | 0.020426 |  |
| `speed_code=L5` | [speed_code = L5] | 0.0543929 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0538194 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0106949 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | -0.000107002 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.1794 |  |
| `log_men` | ln(men_raw) | 2.39598 | [4.852, 6.114] |
| `ammo` | ammo | 0.00356629 | [25, 70] |
| `morale` | morale | -0.0301483 | [0, 16] |
| `melee_attack` | melee_attack | 0.0311915 | [6, 23] |
| `melee_defense` | melee_defense | -0.012147 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0591376 | [9, 30] |
| `projectile_damage0` | projectile_damage | -0.145279 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0707929 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.126534 |  |
| `has_stamina` | [has_stamina] | 0.0929606 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0862675 |  |
| `can_inspire` | [can_inspire] | 0.0874143 |  |
| `can_place_stakes` | [can_place_stakes] | 0.245792 |  |
| `pike_square` | [pike_square] | 0.0338656 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.121082 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.196223 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.184421 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.21005 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.187314 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.32313 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00590242 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.500749 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0288875 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00230798 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000529003 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.99218 |  |
| `log_men` | ln(men_raw) | 1.61799 | [4.852, 6.881] |
| `train` | training code | -0.0171159 | [0, 3] |
| `ammo` | ammo | 0.00195622 | [0, 70] |
| `morale` | morale | 0.0785112 | [0, 18] |
| `melee_defense` | melee_defense | 0.0256311 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.0986388 | [8, 29] |
| `range0` | range | 0.00488969 | [0, 100] |
| `projectile_damage0` | projectile_damage | 1.39531 | [0, 0.83] |
| `speed_num` | speed digit | 0.177021 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.159632 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0601622 |  |
| `can_inspire` | [can_inspire] | -0.45436 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.387558 |  |
| `can_place_stakes` | [can_place_stakes] | 0.032902 |  |
| `scares_enemies` | [scares_enemies] | 0.414347 |  |
| `skirmish` | [skirmish] | -1.17992 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.396986 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.144691 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.121698 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | 0.0182902 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.15096 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.166109 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.31372 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00223034 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -1.76565 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.173827 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.00441832 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 6.0455 |  |
| `log_men` | ln(men_raw) | -0.622616 | [3.871, 5.606] |
| `train` | training code | 0.00987097 | [0, 4] |
| `accuracy` | accuracy | 0.00733559 | [15, 38] |
| `morale` | morale | 0.160684 | [3, 13] |
| `melee_attack` | melee_attack | -0.0689229 | [1, 23] |
| `charge_bonus` | charge_bonus | 0.00209657 | [1, 32] |
| `speed_num` | speed digit | 0.322122 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0387386 |  |
| `can_inspire` | [can_inspire] | -0.0351643 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.746257 |  |
| `can_place_stakes` | [can_place_stakes] | 0.132229 |  |
| `guard_mode` | [guard_mode] | -0.0242296 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.158244 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | 0.0135559 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -0.969677 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.403588 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.007109 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.013324 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.020932 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.12034 |  |
| `log_stars` | ln(command_stars) | 1.38341 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.899 |
| b0 | -80.65 |
| b1 | -56.47 |
| b2 | -32.91 |
| b3 | -11.68 |
| b4 | -1.861 |
| b5 | 43.33 |
| a_star1 | 0.01026 |
| a_star2 | 0.03444 |
| a_star3 | 0.06204 |
| a_star4 | 0.09518 |
| a_star5 | 0.12 |

Per-army commander premium `p_army` (gold, before dividing by N/10):

| army | p_army |
| --- | ---: |
| 7. Danmark | -15.0 |
| 8. Piemonte-Sardegna (1796) | 20.7 |
| 8. UK (Spain, 1808) | 27.0 |
| 9. France (1796) | -1.8 |
| 9. Heiliges Römisches Reich | 22.9 |
| [1798] 5. France (Irlande) | 10.4 |
| [1798] 5. UK (Ireland) | 29.6 |
| [1798] 8. France (Égypte) | -27.2 |
| [1798] 8. Mamālīk | -21.6 |
| [1799] 7. France (Hollande) | -9.8 |
| [1799] 7. UK, Russia (Helder) | 11.6 |
| [1799] 7. Österreich (Schwaben) | 9.8 |
| [1799] 9. France (Italie) | -17.1 |
| [1799] 9. France (Rhin) | -12.1 |
| [1799] 9. Österreich (Italien) | 2.6 |
| [1800] 8. Osmanlı, UK | 7.5 |
| [1804] 7. Irānshahr | -3.1 |
| [1804] 8. Rossiya (Kavkaz, Dunau) | -16.3 |
| [1805] 11. France (Allemagne) | -7.5 |
| [1805] 6. France (Tyrol) | 11.1 |
| [1805] 8. Österreich | 10.5 |
| [1805] 9. Rossiya, Österreich | 1.9 |
| [1806] 10. Preußen | -10.0 |
| [1806] 12. France (Prusse) | -26.1 |
| [1806] 9. Osmanlı | -11.2 |
| [1807] 9. Rossiya (Polsha) | 8.1 |
| [1808] 7. Rossiya (Finlyandiya) | 6.1 |
| [1808] 7. Sverige (Finska) | -4.5 |
| [1809] 10. France (Autriche) | -13.8 |
| [1809] 10. France (Espagne) | -20.6 |
| [1809] 10. UK, España, Portugal | -1.4 |
| [1809] 10. Österreich | -5.0 |
| [1809] 6. UK (Walcheren) | 22.0 |
| [1809] 7. Polska, sojusznicy | -10.2 |
| [1809] 8. Österreich (Tyrol) | 23.0 |
| [1809] 9. España | -1.1 |
| [1811] 7. España | 4.8 |
| [1811] 8. France (Espagne) | -1.2 |
| [1811] 9. UK, Portugal | -4.5 |
| [1812] 10. Rossiya | -14.7 |
| [1812] 11. France (Russie-Centre) | -14.9 |
| [1812] 6. France (Russie-Nord) | 12.6 |
| [1812] 7. France (Russie-Sud) | 5.4 |
| [1812] 7. UK (USA) | -11.8 |
| [1812] 7. United States | 17.0 |
| [1812] 8. Russkiy narod | -13.2 |
| [1814] 8. France | -8.0 |
| [1814] 8. Preußen (Frankreich) | 13.9 |
| [1814] 8. Österreich (Frankreich) | -1.9 |
| [1814] 9. Rossiya (Frantsiya) | -9.8 |
| [1815] 6. Napoli | 13.3 |
| [1815] 6. Österreich (Italien) | 22.5 |
| [1815] 7. Preußen (Flandern) | 10.8 |
| [1815] 9. France (Flandres) | -7.0 |
| [1815] 9. UK, Nederlanden | -2.8 |

#### Army × type multiplier table (118 non-blank cells; blank = 1)

| army | art_foot | art_horse | cav_heavy | cav_lance | cav_light | cav_stand | inf_grena | inf_light | inf_line | inf_milit | staff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7. Danmark |  |  | 0.929 |  |  |  | 0.881 |  | 0.928 |  |  |
| 8. Piemonte-Sardegna (1796) |  |  |  |  |  | 1.116 |  | 0.866 |  |  |  |
| 9. Heiliges Römisches Reich |  |  | 1.189 |  | 1.151 |  | 1.110 |  | 1.125 |  |  |
| [1798] 8. Mamālīk |  |  |  |  | 0.918 |  |  |  |  |  |  |
| [1799] 7. France (Hollande) |  |  |  |  |  |  | 0.902 |  |  |  |  |
| [1799] 7. UK, Russia (Helder) |  |  |  |  |  |  |  |  | 1.119 |  |  |
| [1799] 7. Österreich (Schwaben) |  |  | 0.940 |  | 0.942 |  |  |  | 1.081 |  |  |
| [1799] 9. France (Rhin) |  |  | 1.049 |  |  |  |  |  | 1.084 |  |  |
| [1799] 9. Österreich (Italien) |  |  |  | 0.899 |  |  |  |  | 1.073 |  |  |
| [1800] 8. Osmanlı, UK |  |  | 1.078 |  |  |  |  |  |  |  |  |
| [1804] 7. Irānshahr |  |  | 1.075 |  |  |  |  |  |  |  |  |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  |  |  | 1.051 |  |  |  | 0.805 | 0.914 |  |  |
| [1805] 11. France (Allemagne) |  |  |  |  |  |  |  |  | 0.909 |  |  |
| [1805] 6. France (Tyrol) |  |  | 1.052 |  | 1.046 | 0.883 | 0.929 | 0.917 |  |  |  |
| [1805] 8. Österreich |  |  |  |  | 0.927 |  | 1.021 |  |  |  |  |
| [1805] 9. Rossiya, Österreich |  |  | 0.917 |  |  |  | 1.093 |  | 1.049 |  |  |
| [1806] 10. Preußen |  |  |  |  |  | 0.953 | 1.216 |  |  |  |  |
| [1806] 12. France (Prusse) |  | 0.940 | 0.919 |  |  | 0.961 | 0.925 |  | 0.931 |  | 0.934 |
| [1806] 9. Osmanlı | 1.097 |  |  |  |  |  |  |  | 0.913 |  |  |
| [1807] 9. Rossiya (Polsha) | 0.845 |  | 1.036 |  |  |  |  |  | 1.052 |  |  |
| [1808] 7. Rossiya (Finlyandiya) |  |  |  | 0.838 |  |  |  | 0.819 |  |  |  |
| [1808] 7. Sverige (Finska) |  |  |  |  |  |  | 1.107 |  | 1.103 |  |  |
| [1809] 10. France (Autriche) |  |  |  |  |  | 1.041 | 0.917 |  | 0.947 |  |  |
| [1809] 10. France (Espagne) | 0.931 |  |  |  |  | 0.857 |  |  |  |  |  |
| [1809] 10. UK, España, Portugal |  |  | 1.156 |  |  |  |  |  |  |  |  |
| [1809] 10. Österreich |  |  |  |  |  |  | 0.952 |  | 1.066 |  |  |
| [1809] 6. UK (Walcheren) |  |  |  |  | 1.106 |  |  |  | 1.120 |  |  |
| [1809] 7. Polska, sojusznicy |  |  |  | 0.699 |  |  |  |  |  |  |  |
| [1809] 9. España |  |  |  |  |  |  |  | 1.072 | 1.104 |  |  |
| [1811] 7. España |  |  | 1.062 |  | 1.080 |  |  | 1.065 | 1.083 |  |  |
| [1811] 8. France (Espagne) | 0.924 |  |  |  |  | 0.946 |  |  |  |  |  |
| [1811] 9. UK, Portugal |  |  | 1.053 |  |  |  |  | 0.867 | 0.910 |  |  |
| [1812] 10. Rossiya |  |  |  | 1.034 | 1.084 | 0.961 |  | 1.049 |  |  |  |
| [1812] 11. France (Russie-Centre) | 0.788 |  | 0.947 |  |  |  | 0.935 |  |  |  |  |
| [1812] 6. France (Russie-Nord) |  | 0.913 | 1.070 |  | 0.914 |  |  | 0.885 |  |  |  |
| [1812] 7. France (Russie-Sud) |  |  |  |  |  |  |  | 0.908 | 0.931 |  |  |
| [1812] 7. United States |  |  |  |  |  |  |  |  | 0.924 | 0.682 |  |
| [1812] 8. Russkiy narod |  |  |  | 0.852 |  |  |  |  |  |  |  |
| [1814] 8. France | 0.777 |  | 0.869 |  | 1.079 |  |  | 0.828 | 0.908 |  |  |
| [1814] 8. Preußen (Frankreich) | 1.121 |  | 0.925 |  |  |  |  |  |  |  |  |
| [1814] 8. Österreich (Frankreich) |  |  | 0.911 |  | 0.891 |  | 1.102 |  | 1.103 |  |  |
| [1814] 9. Rossiya (Frantsiya) | 1.061 | 1.048 | 0.894 |  | 1.088 |  | 1.110 | 1.066 | 1.087 |  |  |
| [1815] 6. Napoli |  |  |  |  |  |  | 0.922 |  |  |  |  |
| [1815] 6. Österreich (Italien) |  |  |  |  | 1.057 |  |  | 0.897 |  |  |  |
| [1815] 7. Preußen (Flandern) | 0.899 |  |  |  | 0.932 |  |  |  |  |  |  |
| [1815] 9. France (Flandres) |  |  | 0.829 |  |  | 1.033 |  |  | 0.952 |  |  |
| [1815] 9. UK, Nederlanden |  |  | 0.835 |  |  |  |  |  | 1.068 |  |  |

### 4.5 Model 18b (simplest) — written out in full

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -9.00699 |  |
| `log_men` | ln(men_raw) | 1.97036 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00601819 | [6, 82] |
| `reload_skill` | reload_skill | 0.00449786 | [14, 100] |
| `morale` | morale | 0.0255631 | [2, 12] |
| `melee_defense` | melee_defense | -0.299491 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.397624 | [0, 2] |
| `range0` | range | 0.000935405 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0284301 | [17, 80] |
| `speed_num` | speed digit | 0.182431 | [0, 6] |
| `guns0` | guns | 0.00495475 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.162982 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.359078 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 1.51372 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.623118 | [0, 1.099] |
| `men_raw` | men_raw | -0.00690932 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.145905 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.77476 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.6922 |  |
| `log_men` | ln(men_raw) | 2.49021 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00677493 | [29, 85] |
| `reload_skill` | reload_skill | 0.00350881 | [35, 100] |
| `morale` | morale | 0.105346 | [5, 14] |
| `range0` | range | 0.00175334 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0130918 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.177443 | [14, 40] |
| `speed_num` | speed digit | 0.369444 | [1, 3] |
| `guns0` | guns | -0.173743 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.198311 |  |
| `can_inspire` | [can_inspire] | 0.147636 |  |
| `log_morale` | ln(1 + morale) | -0.541942 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | -0.235722 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.785344 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.51031 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000392095 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | -0.00177098 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | -0.0093687 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0622666 |  |
| `log_men^2` | ln(men_raw)² | 0.0118726 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.00107076 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0272127 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.11088 |  |
| `log_men` | ln(men_raw) | 0.501636 | [4.382, 5.823] |
| `train` | training code | -0.0243417 | [1, 4] |
| `morale` | morale | 0.0138456 | [7, 18] |
| `melee_attack` | melee_attack | -0.0556155 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0148223 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.17748 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.347816 |  |
| `can_inspire` | [can_inspire] | 0.174095 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.26726 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.87845 |  |
| `log_men` | ln(men_raw) | 0.626269 | [4.357, 5.656] |
| `morale` | morale | 0.0379023 | [4, 16] |
| `melee_defense` | melee_defense | -0.0166631 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0628353 | [1, 9] |
| `rank_depth` | rank_depth | -0.0221961 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.271802 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.28526 |  |
| `can_inspire` | [can_inspire] | 0.0733272 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.0153958 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.0812534 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.279404 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.48379 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00321456 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.12925 |  |
| `log_men` | ln(men_raw) | 0.543125 | [4.331, 5.886] |
| `accuracy` | accuracy | -0.0025818 | [0, 34] |
| `reload_skill` | reload_skill | -0.00591457 | [0, 90] |
| `morale` | morale | -0.0241045 | [3, 15] |
| `melee_defense` | melee_defense | -0.0247168 | [3, 23] |
| `range0` | range | 0.0148769 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.265411 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.302081 |  |
| `can_inspire` | [can_inspire] | 0.185349 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.486275 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.236531 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.00771229 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.560697 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.52787 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.167366 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00414766 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.441049 |  |
| `log_men` | ln(men_raw) | 0.615718 | [4.357, 5.781] |
| `morale` | morale | 0.0251215 | [6, 13] |
| `melee_attack` | melee_attack | -0.0262528 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0326373 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.193197 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.343363 |  |
| `log_morale` | ln(1 + morale) | 0.684141 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.49187 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.00913928 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00549096 | [5, 9] |
| `morale^2` | morale² | -0.00295545 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -0.788416 |  |
| `log_men` | ln(men_raw) | 1.7923 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.12107 | [9, 30] |
| `reload_skill` | reload_skill | 0.0040976 | [4, 99] |
| `morale` | morale | 0.032565 | [4, 18] |
| `melee_attack` | melee_attack | 0.145528 | [12, 25] |
| `melee_defense` | melee_defense | -0.0467862 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.0302549 | [16, 33] |
| `range0` | range | -0.00112692 | [70, 100] |
| `projectile_damage0` | projectile_damage | 16.0271 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0625854 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.10382 |  |
| `has_stamina` | [has_stamina] | 0.109379 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.106238 |  |
| `can_inspire` | [can_inspire] | 0.151308 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.3391 |  |
| `can_place_stakes` | [can_place_stakes] | 0.171014 |  |
| `can_build_barricades` | [can_build_barricades] | 0.090112 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.233312 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -2.25338 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.53637 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.14658 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.00606171 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -26.0187 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0100855 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.00325336 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0340685 | [44.35, 168] |
| `morale^2` | morale² | 0.00154925 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00153607 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | 0.241062 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | -0.0105067 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -10.0068 |  |
| `log_men` | ln(men_raw) | 2.72567 | [4.868, 6.114] |
| `train` | training code | 0.00898084 | [1, 4] |
| `reload_skill` | reload_skill | -0.0368356 | [23, 101] |
| `ammo` | ammo | 6.23052e-05 | [15, 70] |
| `melee_attack` | melee_attack | 0.0537663 | [6, 19] |
| `charge_bonus` | charge_bonus | 0.0144746 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0268844 | [14, 20] |
| `speed_num` | speed digit | 0.0509128 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.148745 |  |
| `has_stamina` | [has_stamina] | 0.171406 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0962547 |  |
| `can_inspire` | [can_inspire] | 0.105579 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.580442 |  |
| `guard_mode` | [guard_mode] | 0.0363437 |  |
| `pike_square` | [pike_square] | 0.0167913 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.565259 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.204284 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.00432383 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.153121 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.00819515 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.971334 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00723892 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.101118 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0767339 |  |
| `speed_code=L3` | [speed_code = L3] | -0.139579 |  |
| `speed_code=L4` | [speed_code = L4] | 0.00550103 |  |
| `speed_code=L5` | [speed_code = L5] | 0.0392352 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0548169 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.00459154 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | 3.43369e-05 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.5731 |  |
| `log_men` | ln(men_raw) | 2.50528 | [4.852, 6.114] |
| `ammo` | ammo | 0.00347259 | [25, 70] |
| `morale` | morale | -0.00364967 | [0, 16] |
| `melee_attack` | melee_attack | 0.026238 | [6, 23] |
| `melee_defense` | melee_defense | -0.00187069 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0647362 | [9, 30] |
| `projectile_damage0` | projectile_damage | -1.78864 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0613025 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.129106 |  |
| `has_stamina` | [has_stamina] | 0.0900882 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0909956 |  |
| `can_inspire` | [can_inspire] | 0.117947 |  |
| `can_place_stakes` | [can_place_stakes] | 0.281813 |  |
| `pike_square` | [pike_square] | 0.0233529 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.205956 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.192494 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.17 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.185118 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0979257 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.52313 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00620888 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.723374 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0237962 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00233937 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000417565 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.83855 |  |
| `log_men` | ln(men_raw) | 1.3468 | [4.852, 6.881] |
| `train` | training code | -0.0015035 | [0, 3] |
| `ammo` | ammo | 0.00828755 | [0, 70] |
| `morale` | morale | 0.0892464 | [0, 18] |
| `melee_defense` | melee_defense | 0.0528201 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.120451 | [8, 29] |
| `range0` | range | 0.00648742 | [0, 100] |
| `projectile_damage0` | projectile_damage | 1.6662 | [0, 0.83] |
| `speed_num` | speed digit | 0.154293 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.154176 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0297457 |  |
| `can_inspire` | [can_inspire] | -0.550438 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.483355 |  |
| `can_place_stakes` | [can_place_stakes] | -0.0384188 |  |
| `scares_enemies` | [scares_enemies] | 0.501899 |  |
| `skirmish` | [skirmish] | -1.73539 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.451805 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.12229 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.266034 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | -0.0552399 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.24108 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.323874 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.5935 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00281183 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.763356 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.219789 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.039996 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 6.67375 |  |
| `log_men` | ln(men_raw) | -0.593129 | [3.871, 5.606] |
| `train` | training code | -0.00391688 | [0, 4] |
| `accuracy` | accuracy | 0.0153331 | [15, 38] |
| `morale` | morale | 0.178187 | [3, 13] |
| `melee_attack` | melee_attack | -0.0514934 | [1, 23] |
| `charge_bonus` | charge_bonus | -0.00380718 | [1, 32] |
| `speed_num` | speed digit | 0.312771 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0165651 |  |
| `can_inspire` | [can_inspire] | -0.0311014 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.718611 |  |
| `can_place_stakes` | [can_place_stakes] | 0.128546 |  |
| `guard_mode` | [guard_mode] | -0.0179605 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.0387885 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | 0.00991845 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -1.14465 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.337272 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.00545123 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.0129776 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.00424912 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.1073 |  |
| `log_stars` | ln(command_stars) | 1.39365 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.8865 |
| b0 | -74.97 |
| b1 | -57.38 |
| b2 | -30.24 |
| b3 | 8.432 |
| b4 | 33.17 |
| b5 | 53.3 |
| a_star1 | 0.02126 |
| a_star2 | 0.0424 |
| a_star3 | 0.03695 |
| a_star4 | 0.05957 |
| a_star5 | 0.1216 |


## 5. Error analysis (model 13c)

Out-of-fold CV predictions (10 014 rows) and the holdout (2 504 rows); full tables in
`out/error_analysis_oof_13c.md` and `out/error_analysis_holdout_13c.md`
(`src/error_analysis.py`).

**By kind of row**

| kind | CV n | CV MAE | CV MAPE % | holdout n | holdout MAE | holdout MAPE % |
| --- | --- | --- | --- | --- | --- | --- |
| regular unit | 5 594 | 27.5 | 6.2 | 1 398 | 28.2 | 6.7 |
| commander variant | 4 191 | 28.7 | 8.5 | 1 047 | 28.9 | 12.3 |
| staff general | 229 | 3.5 | 0.4 | 59 | 0.9 | 0.9 |

**Where the misses are**

- **Price level.** Absolute error grows with price but relative error falls: CV MAE is
  17–18 gold below 400 gold, 38 at 700–1 000, 50 at 1 000–1 500 and 65 above 1 500, while
  MAPE drops from 13% (50–200 gold) to 3.6% (above 1 500). The 93 rows under 50 gold (mostly
  near-free commanders) have small absolute errors (median 2.7) but a MAPE of 89%; they
  inflate MAPE, not MAE.
- **Unit type.** Line and light infantry are priced best (regular `inf_line` CV MAE 17.5,
  5.1%; `inf_light` 21.3). The largest absolute misses are heavy cavalry (47 regular,
  42 commanders — but only 4% relative, they are expensive) and foot artillery (40, 8.4%).
  Skirmisher, militia and horse-artillery *commanders* have the worst relative errors
  (MAPE 16–57%): few rows, low prices, and the additive commander premium is least certain
  for them.
- **Commander stars.** Error grows with stars (CV MAE 26 at 0–1 star, 35 at 3, 47–49 at
  4–5) because high-star commanders are rare and expensive. The single largest holdout
  miss is a 5-star skirmisher commander, *Tecumseh* (`[1812] 7. UK (USA)`): predicted
  3 351, true 1 866 — the 5-star slope extrapolated onto an already expensive unit.
- **Training level.** `mob` and `poorly_trained` units are worst (CV MAE 40 and 34; holdout
  `mob` 58.5 with a +30 bias) — Cossack-type and irregular units whose stats spread widely.
- **Army.** Errors do cluster by army: `[1811] 7. España` is the worst army in both CV (MAE
  43.6) and holdout (41.4); the Russian armies are the best (`[1812] 10. Rossiya` 17.5).
  Armies with small N (5–7, i.e. prices ×1.4–2) have larger absolute errors simply because
  their prices are higher (N = 7: MAE 32.9; N = 10: 21.4). After the army table, the mean
  residual per army × type cell still explains 12% of the squared CV error, so army-level
  pricing quirks remain the largest structured source of error. Custom armies are slightly
  worse than Theatre-of-War ones (CV MAE 31.9 vs 27.3).
- **Unique units.** The biggest individual misses are one-of-a-kind units that sit outside
  their type's typical stats: the Ottoman mortar *Havan topu* (CV +874) and the Congreve
  rockets (holdout +581) — two of the four fixed-artillery `[F0]` units, which are priced with
  the foot-artillery formula, the *Württembergische Garde du Corps* (+540, and
  its commander +660), a camel regiment (*Régiment de dromadaires*, +514), and Wellington (a staff general whose army has a divisor of 0.64; −639 in CV).
- **No systematic bias** overall (CV mean error +0.4 gold; holdout +3.7), but some
  commander groups have a type-level bias (CV: light-infantry commanders −13.5, light/
  heavy-cavalry and lancer commanders +11 to +15), a sign that the commander slope differs
  a little by type; per-type commander slopes did not improve CV MAE (exp 11a/11b).

## 6. Limitations and judgment calls

- **`unit_key` type code.** Commander variants are labelled `general`, so the type of the
  unit they command is taken from the type code in `unit_key` (e.g. `inf_line`). Without
  it, CV MAE is ~8.5 worse (exp 06c). Nothing else is taken from `unit_key`, `unit_name`
  or other identifiers.
- **Army tables are lookups, not explanations.** They encode per-army price adjustments
  that no column explains. Model 18b shows what the stat formulas alone achieve (43 MAE,
  R² 0.96); 18a is the middle ground. The army tables can only price armies seen in
  training; an unseen army falls back to multiplier 1 and premium 0, i.e. model 18b.
- **Clamping.** Each input is clamped to the range seen in training for its type. This is
  part of the model (the ranges are in the tables) and is what keeps exp() from
  extrapolating wildly on rare units.
- **Out-of-scope rows.** The `army_corps` rows (13 116) were not used for fitting or
  features. A check on development data showed that Theatre-of-War prices are *not* a
  simple rescaling of the matching army-corps unit's price (log-ratio sd 0.17), so nothing
  is lost.
- **Selection.** Term selection per type was greedy (prune, then add), nested inside CV.
  Different folds picked overlapping but not identical terms; the final terms are those
  selected on all five development folds. Coefficients should be read jointly (log and
  linear versions of the same stat appear together), not one at a time.

## 7. Reproducing

Python 3 with numpy, pandas, scikit-learn (`requirements.txt`). All scripts are
deterministic and write to `out/`.

| step | script |
| --- | --- |
| holdout + folds (run once) | `src/00_make_split.py` |
| baselines | `src/01_baselines.py`, `src/02_clean_and_loglinear.py` |
| experiments 03–18 | `src/0x_…py`, `src/1x_…py` (one script per experiment group) |
| nested term selection (slow, ~3 h on 4 cores, resumable) | `src/13_select_run.py` |
| final candidates | `src/candidates.py`; CV: `src/13_selected_eval.py 13c 18a 18b` |
| holdout (once) | `src/90_holdout.py` |
| export written-out models + hand-pricing check | `src/91_export_final.py` |
| worked examples | `src/92_worked_example.py` |
| error analysis | `src/error_analysis.py out/oof_13c.csv` |
| this report | `src/93_build_report.py` |

Every experiment's CV row is in `RESULTS.md`; working notes are in `NOTES.md`.
