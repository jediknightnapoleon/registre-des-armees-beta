## Model 18a

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.59494 |  |
| `log_men` | ln(men_raw) | 1.85383 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00665348 | [6, 82] |
| `reload_skill` | reload_skill | 0.00391873 | [14, 100] |
| `morale` | morale | 0.0253353 | [2, 12] |
| `melee_defense` | melee_defense | -0.258869 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.339231 | [0, 2] |
| `range0` | range | 0.000918587 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0255547 | [17, 80] |
| `speed_num` | speed digit | 0.192005 | [0, 6] |
| `guns0` | guns | 0.0599313 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.218526 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.294018 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 1.20361 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.522133 | [0, 1.099] |
| `men_raw` | men_raw | -0.00788456 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.194192 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.87916 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -11.6359 |  |
| `log_men` | ln(men_raw) | 2.0463 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00576789 | [29, 85] |
| `reload_skill` | reload_skill | 0.00353084 | [35, 100] |
| `morale` | morale | 0.0916088 | [5, 14] |
| `range0` | range | 0.0019252 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0115331 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.158227 | [14, 40] |
| `speed_num` | speed digit | 0.378688 | [1, 3] |
| `guns0` | guns | -0.244432 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.205333 |  |
| `can_inspire` | [can_inspire] | 0.154375 |  |
| `log_morale` | ln(1 + morale) | -0.502668 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.14613 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.124346 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.10807 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000239348 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | 0.0140589 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | 0.00452648 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0319835 |  |
| `log_men^2` | ln(men_raw)² | 0.0457574 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -8.96067e-05 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.00440016 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.840143 |  |
| `log_men` | ln(men_raw) | 0.553607 | [4.382, 5.823] |
| `train` | training code | -0.0163025 | [1, 4] |
| `morale` | morale | 0.0195228 | [7, 18] |
| `melee_attack` | melee_attack | -0.0460569 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0146388 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.158807 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.344419 |  |
| `can_inspire` | [can_inspire] | 0.163831 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.18251 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.88939 |  |
| `log_men` | ln(men_raw) | 0.612449 | [4.357, 5.656] |
| `morale` | morale | 0.0408833 | [4, 16] |
| `melee_defense` | melee_defense | -0.0255011 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0595644 | [1, 9] |
| `rank_depth` | rank_depth | -0.016745 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.255601 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.309268 |  |
| `can_inspire` | [can_inspire] | 0.0489301 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.170675 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.16089 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.351373 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.5146 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00381028 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.23602 |  |
| `log_men` | ln(men_raw) | 0.53718 | [4.331, 5.886] |
| `accuracy` | accuracy | 0.0102149 | [0, 34] |
| `reload_skill` | reload_skill | -0.00601341 | [0, 90] |
| `morale` | morale | -0.0256014 | [3, 15] |
| `melee_defense` | melee_defense | -0.015994 | [3, 23] |
| `range0` | range | 0.0134142 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.249287 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.288206 |  |
| `can_inspire` | [can_inspire] | 0.150702 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.455477 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.321745 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.0265152 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.573094 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.44371 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.187334 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00478495 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.340264 |  |
| `log_men` | ln(men_raw) | 0.605129 | [4.357, 5.781] |
| `morale` | morale | 0.177628 | [6, 13] |
| `melee_attack` | melee_attack | -0.0491242 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0311136 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.18014 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.351815 |  |
| `log_morale` | ln(1 + morale) | -0.103003 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.897054 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0582503 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.000475724 | [5, 9] |
| `morale^2` | morale² | -0.00701509 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -1.77697 |  |
| `log_men` | ln(men_raw) | 1.51217 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.124753 | [9, 30] |
| `reload_skill` | reload_skill | 0.00412115 | [4, 99] |
| `morale` | morale | -0.0875631 | [4, 18] |
| `melee_attack` | melee_attack | 0.126014 | [12, 25] |
| `melee_defense` | melee_defense | -0.0132544 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.0163161 | [16, 33] |
| `range0` | range | 0.00393881 | [70, 100] |
| `projectile_damage0` | projectile_damage | 3.55695 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0800051 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.0973624 |  |
| `has_stamina` | [has_stamina] | 0.0950211 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.103988 |  |
| `can_inspire` | [can_inspire] | 0.0946074 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.309547 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0713295 |  |
| `can_build_barricades` | [can_build_barricades] | 0.122801 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.13631 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -1.60498 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.224937 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.591153 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.0052713 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -6.02321 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0309351 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.0021427 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0285781 | [44.35, 168] |
| `morale^2` | morale² | 0.00142379 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00220042 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | -0.0307866 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | 0.0142839 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -7.39087 |  |
| `log_men` | ln(men_raw) | 2.28069 | [4.868, 6.114] |
| `train` | training code | 0.00454276 | [1, 4] |
| `reload_skill` | reload_skill | -0.0266861 | [23, 101] |
| `ammo` | ammo | -0.000298063 | [15, 70] |
| `melee_attack` | melee_attack | -0.0216368 | [6, 19] |
| `charge_bonus` | charge_bonus | 0.00405909 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0279625 | [14, 20] |
| `speed_num` | speed digit | 0.0558398 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.152435 |  |
| `has_stamina` | [has_stamina] | 0.114272 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.104404 |  |
| `can_inspire` | [can_inspire] | 0.104997 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.528597 |  |
| `guard_mode` | [guard_mode] | 0.0583106 |  |
| `pike_square` | [pike_square] | 0.0215184 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.367304 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.195959 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0123521 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.0716949 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.00677348 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -1.2134 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00583427 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.130345 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0753115 |  |
| `speed_code=L3` | [speed_code = L3] | -0.0962241 |  |
| `speed_code=L4` | [speed_code = L4] | 0.020426 |  |
| `speed_code=L5` | [speed_code = L5] | 0.0543929 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0538194 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0106949 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | -0.000107002 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.1794 |  |
| `log_men` | ln(men_raw) | 2.39598 | [4.852, 6.114] |
| `ammo` | ammo | 0.00356629 | [25, 70] |
| `morale` | morale | -0.0301483 | [0, 16] |
| `melee_attack` | melee_attack | 0.0311915 | [6, 23] |
| `melee_defense` | melee_defense | -0.012147 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0591376 | [9, 30] |
| `projectile_damage0` | projectile_damage | -0.145279 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0707929 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.126534 |  |
| `has_stamina` | [has_stamina] | 0.0929606 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0862675 |  |
| `can_inspire` | [can_inspire] | 0.0874143 |  |
| `can_place_stakes` | [can_place_stakes] | 0.245792 |  |
| `pike_square` | [pike_square] | 0.0338656 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.121082 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.196223 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.184421 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.21005 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.187314 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.32313 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00590242 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.500749 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0288875 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00230798 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000529003 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.99218 |  |
| `log_men` | ln(men_raw) | 1.61799 | [4.852, 6.881] |
| `train` | training code | -0.0171159 | [0, 3] |
| `ammo` | ammo | 0.00195622 | [0, 70] |
| `morale` | morale | 0.0785112 | [0, 18] |
| `melee_defense` | melee_defense | 0.0256311 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.0986388 | [8, 29] |
| `range0` | range | 0.00488969 | [0, 100] |
| `projectile_damage0` | projectile_damage | 1.39531 | [0, 0.83] |
| `speed_num` | speed digit | 0.177021 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.159632 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0601622 |  |
| `can_inspire` | [can_inspire] | -0.45436 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.387558 |  |
| `can_place_stakes` | [can_place_stakes] | 0.032902 |  |
| `scares_enemies` | [scares_enemies] | 0.414347 |  |
| `skirmish` | [skirmish] | -1.17992 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.396986 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.144691 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.121698 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | 0.0182902 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.15096 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.166109 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.31372 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00223034 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -1.76565 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.173827 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.00441832 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 6.0455 |  |
| `log_men` | ln(men_raw) | -0.622616 | [3.871, 5.606] |
| `train` | training code | 0.00987097 | [0, 4] |
| `accuracy` | accuracy | 0.00733559 | [15, 38] |
| `morale` | morale | 0.160684 | [3, 13] |
| `melee_attack` | melee_attack | -0.0689229 | [1, 23] |
| `charge_bonus` | charge_bonus | 0.00209657 | [1, 32] |
| `speed_num` | speed digit | 0.322122 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0387386 |  |
| `can_inspire` | [can_inspire] | -0.0351643 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.746257 |  |
| `can_place_stakes` | [can_place_stakes] | 0.132229 |  |
| `guard_mode` | [guard_mode] | -0.0242296 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.158244 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | 0.0135559 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -0.969677 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.403588 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.007109 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.013324 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.020932 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.12034 |  |
| `log_stars` | ln(command_stars) | 1.38341 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.899 |
| b0 | -80.65 |
| b1 | -56.47 |
| b2 | -32.91 |
| b3 | -11.68 |
| b4 | -1.861 |
| b5 | 43.33 |
| a_star1 | 0.01026 |
| a_star2 | 0.03444 |
| a_star3 | 0.06204 |
| a_star4 | 0.09518 |
| a_star5 | 0.12 |

