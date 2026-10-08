# Running log

One row per experiment, in the order they were run. AUC / log-loss are on
decisive armies. "val" = fit on training armies before 2026-09-05T22:20:30Z
(80th percentile of training game times, 4 433 armies), scored on the rest of
the training armies (1 114). "test" = fit on all training armies, scored on the
2 168 decisive test armies (played_at >= 2026-09-20T15:25:11Z). Seeds: match
folds 20260920, validation bootstrap 7, test bootstrap 11.

| # | experiment | split | n | AUC | log-loss | notes |
|---|---|---|---|---|---|---|
| 1 | univariate build features, faction-adjusted (`explore.py`) | train | 5 547 | - | - | strongest: combat general present (z 6.1; 4.5 with Elo control), staff stars, gold on artillery (-), lancers (+), light infantry (+, halves under Elo). Paper surplus z 0.7 (-0.2 with Elo). "Unspent gold" looked positive - traced to #3. |
| 2 | Elo check | train | 5 547 | - | - | win change + loss change ~ 23-24 per player and per game (K ~ 24): E = 1 - change/24 (win) or -change/24 (loss) is the pre-game expected score. Coefficient of logit(E) ~ 2.0. |
| 3 | first harness, all decisive rows in fits | test | 2 168 | faction 0.5380, comp 0.5741, cardEB 0.5602 | 0.69193 / 0.68678 / 0.68940 | found 61 rows without rating change: 58 wins, 3 draws, 0 losses, often 1-5 cards (games outside the ladder). They teach "tiny builds win". |
| 4 | exclude unrated rows from every FIT (kept in evaluation) | test | 2 168 | faction 0.5373, comp 0.5712 | 0.69207 / 0.68682 | adopted for all later runs |
| 5 | hybrid (comp + per-card ridge bonus), uncentred, grid lam_card 30..3000 | val / test | 1 114 / 2 168 | 0.6225 / 0.5853 | 0.67208 / 0.68368 | lam_card 300 best on val |
| 6 | reduced composition sets (commander only, +stars, 7-feature "small", arms, classes) | val / test | | small 0.6155 / 0.5829; commander only 0.6035 / 0.5844 | small 0.67685 / 0.68211 | the commander indicator alone carries most of the signal; "small" set fixed here (selected on full training z-scores, so its validation score is slightly optimistic) |
| 7 | small + paper surplus; small + surplus + models | val / test | | 0.6155 / 0.5830 | 0.67702 / 0.68214 | surplus coefficient 0.004 (-0.012 with Elo): paper value adds nothing |
| 8 | uncentred hybrids had faction coefficient -0.6 to -2.1 | - | - | - | - | leave-one-match-out F competes with in-sample card bonuses that absorb the army mean. Fix: card counts centred within army. hybsmall centred: val 0.6214 / 0.67473, test 0.5921 / 0.68028. Adopted. |
| 9 | FINAL evaluation (`evaluate.py`), all models +/- Elo control | val / test | 1 114 / 2 168 | see `out/eval_test.csv` and REPORT.md table | | best val: hybrid (no control). Best test: hybsmall 0.5921 / 0.68028. Best skill-controlled on test log-loss: small+elo 0.5782 / 0.68368 |
| 10 | test match-bootstrap vs faction-only (`test_ci.py`) | test | 2 168 | small+elo dAUC 95% [-0.002, +0.084] | dLL [-0.0132, -0.0038] | hybsmall dAUC [+0.014, +0.097]; paper and cardEB+elo indistinguishable from faction-only |
| 11 | skill controls (`skill.py`): none / Elo / player ridge (lam 5) / both | train | 5 511 | - | - | commander 0.37 -> 0.28 -> 0.31 -> 0.27; light infantry 0.036 -> 0.018 -> 0.022 -> 0.015; stars rises 0.037 -> 0.053; surplus 0.021 -> 0.003 |
| 12 | skill groups (weaker half / stronger half / unknown) | train | 2 365 / 2 364 / 782 | - | - | commander 0.19 / 0.39 / 0.14; stars 0.055 / 0.017 / 0.051; artillery gold -0.31 / -0.16 / -0.28; lancers 0.073 / 0.037 / 0.108 |
| 13 | builds v1: hybsmall+elo, no guardrails | train | - | - | - | 31-card builds of one card type, 0-1 cavalry, gain +1.4 logit: linear extrapolation + summed card noise |
| 14 | split-half optimism (`optimism.py`), hybsmall+elo | train halves | - | - | - | gain of optimised build: card bonuses 0.24 in-sample -> 0.02 on the other half (do not replicate); composition part 0.67 -> 0.44 |
| 15 | builds v2: small+elo, composition guardrails, paper-value tie-break (delta 0.02) | train | - | - | - | picked one-model "commanders" (value 1, 19-69 gold) and negative-value batteries as slot fillers |
| 16 | builds v3: + token-card filter (value < 0.5 x cost, 110 cards) + per-army guardrails | train | - | - | - | b11_x8_014 gain -0.21 (pooled lancer cap 5 below what that army fields) |
| 17 | builds v4 (final): small armies get pooled ranges widened to their own observed builds | train | - | - | - | all 110 MILPs optimal (status 0); all gains >= 0; median gain 0.48 logit in-sample |
| 18 | split-half optimism, final optimiser, 4 candidate models | train halves | - | in-sample / other half (self) / other half (hybrid+elo) | | small+elo 0.585 / 0.394 / 0.341; hybsmall+elo 0.841 / 0.413 / 0.431; comp+elo 1.180 / 0.581 / 0.575; hybrid+elo 1.272 / 0.523 / 0.523 |
| 19 | rule checker (`check_builds.py`) on out/builds.csv and out/builds_noguard.csv; mutation test (extra staff, extra commander, over cap, 5 corps in 4corps, 3rd foot battery, missing army) | - | 110 | - | - | PASS on both files; every mutation caught |
