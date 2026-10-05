## Model 13c

#### Stage 1, type `art_foot`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.02046 |  |
| `log_men` | ln(men_raw) | 1.81669 | [2.996, 6.174] |
| `accuracy` | accuracy | 0.00659277 | [6, 82] |
| `reload_skill` | reload_skill | 0.00415047 | [14, 100] |
| `morale` | morale | 0.0240201 | [2, 12] |
| `melee_defense` | melee_defense | -0.173334 | [3, 6] |
| `charge_bonus` | charge_bonus | 0.22671 | [0, 2] |
| `range0` | range | 0.000971556 | [280, 1400] |
| `projectile_reload_time0` | projectile_reload_time | -0.0242142 | [17, 80] |
| `speed_num` | speed digit | 0.194696 | [0, 6] |
| `guns0` | guns | 0.0728113 | [1, 12] |
| `can_inspire` | [can_inspire] | 0.212069 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.30008 |  |
| `log_melee_defense` | ln(1 + melee_defense) | 0.848449 | [1.386, 1.946] |
| `log_charge_bonus` | ln(1 + charge_bonus) | -0.340579 | [0, 1.099] |
| `men_raw` | men_raw | -0.00794575 | [20, 480] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.177165 | [2.398, 5.081] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 1.77231 | [2.89, 4.394] |

#### Stage 1, type `art_horse`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -11.8421 |  |
| `log_men` | ln(men_raw) | 2.05799 | [2.485, 4.094] |
| `accuracy` | accuracy | 0.00580704 | [29, 85] |
| `reload_skill` | reload_skill | 0.00372279 | [35, 100] |
| `morale` | morale | 0.0976791 | [5, 14] |
| `range0` | range | 0.00203534 | [250, 600] |
| `projectile_damage0` | projectile_damage | 0.0113838 | [9, 90] |
| `projectile_reload_time0` | projectile_reload_time | -0.15991 | [14, 40] |
| `speed_num` | speed digit | 0.382229 | [1, 3] |
| `guns0` | guns | -0.244221 | [1, 5] |
| `has_stamina` | [has_stamina] | 0.205895 |  |
| `can_inspire` | [can_inspire] | 0.143613 |  |
| `log_morale` | ln(1 + morale) | -0.538554 | [1.792, 2.708] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.27342 | [0.6931, 1.609] |
| `log_guns0` | ln(1 + guns) | -0.112185 | [0.6931, 1.792] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 4.12646 | [2.708, 3.714] |
| `morale*accuracy` | morale × accuracy | -0.000257387 | [175, 1162] |
| `unit_training_level=poorly_trained` | [unit_training_level = poorly_trained] | 0.0168214 |  |
| `unit_training_level=trained` | [unit_training_level = trained] | 0.00308421 |  |
| `unit_training_level=well_trained` | [unit_training_level = well_trained] | -0.0240195 |  |
| `log_men^2` | ln(men_raw)² | 0.0471575 | [6.175, 16.76] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.000590672 | [15, 35] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | -0.0134169 | [2.485, 15.48] |

#### Stage 1, type `cav_heavy`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 0.43985 |  |
| `log_men` | ln(men_raw) | 0.579515 | [4.382, 5.823] |
| `train` | training code | -0.0116897 | [1, 4] |
| `morale` | morale | 0.0221076 | [7, 18] |
| `melee_attack` | melee_attack | -0.0528365 | [11, 27] |
| `charge_bonus` | charge_bonus | 0.0139174 | [5, 19] |
| `has_stamina` | [has_stamina] | 0.159837 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.333071 |  |
| `can_inspire` | [can_inspire] | 0.157611 |  |
| `log_melee_attack` | ln(1 + melee_attack) | 1.3098 | [2.485, 3.332] |

#### Stage 1, type `cav_lance`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.52721 |  |
| `log_men` | ln(men_raw) | 0.624105 | [4.357, 5.656] |
| `morale` | morale | 0.0420773 | [4, 16] |
| `melee_defense` | melee_defense | -0.0362097 | [4, 19] |
| `charge_bonus` | charge_bonus | -0.0724043 | [1, 9] |
| `rank_depth` | rank_depth | -0.0103408 | [6, 16] |
| `has_stamina` | [has_stamina] | 0.256603 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.322324 |  |
| `can_inspire` | [can_inspire] | 0.0800484 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.186302 |  |
| `log_melee_attack` | ln(1 + melee_attack) | -0.114133 | [1.946, 2.944] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.440425 | [1.609, 2.996] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.578031 | [0.6931, 2.303] |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.00311508 | [29.65, 90.9] |

