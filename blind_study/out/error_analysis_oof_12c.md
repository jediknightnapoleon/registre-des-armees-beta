# Error analysis: oof_12c

rows 10014, MAE 28.62, MAPE 8.26%, median AE 18.2

## By row kind

| kind          |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|-----:|------:|------------:|-------:|-------:|--------:|
| regular       | 5594 |  28.2 |        17.1 |    6.4 |    1.9 |    55   |
| commander     | 4191 |  30.6 |        21   |   11.1 |    1.5 |    44.8 |
| staff general |  229 |   3.3 |         0.3 |    0.4 |   -2.7 |     0.3 |

## By unit type x kind

|                            |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------------------|-----:|------:|------------:|-------:|-------:|--------:|
| ('inf_line', 'commander')  | 1725 |  23.8 |        16.9 |   10.4 |    0.5 |    14.3 |
| ('inf_line', 'regular')    | 1834 |  18.7 |        12.1 |    5.7 |    2   |    12   |
| ('art_foot', 'regular')    |  507 |  38.2 |        25.8 |    8.1 |    3.6 |     6.8 |
| ('cav_light', 'regular')   |  560 |  32.3 |        21.3 |    4.9 |    0.2 |     6.3 |
| ('cav_light', 'commander') |  485 |  35.3 |        27.7 |    7.2 |   11.9 |     6   |
| ('inf_light', 'commander') |  526 |  31   |        21.5 |    8.1 |   -9.6 |     5.7 |
| ('inf_grena', 'regular')   |  468 |  34.1 |        23.6 |    7.1 |    3.8 |     5.6 |
| ('inf_light', 'regular')   |  605 |  22.1 |        14.4 |    5   |    1.6 |     4.7 |
| ('inf_grena', 'commander') |  322 |  36.9 |        25.7 |    7.2 |    9   |     4.1 |
| ('cav_heavy', 'regular')   |  249 |  44.8 |        30.1 |    3.9 |    5.7 |     3.9 |
| ('inf_skirm', 'regular')   |  294 |  35.5 |        18.2 |   10.8 |    3.7 |     3.6 |
| ('cav_stand', 'regular')   |  312 |  33.3 |        23.6 |    4.6 |   -0.2 |     3.6 |
| ('cav_lance', 'regular')   |  261 |  35.1 |        24.9 |    5.7 |   -1.1 |     3.2 |
| ('cav_heavy', 'commander') |  222 |  41.2 |        25.8 |    4.4 |   17   |     3.2 |
| ('inf_milit', 'regular')   |  293 |  28.6 |        17.5 |   12.9 |    2.4 |     2.9 |
| ('cav_stand', 'commander') |  266 |  29.7 |        23.1 |    5.5 |   -1.2 |     2.8 |
| ('art_foot', 'commander')  |  191 |  37.9 |        25.4 |    8.6 |   -3.3 |     2.5 |
| ('art_horse', 'regular')   |  211 |  32.9 |        16.4 |    7.3 |   -3.1 |     2.4 |
| ('cav_lance', 'commander') |  180 |  34.6 |        25.5 |    7.1 |   10.3 |     2.2 |
| ('inf_milit', 'commander') |  159 |  36.3 |        24.2 |   18.6 |  -17.2 |     2   |
| ('inf_skirm', 'commander') |   60 |  60.3 |        38.6 |   86.8 |  -10.2 |     1.3 |
| ('art_horse', 'commander') |   55 |  35.4 |        25.5 |   92.4 |    5.9 |     0.7 |
| ('staff', 'staff general') |  229 |   3.3 |         0.3 |    0.4 |   -2.7 |     0.3 |

## By price band

| band          |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|-----:|------:|------------:|-------:|-------:|--------:|
| (400, 700]    | 3038 |  27.4 |        18.6 |    5.2 |   -1.8 |    29.1 |
| (200, 400]    | 3056 |  20.4 |        13.9 |    7   |    5.9 |    21.8 |
| (700, 1000]   | 1486 |  36.7 |        25.4 |    4.4 |   -3.7 |    19.1 |
| (1000, 1500]  |  792 |  48.6 |        31.4 |    4.1 |   -5   |    13.4 |
| (50, 200]     | 1253 |  21.4 |        15.7 |   16.8 |   14.1 |     9.4 |
| (1500, 10000] |  296 |  65.6 |        38.7 |    3.7 |  -18.8 |     6.8 |
| (0, 50]       |   93 |  15.7 |         5.8 |  145.6 |   11.3 |     0.5 |

## By faction kind

| faction_kind   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------|-----:|------:|------------:|-------:|-------:|--------:|
| theatre_of_war | 9628 |  28.4 |        18.2 |    8.3 |    1.7 |    95.5 |
| custom         |  386 |  33.4 |        19.7 |    8.1 |   -0.4 |     4.5 |

