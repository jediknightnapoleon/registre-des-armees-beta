# Error analysis: oof_13c

rows 10014, MAE 27.43, MAPE 7.04%, median AE 16.3

## By row kind

| kind          |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|-----:|------:|------------:|-------:|-------:|--------:|
| regular       | 5594 |  27.5 |        16.5 |    6.2 |    1.3 |    56   |
| commander     | 4191 |  28.7 |        17.3 |    8.5 |   -0.6 |    43.7 |
| staff general |  229 |   3.5 |         0.3 |    0.4 |   -3   |     0.3 |

## By unit type x kind

|                            |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------------------|-----:|------:|------------:|-------:|-------:|--------:|
| ('inf_line', 'commander')  | 1725 |  20.6 |        12.9 |    7.9 |   -0.8 |    12.9 |
| ('inf_line', 'regular')    | 1834 |  17.5 |        11.1 |    5.1 |    1.2 |    11.7 |
| ('art_foot', 'regular')    |  507 |  39.7 |        27.3 |    8.4 |    3.7 |     7.3 |
| ('cav_light', 'regular')   |  560 |  32.1 |        21.1 |    4.9 |    0   |     6.5 |
| ('cav_light', 'commander') |  485 |  33.8 |        25.8 |    6.5 |   11.6 |     6   |
| ('inf_light', 'commander') |  526 |  29.4 |        17.5 |    6.7 |  -13.5 |     5.6 |
| ('inf_grena', 'regular')   |  468 |  30.3 |        22   |    6.1 |    0.7 |     5.2 |
| ('inf_light', 'regular')   |  605 |  21.3 |        13.4 |    4.7 |    1.3 |     4.7 |
| ('cav_heavy', 'regular')   |  249 |  46.9 |        30.9 |    4.1 |    7   |     4.3 |
| ('inf_grena', 'commander') |  322 |  34.6 |        22.1 |    6.1 |    4.5 |     4.1 |
| ('cav_stand', 'regular')   |  312 |  33   |        23.7 |    4.6 |   -1.8 |     3.8 |
| ('inf_skirm', 'regular')   |  294 |  33.9 |        22   |   11.3 |    0.9 |     3.6 |
| ('cav_heavy', 'commander') |  222 |  42.1 |        25.5 |    4.4 |   15.2 |     3.4 |
| ('cav_lance', 'regular')   |  261 |  35.1 |        25.8 |    5.7 |   -0   |     3.3 |
| ('cav_stand', 'commander') |  266 |  32.8 |        21.9 |    5.7 |   -7.7 |     3.2 |
| ('inf_milit', 'regular')   |  293 |  27.7 |        16.1 |   12.3 |    2.9 |     3   |
| ('art_foot', 'commander')  |  191 |  37.9 |        22.6 |    8.1 |  -10.5 |     2.6 |
| ('art_horse', 'regular')   |  211 |  34.1 |        15   |    7.7 |   -2   |     2.6 |
| ('cav_lance', 'commander') |  180 |  34.2 |        23.6 |    6.5 |   11.2 |     2.2 |
| ('inf_milit', 'commander') |  159 |  31.4 |        18.7 |   16.3 |  -10.5 |     1.8 |
| ('inf_skirm', 'commander') |   60 |  57.4 |        37.7 |   43.5 |  -16.5 |     1.3 |
| ('art_horse', 'commander') |   55 |  32.4 |        21   |   57   |    4.9 |     0.6 |
| ('staff', 'staff general') |  229 |   3.5 |         0.3 |    0.4 |   -3   |     0.3 |

## By price band

| band          |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|-----:|------:|------------:|-------:|-------:|--------:|
| (400, 700]    | 3038 |  26.4 |        17.5 |    5   |   -3.6 |    29.1 |
| (700, 1000]   | 1486 |  38.4 |        26   |    4.6 |   -3.2 |    20.8 |
| (200, 400]    | 3056 |  18.3 |        11.8 |    6.2 |    3.7 |    20.3 |
| (1000, 1500]  |  792 |  49.8 |        30.6 |    4.2 |   -2.1 |    14.4 |
| (50, 200]     | 1253 |  17.3 |        11.4 |   13.4 |   11.3 |     7.9 |
| (1500, 10000] |  296 |  64.9 |        39.6 |    3.6 |  -17.3 |     7   |
| (0, 50]       |   93 |  14.1 |         2.7 |   89.1 |    9.7 |     0.5 |

## By faction kind

| faction_kind   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------|-----:|------:|------------:|-------:|-------:|--------:|
| theatre_of_war | 9628 |  27.3 |        16.2 |    7   |    0.5 |    95.5 |
| custom         |  386 |  31.9 |        17   |    7.8 |   -0.9 |     4.5 |

## By army (top 15 by share)