#### Stage 1, type `cav_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 1.17577 |  |
| `log_men` | ln(men_raw) | 0.560629 | [4.331, 5.886] |
| `accuracy` | accuracy | 0.0183169 | [0, 34] |
| `reload_skill` | reload_skill | -0.0068121 | [0, 90] |
| `morale` | morale | -0.0224776 | [3, 15] |
| `melee_defense` | melee_defense | -0.0163701 | [3, 23] |
| `range0` | range | 0.0130256 | [0, 100] |
| `has_stamina` | [has_stamina] | 0.233762 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.284086 |  |
| `can_inspire` | [can_inspire] | 0.127423 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.469323 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.39005 | [0, 3.555] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.0485885 | [0, 4.511] |
| `log_morale` | ln(1 + morale) | 0.549779 | [1.386, 2.773] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.435122 | [1.386, 3.178] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.205906 | [0, 2.197] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | -0.00589368 | [4.5, 14] |

#### Stage 1, type `cav_stand`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -0.86945 |  |
| `log_men` | ln(men_raw) | 0.614151 | [4.357, 5.781] |
| `morale` | morale | 0.0699516 | [6, 13] |
| `melee_attack` | melee_attack | -0.0495852 | [9, 19] |
| `charge_bonus` | charge_bonus | 0.0219665 | [2, 8] |
| `has_stamina` | [has_stamina] | 0.183772 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.341317 |  |
| `log_morale` | ln(1 + morale) | 0.563142 | [1.946, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.962623 | [2.303, 2.996] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.140261 | [2.565, 3.135] |
| `close_formation_spacing_vertical` | close_formation_spacing_vertical | 0.00607603 | [5, 9] |
| `morale^2` | morale² | -0.00458919 | [36, 169] |

#### Stage 1, type `inf_grena`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -1.21904 |  |
| `log_men` | ln(men_raw) | 1.58712 | [4.754, 6.091] |
| `accuracy` | accuracy | -0.0737049 | [9, 30] |
| `reload_skill` | reload_skill | 0.00462618 | [4, 99] |
| `morale` | morale | -0.0873833 | [4, 18] |
| `melee_attack` | melee_attack | 0.138177 | [12, 25] |
| `melee_defense` | melee_defense | -0.00589093 | [6, 18] |
| `charge_bonus` | charge_bonus | -0.00658633 | [16, 33] |
| `range0` | range | 0.0046177 | [70, 100] |
| `projectile_damage0` | projectile_damage | 2.15702 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0883271 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.104251 |  |
| `has_stamina` | [has_stamina] | 0.0925669 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0969054 |  |
| `can_inspire` | [can_inspire] | 0.0894509 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.296646 |  |
| `can_place_stakes` | [can_place_stakes] | 0.06642 |  |
| `can_build_barricades` | [can_build_barricades] | 0.165793 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.328419 | [2.303, 3.434] |
| `log_melee_attack` | ln(1 + melee_attack) | -1.56281 | [2.565, 3.258] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.179358 | [1.946, 2.944] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.319742 | [2.833, 3.526] |
| `men_raw` | men_raw | -0.00503684 | [116, 442] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -3.47814 | [0.392, 0.6043] |
| `log_men*morale` | ln(men_raw) × morale | 0.0317859 | [21.92, 98.65] |
| `morale*accuracy` | morale × accuracy | -0.0025665 | [75, 486] |
| `log_men*accuracy` | ln(men_raw) × accuracy | 0.0228026 | [44.35, 168] |
| `morale^2` | morale² | 0.00295442 | [16, 324] |
| `morale*melee_attack` | morale × melee_attack | -0.00357443 | [48, 450] |
| `unit_drill_set=drill_set_infantry_light` | [unit_drill_set = drill_set_infantry_light] | -0.0674352 |  |
| `unit_drill_set=drill_set_infantry_line` | [unit_drill_set = drill_set_infantry_line] | -0.00381048 |  |

#### Stage 1, type `inf_light`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -9.59494 |  |
| `log_men` | ln(men_raw) | 2.38628 | [4.868, 6.114] |
| `train` | training code | 0.00370441 | [1, 4] |
| `reload_skill` | reload_skill | -0.0193203 | [23, 101] |
| `ammo` | ammo | -0.000781809 | [15, 70] |
| `melee_attack` | melee_attack | -0.0606724 | [6, 19] |
| `charge_bonus` | charge_bonus | -0.0262883 | [10, 26] |
| `projectile_reload_time0` | projectile_reload_time | 0.0179023 | [14, 20] |
| `speed_num` | speed digit | 0.0476093 | [3, 6] |
| `can_form_square` | [can_form_square] | 0.146471 |  |
| `has_stamina` | [has_stamina] | 0.105235 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0950384 |  |
| `can_inspire` | [can_inspire] | 0.0992868 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.530077 |  |
| `guard_mode` | [guard_mode] | 0.0550139 |  |
| `pike_square` | [pike_square] | 0.0238322 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.278309 | [2.89, 3.434] |
| `log_morale` | ln(1 + morale) | 0.182951 | [0, 2.639] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.068573 | [0.6931, 2.565] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 0.535508 | [2.398, 3.296] |
| `men_raw` | men_raw | -0.0070115 | [130, 452] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | 0.543036 | [0.5766, 0.6043] |
| `log_men*reload_skill` | ln(men_raw) × reload_skill | 0.00460842 | [130.1, 566.9] |
| `speed_code=G5` | [speed_code = G5] | 0.0795356 |  |
| `speed_code=G6` | [speed_code = G6] | 0.0516237 |  |
| `speed_code=L3` | [speed_code = L3] | -0.0689601 |  |
| `speed_code=L4` | [speed_code = L4] | -0.00254232 |  |
| `speed_code=L5` | [speed_code = L5] | 0.044352 |  |
| `speed_code=L6` | [speed_code = L6] | 0.0522945 |  |
| `log_men*melee_attack` | ln(men_raw) × melee_attack | 0.0126233 | [34.87, 99.29] |
| `melee_attack^2` | melee_attack² | 0.000978336 | [36, 361] |

#### Stage 1, type `inf_line`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -10.8174 |  |
| `log_men` | ln(men_raw) | 2.34546 | [4.852, 6.114] |
| `ammo` | ammo | 0.00357398 | [25, 70] |
| `morale` | morale | -0.0202729 | [0, 16] |
| `melee_attack` | melee_attack | 0.030699 | [6, 23] |
| `melee_defense` | melee_defense | -0.013725 | [1, 15] |
| `charge_bonus` | charge_bonus | -0.0524078 | [9, 30] |
| `projectile_damage0` | projectile_damage | 0.090755 | [0.48, 0.83] |
| `speed_num` | speed digit | 0.0735342 | [1, 5] |
| `can_form_square` | [can_form_square] | 0.130494 |  |
| `has_stamina` | [has_stamina] | 0.0973369 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0849549 |  |
| `can_inspire` | [can_inspire] | 0.0903833 |  |
| `can_place_stakes` | [can_place_stakes] | 0.234749 |  |
| `pike_square` | [pike_square] | 0.0245962 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.00749093 | [2.398, 3.434] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.223655 | [2.303, 4.575] |
| `log_ammo` | ln(1 + ammo) | -0.172419 | [3.258, 4.263] |
| `log_morale` | ln(1 + morale) | -0.219739 | [0, 2.833] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.200912 | [0.6931, 2.773] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.19767 | [2.303, 3.434] |
| `men_raw` | men_raw | -0.00575423 | [128, 452] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | 0.18724 | [2.708, 3.045] |
| `log_men*morale` | ln(men_raw) × morale | 0.0290598 | [0, 91.47] |
| `morale*accuracy` | morale × accuracy | -0.00276654 | [0, 464] |
| `accuracy^2` | accuracy² | 0.000678208 | [100, 900] |

#### Stage 1, type `inf_milit`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | -8.00781 |  |
| `log_men` | ln(men_raw) | 1.252 | [4.852, 6.881] |
| `train` | training code | -0.0156601 | [0, 3] |
| `ammo` | ammo | 0.0070707 | [0, 70] |
| `morale` | morale | 0.0538464 | [0, 18] |
| `melee_defense` | melee_defense | 0.0400157 | [0, 9] |
| `charge_bonus` | charge_bonus | -0.0981182 | [8, 29] |
| `range0` | range | 0.0084037 | [0, 100] |
| `projectile_damage0` | projectile_damage | 0.611061 | [0, 0.83] |
| `speed_num` | speed digit | 0.15691 | [1, 6] |
| `can_form_square` | [can_form_square] | 0.149264 |  |
| `is_shock_resistant` | [is_shock_resistant] | 0.0761999 |  |
| `can_inspire` | [can_inspire] | -0.429865 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.394447 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0891018 |  |
| `scares_enemies` | [scares_enemies] | 0.440117 |  |
| `skirmish` | [skirmish] | -1.20382 |  |
| `log_accuracy` | ln(1 + accuracy) | 0.429669 | [0, 3.401] |
| `log_reload_skill` | ln(1 + reload_skill) | 0.145347 | [0, 4.304] |
| `log_ammo` | ln(1 + ammo) | -0.23588 | [0, 4.263] |
| `log_morale` | ln(1 + morale) | 0.134276 | [0, 2.944] |
| `log_melee_attack` | ln(1 + melee_attack) | 1.06597 | [1.792, 3.135] |
| `log_melee_defense` | ln(1 + melee_defense) | -0.209037 | [0, 2.303] |
| `log_charge_bonus` | ln(1 + charge_bonus) | 1.35794 | [2.197, 3.401] |
| `men_raw` | men_raw | -0.00260315 | [128, 974] |
| `log_projectile_damage0` | ln(1 + projectile_damage) | -0.671394 | [0, 0.6043] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.217308 | [0, 3.045] |
| `log_men^2` | ln(men_raw)² | 0.0439756 | [23.54, 47.35] |

#### Stage 1, type `inf_skirm`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 7.65785 |  |
| `log_men` | ln(men_raw) | -0.59354 | [3.871, 5.606] |
| `train` | training code | 0.0130085 | [0, 4] |
| `accuracy` | accuracy | 0.0295479 | [15, 38] |
| `morale` | morale | 0.1369 | [3, 13] |
| `melee_attack` | melee_attack | -0.00200332 | [1, 23] |
| `charge_bonus` | charge_bonus | -0.026045 | [1, 32] |
| `speed_num` | speed digit | 0.332827 | [1, 3] |
| `has_stamina` | [has_stamina] | -0.0701637 |  |
| `can_inspire` | [can_inspire] | -0.0217118 |  |
| `has_guerrilla_deployment` | [has_guerrilla_deployment] | 0.699408 |  |
| `can_place_stakes` | [can_place_stakes] | 0.0945971 |  |
| `guard_mode` | [guard_mode] | 0.0426935 |  |
| `log_accuracy` | ln(1 + accuracy) | -0.551845 | [2.773, 3.664] |
| `log_ammo` | ln(1 + ammo) | -0.00254475 | [2.398, 4.19] |
| `log_morale` | ln(1 + morale) | -0.796999 | [1.386, 2.639] |
| `log_melee_attack` | ln(1 + melee_attack) | 0.234947 | [0.6931, 3.178] |
| `log_melee_defense` | ln(1 + melee_defense) | 0.0386154 | [0.6931, 2.565] |
| `men_raw` | men_raw | 0.0128665 | [48, 272] |
| `log_projectile_reload_time0` | ln(1 + projectile_reload_time) | -0.0313132 | [2.833, 3.611] |

#### Stage 1, type `staff`

| term | x | coefficient | clamp x to |
| --- | --- | ---: | --- |
| `const` | intercept | 4.10295 |  |
| `log_stars` | ln(command_stars) | 1.3985 | [0, 2.197] |

#### Commander stage

| coefficient | value |
| --- | ---: |
| a | 0.8989 |
| b0 | -81.44 |
| b1 | -58.71 |
| b2 | -35.42 |
| b3 | -17.49 |
| b4 | -1.301 |
| b5 | 39.16 |
| a_star1 | 0.01207 |
| a_star2 | 0.03208 |
| a_star3 | 0.06592 |
| a_star4 | 0.09 |
| a_star5 | 0.1228 |

Per-army commander premium `p_army` (gold, before dividing by N/10):

| army | p_army |
| --- | ---: |
| 7. Danmark | -13.4 |
| 8. Piemonte-Sardegna (1796) | 17.4 |
| 8. UK (Spain, 1808) | 12.8 |
| 9. France (1796) | 4.2 |
| 9. Heiliges Römisches Reich | 11.6 |
| [1798] 5. France (Irlande) | -5.9 |
| [1798] 5. UK (Ireland) | 27.2 |
| [1798] 8. France (Égypte) | -10.2 |
| [1798] 8. Mamālīk | -8.8 |
| [1799] 7. France (Hollande) | -1.2 |
| [1799] 7. UK, Russia (Helder) | 16.1 |
| [1799] 7. Österreich (Schwaben) | 7.8 |
| [1799] 9. France (Italie) | -3.6 |
| [1799] 9. France (Rhin) | -5.6 |
| [1799] 9. Österreich (Italien) | 0.3 |
| [1800] 8. Osmanlı, UK | 5.8 |
| [1804] 7. Irānshahr | -4.1 |
| [1804] 8. Rossiya (Kavkaz, Dunau) | -10.6 |
| [1805] 11. France (Allemagne) | -7.0 |
| [1805] 6. France (Tyrol) | 15.2 |
| [1805] 8. Österreich | 3.6 |
| [1805] 9. Rossiya, Österreich | -7.5 |
| [1806] 10. Preußen | -12.5 |
| [1806] 12. France (Prusse) | -19.3 |
| [1806] 9. Osmanlı | -8.5 |
| [1807] 9. Rossiya (Polsha) | -4.2 |
| [1808] 7. Rossiya (Finlyandiya) | -4.1 |
| [1808] 7. Sverige (Finska) | -6.9 |
| [1809] 10. France (Autriche) | -11.1 |
| [1809] 10. France (Espagne) | -17.1 |
| [1809] 10. UK, España, Portugal | 0.8 |
| [1809] 10. Österreich | -5.7 |
| [1809] 6. UK (Walcheren) | 20.7 |
| [1809] 7. Polska, sojusznicy | -0.5 |
| [1809] 8. Österreich (Tyrol) | 15.2 |
| [1809] 9. España | 0.5 |
| [1811] 7. España | 5.5 |
| [1811] 8. France (Espagne) | 0.9 |
| [1811] 9. UK, Portugal | -3.3 |
| [1812] 10. Rossiya | -16.2 |
| [1812] 11. France (Russie-Centre) | -17.6 |
| [1812] 6. France (Russie-Nord) | 12.8 |
| [1812] 7. France (Russie-Sud) | 7.5 |
| [1812] 7. UK (USA) | -9.4 |
| [1812] 7. United States | 11.4 |
| [1812] 8. Russkiy narod | -10.4 |
| [1814] 8. France | -1.7 |
| [1814] 8. Preußen (Frankreich) | 3.5 |
| [1814] 8. Österreich (Frankreich) | -0.7 |
| [1814] 9. Rossiya (Frantsiya) | -7.3 |
| [1815] 6. Napoli | 9.8 |
| [1815] 6. Österreich (Italien) | 14.6 |
| [1815] 7. Preußen (Flandern) | 12.2 |
| [1815] 9. France (Flandres) | -5.4 |
| [1815] 9. UK, Nederlanden | 2.2 |

#### Army × type multiplier table (328 non-blank cells; blank = 1)

| army | art_foot | art_horse | cav_heavy | cav_lance | cav_light | cav_stand | inf_grena | inf_light | inf_line | inf_milit | inf_skirm | staff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7. Danmark |  |  | 0.915 |  | 0.920 | 0.948 | 0.886 | 0.886 | 0.925 |  |  |  |
| 8. Piemonte-Sardegna (1796) |  |  | 0.971 |  |  | 1.111 |  | 0.910 | 1.027 |  |  |  |
| 8. UK (Spain, 1808) |  |  |  |  | 0.977 |  |  | 1.098 | 1.049 |  |  |  |
| 9. France (1796) |  |  | 0.981 |  | 1.030 | 1.031 | 0.888 | 0.968 | 0.915 |  |  |  |
| 9. Heiliges Römisches Reich | 1.144 |  | 1.176 |  | 1.138 |  | 1.112 | 1.093 | 1.131 | 1.088 | 1.130 | 1.132 |
| [1798] 5. France (Irlande) |  | 1.031 |  |  | 1.165 |  |  |  | 0.951 |  | 1.064 |  |
| [1798] 5. UK (Ireland) |  |  |  |  |  |  | 1.056 |  |  |  | 1.070 |  |
| [1798] 8. France (Égypte) |  |  |  |  | 0.968 | 0.924 | 0.900 |  | 0.924 |  |  | 0.937 |
| [1798] 8. Mamālīk |  |  | 1.026 | 0.933 | 0.896 |  |  |  | 0.925 |  | 0.904 |  |
| [1799] 7. France (Hollande) |  |  |  |  | 0.913 |  | 0.921 |  | 0.909 |  |  |  |
| [1799] 7. UK, Russia (Helder) | 0.971 |  |  | 1.055 | 0.936 |  |  | 1.087 | 1.140 |  |  |  |
| [1799] 7. Österreich (Schwaben) |  | 0.978 | 0.922 | 0.911 | 0.926 | 1.051 | 1.024 | 1.099 | 1.082 | 0.895 |  |  |
| [1799] 9. France (Italie) | 0.855 |  |  |  | 0.943 |  | 0.886 |  | 0.904 |  |  | 0.958 |
| [1799] 9. France (Rhin) | 1.026 |  | 1.042 |  | 0.932 | 0.966 | 0.936 |  | 1.026 |  |  |  |
| [1799] 9. Österreich (Italien) | 1.021 | 0.966 |  | 0.880 |  |  | 0.974 | 1.031 | 1.073 |  |  |  |
| [1800] 8. Osmanlı, UK | 0.951 |  | 1.070 |  | 0.973 |  |  | 1.086 | 1.036 |  |  |  |
| [1804] 7. Irānshahr |  |  | 1.059 | 1.075 | 0.915 |  |  |  | 1.028 |  |  |  |
| [1804] 8. Rossiya (Kavkaz, Dunau) |  |  | 1.021 | 1.034 | 0.975 | 0.967 | 0.923 | 0.806 | 0.915 |  |  |  |
| [1805] 11. France (Allemagne) | 0.954 | 0.958 |  |  |  |  | 0.940 |  | 0.864 |  |  | 0.957 |
| [1805] 6. France (Tyrol) | 1.017 |  | 1.039 |  | 1.036 | 0.885 | 0.912 | 0.924 | 0.936 |  |  |  |
| [1805] 8. Österreich |  |  | 0.977 |  | 0.925 |  | 1.015 | 1.102 | 1.049 |  |  |  |
| [1805] 9. Rossiya, Österreich |  |  | 0.895 | 1.042 | 1.033 | 1.050 | 1.099 | 1.027 | 1.050 |  |  |  |
| [1806] 10. Preußen |  | 0.968 | 0.953 |  | 1.039 | 0.956 | 1.234 | 1.071 |  |  |  |  |
| [1806] 12. France (Prusse) | 0.935 | 0.929 | 0.900 |  | 0.964 | 0.965 | 0.907 | 0.952 | 0.885 |  |  | 0.924 |
| [1806] 9. Osmanlı | 1.078 |  |  | 0.908 | 1.046 |  |  |  | 0.969 | 0.909 | 1.187 |  |
| [1807] 9. Rossiya (Polsha) | 0.819 | 1.020 | 1.022 |  | 1.044 |  | 1.077 | 1.109 | 1.052 |  |  |  |
| [1808] 7. Rossiya (Finlyandiya) |  |  | 0.980 | 0.829 | 1.040 | 1.041 |  | 0.843 | 1.033 |  |  |  |
| [1808] 7. Sverige (Finska) | 1.022 |  | 1.032 |  | 0.937 |  | 1.102 | 0.972 | 1.098 |  | 1.077 |  |
| [1809] 10. France (Autriche) |  |  | 0.952 |  |  | 1.039 | 0.906 |  | 0.916 |  |  |  |
| [1809] 10. France (Espagne) | 0.918 |  |  | 1.047 | 1.027 | 0.858 | 0.958 | 0.935 | 0.949 |  | 1.044 |  |
| [1809] 10. UK, España, Portugal | 1.026 |  | 1.158 |  | 1.033 | 1.072 |  |  |  |  |  | 1.365 |
| [1809] 10. Österreich |  |  | 0.968 |  | 0.963 | 1.044 | 0.954 | 1.079 | 1.077 |  |  |  |
| [1809] 6. UK (Walcheren) | 0.914 |  | 1.045 |  | 1.088 |  |  |  | 1.140 |  | 0.912 |  |
| [1809] 7. Polska, sojusznicy |  |  | 0.984 | 0.673 |  | 1.065 | 0.971 | 0.919 | 0.926 |  | 0.941 |  |
| [1809] 8. Österreich (Tyrol) |  |  |  |  | 1.064 |  |  | 1.051 | 1.043 |  | 1.104 |  |
| [1809] 9. España | 0.895 |  | 1.032 |  |  | 1.109 |  | 1.093 | 1.077 | 0.963 |  |  |
| [1811] 7. España | 0.925 |  | 1.064 | 1.053 | 1.073 | 1.050 | 1.062 | 1.091 | 1.058 | 0.949 |  |  |
| [1811] 8. France (Espagne) | 0.915 |  | 1.042 | 1.028 | 0.970 | 0.949 | 0.911 |  | 0.952 |  | 0.949 |  |
| [1811] 9. UK, Portugal |  |  | 1.041 |  | 0.976 | 0.971 | 1.034 | 0.887 | 0.926 |  |  | 0.944 |
| [1812] 10. Rossiya | 0.961 |  | 0.978 | 1.036 | 1.081 | 0.971 | 1.031 | 1.063 | 1.016 |  | 0.951 |  |
| [1812] 11. France (Russie-Centre) | 0.777 |  | 0.932 |  |  |  | 0.937 |  | 0.958 |  | 0.969 |  |
| [1812] 6. France (Russie-Nord) |  | 0.917 | 1.053 | 1.097 | 0.900 | 1.059 | 0.962 | 0.894 | 0.968 |  |  |  |
| [1812] 7. France (Russie-Sud) | 0.982 |  | 1.038 |  | 0.957 | 0.971 |  | 0.917 | 0.924 |  |  |  |
| [1812] 7. UK (USA) | 0.945 |  | 1.027 |  |  |  | 1.058 | 0.948 |  | 1.063 |  |  |
| [1812] 7. United States | 1.034 |  |  |  |  | 1.105 | 1.063 | 1.048 | 0.913 | 0.706 |  |  |
| [1812] 8. Russkiy narod |  | 1.106 |  | 0.840 |  |  |  |  |  | 1.139 | 0.824 |  |
| [1814] 8. France | 0.767 | 0.979 | 0.855 |  | 1.077 | 0.965 | 0.898 | 0.821 | 0.863 | 0.943 | 1.058 |  |
| [1814] 8. Preußen (Frankreich) | 1.117 | 1.015 | 0.916 | 1.019 | 1.024 |  |  |  | 1.060 |  | 1.037 |  |
| [1814] 8. Österreich (Frankreich) |  |  | 0.898 | 1.045 | 0.878 |  | 1.106 | 0.988 | 1.101 |  |  |  |
| [1814] 9. Rossiya (Frantsiya) | 1.039 | 1.050 | 0.882 | 0.968 | 1.076 |  | 1.117 | 1.086 | 1.092 |  |  |  |
| [1815] 6. Napoli |  |  |  | 0.951 |  |  | 0.922 | 1.089 |  |  |  |  |
| [1815] 6. Österreich (Italien) | 1.040 |  | 1.050 | 0.961 | 1.049 |  | 1.048 | 0.925 | 1.020 |  |  |  |
| [1815] 7. Preußen (Flandern) | 0.895 |  |  |  | 0.925 | 0.955 |  | 1.144 |  | 1.026 |  |  |
| [1815] 9. France (Flandres) | 0.969 | 0.955 | 0.817 |  |  | 1.037 |  | 0.982 | 0.904 |  |  |  |
| [1815] 9. UK, Nederlanden |  |  | 0.818 |  | 0.966 |  | 1.078 |  | 1.080 |  | 1.038 |  |
