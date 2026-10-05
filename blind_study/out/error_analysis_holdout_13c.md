# Error analysis: holdout_13c

rows 2504, MAE 27.82, MAPE 8.88%, median AE 16.3

## By row kind

| kind          |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|-----:|------:|------------:|-------:|-------:|--------:|
| regular       | 1398 |  28.2 |        16.6 |    6.7 |    4.5 |    56.5 |
| commander     | 1047 |  28.9 |        17.6 |   12.3 |    2.8 |    43.4 |
| staff general |   59 |   0.9 |         0.4 |    0.9 |   -0.6 |     0.1 |

## By unit type x kind

|                            |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------------------|----:|------:|------------:|-------:|-------:|--------:|
| ('inf_line', 'commander')  | 432 |  21.2 |        13.7 |    9.1 |   -1.8 |    13.1 |
| ('inf_line', 'regular')    | 461 |  16.6 |        10.5 |    5   |    1.5 |    11   |
| ('cav_light', 'regular')   | 142 |  36.5 |        23.6 |    6.8 |    8   |     7.4 |
| ('art_foot', 'regular')    | 128 |  38.4 |        23.8 |    9.7 |   11.9 |     7.1 |
| ('inf_light', 'commander') | 153 |  29.7 |        15.5 |    6.8 |  -10   |     6.5 |
| ('cav_stand', 'regular')   |  75 |  50.1 |        32.2 |    6.5 |   -4.7 |     5.4 |
| ('cav_light', 'commander') | 119 |  29.9 |        22.5 |    5.6 |   10.3 |     5.1 |
| ('inf_grena', 'regular')   | 117 |  29.6 |        19.7 |    4.8 |    0.7 |     5   |
| ('inf_light', 'regular')   | 150 |  22.1 |        17   |    5.1 |   -0.2 |     4.8 |
| ('cav_heavy', 'regular')   |  60 |  47.7 |        28.8 |    3.8 |   14.7 |     4.1 |
| ('cav_lance', 'regular')   |  65 |  39.7 |        24.4 |    8   |   14.6 |     3.7 |
| ('cav_stand', 'commander') |  75 |  33.2 |        21.8 |    6   |    1.2 |     3.6 |
| ('inf_grena', 'commander') |  70 |  31.8 |        23.7 |    6.1 |   11.9 |     3.2 |
| ('inf_skirm', 'regular')   |  74 |  28.1 |        19.4 |   10.4 |    0.1 |     3   |
| ('cav_heavy', 'commander') |  58 |  35.5 |        25.4 |    3.7 |   20.7 |     3   |
| ('inf_skirm', 'commander') |  16 | 123.8 |        29.5 |   14.5 |   94.5 |     2.8 |
| ('inf_milit', 'regular')   |  74 |  25   |        14.6 |   12   |    9.5 |     2.7 |
| ('inf_milit', 'commander') |  42 |  43.8 |        26.6 |   18.1 |    8.6 |     2.6 |
| ('art_horse', 'regular')   |  52 |  32.9 |        15.9 |   11   |   13.4 |     2.5 |
| ('art_foot', 'commander')  |  36 |  31.3 |        25.5 |    5.4 |  -14   |     1.6 |
| ('cav_lance', 'commander') |  25 |  28.3 |        23.4 |   16   |   19.7 |     1   |
| ('art_horse', 'commander') |  21 |  25.4 |        12.3 |  215.5 |    2.5 |     0.8 |
| ('staff', 'staff general') |  59 |   0.9 |         0.4 |    0.9 |   -0.6 |     0.1 |

## By price band

| band          |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|:--------------|----:|------:|------------:|-------:|-------:|--------:|
| (400, 700]    | 732 |  25.5 |        17.7 |    4.8 |   -1.6 |    26.8 |
| (700, 1000]   | 365 |  40.2 |        27.4 |    4.9 |    0.8 |    21.1 |
| (200, 400]    | 763 |  18.4 |        11.4 |    6.3 |    3.5 |    20.2 |
| (1000, 1500]  | 216 |  45.1 |        28.1 |    3.8 |    6.3 |    14   |
| (1500, 10000] |  64 |  96.2 |        49.5 |    5.3 |   26.5 |     8.8 |
| (50, 200]     | 346 |  17.2 |        11.8 |   13.9 |   11.6 |     8.5 |
| (0, 50]       |  18 |  21.6 |        13.3 |  340   |   19   |     0.6 |

## By faction kind

| faction_kind   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:---------------|-----:|------:|------------:|-------:|-------:|--------:|
| theatre_of_war | 2404 |  27.5 |        16.1 |    8.8 |    3.5 |    94.9 |
| custom         |  100 |  35.4 |        21   |   11   |    6.4 |     5.1 |

