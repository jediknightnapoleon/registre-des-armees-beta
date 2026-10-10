
### Infantry (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + corps terms + army offset + army×class offset

| term | grenadiers | irregulars | light | line | militia | skirmishers |
|---|---|---|---|---|---|---|
| constant (intercept + class) | +3.638 | +3.137 | +2.971 | +2.994 | +1.199 | +3.411 |
| × log(size) [size = men_raw] | +0.3312 | +0.4880 | +0.2800 | +0.3057 | +0.4087 | +0.6483 |
| × max(0, log(men_raw/150)) | +1.3876 | +1.3876 | +1.3876 | +1.3876 | +1.3876 | +1.3876 |
| × max(0, log(men_raw/200)) | -0.7072 | -0.7072 | -0.7072 | -0.7072 | -0.7072 | -0.7072 |
| × max(0, log(men_raw/260)) | -0.2195 | -0.2195 | -0.2195 | -0.2195 | -0.2195 | -0.2195 |
| × max(0, log(men_raw/340)) | -0.6908 | -0.6908 | -0.6908 | -0.6908 | -0.6908 | -0.6908 |
| × accuracy | -0.0075 | -0.0075 | -0.0075 | -0.0075 | -0.0075 | -0.0075 |
| × log(1+accuracy) | +0.4625 | +0.5021 | +0.5022 | +0.3515 | +0.5500 | +0.4548 |
| × reload_skill | +0.0053 | +0.0053 | +0.0053 | +0.0053 | +0.0053 | +0.0053 |
| × log(1+reload_skill) | -0.0970 | -0.0797 | +0.0567 | -0.0196 | +0.0364 | -0.1432 |
| × ammo | +0.0004 | +0.0004 | +0.0004 | +0.0004 | +0.0004 | +0.0004 |
| × log(1+ammo) | -0.0306 | -0.0727 | -0.0083 | -0.0310 | -0.1564 | -0.0412 |
| × morale | +0.0475 | +0.0475 | +0.0475 | +0.0475 | +0.0475 | +0.0475 |
| × log(1+morale) | -0.1277 | -0.0562 | -0.1231 | -0.0343 | +0.0950 | -0.1668 |
| × melee_attack | -0.0020 | -0.0020 | -0.0020 | -0.0020 | -0.0020 | -0.0020 |
| × log(1+melee_attack) | +0.3713 | +0.3265 | +0.3974 | +0.4701 | +0.7274 | +0.1467 |
| × melee_defense | -0.0205 | -0.0205 | -0.0205 | -0.0205 | -0.0205 | -0.0205 |
| × log(1+melee_defense) | +0.3177 | +0.1889 | +0.1741 | +0.2710 | +0.1568 | +0.2724 |
| × charge_bonus | -0.0084 | -0.0084 | -0.0084 | -0.0084 | -0.0084 | -0.0084 |
| × log(1+charge_bonus) | +0.1975 | +0.1096 | +0.2577 | +0.3207 | +0.4018 | +0.0694 |
| if can_form_square | +0.122 | +0.122 | +0.122 | +0.122 | +0.122 | +0.122 |
| if has_stamina | +0.089 | +0.089 | +0.089 | +0.089 | +0.089 | +0.089 |
| if is_shock_resistant | +0.096 | +0.096 | +0.096 | +0.096 | +0.096 | +0.096 |
| if can_inspire | +0.082 | +0.082 | +0.082 | +0.082 | +0.082 | +0.082 |
| if has_guerrilla_deployment | +0.497 | +0.497 | +0.497 | +0.497 | +0.497 | +0.497 |
| if can_place_stakes | +0.105 | +0.105 | +0.105 | +0.105 | +0.105 | +0.105 |
| if can_place_mines | -0.090 | -0.090 | -0.090 | -0.090 | -0.090 | -0.090 |
| if scares_enemies | -0.110 | -0.110 | -0.110 | -0.110 | -0.110 | -0.110 |
| if can_build_barricades | -0.052 | -0.052 | -0.052 | -0.052 | -0.052 | -0.052 |
| if skirmish | -1.010 | -1.010 | -1.010 | -1.010 | -1.010 | -1.010 |
| if guard_mode | -0.005 | -0.005 | -0.005 | -0.005 | -0.005 | -0.005 |
| if can_snipe | +0.519 | +0.519 | +0.519 | +0.519 | +0.519 | +0.519 |
| if pike_square | +0.032 | +0.032 | +0.032 | +0.032 | +0.032 | +0.032 |

Training level: poorly_trained -0.012, mob -0.008, well_trained +0.004, trained +0.007, elite +0.009

Speed code: G1 -0.019, G2 -0.128, G3 -0.052, G4 +0.039, G5 +0.132, G6 +0.229, GS1 -0.391, GS2 -0.131, GS3 +0.134, L1 -0.322, L2 -0.172, L3 -0.059, L4 +0.009, L5 +0.091, L6 +0.138, S1 -0.131, S2 +0.159, S3 +0.473

Army terms: × log(corps_number) -0.9166; if empire -0.037; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.


### Cavalry (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + corps terms + army offset + army×class offset

