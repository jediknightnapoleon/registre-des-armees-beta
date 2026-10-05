# Army audit (descriptive, all clean rows)

Ratios are real price ÷ price implied by stats (model 18b: stat formulas + N/10, no army terms). 18b misses single units by ~11% on average; read army/type medians over many units, not single rows. Rows under 50 gold are left out of ratio medians.

## 1. Does N/10 apply to units?

Identical regular units (same feature hash) priced in armies with different N: 85 pairs; (price ratio) ÷ (N ratio): median 0.999, within ±5%: 52%.

## 2. Armies whose standalone generals deviate from N/10

Standalone-general price at N = 10 by stars: {1.0: 60, 2.0: 159, 3.0: 281, 4.0: 420, 5.0: 574, 6.0: 741, 7.0: 920, 8.0: 1109, 9.0: 1308}.
Armies whose generals follow N/10: units vs stats median 0.992, IQR 0.968–1.011.

| army_corps_name                 |   N/10 |   generals' divisor |   generals vs N/10 |   units vs stats |   commanders vs stats |
|:--------------------------------|-------:|--------------------:|-------------------:|-----------------:|----------------------:|
| 9. Heiliges Römisches Reich     |    0.9 |               0.789 |              1.14  |            1.123 |                 1.158 |
| [1798] 8. France (Égypte)       |    0.8 |               0.85  |              0.941 |            0.98  |                 1.009 |
| [1799] 9. France (Italie)       |    0.9 |               0.94  |              0.958 |            0.974 |                 0.95  |
| [1805] 11. France (Allemagne)   |    1.1 |               1.15  |              0.956 |            0.988 |                 0.964 |
| [1806] 12. France (Prusse)      |    1.2 |               1.3   |              0.923 |            0.95  |                 0.94  |
| [1809] 10. UK, España, Portugal |    1   |               0.633 |              1.579 |            0.977 |                 0.977 |
| [1811] 9. UK, Portugal          |    0.9 |               0.955 |              0.942 |            0.904 |                 0.884 |
| [1814] 9. Rossiya (Frantsiya)   |    0.9 |               0.874 |              1.03  |            1.049 |                 1.033 |

## 3. All armies: units and commanders vs stats

Across armies, regular-unit level: median 0.990, 10th–90th percentile 0.928–1.044.