| army_corps_name                   |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------------------|----:|------:|------------:|-------:|-------:|--------:|
| [1811] 7. España                  | 336 |  43.6 |        28.9 |    8.6 |   -1.4 |     5.3 |
| [1811] 8. France (Espagne)        | 459 |  25.1 |        15.4 |    6.3 |   -0.5 |     4.2 |
| [1812] 11. France (Russie-Centre) | 450 |  23   |        11.5 |    5.5 |   -0.7 |     3.8 |
| [1812] 10. Rossiya                | 526 |  17.5 |        11.1 |    4.1 |   -0.5 |     3.3 |
| [1814] 9. Rossiya (Frantsiya)     | 352 |  22.3 |        16.5 |    4.2 |    1   |     2.9 |
| [1809] 10. France (Autriche)      | 325 |  23.7 |        13.1 |    7.3 |    2.6 |     2.8 |
| [1814] 8. France                  | 288 |  25.3 |        17.2 |    7.9 |    0.8 |     2.6 |
| [1806] 12. France (Prusse)        | 314 |  22.6 |        15.4 |    6.5 |    3.3 |     2.6 |
| [1815] 9. France (Flandres)       | 260 |  27.1 |        15.4 |    6.6 |    2.6 |     2.6 |
| [1809] 10. France (Espagne)       | 377 |  18.3 |        11.2 |    5.8 |   -0.2 |     2.5 |
| [1809] 10. UK, España, Portugal   | 247 |  27.3 |        17.4 |    8.6 |   -3   |     2.5 |
| [1806] 10. Preußen                | 284 |  23.5 |        13.4 |   12.7 |    0.5 |     2.4 |
| [1815] 9. UK, Nederlanden         | 250 |  26.4 |        15.3 |    8   |   -2.2 |     2.4 |
| [1812] 6. France (Russie-Nord)    | 208 |  31.3 |        18.2 |    6.2 |    2.3 |     2.4 |
| [1799] 7. Österreich (Schwaben)   | 250 |  25   |        14.8 |    6.1 |    2.6 |     2.3 |

## By corps number N

|   corps_n |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|----------:|-----:|------:|------------:|-------:|-------:|--------:|
|         8 | 2169 |  29.5 |        17.5 |    8   |    0   |    23.3 |
|         9 | 2395 |  25.3 |        15.3 |    6.4 |    0.4 |    22   |
|         7 | 1713 |  32.9 |        20   |    7.6 |    1.6 |    20.5 |
|        10 | 2013 |  21.4 |        13   |    7   |   -0.3 |    15.7 |
|         6 |  723 |  35.5 |        23   |    6.6 |   -0.6 |     9.3 |
|        11 |  610 |  24.3 |        13   |    5.5 |   -0.5 |     5.4 |
|        12 |  314 |  22.6 |        15.4 |    6.5 |    3.3 |     2.6 |
|         5 |   77 |  42.5 |        22.3 |    9.5 |    4.3 |     1.2 |

## By command stars (commanders)

|   stars |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|--------:|-----:|------:|------------:|-------:|-------:|--------:|
|       0 | 7103 |  26.2 |        15.9 |    7.2 |    1.2 |    67.7 |
|       1 | 1241 |  26.1 |        15.3 |    7.6 |   -0.1 |    11.8 |
|       2 |  926 |  30.4 |        18.3 |    6.7 |   -1.1 |    10.3 |
|       3 |  498 |  34.5 |        23.7 |    5.1 |   -1.4 |     6.3 |
|       4 |  140 |  46.8 |        28.7 |    5.5 |   -8.7 |     2.4 |
|       5 |   55 |  49.3 |        26.7 |    4.5 |   -4.2 |     1   |
|       6 |   27 |  30.8 |         0.8 |    2.1 |  -13.4 |     0.3 |
|       8 |    6 | 108.1 |         1.8 |    6.2 | -106.5 |     0.2 |
|       7 |   11 |  31.4 |         1.5 |    2.4 |  -30.2 |     0.1 |
|       9 |    7 |   1.6 |         1.1 |    0.1 |    0.7 |     0   |

## By training level

| unit_training_level   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------|-----:|------:|------------:|-------:|-------:|--------:|
| well_trained          | 4328 |  25.3 |        16.2 |    5.5 |    0.7 |    39.9 |
| trained               | 3369 |  24.3 |        14.8 |    6.5 |    0.4 |    29.9 |
| poorly_trained        | 1196 |  34   |        20.9 |   14.4 |   -0.4 |    14.8 |
| elite                 |  708 |  36.6 |        16.5 |    4.7 |   -4.7 |     9.4 |
| mob                   |  413 |  40.2 |        22.3 |   10.6 |    8.3 |     6   |

## 25 largest absolute errors

