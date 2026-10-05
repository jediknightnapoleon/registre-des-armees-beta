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

## Holdout (final, evaluated once)

| model | holdout MAE | MAPE % | R² |
| --- | --- | --- | --- |