| army_corps_name                   |   commander |   regular |   n |   share below stats |   gold vs stats |   rank (1 = cheapest units) |
|:----------------------------------|------------:|----------:|----:|--------------------:|----------------:|----------------------------:|
| 7. Danmark                        |       0.907 |     0.875 |  71 |               0.93  |       -5222.06  |                           1 |
| [1814] 8. France                  |       0.921 |     0.897 | 351 |               0.821 |      -12618.9   |                           2 |
| [1811] 9. UK, Portugal            |       0.884 |     0.904 | 253 |               0.842 |      -10924.3   |                           3 |
| [1798] 8. Mamālīk                 |       0.952 |     0.914 |  60 |               0.717 |       -1920.83  |                           4 |
| [1799] 7. France (Hollande)       |       0.932 |     0.917 |  85 |               0.8   |       -2588.53  |                           5 |
| [1812] 7. France (Russie-Sud)     |       0.947 |     0.928 | 227 |               0.749 |       -5130.34  |                           6 |
| [1804] 8. Rossiya (Kavkaz, Dunau) |       0.876 |     0.928 | 177 |               0.78  |       -4698.44  |                           7 |
| [1806] 12. France (Prusse)        |       0.94  |     0.95  | 369 |               0.843 |       -9681.99  |                           8 |
| [1812] 6. France (Russie-Nord)    |       1.001 |     0.951 | 252 |               0.603 |       -3272.85  |                           9 |
| 8. Piemonte-Sardegna (1796)       |       1.033 |     0.955 |  79 |               0.646 |        -467.128 |                          10 |
| [1812] 7. United States           |       0.919 |     0.956 | 137 |               0.642 |       -4268.77  |                          11 |
| [1815] 9. France (Flandres)       |       0.953 |     0.963 | 330 |               0.685 |       -9440.38  |                          12 |
| [1805] 6. France (Tyrol)          |       1.018 |     0.963 | 228 |               0.575 |       -1766.6   |                          13 |
| [1809] 10. France (Espagne)       |       0.91  |     0.969 | 462 |               0.777 |      -10244.8   |                          14 |
| [1809] 7. Polska, sojusznicy      |       0.964 |     0.972 | 193 |               0.663 |       -9321.3   |                          15 |
| [1799] 9. France (Italie)         |       0.95  |     0.974 | 190 |               0.679 |       -1784.54  |                          16 |
| [1806] 9. Osmanlı                 |       0.933 |     0.975 | 103 |               0.65  |       -2283.47  |                          17 |
| [1809] 10. UK, España, Portugal   |       0.977 |     0.977 | 298 |               0.597 |        2131.17  |                          18 |
| [1812] 8. Russkiy narod           |       0.93  |     0.978 |  88 |               0.739 |       -2881.34  |                          19 |
| [1798] 8. France (Égypte)         |       1.009 |     0.98  | 106 |               0.585 |       -1633.02  |                          20 |
| [1804] 7. Irānshahr               |       1.005 |     0.98  |  54 |               0.519 |         589.877 |                          21 |
| [1815] 7. Preußen (Flandern)      |       1.027 |     0.982 | 224 |               0.518 |       -2689.16  |                          22 |
| [1809] 10. France (Autriche)      |       0.941 |     0.982 | 390 |               0.672 |       -4581.57  |                          23 |
| [1815] 6. Napoli                  |       1.035 |     0.982 |  82 |               0.512 |        -226.398 |                          24 |
| [1811] 8. France (Espagne)        |       0.996 |     0.983 | 558 |               0.591 |       -3655.36  |                          25 |
| [1805] 11. France (Allemagne)     |       0.964 |     0.988 | 190 |               0.595 |         -66.647 |                          26 |
| [1812] 7. UK (USA)                |       1.016 |     0.989 | 113 |               0.504 |       -2588.83  |                          27 |
| [1808] 7. Rossiya (Finlyandiya)   |       1.03  |     0.99  |  95 |               0.484 |       -2208.81  |                          28 |
| [1805] 8. Österreich              |       1.002 |     0.993 | 315 |               0.508 |         -82.89  |                          29 |
| [1815] 6. Österreich (Italien)    |       1.046 |     0.994 | 187 |               0.439 |        2715.74  |                          30 |
| [1798] 5. UK (Ireland)            |       1.226 |     0.996 |  63 |               0.302 |        1372.46  |                          31 |
| [1812] 11. France (Russie-Centre) |       0.951 |     0.996 | 527 |               0.638 |       -8418.97  |                          32 |
| 9. France (1796)                  |       1.014 |     0.997 | 104 |               0.5   |         345.648 |                          33 |
| [1798] 5. France (Irlande)        |       1.059 |     1.003 |  29 |               0.448 |         146.126 |                          34 |
| [1809] 10. Österreich             |       0.99  |     1.003 | 294 |               0.5   |        -319.073 |                          35 |
| [1812] 10. Rossiya                |       0.982 |     1.005 | 631 |               0.506 |        1408.86  |                          36 |
| [1799] 7. Österreich (Schwaben)   |       1.071 |     1.005 | 300 |               0.37  |         553.247 |                          37 |
| [1800] 8. Osmanlı, UK             |       1.03  |     1.01  | 204 |               0.422 |        2384.64  |                          38 |
| [1806] 10. Preußen                |       0.972 |     1.011 | 346 |               0.512 |        3406.83  |                          39 |
| [1814] 8. Österreich (Frankreich) |       1.035 |     1.011 | 288 |               0.431 |       -3675.83  |                          40 |
| [1815] 9. UK, Nederlanden         |       1.013 |     1.012 | 310 |               0.429 |       -1672.14  |                          41 |
| [1805] 9. Rossiya, Österreich     |       1.013 |     1.018 | 140 |               0.386 |        2043.93  |                          42 |
| [1814] 8. Preußen (Frankreich)    |       1.039 |     1.019 | 229 |               0.341 |        2336.47  |                          43 |
| [1807] 9. Rossiya (Polsha)        |       1.022 |     1.019 | 229 |               0.354 |        1993.93  |                          44 |
| [1809] 8. Österreich (Tyrol)      |       1.067 |     1.024 | 155 |               0.277 |        3920.19  |                          45 |
| [1799] 9. Österreich (Italien)    |       0.997 |     1.025 | 219 |               0.434 |        1802.15  |                          46 |
| [1809] 9. España                  |       1.031 |     1.025 | 296 |               0.402 |        2276.6   |                          47 |
| 8. UK (Spain, 1808)               |       1.029 |     1.031 |  48 |               0.229 |        1425.23  |                          48 |
| [1811] 7. España                  |       1.088 |     1.039 | 421 |               0.259 |       10294     |                          49 |
| [1799] 9. France (Rhin)           |       1.049 |     1.048 | 181 |               0.315 |        2970.22  |                          50 |
| [1814] 9. Rossiya (Frantsiya)     |       1.033 |     1.049 | 436 |               0.289 |        6527.08  |                          51 |
| [1799] 7. UK, Russia (Helder)     |       1.109 |     1.052 | 109 |               0.156 |        5062.71  |                          52 |
| [1808] 7. Sverige (Finska)        |       1.06  |     1.058 |  70 |               0.329 |         833.442 |                          53 |
| [1809] 6. UK (Walcheren)          |       1.127 |     1.066 | 123 |               0.154 |        7121.33  |                          54 |
| 9. Heiliges Römisches Reich       |       1.158 |     1.123 | 144 |               0.167 |        9479.1   |                          55 |

