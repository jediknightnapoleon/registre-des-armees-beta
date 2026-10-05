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

EXCLUDED_TABLE

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
   units only in some cases (all data, units compared with the stats-only model 18b; armies
   whose generals follow N/10 have a median unit level of 1.00, IQR 0.97–1.02):
   - **whole army:** HRE units are ×1.12 (generals ×1.14 = 0.9/0.79); Rossiya (Frantsiya)
     units ×1.04 (generals ×1.03).
   - **generals only:** UK, España, Portugal — generals ×1.58, units ×0.98 (normal);
     France (Égypte) — generals ×0.94, units ×0.99.
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

MODELS_PLACEHOLDER