## By army (top 15 by share)

| army_corps_name                   |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------------------|----:|------:|------------:|-------:|-------:|--------:|
| [1811] 7. España                  | 336 |  45.7 |        31.1 |    9.4 |   -4   |     5.4 |
| [1812] 11. France (Russie-Centre) | 450 |  26.3 |        16.5 |    7.7 |    7.4 |     4.1 |
| [1811] 8. France (Espagne)        | 459 |  25.3 |        16.1 |    6.8 |   -0.6 |     4   |
| [1812] 10. Rossiya                | 526 |  19.1 |        14.6 |    4.7 |    6.1 |     3.5 |
| [1809] 10. France (Espagne)       | 377 |  22.3 |        16.2 |    8.5 |    8.9 |     2.9 |
| [1809] 10. France (Autriche)      | 325 |  25.7 |        16.7 |    9.9 |    8.4 |     2.9 |
| [1814] 9. Rossiya (Frantsiya)     | 352 |  22.5 |        15.3 |    4.3 |    5.4 |     2.8 |
| [1806] 12. France (Prusse)        | 314 |  25.1 |        19   |    8.7 |    9.9 |     2.7 |
| [1814] 8. France                  | 288 |  26.3 |        17.9 |    8.4 |    2.1 |     2.6 |
| [1806] 10. Preußen                | 284 |  26.4 |        19.1 |   21.7 |    6.6 |     2.6 |
| [1812] 6. France (Russie-Nord)    | 208 |  34.6 |        23.4 |    6.7 |   -5.7 |     2.5 |
| [1799] 7. Österreich (Schwaben)   | 250 |  28   |        18.8 |    7.2 |    1   |     2.4 |
| [1805] 6. France (Tyrol)          | 190 |  36.3 |        26.9 |    5.9 |   -9.9 |     2.4 |
| [1815] 9. France (Flandres)       | 260 |  26.5 |        14.9 |    6.7 |    3.3 |     2.4 |
| [1815] 9. UK, Nederlanden         | 250 |  26.6 |        13.7 |    7.9 |   -0.6 |     2.3 |

## By corps number N

|   corps_n |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|----------:|-----:|------:|------------:|-------:|-------:|--------:|
|         8 | 2169 |  29.4 |        17.8 |    9.3 |    0.5 |    22.2 |
|         9 | 2395 |  25.9 |        15.5 |    6.8 |    2.5 |    21.7 |
|         7 | 1713 |  34.1 |        21.8 |    8   |   -0.2 |    20.4 |
|        10 | 2013 |  23   |        16.1 |    9.4 |    5.9 |    16.1 |
|         6 |  723 |  38.5 |        27.2 |    7   |  -10.9 |     9.7 |
|        11 |  610 |  26.9 |        16.9 |    7.2 |    6.1 |     5.7 |
|        12 |  314 |  25.1 |        19   |    8.7 |    9.9 |     2.7 |
|         5 |   77 |  51.1 |        40   |   15   |  -18.4 |     1.4 |

## By command stars (commanders)

|   stars |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|--------:|-----:|------:|------------:|-------:|-------:|--------:|
|       0 | 7103 |  27.6 |        17.6 |    8.6 |    2.1 |    68.3 |
|       1 | 1241 |  28.5 |        19.3 |    9.1 |    2.1 |    12.4 |
|       2 |  926 |  31.1 |        20.1 |    7.1 |    0.9 |    10   |
|       3 |  498 |  32.3 |        19.5 |    5.1 |   -0.8 |     5.6 |
|       4 |  140 |  43.7 |        28.8 |    5.3 |   -7.2 |     2.1 |
|       5 |   55 |  49.8 |        23.5 |    4.6 |    3.3 |     1   |
|       6 |   27 |  28.7 |         0.9 |    2   |  -15.6 |     0.3 |
|       8 |    6 |  99.7 |         3.5 |    5.8 |  -98.4 |     0.2 |
|       7 |   11 |  26.2 |         1.6 |    2   |  -10.8 |     0.1 |
|       9 |    7 |   1.5 |         0.6 |    0.1 |    1.3 |     0   |

## By training level

| unit_training_level   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------|-----:|------:|------------:|-------:|-------:|--------:|
| well_trained          | 4328 |  25.9 |        17.6 |    6   |    1.8 |    39.1 |
| trained               | 3369 |  26.5 |        17.5 |    7.7 |    1.9 |    31.1 |
| poorly_trained        | 1196 |  34.6 |        22.6 |   19   |    0   |    14.4 |
| elite                 |  708 |  37   |        14.7 |    4.8 |   -2.1 |     9.1 |
| mob                   |  413 |  43.4 |        24.3 |   11.4 |    8.6 |     6.3 |

## 25 largest absolute errors

