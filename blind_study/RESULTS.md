# Results log

Append one row per experiment. Metrics are 5-fold CV on the development 80%, as mean ± sd
over folds, on total price (`base_mp_cost`). Holdout results go in a separate table at the
bottom, filled in only at the end.

| id | time (UTC) | segment | model & features | CV MAE (gold) | MAPE % | R² | params | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Holdout (final, evaluated once)

| model | holdout MAE | MAPE % | R² |
| --- | --- | --- | --- |