| term | heavy | lancers | light | missile | standard |
|---|---|---|---|---|---|
| constant (intercept + class) | +5.373 | +5.547 | +5.791 | +5.771 | +5.362 |
| × log(size) [size = men_raw] | +0.1563 | +0.1289 | +0.0908 | +0.1274 | +0.1285 |
| × max(0, log(men_raw/100)) | +0.7779 | +0.7779 | +0.7779 | +0.7779 | +0.7779 |
| × max(0, log(men_raw/130)) | -0.4656 | -0.4656 | -0.4656 | -0.4656 | -0.4656 |
| × max(0, log(men_raw/170)) | +0.2203 | +0.2203 | +0.2203 | +0.2203 | +0.2203 |
| × max(0, log(men_raw/230)) | -0.1673 | -0.1673 | -0.1673 | -0.1673 | -0.1673 |
| × accuracy | +0.0303 | +0.0303 | +0.0303 | +0.0303 | +0.0303 |
| × log(1+accuracy) | -0.5007 | -0.5007 | -0.5146 | -0.4938 | -0.4939 |
| × reload_skill | +0.0012 | +0.0012 | +0.0012 | +0.0012 | +0.0012 |
| × log(1+reload_skill) | -0.0421 | -0.0421 | -0.0545 | -0.0352 | -0.0367 |
| × ammo | -0.0206 | -0.0206 | -0.0206 | -0.0206 | -0.0206 |
| × log(1+ammo) | +0.5139 | +0.5139 | +0.5188 | +0.5016 | +0.5216 |
| × morale | +0.0033 | +0.0033 | +0.0033 | +0.0033 | +0.0033 |
| × log(1+morale) | +0.3181 | +0.3096 | +0.2527 | +0.2833 | +0.3190 |
| × melee_attack | -0.0233 | -0.0233 | -0.0233 | -0.0233 | -0.0233 |
| × log(1+melee_attack) | +0.4064 | +0.4193 | +0.4449 | +0.4191 | +0.4568 |
| × melee_defense | +0.0036 | +0.0036 | +0.0036 | +0.0036 | +0.0036 |
| × log(1+melee_defense) | +0.0303 | -0.0163 | +0.0591 | +0.0020 | +0.0306 |
| × charge_bonus | -0.0119 | -0.0119 | -0.0119 | -0.0119 | -0.0119 |
| × log(1+charge_bonus) | +0.3105 | +0.2738 | +0.2372 | +0.2670 | +0.2393 |
| if has_stamina | +0.231 | +0.231 | +0.231 | +0.231 | +0.231 |
| if is_shock_resistant | +0.302 | +0.302 | +0.302 | +0.302 | +0.302 |
| if can_inspire | +0.135 | +0.135 | +0.135 | +0.135 | +0.135 |
| if has_guerrilla_deployment | +0.285 | +0.285 | +0.285 | +0.285 | +0.285 |
| if skirmish | -0.137 | -0.137 | -0.137 | -0.137 | -0.137 |

Training level: mob -0.033, elite -0.000, well_trained +0.003, poorly_trained +0.015, trained +0.015

Speed code: C1 -0.005, C2 +0.011, C3 +0.072, C4 +0.066, C5 +0.117, L1 -0.262

Army terms: × log(corps_number) -0.9647; if empire -0.056; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.


### Artillery (M1)

log(price) = **constant(class)** + size terms + stat terms + ability terms + training + speed + gun table + calibre terms + corps terms + army offset + army×class offset

| term | foot | horse |
|---|---|---|
| constant (intercept + class) | +4.358 | +4.893 |
| × log(size) [size = guns] | +1.2094 | +1.2520 |
| × accuracy | +0.0090 | +0.0090 |
| × log(1+accuracy) | -0.1591 | -0.1996 |
| × reload_skill | +0.0037 | +0.0037 |
| × log(1+reload_skill) | -0.0099 | -0.0352 |
| × morale | +0.0288 | +0.0288 |
| × log(1+morale) | -0.0547 | -0.0173 |
| × melee_attack | -0.0026 | -0.0026 |
| × log(1+melee_attack) | +0.1055 | +0.0903 |
| × melee_defense | -0.0791 | -0.0791 |
| × log(1+melee_defense) | +0.4462 | +0.4635 |
| × charge_bonus | +0.0852 | +0.0852 |
| × log(1+charge_bonus) | -0.1470 | -0.1355 |
| if has_stamina | +0.141 | +0.141 |
| if can_inspire | +0.188 | +0.188 |
| if has_guerrilla_deployment | +0.274 | +0.274 |

Training level: elite -0.045, poorly_trained +0.012, trained +0.015, well_trained +0.019

Speed code: F1 -0.289, F2 -0.273, F3 -0.169, F4 +0.031, F5 +0.253, F6 +0.447, H1 -0.257, H2 -0.026, H3 +0.283

Gun-count table (add; 3 guns = 0; 5 = 5 or more): 1 guns -0.900, 2 guns -0.142, 4 guns +0.060, 5 guns +0.124

Projectile table: 2_pounder -0.078, howitzer_7_pounder shell -0.070, unicorn_20_pounder shell -0.066, 6_pounder -0.048, 3_pounder -0.043, howitzer_6_In shell -0.022, 18_pounder -0.021, 10_pounder -0.017, 64_pounder -0.010, 8_pounder -0.003, 24_pounder +0.008, 9_pounder +0.035, 12_pounder +0.044, howitzer_5_In shell +0.059, 4_pounder +0.065, 5_pounder +0.070, unicorn_10_pounder shell +0.097

Calibre/ballistics: × log(projectile_damage) +0.2627; if howitzer/unicorn shell -1.004; × log(range) -0.5034; × log(projectile_reload_time) +1.3880

Army terms: × log(corps_number) -0.9427; if empire -0.046; plus the army offset (out/army_offsets_M1.csv) and army×class offset (out/army_class_offsets_M1.csv), both 0 for an army not in the tables.