Per-army commander premium `p_army` (gold, before dividing by N/10):

| army | p_army |
| --- | ---: |
| 7. Danmark | -15.0 |
| 8. Piemonte-Sardegna (1796) | 20.7 |
| 8. UK (Spain, 1808) | 27.0 |
| 9. France (1796) | -1.8 |
| 9. Heiliges Römisches Reich | 22.9 |
| [1798] 5. France (Irlande) | 10.4 |
| [1798] 5. UK (Ireland) | 29.6 |
| [1798] 8. France (Égypte) | -27.2 |
| [1798] 8. Mamālīk | -21.6 |
| [1799] 7. France (Hollande) | -9.8 |
| [1799] 7. UK, Russia (Helder) | 11.6 |
| [1799] 7. Österreich (Schwaben) | 9.8 |
| [1799] 9. France (Italie) | -17.1 |
| [1799] 9. France (Rhin) | -12.1 |
| [1799] 9. Österreich (Italien) | 2.6 |
| [1800] 8. Osmanlı, UK | 7.5 |
| [1804] 7. Irānshahr | -3.1 |
| [1804] 8. Rossiya (Kavkaz, Dunau) | -16.3 |
| [1805] 11. France (Allemagne) | -7.5 |
| [1805] 6. France (Tyrol) | 11.1 |
| [1805] 8. Österreich | 10.5 |
| [1805] 9. Rossiya, Österreich | 1.9 |
| [1806] 10. Preußen | -10.0 |
| [1806] 12. France (Prusse) | -26.1 |
| [1806] 9. Osmanlı | -11.2 |
| [1807] 9. Rossiya (Polsha) | 8.1 |
| [1808] 7. Rossiya (Finlyandiya) | 6.1 |
| [1808] 7. Sverige (Finska) | -4.5 |
| [1809] 10. France (Autriche) | -13.8 |
| [1809] 10. France (Espagne) | -20.6 |
| [1809] 10. UK, España, Portugal | -1.4 |
| [1809] 10. Österreich | -5.0 |
| [1809] 6. UK (Walcheren) | 22.0 |
| [1809] 7. Polska, sojusznicy | -10.2 |
| [1809] 8. Österreich (Tyrol) | 23.0 |
| [1809] 9. España | -1.1 |
| [1811] 7. España | 4.8 |
| [1811] 8. France (Espagne) | -1.2 |
| [1811] 9. UK, Portugal | -4.5 |
| [1812] 10. Rossiya | -14.7 |
| [1812] 11. France (Russie-Centre) | -14.9 |
| [1812] 6. France (Russie-Nord) | 12.6 |
| [1812] 7. France (Russie-Sud) | 5.4 |
| [1812] 7. UK (USA) | -11.8 |
| [1812] 7. United States | 17.0 |
| [1812] 8. Russkiy narod | -13.2 |
| [1814] 8. France | -8.0 |
| [1814] 8. Preußen (Frankreich) | 13.9 |
| [1814] 8. Österreich (Frankreich) | -1.9 |
| [1814] 9. Rossiya (Frantsiya) | -9.8 |
| [1815] 6. Napoli | 13.3 |
| [1815] 6. Österreich (Italien) | 22.5 |
| [1815] 7. Preußen (Flandern) | 10.8 |
| [1815] 9. France (Flandres) | -7.0 |
| [1815] 9. UK, Nederlanden | -2.8 |

