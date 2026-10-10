# Working notes (blind AC pricing study)

## Status log
- Data: 7 198 scored regular rows (7 205 minus 7 fixed art.; 7 regular art. rows have empty fold = always-train).
  Every unit_key is unique (one row per unit per army), so there is no "same unit in other army" price to borrow.
- Scripts in src/: common.py (loading, metrics), harness.py (CV over given folds, report -> RESULTS.md),
  features.py (Design blocks + generalised ridge with per-group penalties).

## Learned so far
- Baselines: B0 class mean MAE 236.6; B1 class mean scaled by size MAE 214.0.
- corps_number is a huge army effect: in a log-price model the army mean residual falls almost linearly/convexly
  from about +0.7 (cn 3) to -0.4 (cn 13); corr(army mean residual, cn) = -0.94 infantry, -0.92 cavalry, -0.82 artillery.
  i.e. high-numbered armies have cheaper units. Shape looks like 1/(cn + ~2) or a convex exp.
- E01 log-linear per arm (size, stats, abilities, class, training, speed, cn one-hot, side): MAE 63.9, MAPE 10.4%.
- E02 + shrunk per-army offset: MAE 58.2. Artillery is the weakest arm (MAPE ~16%).

## Next
- size curve per class (residual vs log size), artillery-specific features (calibre via projectile_damage, crew men, range),
  stats additive vs multiplicative, functional form for corps_number, army-level features from faction_key (a/b, nn, x-digit).

## Update after E03-E06 (about 45 min in)
- men_raw (not men_display) is what price follows: two identical Cossack units differing only men_raw 120 vs 121 cost 752 vs 764.
- Stat effects are concave in log-price (saturating) -> log1p(stat) + linear stat terms (E03c) help.
- log-size^2 + class-specific log-size slope help; artillery needs calibre (log projectile_damage), howitzer flag,
  log range, log reload + guns one-hot (1-gun batteries are much cheaper than a power law says): art MAE 107 -> 71 (E03f).
- Army: joint army FE (common across arms, corr 0.92-0.96 between arms) ~ -0.92*log(cn) (price ~ cn^-0.92);
  residual army sd after cn ~0.066 in log; empire -0.04, 'r' faction-key letter -0.10, weak link to roster mean value.
  faction_key codes (era nn, x-digit, r) help the no-army-table model a bit (E04b 51.1 vs 52.9).
- Per-army offsets (E04a 45.9) and per-army x class offsets (E05f pen 2: 40.4) are worth a lot.
  Per-arm models already make the army offset an army x arm offset.
- log1p stats x class interactions (pen 5) help infantry (E06a overall 38.4). abilities x class small gain.
- unit_cap/division one-hot and formation geometry: no gain.

## Next
- error analysis on E06a; artillery size form; consider final spec + nested penalty selection + unseen-army test.

## Update after E07-E09 + final runs (about 1h20 in)
- Hinge spline in log men_raw (knots 60,100,150,220,320) beats quadratic: infantry 29.8 -> 26.9 (E07a); quad then redundant (E09b).
- log(cn) single slope is as good as cn one-hot once army offsets exist (E07d) -> use log cn (price ~ cn^b).
- Artillery projectile one-hot: art 56.3 -> 48.4 (E08a). Gun-count one-hot is essential (E09c without: art 67.6).
- Linear stat terms needed besides log1p (E09a worse by 2 gold on infantry).
- army x class offsets are idiosyncratic: hardly correlated with any army-class aggregate (|r| < 0.25).
- FINAL (src/final.py, nested penalty choice per fold; choices very stable):
  M1 (army tables) CV MAE 34.6 / MAPE 5.78% / R2 0.976; unseen-army 64.8 / 7.99%.
  M2 (army-blind, fk codes) CV 47.9 / 7.60%; unseen-army 71.4 / 8.62% -> M1 with zero offsets generalises better than M2!
## Next
- analysis.py: coefficients of M1 (all data), size curves + size-band errors, army findings, error analysis, CSV outputs.
- generals (staff + commander variants) if time; then REPORT.md.

## Update: finals done (about 2h30 in)
- E10a: in-range spline knots (inf 150/200/260/340, cav 100/130/170/230) as good/better -> adopted in final.py.
- FINAL M1 (nested): CV MAE 34.1 ± 0.9, MAPE 5.73%, R2 0.977; unseen-army 64.2 / 7.98%. M2: 47.5 / 7.59%; unseen 71.5 / 8.67%.
- price ~ cn^-0.92..-0.96 in every arm (and staff generals cn^-0.93); empire armies 4-6% cheaper; after that army offsets
  have sd ~0.05 and are only weakly shared across arms (r ~0.25-0.30); army x class offsets sd 0.04-0.06.
- Size: infantry flat (elasticity ~0.3) below 150 men_raw, steep 150-200 (~1.7), ~1 at 200-260, ~0.8 at 260-340, ~0.1 above 340;
  skirmishers/militia/irregulars steeper. Cavalry flat (~0.1-0.16) below 100 men_raw, ~0.5-0.9 above. Artillery: gun factor vs 3 guns
  1:0.11 2:0.53 4:1.5 5:2.1 -> 1-gun units are nearly free; roughly linear from 2 guns up (price ~ guns - 1.1).
- Staff generals: G-ST1 T[stars] x cn^-0.93, MAPE 4.7%. Commander variants: additive G-CV4 (MAE 36.1, MAPE 10.6%) beats
  multiplicative G-CV2 (49.4, 16.8%); G-CV5 best MAE 31.0. Sub-100-gold variants dominate MAPE.
- Remaining: REPORT.md.

## Done (about 2h45)
- REPORT.md written (sections: summary, protocol, CV + unseen tables, M1 in full incl. worked example, generals,
  size, army, error analysis, limitations, files). out/ has oof/holdout/generals CSVs, coefficient tables, army tables.
- If resumed: possible next steps - commander variants under 100 gold (mixed additive/multiplicative), artillery horse
  batteries, smaller formula (fewer stat terms) at a small accuracy cost.