## 4. [1809] 10. UK, España, Portugal

|                            |   n |   median |     gold |
|:---------------------------|----:|---------:|---------:|
| ('art_foot', 'commander')  |   7 |    1.066 |  160.042 |
| ('art_foot', 'regular')    |  14 |    1.014 |  197.49  |
| ('art_horse', 'commander') |   1 |    1.027 |   11.952 |
| ('art_horse', 'regular')   |   2 |    0.985 |  -11.377 |
| ('cav_heavy', 'commander') |   7 |    1.133 | 1304.87  |
| ('cav_heavy', 'regular')   |   9 |    1.172 | 1734.68  |
| ('cav_lance', 'commander') |   1 |    1.033 |   11.544 |
| ('cav_lance', 'regular')   |   1 |    1.089 |   32.941 |
| ('cav_light', 'commander') |  13 |    0.902 | -219.113 |
| ('cav_light', 'regular')   |  17 |    1     |  136.337 |
| ('cav_stand', 'commander') |   6 |    0.955 |  -72.818 |
| ('cav_stand', 'regular')   |   7 |    0.977 |   -4.152 |
| ('inf_grena', 'commander') |   4 |    1.005 |    5.893 |
| ('inf_grena', 'regular')   |   9 |    1.006 |   -6.497 |
| ('inf_light', 'commander') |  19 |    1.001 |  710.783 |
| ('inf_light', 'regular')   |  20 |    0.98  | -150.193 |
| ('inf_line', 'commander')  |  59 |    0.948 | -880.218 |
| ('inf_line', 'regular')    |  56 |    0.955 | -912.79  |
| ('inf_milit', 'commander') |   9 |    1.063 |   78.706 |
| ('inf_milit', 'regular')   |  24 |    0.96  |  -63.615 |
| ('inf_skirm', 'commander') |   3 |    1.12  |   82.329 |
| ('inf_skirm', 'regular')   |  10 |    0.923 |  -15.624 |

Standalone generals:

| unit_name                                       |   stars |   base_mp_cost |    pred |    r |
|:------------------------------------------------|--------:|---------------:|--------:|-----:|
| Arthur Wellesley 'Wellington'                   |       8 |           1746 | 1097.6  | 1.59 |
| William Carr Beresford                          |       2 |            250 |  159.86 | 1.56 |
| Don Gregorio Garcia de la Cuesta                |       1 |             95 |   60.78 | 1.56 |
| Francisco da Silveira Pinto da Fonseca Teixeira |       1 |             95 |   60.78 | 1.56 |

Cheapest units vs stats:

| unit_name                                                                                                     | kind      | seg       |   base_mp_cost |   pred |    r |
|:--------------------------------------------------------------------------------------------------------------|:----------|:----------|---------------:|-------:|-----:|
| António Lobo Teixeira de Barros (Infantaria N.° 13 'Santarém') [L2]                                           | commander | inf_line  |             72 | 138.54 | 0.52 |
| Francisco de Paula Gómez de Terán y Negrete 'Marqués de Portazgo' (Infantería de Badajoz 'el Cumplidor') [L2] | commander | inf_line  |             64 | 104.13 | 0.61 |
| Gerónimo Puig Amigó (Cazadores Imperiales Sagrados de Toledo) [C4]                                            | commander | cav_light |             80 | 126.34 | 0.63 |
| Luis Padilla (Infantería de Murcia 'el Leal') [L3]                                                            | commander | inf_line  |            102 | 160.82 | 0.63 |
| Ordenanças de Tabosa [L1]                                                                                     | regular   | inf_milit |             51 |  79.22 | 0.64 |
| Infantaria N.° 13 'Santarém' [L2]                                                                             | regular   | inf_line  |            114 | 172.61 | 0.66 |
| ¤ Robert Nixon (Caçadores N.° 2 'Voluntários do Beja') [L4]                                                   | commander | inf_light |             67 | 101.39 | 0.66 |
| Infantería de Badajoz 'el Cumplidor' [L2]                                                                     | regular   | inf_line  |             94 | 137.61 | 0.68 |

## 4. [1811] 9. UK, Portugal

|                            |   n |   median |      gold |
|:---------------------------|----:|---------:|----------:|
| ('art_foot', 'commander')  |   8 |    1.006 |    17.252 |
| ('art_foot', 'regular')    |   9 |    0.974 |   -33.766 |
| ('art_horse', 'commander') |   2 |    0.952 |   -52.519 |
| ('art_horse', 'regular')   |   1 |    0.95  |   -32.657 |
| ('cav_heavy', 'commander') |   5 |    1.039 |   369.251 |
| ('cav_heavy', 'regular')   |   3 |    1.038 |   239.733 |
| ('cav_light', 'commander') |   8 |    0.959 |  -326.835 |
| ('cav_light', 'regular')   |   8 |    0.96  |  -221.248 |
| ('cav_stand', 'commander') |   4 |    0.904 |  -135.103 |
| ('cav_stand', 'regular')   |   4 |    0.99  |   -32.565 |
| ('inf_grena', 'commander') |   1 |    1.054 |    50.061 |
| ('inf_grena', 'regular')   |   1 |    0.998 |    -1.597 |
| ('inf_light', 'commander') |  17 |    0.861 |  -628.796 |
| ('inf_light', 'regular')   |  16 |    0.877 | -1235.92  |
| ('inf_line', 'commander')  |  75 |    0.87  | -4617.36  |
| ('inf_line', 'regular')    |  73 |    0.891 | -4199.71  |
| ('inf_skirm', 'commander') |   5 |    1.004 |    64.193 |
| ('inf_skirm', 'regular')   |  13 |    0.995 |  -146.735 |

Standalone generals:

| unit_name                     |   stars |   base_mp_cost |    pred |    r |
|:------------------------------|--------:|---------------:|--------:|-----:|
| Arthur Wellesley 'Wellington' |       8 |           1161 | 1219.56 | 0.95 |
| Sir Thomas Graham             |       3 |            294 |  312.31 | 0.94 |
| William Carr Beresford        |       2 |            167 |  177.62 | 0.94 |

Cheapest units vs stats:

