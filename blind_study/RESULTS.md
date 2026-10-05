# Results log

Append one row per experiment. Metrics are 5-fold CV on the development 80%, as mean ± sd
over folds, on total price (`base_mp_cost`). Holdout results go in a separate table at the
bottom, filled in only at the end.

| id | time (UTC) | segment | model & features | CV MAE (gold) | MAPE % | R² | params | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | 2026-10-05 03:47 | all | global mean | 308.0 ± 4.2 | 343.77 ± 402.27 | -0.0006 ± 0.0004 | 1 | baseline 1 |
| 02a | 2026-10-05 03:47 | all | mean per unit_class | 269.3 ± 5.3 | 313.86 ± 377.90 | 0.0926 ± 0.0226 | 15 | baseline 2 |
| 02b | 2026-10-05 03:47 | all | per-class gold/man x men_raw | 280.7 ± 6.0 | 127.85 ± 54.07 | 0.0401 ± 0.0470 | 15 | baseline 2, size-scaled |
| 02c | 2026-10-05 03:47 | all | per class: mean or gold/man x men (chosen on train fold) | 253.2 ± 5.4 | 307.94 ± 377.25 | 0.1279 ± 0.0463 | 15 | baseline 2, best of both per class |
| 02d | 2026-10-05 03:51 | all (clean) | global mean | 283.8 ± 2.5 | 331.25 ± 388.59 | -0.0010 ± 0.0006 | 1 | baseline 1 after excluding 34 joke/placeholder rows |
| 02e | 2026-10-05 03:51 | all (clean) | per class: mean or gold/man x men (chosen on train) | 228.7 ± 4.8 | 305.68 ± 378.55 | 0.2749 ± 0.0605 | 15 | baseline 2 on clean set |
| 03 | 2026-10-05 03:51 | staff generals / rest | log price ~ class + log men + log N + stars; staff: 1 if no stars else log-linear(log stars, log N) | 212.3 ± 6.1 | 63.91 ± 9.81 | 0.3123 ± 0.0258 | 21 | multiplicative structure; corps number N from army name |
| 04 | 2026-10-05 03:51 | staff / inf / cav / art | log-linear, all raw stats + flags + class + log men + log N (linear in stats) | 73.3 ± 4.8 | 18.14 ± 2.84 | 0.6098 ± 0.6309 | ~40/seg | first full log-linear per base type |
| 05a | 2026-10-05 03:53 | staff / inf / cav / art, joint | log-linear stats (as exp 04) + army offset = -log(N/10) fixed | 73.4 ± 5.2 | 18.20 ± 2.83 | 0.5744 ± 0.7121 | 38/seg + 0 army | faction divisor modelling |
| 05b | 2026-10-05 03:53 | staff / inf / cav / art, joint | log-linear stats (as exp 04) + -log(N/10) + per-army deviation (ridge 1e-3) | 71.8 ± 6.1 | 17.49 ± 2.97 | 0.5319 ± 0.8202 | 38/seg + 55 army | faction divisor modelling |
| 05c | 2026-10-05 03:53 | staff / inf / cav / art, joint | log-linear stats (as exp 04) + free per-army lookup (no N) | 72.2 ± 6.3 | 17.52 ± 2.98 | 0.5244 ± 0.8363 | 38/seg + 55 army | faction divisor modelling |
| 06a | 2026-10-05 03:56 | 12 segments, joint | type segments; log-linear stats + commander terms; army offset | 54.4 ± 2.4 | 14.38 ± 3.29 | 0.9006 ± 0.1056 | 32/seg + 55 army | unit type from unit_key token; commanders join their unit's segment: big gain |
| 06b | 2026-10-05 03:56 | 12 segments, joint | 06a, fit without rows < 50 gold | 51.2 ± 2.1 | 14.39 ± 3.46 | 0.9016 ± 0.1218 | 32/seg + 55 army | near-free commanders (<50) distort log fit; dropping them from training helps |
| 06c | 2026-10-05 03:56 | 4 segments, joint | base-type segments + speed-letter/drill dummies (no unit_key); fit w/o < 50 gold | 59.7 ± 2.5 | 16.07 ± 2.95 | 0.8830 ± 0.1246 | 38/seg + 55 army | without unit_key type code: +8.5 MAE worse than 06b |
| 07a | 2026-10-05 03:57 | 12 segments, joint | 06b with separate army offsets for staff generals and units | 51.1 ± 2.1 | 14.35 ± 3.46 | 0.9016 ± 0.1218 | 32/seg + 105 army | negligible gain |
| 07b | 2026-10-05 03:57 | 12 segments, joint | 07a with weaker shrinkage (1e-4) | 51.2 ± 2.1 | 14.34 ± 3.44 | 0.9009 ± 0.1233 | 32/seg + 105 army | shrinkage barely matters |
| 07c | 2026-10-05 03:57 | 12 segments, joint | 07a with stronger shrinkage (1e-2) | 50.8 ± 2.0 | 14.46 ± 3.52 | 0.9041 ± 0.1170 | 32/seg + 105 army | army offsets are not the bottleneck; unit stats are |
| 08a | 2026-10-05 03:59 | 11 types x (regular, commander) + staff, joint | commander/regular split; army offsets: staff + units tables | 50.3 ± 2.6 | 14.78 ± 5.43 | 0.9122 ± 0.0932 | 31/seg + 105 army | separate coefficients for commanders helps a little |
| 08b | 2026-10-05 03:59 | 11 types x (regular, commander) + staff, joint | commander/regular split; army offsets per base type (staff/inf/cav/art) | 48.5 ± 2.5 | 14.46 ± 5.38 | 0.9136 ± 0.0963 | 31/seg + 215 army | army effect differs by broad type |
| 08c | 2026-10-05 03:59 | 11 types x (regular, commander) + staff, joint | commander/regular split; army offsets per unit type (12 tables) | 48.5 ± 2.5 | 14.55 ± 5.43 | 0.9134 ± 0.0969 | 31/seg + 585 army | shrinkage 1e-2 too strong for small army x type cells |
| 08d | 2026-10-05 03:59 | 11 types x (regular, commander) + staff, joint | 08b with weak army shrinkage (1e-4) | 47.4 ± 2.4 | 13.85 ± 4.98 | 0.9028 ± 0.1239 | 31/seg + 215 army | weak shrinkage better |
| 08e | 2026-10-05 04:00 | 11 types x (regular, commander) + staff, joint | 08c with weak army shrinkage (1e-4) | 42.5 ± 2.5 | 13.29 ± 5.16 | 0.9004 ± 0.1423 | 31/seg + 585 army | army x unit-type table (55x12) helps most; not compact |
| 09a | 2026-10-05 04:01 | regular: 11 types + staff; commanders: stage 2 | two-stage; commander adj. global (a, b0..b5), least squares | 39.5 ± 2.2 | 9.45 ± 0.61 | 0.9118 ± 0.1287 | 29/seg + 579 army + 7 cv | commanders additive in regular price: big gain, 7 params |
| 09b | 2026-10-05 04:01 | regular: 11 types + staff; commanders: stage 2 | two-stage; commander adj. per base type, least squares | 39.6 ± 2.2 | 9.89 ± 0.63 | 0.9122 ± 0.1286 | 29/seg + 579 army + 21 cv | no gain over global |
| 09c | 2026-10-05 04:01 | regular: 11 types + staff; commanders: stage 2 | two-stage; commander adj. per unit type, least squares | 39.3 ± 2.1 | 10.49 ± 1.63 | 0.9136 ± 0.1285 | 29/seg + 579 army + 77 cv | marginal |
| 09d | 2026-10-05 04:01 | regular: 11 types + staff; commanders: stage 2 | two-stage; commander adj. per unit type, least abs. deviation | 39.1 ± 2.0 | 9.68 ± 0.72 | 0.9136 ± 0.1285 | 29/seg + 579 army + 77 cv | LAD marginally better; global LS is the simple choice |
| 10a | 2026-10-05 04:04 | regular: 11 types + staff; commanders: stage 2 | 09a + log1p stats, men_raw, log1p art stats; clamp; ridge 1e-4 | 32.1 ± 1.2 | 7.46 ± 0.32 | 0.9806 ± 0.0021 | 41/seg + 579 army + 7 cv | log stats + clamping: big gain, R2 stable |
| 10b | 2026-10-05 04:04 | regular: 11 types + staff; commanders: stage 2 | 10a with ridge 1e-5 | 32.0 ± 1.3 | 7.42 ± 0.33 | 0.9800 ± 0.0027 | 41/seg + 579 army + 7 cv | ~same |
| 10c | 2026-10-05 04:04 | regular: 11 types + staff; commanders: stage 2 | 10a with ridge 1e-3 | 33.9 ± 1.1 | 8.29 ± 0.73 | 0.9801 ± 0.0017 | 41/seg + 579 army + 7 cv | too much shrinkage |
| 10d | 2026-10-05 04:04 | regular: 11 types + staff; commanders: stage 2 | 10a but army offsets per base type (staff/inf/cav/art) | 38.2 ± 1.3 | 8.50 ± 0.43 | 0.9717 ± 0.0042 | 41/seg + 215 army + 7 cv | compact army table costs +6 MAE |
| 11a | 2026-10-05 04:06 | regular: 11 types + staff; commanders: stage 2 | 10b + commander slope a per base type | 32.0 ± 1.2 | 7.38 ± 0.28 | 0.9801 ± 0.0027 | 41/seg + 579 army + 9 cv | ~no gain |
| 11b | 2026-10-05 04:06 | regular: 11 types + staff; commanders: stage 2 | 10b + commander slope a per unit type | 32.3 ± 1.4 | 7.48 ± 0.32 | 0.9802 ± 0.0029 | 41/seg + 579 army + 17 cv | no gain |
| 11c | 2026-10-05 04:06 | regular: 11 types + staff; commanders: stage 2 | 10b + commander star-specific slopes | 31.7 ± 1.2 | 7.64 ± 0.73 | 0.9801 ± 0.0025 | 41/seg + 579 army + 12 cv | small gain; commander stage near its floor |
| 11d | 2026-10-05 04:06 | regular: 11 types + staff; commanders: stage 2 | 10b + commander slope per unit type + star slopes | 32.0 ± 1.3 | 7.54 ± 0.42 | 0.9803 ± 0.0027 | 41/seg + 579 army + 22 cv | no gain |
| 12a | 2026-10-05 04:07 | regular: 11 types + staff; commanders: stage 2 | 11c + stage-1 weights = price | 29.8 ± 0.9 | 7.90 ± 1.32 | 0.9835 ± 0.0018 | 41/seg + 579 army + 12 cv | aligning loss with gold MAE helps |
| 12b | 2026-10-05 04:07 | regular: 11 types + staff; commanders: stage 2 | 11c + stage-1 LAD on log (IRLS 10) | 29.9 ± 1.1 | 7.53 ± 0.71 | 0.9821 ± 0.0030 | 41/seg + 579 army + 12 cv | robust loss helps |
| 12c | 2026-10-05 04:07 | regular: 11 types + staff; commanders: stage 2 | 11c + stage-1 price-weighted LAD on log (IRLS 10) | 28.6 ± 0.8 | 8.26 ± 1.93 | 0.9841 ± 0.0023 | 41/seg + 579 army + 12 cv | both combined: best so far |
| 12d | 2026-10-05 04:08 | regular: 11 types + staff; commanders: stage 2 | 12c + commander stage by LAD | 28.6 ± 0.9 | 8.11 ± 1.83 | 0.9842 ± 0.0024 | 41/seg + 579 army + 12 cv | same as 12c; keep LS for commander stage |

## Holdout (final, evaluated once)

| model | holdout MAE | MAPE % | R² |
| --- | --- | --- | --- |