| unit_name                                                                                         | army_corps_name                   | kind          | seg       |   base_mp_cost |   pred |   err |
|:--------------------------------------------------------------------------------------------------|:----------------------------------|:--------------|:----------|---------------:|-------:|------:|
| Havan topu [F0]                                                                                   | [1806] 9. Osmanlı                 | regular       | art_foot  |           1392 |   2266 |   874 |
| Franz von Harling (Württembergische Garde du Corps) [C1]                                          | [1799] 7. Österreich (Schwaben)   | commander     | cav_heavy |            661 |   1321 |   660 |
| Arthur Wellesley 'Wellington'                                                                     | [1809] 10. UK, España, Portugal   | staff general | staff     |           1746 |   1107 |  -639 |
| Württembergische Garde du Corps [C1]                                                              | [1799] 7. Österreich (Schwaben)   | regular       | cav_heavy |            861 |   1401 |   540 |
| 5e d'artillerie à cheval de 4 livres [H3]                                                         | [1812] 11. France (Russie-Centre) | regular       | art_horse |           1918 |   1385 |  -533 |
| Régiment de dromadaires [DR]                                                                      | [1798] 8. France (Égypte)         | regular       | cav_stand |            534 |   1048 |   514 |
| ¤ Charles Morand (1er chasseurs à pied) [L4]                                                      | [1815] 9. France (Flandres)       | commander     | inf_light |           1561 |   1144 |  -417 |
| ¤ Robert Craufurd 'Black Bob' (52nd (Oxfordshire) Light Foot 'the Light Bobs') [L6]               | [1809] 10. UK, España, Portugal   | commander     | inf_light |           1336 |    930 |  -406 |
| Jean Barthélemot de Sorbier (1ère d'artillerie à pied de la Vieille Garde, 12 livres) [F3]        | [1812] 11. France (Russie-Centre) | commander     | art_foot  |           2221 |   1837 |  -384 |
| ¤ Fotjägare 'Savolax' [L5]                                                                        | [1808] 7. Sverige (Finska)        | regular       | inf_light |           1248 |   1609 |   361 |
| ¤ Louis-Victorin Cassagne (25e de ligne 'les Poitevins') [L5]                                     | [1798] 8. France (Égypte)         | commander     | inf_line  |            966 |   1315 |   349 |
| Madāfi‘u Al Hisar [F1]                                                                            | [1798] 8. Mamālīk                 | regular       | art_foot  |           1306 |    959 |  -347 |
| ¤ Nicolas Oudinot 'le Bayard moderne' (1er grenadiers de réserve 'les Grenadiers d'Oudinot') [G5] | [1805] 11. France (Allemagne)     | commander     | inf_grena |           1696 |   1358 |  -338 |
| ¤ Peregrine Maitland (1st Foot Guards 'the Tow-Rows') [L2]                                        | [1809] 6. UK (Walcheren)          | commander     | inf_line  |           2164 |   1833 |  -331 |
| Shaawanwaki 'Shawnee' [GS2]                                                                       | [1812] 7. UK (USA)                | regular       | inf_skirm |           1011 |   1340 |   329 |
| Letuchiy korpus [GS3]                                                                             | [1812] 8. Russkiy narod           | regular       | inf_skirm |           1515 |   1843 |   328 |
| Carabineros Reales [C2]                                                                           | [1809] 10. UK, España, Portugal   | regular       | cav_heavy |           1363 |   1053 |  -310 |
| 6-pund ridende artilleri [H2]                                                                     | 7. Danmark                        | regular       | art_horse |            311 |    618 |   307 |
| Meath militia 'mílíste An Mhí' [G3]                                                               | [1798] 5. France (Irlande)        | regular       | inf_milit |            737 |   1039 |   302 |
| Yegor Vlastov (Leyb-gvardyi Konnyi) [C2]                                                          | [1808] 7. Rossiya (Finlyandiya)   | commander     | cav_heavy |           1482 |   1782 |   300 |
| 5 okka muhasara topçusu [F2]                                                                      | [1800] 8. Osmanlı, UK             | regular       | art_foot  |           1524 |   1821 |   297 |
| John Ormsby Vandeleur (5th (Princess Charlotte of Wales') Dragoon Guards 'the Green Horse') [C2]  | [1798] 5. UK (Ireland)            | commander     | cav_heavy |           2706 |   2990 |   284 |
| ¤ 25e de ligne 'les Poitevins' [L5]                                                               | [1798] 8. France (Égypte)         | regular       | inf_line  |            843 |   1127 |   284 |
| Antoine-François Andréossy (Obusiers) [F3]                                                        | [1798] 8. France (Égypte)         | commander     | art_foot  |           1729 |   1447 |  -282 |
| Cacciatori della milizia [S1]                                                                     | 8. Piemonte-Sardegna (1796)       | regular       | inf_skirm |            709 |    432 |  -277 |

Share of squared error explained by army x type mean residual: 0.120