| unit_name                                                             | kind      | seg       |   base_mp_cost |   pred |    r |
|:----------------------------------------------------------------------|:----------|:----------|---------------:|-------:|-----:|
| William Cornwallis Eustace (Chasseurs britanniques) [L4]              | commander | inf_light |            101 | 194.43 | 0.52 |
| ¤ William Kelly (24th (2nd Warwickshire) Foot 'Howard's Greens') [L3] | commander | inf_line  |             80 | 134.5  | 0.59 |
| John Browne (Cavalaria de batalha N.° 8 'Elvas') [C3]                 | commander | cav_stand |            124 | 208.05 | 0.6  |
| Richard Bushe (Infantaria N.° 20) [L2]                                | commander | inf_line  |             69 | 114.11 | 0.6  |
| ¤ William Grant (82nd Foot 'Prince of Wales' Volunteers') [L3]        | commander | inf_line  |            139 | 222.27 | 0.63 |
| ¤ William Thomas Dilkes (3rd (Scots) Foot Guards 'the Kiddies') [G4]  | commander | inf_line  |            405 | 628.95 | 0.64 |
| ¤ João António Tavares (Infantaria N.° 3 'Estremoz') [L4]             | commander | inf_line  |            211 | 308.16 | 0.68 |
| ¤ David Campbell (9th (East Norfolk) Foot 'the Holy Boys') [L3]       | commander | inf_line  |            131 | 190.16 | 0.69 |

## 4. [1809] 7. Polska, sojusznicy

|                            |   n |   median |      gold |
|:---------------------------|----:|---------:|----------:|
| ('art_foot', 'commander')  |   6 |    1.082 |   180.809 |
| ('art_foot', 'regular')    |  10 |    1.033 |   152.284 |
| ('art_horse', 'commander') |   3 |    1.033 |    40.883 |
| ('art_horse', 'regular')   |   5 |    0.993 |    37.826 |
| ('cav_heavy', 'commander') |   8 |    1.015 |   -48.394 |
| ('cav_heavy', 'regular')   |   8 |    1.009 |  -188.831 |
| ('cav_lance', 'commander') |  10 |    0.587 | -3626.03  |
| ('cav_lance', 'regular')   |  11 |    0.581 | -3947.96  |
| ('cav_light', 'commander') |   9 |    1.005 |   114.462 |
| ('cav_light', 'regular')   |   9 |    1.016 |   133.388 |
| ('cav_stand', 'commander') |   8 |    1.126 |   429.37  |
| ('cav_stand', 'regular')   |   8 |    1.076 |   378.072 |
| ('inf_grena', 'commander') |   6 |    0.956 |  -345.298 |
| ('inf_grena', 'regular')   |   5 |    0.944 |  -275.01  |
| ('inf_light', 'commander') |   7 |    0.936 |  -235.246 |
| ('inf_light', 'regular')   |   7 |    0.861 |  -511.315 |
| ('inf_line', 'commander')  |  37 |    0.931 |  -762.601 |
| ('inf_line', 'regular')    |  34 |    0.952 |  -796.138 |
| ('inf_skirm', 'regular')   |   2 |    0.883 |   -51.572 |

Standalone generals:

| unit_name              |   stars |   base_mp_cost |   pred |    r |
|:-----------------------|--------:|---------------:|-------:|-----:|
| Jérôme Bonaparte       |       0 |              1 |   1    | 1    |
| Józef Poniatowski [C4] |       5 |            820 | 815.85 | 1.01 |
| Serguei Golitsyn       |       1 |             87 |  86.83 | 1    |

Cheapest units vs stats:

| unit_name                                           | kind      | seg       |   base_mp_cost |   pred |    r |
|:----------------------------------------------------|:----------|:----------|---------------:|-------:|-----:|
| Donskie kazaki 'Kharitonov' [C5]                    | regular   | cav_lance |            189 | 672.46 | 0.28 |
| Andrian Denissov (Donskie kazaki 'Denissov') [C5]   | commander | cav_lance |            288 | 697.62 | 0.41 |
| Vassili Syssoyev (Donskie kazaki 'Syssoyev') [C5]   | commander | cav_lance |            329 | 746.25 | 0.44 |
| Ivan Vadbolski (Tatarskie oulani) [C4]              | commander | cav_lance |            219 | 469.68 | 0.47 |
| Litovskie oulani [C4]                               | regular   | cav_lance |            245 | 498.79 | 0.49 |
| Donskie kazaki 'Denissov' [C5]                      | regular   | cav_lance |            401 | 805.31 | 0.5  |
| Nikolai Ilovayski (Donskie kazaki 'Ilovayski') [C5] | commander | cav_lance |            333 | 643.94 | 0.52 |
| Donskie kazaki 'Syssoyev' [C5]                      | regular   | cav_lance |            482 | 923.39 | 0.52 |

## 5. Cossacks (name contains 'kazaki'), by army (n ≥ 3)

| army_corps_name                   |   n |   median |
|:----------------------------------|----:|---------:|
| [1809] 7. Polska, sojusznicy      |   7 |    0.498 |
| [1808] 7. Rossiya (Finlyandiya)   |   8 |    0.848 |
| [1799] 9. Österreich (Italien)    |  12 |    0.892 |
| [1799] 7. Österreich (Schwaben)   |   5 |    0.902 |
| [1814] 9. Rossiya (Frantsiya)     |  66 |    0.955 |
| [1812] 8. Russkiy narod           |  59 |    0.966 |
| [1805] 9. Rossiya, Österreich     |   9 |    1.023 |
| [1812] 10. Rossiya                |  45 |    1.023 |
| [1807] 9. Rossiya (Polsha)        |   3 |    1.053 |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  18 |    1.231 |

## 5. All lancers (cav_lance), by army (n ≥ 3)

| army_corps_name                   |   n |   median |
|:----------------------------------|----:|---------:|
| [1809] 7. Polska, sojusznicy      |  21 |    0.581 |
| [1808] 7. Rossiya (Finlyandiya)   |  10 |    0.836 |
| [1798] 8. Mamālīk                 |   5 |    0.872 |
| [1806] 9. Osmanlı                 |  12 |    0.881 |
| [1799] 9. Österreich (Italien)    |  12 |    0.892 |
| [1805] 8. Österreich              |   6 |    0.934 |
| [1812] 8. Russkiy narod           |  67 |    0.952 |
| [1807] 9. Rossiya (Polsha)        |   7 |    0.959 |
| [1814] 9. Rossiya (Frantsiya)     |  75 |    0.965 |
| [1814] 8. France                  |  12 |    0.968 |
| [1799] 7. Österreich (Schwaben)   |  13 |    0.976 |
| [1812] 11. France (Russie-Centre) |  40 |    0.98  |
| [1815] 7. Preußen (Flandern)      |  38 |    0.986 |
| [1815] 9. France (Flandres)       |  16 |    0.996 |
| [1809] 10. Österreich             |   8 |    0.999 |
| [1815] 6. Österreich (Italien)    |   4 |    0.999 |
| [1812] 10. Rossiya                |  57 |    1.009 |
| [1814] 8. Preußen (Frankreich)    |  21 |    1.012 |
| [1811] 8. France (Espagne)        |  11 |    1.015 |
| [1800] 8. Osmanlı, UK             |  14 |    1.021 |
| [1804] 7. Irānshahr               |   8 |    1.022 |
| [1811] 7. España                  |   6 |    1.026 |
| [1805] 9. Rossiya, Österreich     |  14 |    1.031 |
| [1809] 10. France (Espagne)       |   5 |    1.033 |
| [1812] 6. France (Russie-Nord)    |   5 |    1.14  |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  20 |    1.151 |
| 9. Heiliges Römisches Reich       |   3 |    1.159 |

## 5. British/Portuguese line + light infantry, by army (n ≥ 3)

| army_corps_name                 |   n |   median |
|:--------------------------------|----:|---------:|
| [1811] 9. UK, Portugal          | 161 |    0.875 |
| [1809] 10. UK, España, Portugal |  98 |    0.948 |
| [1812] 7. UK (USA)              |  26 |    0.986 |
| [1800] 8. Osmanlı, UK           |  60 |    1.034 |
| 8. UK (Spain, 1808)             |  34 |    1.035 |
| [1815] 9. UK, Nederlanden       |  60 |    1.059 |
| [1814] 8. Preußen (Frankreich)  |  19 |    1.07  |
| [1799] 7. UK, Russia (Helder)   |  62 |    1.102 |
| [1809] 6. UK (Walcheren)        |  88 |    1.107 |
| [1798] 5. UK (Ireland)          |   7 |    1.118 |

## 6. Wellington in every army

| army_corps_name                 |   stars |   base_mp_cost |   standard price |   ratio |
|:--------------------------------|--------:|---------------:|-----------------:|--------:|
| [1809] 10. UK, España, Portugal |       8 |           1746 |             1109 |   1.574 |
| [1815] 9. UK, Nederlanden       |       7 |           1022 |             1022 |   1     |
| [1811] 9. UK, Portugal          |       8 |           1161 |             1232 |   0.942 |
