## Model 18b

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -9.00699 |  |
| `log_men` | ln(men_raw) | 1.97036 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00601819 | [6, 82] |
| `reload_skill` | reload_skill | 0.00449786 | [14, 100] |
| `morale` | morale | 0.0255631 | [2, 12] |
| `melee_defense` | melee_defense | -0.299491 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.397624 | [0, 2] |
| `range0` | range | 0.000935405 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0284301 | [17, 80] |
| `speed_num` | speed digit | 0.182431 | [0, 6] |
| `guns0` | guns | 0.00495475 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.162982 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.359078 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 1.51372 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.623118 | [0, 1.099] |
| `men_raw` | men_raw | -0.00690932 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.145905 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.77476 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.6922 |  |
| `log_men` | ln(men_raw) | 2.49021 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00677493 | [29, 85] |
| `reload_skill` | reload_skill | 0.00350881 | [35, 100] |
| `morale` | morale | 0.105346 | [5, 14] |
| `range0` | range | 0.00175334 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0130918 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.177443 | [14, 40] |
| `speed_num` | speed digit | 0.369444 | [1, 3] |
| `guns0` | guns | -0.173743 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.198311 |  |
| `can_inspire` | [can_inspire] | 0.147636 |  |
| `log_morale` | ln(1 + morale) | -0.541942 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | -0.235722 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.785344 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.51031 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000392095 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | -0.00177098 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | -0.0093687 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0622666 |  |
| `log_men^2` | ln(men_raw)² | 0.0118726 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.00107076 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0272127 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.11088 |  |
| `log_men` | ln(men_raw) | 0.501636 | [4.382, 5.823] |
| `train` | training code | -0.0243417 | [1, 4] |
| `morale` | morale | 0.0138456 | [7, 18] |
| `melee_attack` | melee_attack | -0.0556155 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0148223 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.17748 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.347816 |  |
| `can_inspire` | [can_inspire] | 0.174095 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.26726 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.87845 |  |
| `log_men` | ln(men_raw) | 0.626269 | [4.357, 5.656] |
| `morale` | morale | 0.0379023 | [4, 16] |
| `melee_defense` | melee_defense | -0.0166631 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0628353 | [1, 9] |
| `rank_depth` | rank_depth | -0.0221961 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.271802 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.28526 |  |
| `can_inspire` | [can_inspire] | 0.0733272 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.0153958 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.0812534 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.279404 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.48379 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00321456 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.12925 |  |
| `log_men` | ln(men_raw) | 0.543125 | [4.331, 5.886] |
| `accuracy` | accuracy | -0.0025818 | [0, 34] |
| `reload_skill` | reload_skill | -0.00591457 | [0, 90] |
| `morale` | morale | -0.0241045 | [3, 15] |
| `melee_defense` | melee_defense | -0.0247168 | [3, 23] |
| `range0` | range | 0.0148769 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.265411 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.302081 |  |
| `can_inspire` | [can_inspire] | 0.185349 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.486275 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.236531 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.00771229 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.560697 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.52787 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.167366 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00414766 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.441049 |  |
| `log_men` | ln(men_raw) | 0.615718 | [4.357, 5.781] |
| `morale` | morale | 0.0251215 | [6, 13] |
| `melee_attack` | melee_attack | -0.0262528 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0326373 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.193197 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.343363 |  |
| `log_morale` | ln(1 + morale) | 0.684141 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.49187 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.00913928 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00549096 | [5, 9] |
| `morale^2` | morale² | -0.00295545 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -0.788416 |  |
| `log_men` | ln(men_raw) | 1.7923 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.12107 | [9, 30] |
| `reload_skill` | reload_skill | 0.0040976 | [4, 99] |
| `morale` | morale | 0.032565 | [4, 18] |
| `melee_attack` | melee_attack | 0.145528 | [12, 25] |
| `melee_defense` | melee_defense | -0.0467862 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.0302549 | [16, 33] |
| `range0` | range | -0.00112692 | [70, 100] |
| `projectile_damage0` | projectile_damage | 16.0271 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0625854 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.10382 |  |
| `has_stamina` | [has_stamina] | 0.109379 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.106238 |  |
| `can_inspire` | [can_inspire] | 0.151308 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.3391 |  |
| `can_place_stakes` | [can_place_stakes] | 0.171014 |  |
| `can_build_barricades` | [can_build_barricades] | 0.090112 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.233312 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -2.25338 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.53637 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.14658 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.00606171 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -26.0187 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0100855 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.00325336 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0340685 | [44.35, 168] |
| `morale^2` | morale² | 0.00154925 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00153607 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | 0.241062 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | -0.0105067 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -10.0068 |  |
| `log_men` | ln(men_raw) | 2.72567 | [4.868, 6.114] |
| `train` | training code | 0.00898084 | [1, 4] |
| `reload_skill` | reload_skill | -0.0368356 | [23, 101] |
| `ammo` | ammo | 6.23052e-05 | [15, 70] |
| `melee_attack` | melee_attack | 0.0537663 | [6, 19] |
| `charge_bonus` | charge_bonus | 0.0144746 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0268844 | [14, 20] |
| `speed_num` | speed digit | 0.0509128 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.148745 |  |
| `has_stamina` | [has_stamina] | 0.171406 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0962547 |  |
| `can_inspire` | [can_inspire] | 0.105579 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.580442 |  |
| `guard_mode` | [guard_mode] | 0.0363437 |  |
| `pike_square` | [pike_square] | 0.0167913 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.565259 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.204284 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.00432383 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.153121 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.00819515 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.971334 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00723892 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.101118 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0767339 |  |
| `speed_code=L3` | [speed_code = L3] | -0.139579 |  |
| `speed_code=L4` | [speed_code = L4] | 0.00550103 |  |
| `speed_code=L5` | [speed_code = L5] | 0.0392352 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0548169 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.00459154 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | 3.43369e-05 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -12.5731 |  |
| `log_men` | ln(men_raw) | 2.50528 | [4.852, 6.114] |
| `ammo` | ammo | 0.00347259 | [25, 70] |
| `morale` | morale | -0.00364967 | [0, 16] |
| `melee_attack` | melee_attack | 0.026238 | [6, 23] |
| `melee_defense` | melee_defense | -0.00187069 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0647362 | [9, 30] |
| `projectile_damage0` | projectile_damage | -1.78864 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0613025 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.129106 |  |
| `has_stamina` | [has_stamina] | 0.0900882 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0909956 |  |
| `can_inspire` | [can_inspire] | 0.117947 |  |
| `can_place_stakes` | [can_place_stakes] | 0.281813 |  |
| `pike_square` | [pike_square] | 0.0233529 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.205956 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.192494 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.17 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.185118 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0979257 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.52313 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00620888 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.723374 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0237962 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00233937 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000417565 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.83855 |  |
| `log_men` | ln(men_raw) | 1.3468 | [4.852, 6.881] |
| `train` | training code | -0.0015035 | [0, 3] |
| `ammo` | ammo | 0.00828755 | [0, 70] |
| `morale` | morale | 0.0892464 | [0, 18] |
| `melee_defense` | melee_defense | 0.0528201 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.120451 | [8, 29] |
| `range0` | range | 0.00648742 | [0, 100] |
| `projectile_damage0` | projectile_damage | 1.6662 | [0, 0.83] |
| `speed_num` | speed digit | 0.154293 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.154176 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0297457 |  |
| `can_inspire` | [can_inspire] | -0.550438 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.483355 |  |
| `can_place_stakes` | [can_place_stakes] | -0.0384188 |  |
| `scares_enemies` | [scares_enemies] | 0.501899 |  |
| `skirmish` | [skirmish] | -1.73539 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.451805 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.12229 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.266034 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | -0.0552399 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.24108 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.323874 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.5935 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00281183 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.763356 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.219789 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.039996 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 6.67375 |  |
| `log_men` | ln(men_raw) | -0.593129 | [3.871, 5.606] |
| `train` | training code | -0.00391688 | [0, 4] |
| `accuracy` | accuracy | 0.0153331 | [15, 38] |
| `morale` | morale | 0.178187 | [3, 13] |
| `melee_attack` | melee_attack | -0.0514934 | [1, 23] |
| `charge_bonus` | charge_bonus | -0.00380718 | [1, 32] |
| `speed_num` | speed digit | 0.312771 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0165651 |  |
| `can_inspire` | [can_inspire] | -0.0311014 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.718611 |  |
| `can_place_stakes` | [can_place_stakes] | 0.128546 |  |
| `guard_mode` | [guard_mode] | -0.0179605 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.0387885 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | 0.00991845 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -1.14465 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.337272 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.00545123 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.0129776 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.00424912 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.1073 |  |
| `log_stars` | ln(command_stars) | 1.39365 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.8865 |
| b0 | -74.97 |
| b1 | -57.38 |
| b2 | -30.24 |
| b3 | 8.432 |
| b4 | 33.17 |
| b5 | 53.3 |
| a_star1 | 0.02126 |
| a_star2 | 0.0424 |
| a_star3 | 0.03695 |
| a_star4 | 0.05957 |
| a_star5 | 0.1216 |
