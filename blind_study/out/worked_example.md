
### 18b: Lineinaya pekhota 'Kexholm' [L3] — [1812] 10. Rossiya (true price 487)
type inf_line, commander=0, stars=0.0, N=10
| term | x | clamped | coef | coef·x |
| --- | ---: | ---: | ---: | ---: |
| const | | | -12.573 | -12.5731 |
| log_men | 5.591 | 5.591 | 2.5053 | 14.0070 |
| ammo | 38 | 38 | 0.0034726 | 0.1320 |
| morale | 11 | 11 | -0.0036497 | -0.0401 |
| melee_attack | 15 | 15 | 0.026238 | 0.3936 |
| melee_defense | 8 | 8 | -0.0018707 | -0.0150 |
| charge_bonus | 23 | 23 | -0.064736 | -1.4889 |
| projectile_damage0 | 0.82 | 0.82 | -1.7886 | -1.4667 |
| speed_num | 3 | 3 | 0.061302 | 0.1839 |
| has_stamina | 1 | 1 | 0.090088 | 0.0901 |
| is_shock_resistant | 1 | 1 | 0.090996 | 0.0910 |
| log_accuracy | 3.091 | 3.091 | 0.20596 | 0.6366 |
| log_reload_skill | 3.871 | 3.871 | 0.19249 | 0.7452 |
| log_ammo | 3.664 | 3.664 | -0.17 | -0.6228 |
| log_morale | 2.485 | 2.485 | -0.18512 | -0.4600 |
| log_melee_defense | 2.197 | 2.197 | 0.097926 | 0.2152 |
| log_charge_bonus | 3.178 | 3.178 | 1.5231 | 4.8406 |
| men_raw | 268 | 268 | -0.0062089 | -1.6640 |
| log_projectile_reload_time0 | 2.89 | 2.89 | 0.72337 | 2.0908 |
| log_men*morale | 61.5 | 61.5 | 0.023796 | 1.4635 |
| morale*accuracy | 231 | 231 | -0.0023394 | -0.5404 |
| accuracy^2 | 441 | 441 | 0.00041757 | 0.1841 |

sum z = 6.2025; army×type multiplier = 1.000
regular price = exp(z) × multiplier × 10/N = 494.0 × 1.000 × 10/10 = 494.0
model prediction 494.0

### 18b: Friedrich Carl zu Hohenlohe-Ingelfingen (Chevaulegers Nr. 31 'La Tour') [C4] — 9. Heiliges Römisches Reich (true price 1368)
type cav_light, commander=1, stars=2.0, N=9
| term | x | clamped | coef | coef·x |
| --- | ---: | ---: | ---: | ---: |
| const | | | 1.1292 | 1.1292 |
| log_men | 5.226 | 5.226 | 0.54312 | 2.8382 |
| morale | 14 | 14 | -0.024105 | -0.3375 |
| melee_defense | 17 | 17 | -0.024717 | -0.4202 |
| has_stamina | 1 | 1 | 0.26541 | 0.2654 |
| is_shock_resistant | 1 | 1 | 0.30208 | 0.3021 |
| log_morale | 2.708 | 2.708 | 0.5607 | 1.5184 |
| log_melee_defense | 2.89 | 2.89 | 0.52787 | 1.5257 |
| log_charge_bonus | 1.792 | 1.792 | 0.16737 | 0.2999 |
| close_formation_spacing_vertical | 6 | 6 | -0.0041477 | -0.0249 |

sum z = 7.0965; army×type multiplier = 1.000
regular price = exp(z) × multiplier × 10/N = 1207.7 × 1.000 × 10/9 = 1341.9
commander price = max(1, a·p_reg + (b2 + p_army)·10/N) = max(1, 0.9289×1341.9 + -30.2×10/9) = 1212.8
model prediction 1212.8

### 13c: Lineinaya pekhota 'Kexholm' [L3] — [1812] 10. Rossiya (true price 487)
type inf_line, commander=0, stars=0.0, N=10
| term | x | clamped | coef | coef·x |
| --- | ---: | ---: | ---: | ---: |
| const | | | -10.817 | -10.8174 |
| log_men | 5.591 | 5.591 | 2.3455 | 13.1134 |
| ammo | 38 | 38 | 0.003574 | 0.1358 |
| morale | 11 | 11 | -0.020273 | -0.2230 |
| melee_attack | 15 | 15 | 0.030699 | 0.4605 |
| melee_defense | 8 | 8 | -0.013725 | -0.1098 |
| charge_bonus | 23 | 23 | -0.052408 | -1.2054 |
| projectile_damage0 | 0.82 | 0.82 | 0.090755 | 0.0744 |
| speed_num | 3 | 3 | 0.073534 | 0.2206 |
| has_stamina | 1 | 1 | 0.097337 | 0.0973 |
| is_shock_resistant | 1 | 1 | 0.084955 | 0.0850 |
| log_accuracy | 3.091 | 3.091 | -0.0074909 | -0.0232 |
| log_reload_skill | 3.871 | 3.871 | 0.22365 | 0.8658 |
| log_ammo | 3.664 | 3.664 | -0.17242 | -0.6317 |
| log_morale | 2.485 | 2.485 | -0.21974 | -0.5460 |
| log_melee_defense | 2.197 | 2.197 | 0.20091 | 0.4414 |
| log_charge_bonus | 3.178 | 3.178 | 1.1977 | 3.8063 |
| men_raw | 268 | 268 | -0.0057542 | -1.5421 |
| log_projectile_reload_time0 | 2.89 | 2.89 | 0.18724 | 0.5412 |
| log_men*morale | 61.5 | 61.5 | 0.02906 | 1.7872 |
| morale*accuracy | 231 | 231 | -0.0027665 | -0.6391 |
| accuracy^2 | 441 | 441 | 0.00067821 | 0.2991 |

sum z = 6.1905; army×type multiplier = 1.016
regular price = exp(z) × multiplier × 10/N = 488.1 × 1.016 × 10/10 = 496.0
model prediction 496.0

### 13c: Friedrich Carl zu Hohenlohe-Ingelfingen (Chevaulegers Nr. 31 'La Tour') [C4] — 9. Heiliges Römisches Reich (true price 1368)
type cav_light, commander=1, stars=2.0, N=9
| term | x | clamped | coef | coef·x |
| --- | ---: | ---: | ---: | ---: |
| const | | | 1.1758 | 1.1758 |
| log_men | 5.226 | 5.226 | 0.56063 | 2.9297 |
| morale | 14 | 14 | -0.022478 | -0.3147 |
| melee_defense | 17 | 17 | -0.01637 | -0.2783 |
| has_stamina | 1 | 1 | 0.23376 | 0.2338 |
| is_shock_resistant | 1 | 1 | 0.28409 | 0.2841 |
| log_morale | 2.708 | 2.708 | 0.54978 | 1.4888 |
| log_melee_defense | 2.89 | 2.89 | 0.43512 | 1.2577 |
| log_charge_bonus | 1.792 | 1.792 | 0.20591 | 0.3689 |
| close_formation_spacing_vertical | 6 | 6 | -0.0058937 | -0.0354 |

sum z = 7.1104; army×type multiplier = 1.138
regular price = exp(z) × multiplier × 10/N = 1224.7 × 1.138 × 10/9 = 1548.7
commander price = max(1, a·p_reg + (b2 + p_army)·10/N) = max(1, 0.9309×1548.7 + -23.9×10/9) = 1415.2
model prediction 1415.2