| unit_name                                                                                         | army_corps_name                   | kind          | seg       |   base_mp_cost |   pred |   err |
|:--------------------------------------------------------------------------------------------------|:----------------------------------|:--------------|:----------|---------------:|-------:|------:|
| Havan topu [F0]                                                                                   | [1806] 9. Osmanlı                 | regular       | art_foot  |           1392 |   2484 |  1092 |
| Letuchiy korpus [GS3]                                                                             | [1812] 8. Russkiy narod           | regular       | inf_skirm |           1515 |   2342 |   827 |
| Franz von Harling (Württembergische Garde du Corps) [C1]                                          | [1799] 7. Österreich (Schwaben)   | commander     | cav_heavy |            661 |   1269 |   608 |
| Arthur Wellesley 'Wellington'                                                                     | [1809] 10. UK, España, Portugal   | staff general | staff     |           1746 |   1160 |  -586 |
| Württembergische Garde du Corps [C1]                                                              | [1799] 7. Österreich (Schwaben)   | regular       | cav_heavy |            861 |   1377 |   516 |
| 5e d'artillerie à cheval de 4 livres [H3]                                                         | [1812] 11. France (Russie-Centre) | regular       | art_horse |           1918 |   1404 |  -514 |
| Régiment de dromadaires [DR]                                                                      | [1798] 8. France (Égypte)         | regular       | cav_stand |            534 |   1034 |   500 |
| ¤ Peregrine Maitland (1st Foot Guards 'the Tow-Rows') [L2]                                        | [1809] 6. UK (Walcheren)          | commander     | inf_line  |           2164 |   1749 |  -415 |
| Shaawanwaki 'Shawnee' [GS2]                                                                       | [1812] 7. UK (USA)                | regular       | inf_skirm |           1011 |   1414 |   403 |
| ¤ Moore Disney (1st Foot Guards 'the Tow-Rows') [L2]                                              | [1809] 6. UK (Walcheren)          | commander     | inf_line  |           1894 |   1512 |  -382 |
| Ouralskie tatari [C4]                                                                             | [1812] 8. Russkiy narod           | regular       | cav_light |           1111 |   1489 |   378 |
| Andreas Höfer 'der Sandwirth' (Rinn Landstürm) [L5]                                               | [1809] 8. Österreich (Tyrol)      | commander     | inf_milit |           1552 |   1920 |   368 |
| Jean Barthélemot de Sorbier (1ère d'artillerie à pied de la Vieille Garde, 12 livres) [F3]        | [1812] 11. France (Russie-Centre) | commander     | art_foot  |           2221 |   1857 |  -364 |
| Dragoni di Sua Maestà Reale [C3]                                                                  | 8. Piemonte-Sardegna (1796)       | regular       | cav_stand |           1684 |   2028 |   344 |
| ¤ Nicolas Oudinot 'le Bayard moderne' (1er grenadiers de réserve 'les Grenadiers d'Oudinot') [G5] | [1805] 11. France (Allemagne)     | commander     | inf_grena |           1696 |   1361 |  -335 |
| ¤ Charles Morand (1er chasseurs à pied) [L4]                                                      | [1815] 9. France (Flandres)       | commander     | inf_light |           1561 |   1237 |  -324 |
| ¤ Fotjägare 'Savolax' [L5]                                                                        | [1808] 7. Sverige (Finska)        | regular       | inf_light |           1248 |   1560 |   312 |
| Carabineros Reales [C2]                                                                           | [1809] 10. UK, España, Portugal   | regular       | cav_heavy |           1363 |   1056 |  -307 |
| 1. Tiradores de Cantabria [S2]                                                                    | [1811] 7. España                  | regular       | inf_skirm |            749 |   1051 |   302 |
| 6-pund ridende artilleri [H2]                                                                     | 7. Danmark                        | regular       | art_horse |            311 |    612 |   301 |
| Jean-Baptiste Duchand de Sancey (Artillerie à cheval de la Vieille Garde, 6 livres) [H2]          | [1815] 9. France (Flandres)       | commander     | art_horse |           2542 |   2245 |  -297 |
| Ermeni okçuları [L5]                                                                              | [1806] 9. Osmanlı                 | regular       | inf_milit |            585 |    295 |  -290 |
| John Ormsby Vandeleur (5th (Princess Charlotte of Wales') Dragoon Guards 'the Green Horse') [C2]  | [1798] 5. UK (Ireland)            | commander     | cav_heavy |           2706 |   2994 |   288 |
| Artillerie à cheval de la Vieille Garde, 6 livres [H2]                                            | [1814] 8. France                  | regular       | art_horse |           2627 |   2348 |  -279 |
| Teyoninhokarawen 'John Norton, the Snipe' (Lenape 'Delaware') [GS2]                               | [1812] 7. UK (USA)                | commander     | inf_skirm |            370 |    648 |   278 |

Share of squared error explained by army x type mean residual: 0.111