#### Army × type multiplier table (118 non-blank cells; blank = 1)

| army | art_foot | art_horse | cav_heavy | cav_lance | cav_light | cav_stand | inf_grena | inf_light | inf_line | inf_milit | staff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7. Danmark |  |  | 0.929 |  |  |  | 0.881 |  | 0.928 |  |  |
| 8. Piemonte-Sardegna (1796) |  |  |  |  |  | 1.116 |  | 0.866 |  |  |  |
| 9. Heiliges Römisches Reich |  |  | 1.189 |  | 1.151 |  | 1.110 |  | 1.125 |  |  |
| [1798] 8. Mamālīk |  |  |  |  | 0.918 |  |  |  |  |  |  |
| [1799] 7. France (Hollande) |  |  |  |  |  |  | 0.902 |  |  |  |  |
| [1799] 7. UK, Russia (Helder) |  |  |  |  |  |  |  |  | 1.119 |  |  |
| [1799] 7. Österreich (Schwaben) |  |  | 0.940 |  | 0.942 |  |  |  | 1.081 |  |  |
| [1799] 9. France (Rhin) |  |  | 1.049 |  |  |  |  |  | 1.084 |  |  |
| [1799] 9. Österreich (Italien) |  |  |  | 0.899 |  |  |  |  | 1.073 |  |  |
| [1800] 8. Osmanlı, UK |  |  | 1.078 |  |  |  |  |  |  |  |  |
| [1804] 7. Irānshahr |  |  | 1.075 |  |  |  |  |  |  |  |  |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  |  |  | 1.051 |  |  |  | 0.805 | 0.914 |  |  |
| [1805] 11. France (Allemagne) |  |  |  |  |  |  |  |  | 0.909 |  |  |
| [1805] 6. France (Tyrol) |  |  | 1.052 |  | 1.046 | 0.883 | 0.929 | 0.917 |  |  |  |
| [1805] 8. Österreich |  |  |  |  | 0.927 |  | 1.021 |  |  |  |  |
| [1805] 9. Rossiya, Österreich |  |  | 0.917 |  |  |  | 1.093 |  | 1.049 |  |  |
| [1806] 10. Preußen |  |  |  |  |  | 0.953 | 1.216 |  |  |  |  |
| [1806] 12. France (Prusse) |  | 0.940 | 0.919 |  |  | 0.961 | 0.925 |  | 0.931 |  | 0.934 |
| [1806] 9. Osmanlı | 1.097 |  |  |  |  |  |  |  | 0.913 |  |  |
| [1807] 9. Rossiya (Polsha) | 0.845 |  | 1.036 |  |  |  |  |  | 1.052 |  |  |
| [1808] 7. Rossiya (Finlyandiya) |  |  |  | 0.838 |  |  |  | 0.819 |  |  |  |
| [1808] 7. Sverige (Finska) |  |  |  |  |  |  | 1.107 |  | 1.103 |  |  |
| [1809] 10. France (Autriche) |  |  |  |  |  | 1.041 | 0.917 |  | 0.947 |  |  |
| [1809] 10. France (Espagne) | 0.931 |  |  |  |  | 0.857 |  |  |  |  |  |
| [1809] 10. UK, España, Portugal |  |  | 1.156 |  |  |  |  |  |  |  |  |
| [1809] 10. Österreich |  |  |  |  |  |  | 0.952 |  | 1.066 |  |  |
| [1809] 6. UK (Walcheren) |  |  |  |  | 1.106 |  |  |  | 1.120 |  |  |
| [1809] 7. Polska, sojusznicy |  |  |  | 0.699 |  |  |  |  |  |  |  |
| [1809] 9. España |  |  |  |  |  |  |  | 1.072 | 1.104 |  |  |
| [1811] 7. España |  |  | 1.062 |  | 1.080 |  |  | 1.065 | 1.083 |  |  |
| [1811] 8. France (Espagne) | 0.924 |  |  |  |  | 0.946 |  |  |  |  |  |
| [1811] 9. UK, Portugal |  |  | 1.053 |  |  |  |  | 0.867 | 0.910 |  |  |
| [1812] 10. Rossiya |  |  |  | 1.034 | 1.084 | 0.961 |  | 1.049 |  |  |  |
| [1812] 11. France (Russie-Centre) | 0.788 |  | 0.947 |  |  |  | 0.935 |  |  |  |  |
| [1812] 6. France (Russie-Nord) |  | 0.913 | 1.070 |  | 0.914 |  |  | 0.885 |  |  |  |
| [1812] 7. France (Russie-Sud) |  |  |  |  |  |  |  | 0.908 | 0.931 |  |  |
| [1812] 7. United States |  |  |  |  |  |  |  |  | 0.924 | 0.682 |  |
| [1812] 8. Russkiy narod |  |  |  | 0.852 |  |  |  |  |  |  |  |
| [1814] 8. France | 0.777 |  | 0.869 |  | 1.079 |  |  | 0.828 | 0.908 |  |  |
| [1814] 8. Preußen (Frankreich) | 1.121 |  | 0.925 |  |  |  |  |  |  |  |  |
| [1814] 8. Österreich (Frankreich) |  |  | 0.911 |  | 0.891 |  | 1.102 |  | 1.103 |  |  |
| [1814] 9. Rossiya (Frantsiya) | 1.061 | 1.048 | 0.894 |  | 1.088 |  | 1.110 | 1.066 | 1.087 |  |  |
| [1815] 6. Napoli |  |  |  |  |  |  | 0.922 |  |  |  |  |
| [1815] 6. Österreich (Italien) |  |  |  |  | 1.057 |  |  | 0.897 |  |  |  |
| [1815] 7. Preußen (Flandern) | 0.899 |  |  |  | 0.932 |  |  |  |  |  |  |
| [1815] 9. France (Flandres) |  |  | 0.829 |  |  | 1.033 |  |  | 0.952 |  |  |
| [1815] 9. UK, Nederlanden |  |  | 0.835 |  |  |  |  |  | 1.068 |  |  |