## By army (top 15 by share)

| army_corps_name                   |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------------------|----:|------:|------------:|-------:|-------:|--------:|
| [1811] 7. España                  |  92 |  41.4 |        21.7 |    8.4 |    4.7 |     5.5 |
| [1812] 10. Rossiya                | 120 |  21.6 |        12.7 |    4.9 |   -0.2 |     3.7 |
| [1811] 8. France (Espagne)        | 111 |  22.3 |        13.7 |    5.8 |   -1.7 |     3.6 |
| [1814] 8. France                  |  75 |  32.1 |        13.6 |    6.9 |    0.9 |     3.5 |
| [1815] 9. France (Flandres)       |  83 |  28.6 |        18.6 |    7.2 |    7   |     3.4 |
| [1812] 7. UK (USA)                |  23 |  99.7 |        21   |   12   |   72.5 |     3.3 |
| [1815] 9. UK, Nederlanden         |  66 |  33.7 |        18.4 |    9   |    9.9 |     3.2 |
| [1814] 9. Rossiya (Frantsiya)     |  88 |  23.2 |        14.6 |    4.1 |   -8.1 |     2.9 |
| [1805] 8. Österreich              |  83 |  23.7 |        17.1 |    6.6 |    1.9 |     2.8 |
| [1814] 8. Preußen (Frankreich)    |  70 |  27.1 |        17.2 |    6.4 |    8.4 |     2.7 |
| [1812] 11. France (Russie-Centre) |  91 |  20.3 |        10.7 |    8.2 |    0.8 |     2.7 |
| [1806] 12. France (Prusse)        |  69 |  24.6 |        17.2 |    6.1 |   -1.9 |     2.4 |
| [1809] 10. France (Espagne)       |  97 |  17.5 |        11.6 |    7.1 |   -0.4 |     2.4 |
| [1809] 7. Polska, sojusznicy      |  45 |  37.3 |        21.2 |   10   |   15   |     2.4 |
| [1811] 9. UK, Portugal            |  54 |  29.3 |        14.2 |    6.6 |    2.2 |     2.3 |

## By corps number N

|   corps_n |   n |   MAE |   median_AE |   MAPE |   bias |   share |
|----------:|----:|------:|------------:|-------:|-------:|--------:|
|         7 | 446 |  38.3 |        19.7 |    8.8 |   12   |    24.5 |
|         8 | 567 |  28.7 |        17.1 |    6.7 |    2.9 |    23.4 |
|         9 | 630 |  25   |        16.1 |   14.3 |    1   |    22.6 |
|        10 | 475 |  19.9 |        12.5 |    6.2 |    1   |    13.5 |
|         6 | 169 |  31.4 |        22.1 |    5.4 |    3.7 |     7.6 |
|        11 | 128 |  23.9 |        15.5 |    7.8 |    1.6 |     4.4 |
|        12 |  69 |  24.6 |        17.2 |    6.1 |   -1.9 |     2.4 |
|         5 |  20 |  52.5 |        23.8 |    8   |   16.5 |     1.5 |

## By command stars (commanders)

|   stars |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|--------:|-----:|------:|------------:|-------:|-------:|--------:|
|       0 | 1775 |  26.9 |        16.1 |   10.1 |    4.1 |    68.5 |
|       1 |  358 |  21.9 |        12.5 |    6.4 |    0   |    11.3 |
|       2 |  209 |  28.3 |        20.7 |    5.5 |   -0.3 |     8.5 |
|       3 |  104 |  39.3 |        26.2 |    5.4 |    1.4 |     5.9 |
|       5 |   14 | 147.5 |        43.7 |   10   |  104.9 |     3   |
|       4 |   44 |  46.2 |        22.5 |    4.3 |    6.2 |     2.9 |

## By training level

| unit_training_level   |    n |   MAE |   median_AE |   MAPE |   bias |   share |
|:----------------------|-----:|------:|------------:|-------:|-------:|--------:|
| well_trained          | 1062 |  26.1 |        17.4 |    5.5 |    0.6 |    39.8 |
| trained               |  862 |  24.7 |        14.8 |    7.6 |    4.5 |    30.6 |
| poorly_trained        |  303 |  30.6 |        16.7 |   25.9 |    7.9 |    13.3 |
| elite                 |  191 |  33.2 |         9.8 |    3.9 |   -2.3 |     9.1 |
| mob                   |   86 |  58.5 |        26.2 |   13.8 |   30.2 |     7.2 |

## 25 largest absolute errors

