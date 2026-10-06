# Results log

One row per experiment. CV = grouped 5-fold on `regular_unit_key`, seed 0; all 5 238 rows scored; predictions clipped at >= 1.

| id | model | params | CV MAE | sd | median APE % | notes |
|---|---|---|---|---|---|---|
| B0 | C = P (no change) | 0 | 94.02 | 1.20 | 19.10 |  |
| B00 | C = global median | 1 | 285.06 | 7.28 | 46.88 |  |
| L1ols | C = a P + b [ols] | 2 | 75.37 | 1.31 | 14.87 |  |
| L2ols | C = P(a + c s) + b + d s [ols] | 4 | 34.74 | 1.04 | 5.27 |  |
| L3ols | C = P(a + c s + e s^2) + b + d s + f s^2 [ols] | 6 | 33.97 | 1.09 | 4.84 |  |
| L4ols | per arm: C = P(a + c s) + b + d s [ols] | 12 | 19.17 | 0.29 | 2.65 |  |
| L5ols | star lookup: C = a_s P + b_s (s<=6) [ols] | 14 | 33.76 | 0.85 | 4.71 |  |
| L6ols | arm x star lookup (s<=5): C = a P + b [ols] | 36 | 17.25 | 0.56 | 2.11 |  |
| L1lad | C = a P + b [lad] | 2 | 71.74 | 1.60 | 12.57 |  |
| L2lad | C = P(a + c s) + b + d s [lad] | 4 | 33.89 | 1.61 | 4.98 |  |
| L3lad | C = P(a + c s + e s^2) + b + d s + f s^2 [lad] | 6 | 33.24 | 1.73 | 4.78 |  |
| L4lad | per arm: C = P(a + c s) + b + d s [lad] | 12 | 17.53 | 0.63 | 2.29 |  |
| L5lad | star lookup: C = a_s P + b_s (s<=6) [lad] | 14 | 33.05 | 1.47 | 4.74 |  |
| L6lad | arm x star lookup (s<=5): C = a P + b [lad] | 36 | 15.89 | 0.77 | 1.77 |  |
| D1ols | C = P(a + sum w_k dk) + b [ols] | 8 | 23.53 | 0.68 | 3.69 |  |
| D2ols | C = P(a + sum w_k dk) + b + sum v_k dk [ols] | 14 | 17.29 | 0.64 | 2.13 |  |
| D3ols | arm a,b + P*w dk + v dk [ols] | 18 | 17.61 | 0.80 | 2.19 |  |
| D4ols | per-arm star model L4 + deltas (P*dk, dk) [ols] | 24 | 17.98 | 0.65 | 2.20 |  |
| D5ols | C = P(a + sum w_k dk/reg_k) + b + c s [ols] | 9 | 25.21 | 0.36 | 4.02 |  |
| D6ols | arm a,b + rel deltas (P*, plain) + s [ols] | 19 | 21.63 | 0.87 | 3.23 |  |
| D1lad | C = P(a + sum w_k dk) + b [lad] | 8 | 22.04 | 0.67 | 3.03 |  |
| D2lad | C = P(a + sum w_k dk) + b + sum v_k dk [lad] | 14 | 16.20 | 0.74 | 1.89 |  |
| D3lad | arm a,b + P*w dk + v dk [lad] | 18 | 15.87 | 0.69 | 1.87 |  |
| D4lad | per-arm star model L4 + deltas (P*dk, dk) [lad] | 24 | 15.59 | 0.68 | 1.77 |  |
| D5lad | C = P(a + sum w_k dk/reg_k) + b + c s [lad] | 9 | 21.70 | 1.71 | 2.60 |  |
| D6lad | arm a,b + rel deltas (P*, plain) + s [lad] | 19 | 18.68 | 1.18 | 2.22 |  |
| M1lad | per arm: P(a+cs) + men(g+hs) + b + ds [lad] | 18 | 15.09 | 0.58 | 2.00 |  |
| M2lad | per arm: P(a+cs) + g men + b + ds [lad] | 15 | 15.44 | 0.49 | 2.08 |  |
| M3lad | M1 + per-arm P*(size ratio-1) [lad] | 21 | 13.29 | 0.74 | 1.98 |  |
| M4lad | L4 + per-arm P*(size ratio-1) [lad] | 15 | 15.42 | 0.69 | 2.27 |  |
| M5lad | M3 + per-arm corps, P*corps [lad] | 27 | 12.76 | 0.80 | 1.96 |  |
| M6lad | M3 + per-arm s*corps [lad] | 24 | 12.73 | 0.75 | 1.97 |  |
| E1 | arm a,b + P*(size-1) + men*dk [lad] | 13 | 25.43 | 1.61 | 2.93 |  |
| E2 | arm a,b + P*(size-1) + men*dk + P*dk [lad] | 19 | 13.90 | 0.61 | 1.65 |  |
| E3 | arm a,b + P*(size-1) + men*dk + P*dk + dk [lad] | 25 | 12.55 | 0.80 | 1.49 |  |
| E4 | E2 + corps*dk [lad] | 25 | 13.37 | 0.70 | 1.64 |  |
| E5 | E2 + corps*s + s [lad] | 21 | 11.58 | 0.73 | 1.38 |  |
| E6 | arm a,b + P*(size-1) + men*s*arm + P*s*arm + s*arm + corps*s [lad] | 17 | 14.36 | 0.69 | 2.10 |  |
| F1 | arm a,b + P(size-1) + F*men*dk + P*dk, F=1+lam(corps-9) [lad] | 20 | 13.43 | 0.71 | 1.64 | lam=-0.04 |
| F2 | arm a,b + P(size-1) + F*men*dk + F*dk + P*dk, F=1+lam(corps-9) [lad] | 26 | 11.81 | 0.85 | 1.39 | lam=-0.04 |
| F3 | arm a,b + P(size-1) + F*men*dk + F*dk, F=1+lam(corps-9) [lad] | 20 | 18.59 | 1.05 | 2.33 | lam=-0.02 |
| V1 | C = P + arm consts + V*dk [lad] | 11 | 29.57 | 0.93 | 3.98 | V=army-free stat value (diagnostic) |
| V2 | C = P + arm consts + P*dk (compare) [lad] | 11 | 19.82 | 0.53 | 2.63 | V=army-free stat value (diagnostic) |
| V3 | C = P + arm consts + V*dk + men*dk [lad] | 17 | 22.14 | 0.59 | 2.80 | V=army-free stat value (diagnostic) |
| V4 | C = aP + arm consts + V*arm + V*dk + men*dk [lad] | 20 | 17.33 | 0.45 | 2.13 | V=army-free stat value (diagnostic) |
| V5 | C = a_arm P + arm consts + V*arm + V*dk + men*dk + dk [lad] | 28 | 15.05 | 0.76 | 1.84 | V=army-free stat value (diagnostic) |
| G0 | E5 core, no size term (men*dk uses regular men) [lad] | 20 | 12.39 | 0.46 | 1.37 | size rows MAE 235, other 9.38 |
| G1 | core + P*(ratio-1) [lad] | 21 | 11.46 | 0.66 | 1.38 | size rows MAE 165, other 9.38 |
| G2 | core + per-arm P*(ratio-1) [lad] | 23 | 10.46 | 0.72 | 1.38 | size rows MAE 90, other 9.38 |
| G3 | core + per-arm P*(ratio^2-1) [lad] | 23 | 10.56 | 0.77 | 1.38 | size rows MAE 98, other 9.38 |
| G4 | core + inf/cav P*(ratio-1) + art P*(ratio^2-1) [lad] | 23 | 10.48 | 0.63 | 1.38 | size rows MAE 92, other 9.38 |
| G5 | core + per-arm P*(ratio-1) + per-arm (ratio-1) [lad] | 26 | 10.39 | 0.72 | 1.37 | size rows MAE 85, other 9.38 |
| H1 | G2 + P*s^2 [lad] | 24 | 10.28 | 0.65 | 1.32 |  |
| H2 | G2 + per-arm P*s^2 [lad] | 26 | 10.12 | 0.59 | 1.32 |  |
| H3 | G2 + per-arm P*s^2 + s^2 [lad] | 27 | 10.10 | 0.59 | 1.29 |  |
| H4 | G2 + per-arm P*s^2 + men*s^2 [lad] | 27 | 10.12 | 0.59 | 1.31 |  |
| H5 | per arm P(a+cs+es^2) + b + ds + men*s(arm) + corps*s + size [lad] | 22 | 11.96 | 0.45 | 1.72 |  |
| H6 | H5 + men*s^2(arm) [lad] | 25 | 11.86 | 0.44 | 1.69 |  |
| N1 | P exp(a_arm + b.dk) ratio^g_arm + men v.dk + c_arm + d s(corps-9) | 22 | 12.16 | 0.42 | 1.65 |  |
| N2 | P exp(a_arm + b.dk) ratio^g_arm + c_arm + d s(corps-9) | 16 | 18.56 | 0.64 | 2.66 |  |
| N3 | (P+K) exp(a_arm+b.dk) ratio^g_arm + men v.dk + c_arm + d s(corps-9) | 23 | 11.61 | 0.57 | 1.52 |  |
| I0 | G2 core (reference) [lad] | 23 | 10.46 | 0.72 | 1.38 |  |
| I1 | core minus stars terms (S, corps*S) [lad] | 21 | 12.86 | 0.52 | 1.66 |  |
| I2 | core minus corps*S [lad] | 22 | 11.13 | 0.74 | 1.44 |  |
| I3 | core minus men*dk [lad] | 17 | 13.64 | 0.72 | 1.81 |  |
| I4 | core minus size terms [lad] | 20 | 12.39 | 0.46 | 1.37 |  |
| I5 | core minus all stat deltas (stars only: P*s, men*s, s, corps*s per arm) [lad] | 19 | 13.34 | 0.53 | 2.09 |  |
| I6 | core + corps, P*corps [lad] | 25 | 10.31 | 0.75 | 1.35 |  |
| I7 | core + side [lad] | 24 | 10.43 | 0.71 | 1.35 |  |
| I8 | core + men [lad] | 24 | 10.43 | 0.70 | 1.37 |  |
| I9 | core + class dummies (12) [lad] | 36 | 10.31 | 0.77 | 1.34 |  |
| I10 | core + training dummies (5) [lad] | 28 | 10.43 | 0.74 | 1.35 |  |
| I11 | core + army intercepts (55, lookup) [lad] | 77 | 10.20 | 0.73 | 1.32 | army lookup |
| I12 | core + army P-multipliers (55, lookup) [lad] | 77 | 10.22 | 0.71 | 1.32 | army lookup |
| I13 | core + regular flags (13) [lad] | 36 | 10.07 | 0.72 | 1.32 |  |
| I14 | core + P*flags (13) [lad] | 36 | 10.05 | 0.67 | 1.31 |  |
| I15 | core + scare gained [lad] | 24 | 10.47 | 0.74 | 1.37 |  |
| I16 | core + regular stats (8) [lad] | 31 | 10.00 | 0.75 | 1.30 |  |
| I17 | core + P*regular stats (8) [lad] | 31 | 10.11 | 0.73 | 1.30 |  |
| J1 | arm a,b + P*(mo,md,cb,ac,rl) + men*dmo + s + corps*s + size3 [lad] | 17 | 10.46 | 0.72 | 1.38 |  |
| J2 | J1 with men*s instead of men*dmo [lad] | 17 | 12.11 | 0.63 | 1.68 |  |
| J3 | J1 with men (const) instead of men*dmo [lad] | 17 | 11.59 | 0.78 | 1.58 |  |
| J4 | J1 + men*dmd + men*dac [lad] | 19 | 10.46 | 0.73 | 1.37 |  |
| J5 | J1 with single a (P) + arm b [lad] | 15 | 10.73 | 0.69 | 1.42 |  |
| J6 | J1 with single b + arm a [lad] | 15 | 11.36 | 0.77 | 1.58 |  |
| J7 | J1 with single size term [lad] | 15 | 11.47 | 0.65 | 1.38 |  |
| J8 | J1 with size: inf/cav shared, art own [lad] | 16 | 10.38 | 0.64 | 1.38 |  |
| J9 | J1 minus P*drl [lad] | 16 | 10.98 | 0.79 | 1.46 |  |
| J10 | J1 minus P*dac [lad] | 16 | 11.01 | 0.80 | 1.38 |  |
| J11 | J1 minus P*dcb [lad] | 16 | 10.75 | 0.71 | 1.38 |  |
| J12 | J1 minus P*dmd [lad] | 16 | 11.45 | 0.73 | 1.57 |  |
| J13 | J1 minus P*dmo [lad] | 16 | 11.88 | 0.63 | 1.63 |  |
| J14 | J1 + P*dma [lad] | 18 | 10.44 | 0.71 | 1.37 |  |
| J15 | J1 minus s, corps*s [lad] | 15 | 14.14 | 0.60 | 1.91 |  |
| J16 | J1 minus corps*s [lad] | 16 | 11.17 | 0.78 | 1.44 |  |
| K0 | J8 [ols] | 16 | 10.64 | 0.64 | 1.48 |  |
| K1 | J8 + corps*men*dmo [lad] | 17 | 10.31 | 0.65 | 1.36 |  |
| K2 | J8 + per-arm s, corps*s [lad] | 20 | 10.13 | 0.68 | 1.35 |  |
| K3 | J8 + s^2 [lad] | 17 | 10.20 | 0.62 | 1.34 |  |
| K4 | J8 + P*s^2 [lad] | 17 | 10.19 | 0.60 | 1.32 |  |
| K5 | J8 + corps (main) [lad] | 17 | 10.35 | 0.65 | 1.37 |  |
| K6 | J8 + P*corps [lad] | 17 | 10.24 | 0.67 | 1.36 |  |
| K7 | J8 + corps*P*dmo [lad] | 17 | 10.18 | 0.70 | 1.36 |  |
| K8 | J8 with men_c instead of men_r [lad] | 16 | 10.50 | 0.66 | 1.37 |  |
| K9 | J8 + P*s^2 + s^2 [lad] | 18 | 10.17 | 0.61 | 1.34 |  |
| K10 | J8 + reg stats(8) [lad] | 24 | 9.91 | 0.65 | 1.32 |  |
| Q1 | J8 with per-arm men*dmo [lad] | 18 | 10.34 | 0.63 | 1.38 |  |
| Q2 | J8 + per-arm men [lad] | 19 | 10.38 | 0.65 | 1.38 |  |
| Q3 | J8 + men*s [lad] | 17 | 10.38 | 0.66 | 1.38 |  |
| Q4 | J8 + per-arm men + men*s [lad] | 20 | 10.37 | 0.65 | 1.38 |  |
| Q5 | J8 with per-arm men*dmo + men*s [lad] | 19 | 10.34 | 0.63 | 1.38 |  |
| Q6 | J8 with per-arm men*dmo + men*dmd + men*drl [lad] | 20 | 10.34 | 0.62 | 1.37 |  |
| R1 | J8 + P/men [lad] | 17 | 10.35 | 0.63 | 1.38 |  |
| R2 | J8 + per-arm P/men [lad] | 19 | 10.34 | 0.64 | 1.39 |  |
| R3 | J8 + per-arm 1/men [lad] | 19 | 10.34 | 0.64 | 1.38 |  |
| R4 | J8 - men*dmo + per-arm P/men [lad] | 18 | 11.78 | 0.62 | 1.59 |  |
| R5 | J8 + P/men + P/men*s [lad] | 18 | 10.34 | 0.64 | 1.38 |  |
| R6 | J8 + P/men*dmo [lad] | 17 | 10.36 | 0.63 | 1.38 |  |
| T1 | J8 + depth-4 tree on residuals (diagnostic) | 31 | 9.79 | 0.61 | 1.30 | tree leaves ~16 |
| T2 | C = P + depth-4 tree(C-P) | 16 | 26.89 | 0.68 | 3.88 | 16 leaves |
| T1 | J8 + depth-4 tree on residuals (diagnostic) | 31 | 9.79 | 0.61 | 1.30 | tree leaves ~16 |
| T2 | C = P + depth-4 tree(C-P) | 16 | 26.89 | 0.68 | 3.88 | 16 leaves |
| U1 | J8 with men*d(morale^2) [lad] | 16 | 12.06 | 0.68 | 1.57 |  |
| U2 | J8 + men*d(morale^2) [lad] | 17 | 10.17 | 0.61 | 1.34 |  |
| U3 | J8 + P*d(morale^2) [lad] | 17 | 10.38 | 0.65 | 1.37 |  |
| U4 | J8 + men*dmo*reg_morale [lad] | 17 | 10.17 | 0.61 | 1.34 |  |
| U5 | J8 + P*d(stat^2) x5 [lad] | 21 | 9.86 | 0.63 | 1.29 |  |
| U6 | J8 + P*d(morale^2) + men*d(morale^2) [lad] | 18 | 10.05 | 0.64 | 1.30 |  |
| W1 | J8 fully per arm [lad] | 29 | 10.03 | 0.76 | 1.32 |  |
| W2 | arm x star lookup (a,b) + men*dmo + corps*s + size, per arm [lad] | 45 | 10.00 | 0.68 | 1.26 |  |
| Z1 | aP + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps) + g P(r-1) [lad] | 9 | 13.58 | 0.85 | 1.71 |  |
| Z2 | aP + b + P(w.dmo,dmd,dac,drl) + v men dmo + s(k - c corps) + g P(r-1) [lad] | 10 | 13.06 | 0.81 | 1.69 |  |
| Z3 | aP + b + P(w.dmo,dmd,dcb,dac,drl) + v men dmo + s(k - c corps) + g P(r-1) [lad] | 11 | 12.90 | 0.76 | 1.69 |  |
| Z4 | aP + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps) [lad] | 8 | 14.56 | 0.68 | 1.72 |  |
| Z5 | aP + b + P(w.dmo,dmd) + v men dmo + s(k - c corps) + g P(r-1) [lad] | 8 | 18.87 | 0.95 | 2.04 |  |
| Z6 | a_arm P + b + P(w.dmo,dmd,drl) + v men dmo + s(k - c corps) + g P(r-1) [lad] | 11 | 12.92 | 0.71 | 1.60 |  |
| Z7 | stars only: P(a + c s) + b + v men (1+floor(s/2)) + s(k - c corps) + g P(r-1) [lad] | 7 | 24.37 | 1.09 | 3.14 |  |
| Z8 | stars+arm: P(a_arm + c_arm s) + b + v men dmo + s(k - c corps) + g P(r-1) [lad] | 11 | 13.03 | 0.51 | 1.67 |  |
| Z9 | Z1 with art size separate [lad] | 10 | 12.42 | 0.83 | 1.71 |  |
| Z10 | Z2 with art size separate [lad] | 11 | 11.90 | 0.80 | 1.68 |  |
| X1 | a_arm P + b_arm + size + lam_army*(P w.d + men v dmo + k s) (55 army scales) | 69 | 10.10 | 0.64 | 1.34 | army lookup on premium |
| FS1 | forward selection step 1: J8 + P*d(charge^2) [lad] | 17 | 10.07 | – | – | src/exp18_forward.py; out/forward_selection.txt |
| FS2 | FS1 + men*d(morale^2) [lad] | 18 | 9.81 | – | – | |
| FS3 | FS2 + corps*P*dmorale [lad] | 19 | 9.46 | – | – | |
| FS4 | FS3 + per-arm s, corps*s [lad] | 23 | 9.21 | – | – | |
| FS5 | FS4 + P*d(reload^2) [lad] | 24 | 9.01 | – | – | |
| FS6 | FS5 + men*dreload [lad] | 25 | 8.80 | – | – | |
| FS7 | FS6 + imperial [lad] | 26 | 8.58 | 0.64 | 1.08 | **chosen BEST** (one-SE rule vs FS10 minimum 8.36) |
| FS8 | FS7 + class=infantry_militia [lad] | 27 | 8.50 | – | – | |
| FS9 | FS8 + s^2 [lad] | 28 | 8.44 | – | – | |
| FS10 | FS9 + P*d(morale^2) [lad] | 29 | 8.36 | – | – | minimum on the path; stopped at 10 steps |
| FINAL-BEST | FS7 refit, src/final.py; seeds 0/1/2/3: 8.58/8.61/8.59/8.63 | 26 | 8.58 | 0.64 | 1.08 | out/final_report.txt |
| FINAL-FALLBACK | J8 refit; seeds 0/1/2/3: 10.38/10.44/10.38/10.39 | 16 | 10.38 | 0.64 | 1.38 | |
| FINAL-MINIMAL | Z10 refit; seeds 0/1/2/3: 11.90/11.94/11.92/11.92 | 11 | 11.90 | 0.80 | 1.68 | |