| unit_name                                                                           | army_corps_name                 | kind      | seg       |   base_mp_cost |   pred |   err |
|:------------------------------------------------------------------------------------|:--------------------------------|:----------|:----------|---------------:|-------:|------:|
| Tecumseh (Shaawanwaki 'Shawnee') [GS2]                                              | [1812] 7. UK (USA)              | commander | inf_skirm |           1866 |   3351 |  1485 |
| Congreve rockets 'Whinyates'' [F0]                                                  | [1815] 9. UK, Nederlanden       | regular   | art_foot  |            658 |   1239 |   581 |
| ¤ Johan August Sandels (Fotjägare 'Savolax') [L5]                                   | [1808] 7. Sverige (Finska)      | commander | inf_light |           1618 |   2046 |   428 |
| Jerónimo Merino Cob 'el Cura Merino' (Voluntarios de Arlanza) [G4]                  | [1811] 7. España                | commander | inf_milit |            722 |   1135 |   413 |
| Dragons de l’Impératrice 'les Muscadins' [C3]                                       | [1814] 8. France                | regular   | cav_stand |           2050 |   1660 |  -390 |
| Leyb-gvardyi Konnyi [C2]                                                            | [1808] 7. Rossiya (Finlyandiya) | regular   | cav_heavy |           1681 |   2019 |   338 |
| {Vieille Garde} Dragons de l’Impératrice 'les Muscadins' [C3]                       | [1814] 8. France                | regular   | cav_stand |           1576 |   1253 |  -323 |
| ¤ François-Xavier Donzelot (61e de ligne 'le Vermandois') [L4]                      | [1798] 8. France (Égypte)       | commander | inf_line  |            828 |   1142 |   314 |
| ¤ 61e de ligne 'le Vermandois' [L4]                                                 | [1798] 8. France (Égypte)       | regular   | inf_line  |            709 |   1019 |   310 |
| 3-pund kørende artilleri [H3]                                                       | 7. Danmark                      | regular   | art_horse |            262 |    558 |   296 |
| Donskie kazaki 'Kharitonov' [C5]                                                    | [1809] 7. Polska, sojusznicy    | regular   | cav_lance |            189 |    448 |   259 |
| ¤ Robert Craufurd 'Black Bob' (52nd (Oxfordshire) Light Foot 'the Light Bobs') [L6] | [1811] 9. UK, Portugal          | commander | inf_light |           1307 |   1048 |  -259 |
| Dragoni del Piemonte 'Dragons jaunes' [C3]                                          | 8. Piemonte-Sardegna (1796)     | regular   | cav_stand |           1340 |   1595 |   255 |
| ¤ 1st Foot Guards 'the Tow-Rows' [L2]                                               | [1809] 6. UK (Walcheren)        | regular   | inf_line  |           1936 |   1686 |  -250 |
| Jean-Baptiste Chaffardon (Dragoni del Piemonte 'Dragons jaunes') [C3]               | 8. Piemonte-Sardegna (1796)     | commander | cav_stand |           1183 |   1426 |   243 |
| ¤ Johan Adam Cronstedt (Lätt infanteri 'Savolax') [L5]                              | [1808] 7. Sverige (Finska)      | commander | inf_light |           1146 |   1373 |   227 |
| Hashdu Mamāliki 'Wadi Al Nil' [C4]                                                  | [1798] 8. Mamālīk               | regular   | cav_light |           1127 |   1348 |   221 |
| Húsares de Cantabria [C4]                                                           | [1811] 7. España                | regular   | cav_light |           1336 |   1552 |   216 |
| Neshnabé 'Pottawatomi' [L3]                                                         | [1812] 7. UK (USA)              | regular   | inf_milit |            386 |    598 |   212 |
| 5th (Princess Charlotte of Wales') Dragoon Guards 'the Green Horse' [C2]            | [1798] 5. UK (Ireland)          | regular   | cav_heavy |           2814 |   3018 |   204 |
| Bartolomé Amor Pisa (Húsares de La Rioja) [C4]                                      | [1811] 7. España                | commander | cav_light |            837 |   1034 |   197 |
| Leyb-gvardyi Dragouni [C3]                                                          | [1812] 10. Rossiya              | regular   | cav_stand |            295 |    492 |   197 |
| Herregårdsskytterne [C4]                                                            | 7. Danmark                      | regular   | cav_light |             71 |    267 |   196 |
| Húsares de Iberia [C4]                                                              | [1811] 7. España                | regular   | cav_light |           1047 |   1240 |   193 |
| ¤ Grenadiers de ligne du 109e [G5]                                                  | [1798] 5. France (Irlande)      | regular   | inf_grena |            886 |   1078 |   192 |

Share of squared error explained by army x type mean residual: 0.339
