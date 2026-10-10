# Best teams of four at a fixed points total

*Steps A1–A4 of `analysis/TEAM_OPTIMISER_PLAN.md`, October 2026.* The question:
**given a fixed team points total, which four corps give the most cost-effective builds?**

Every number comes from an output file in `analysis/output/teams/`:

| File | What |
|---|---|
| `value_bases.md`, `values_ac.csv`, `values_tow_sb.csv` | Per-card values in each version (`analysis/team_values.py`) |
| `ac_build_summary_<v>.csv`, `ac_builds_<v>.csv` | Every AC corps' best build, rebates included (`analysis/ac_builds.py`) |
| `teams_ac.csv`, `teams_tow.csv` | Every legal team of four, valued in each version (`analysis/team_search.py`) |
| `best_teams.csv` | The best team per pool and points total, by total and by weakest member |
| `value_per_point.csv` | Every army's best-build value per corps point, ranked within its pool |
| `team_search.json` | The balance, rebate and version statistics quoted below |

"Value" here is the normative value of the stats bought: the gold the pricing model says the cards
would cost at corps 8. It measures stats per gold as the game's own pricing rule weighs them. It is
not a battle simulation.

## Summary

1. **At a fixed total, how the points are split barely matters for AC; which corps you pick does.**
   - A corps' best-build value grows almost in proportion to its number N (∝ N^0.95–0.98).
   - So 6 + 6 + 12 + 12 is worth only 0.26% less than 9 + 9 + 9 + 9 on the curve.
   - Within a theatre at a fixed total, the spread of N explains almost nothing: Spearman ρ = 0.09.
   - **Practical rule:** a team's value is about T × the members' value per point. Pick the corps
     with the most value per point (§5.2).
2. **ToW and Custom teams do gain from a balanced split.** About 2.4% of team value per standard
   deviation of N (ρ = −0.25). The best team sits at or below the median spread in 70% of cases.
3. **Formation rebates are worth a median 6% of a corps' value** (p90 11%, max 21%). 217 of 223 corps
   gain more than 1%.
   - They hardly reorder teams overall (ρ = 0.989 with against without).
   - But they change the single best team in 43% of theatre × total cells.
   - So the team ranking must use rebate-aware builds.
4. **With rebates, an AC army's face value is routinely above 10 000.** A model-free optimiser
   (value = real list price, the user's suggestion) reaches a median face value of **11 037** for
   10 000. 208 of 223 corps pass 10 500, and 10 pass 12 000. The best is 5. Steinheil / F.K at
   **12 687**.
   - The model-based builds stay close to that: median face value 10 908.
   - Chasing face value costs a median 1.8% of model value.
5. **A few corps are bargains in every value version.**
   - **AC:** 8. Kellermann / III.RC (+34–35% over the value curve), 6. Chasteler / VIII.K (+30–46%),
     9. Uxbridge / CC (+20–22%).
   - **ToW, Imperial:** [1812] 7. United States and [1809] 7. Polska, sojusznicy are in nearly every
     best Imperial team.
   - **Caveat:** 6. Davidov / Narod (+73% in `sb`) and [1812] 8. Russkiy narod lead partly because of
     the model's known weak spot, very large militia (§6).
6. **The size-band values (`sb`) behave like full harmonisation, which supports the user's suspicion.**
   - On mid-size and small strata, `sb` moves values the same way full harmonisation does.
   - The part of raw value it removes predicts winning in the ladder replays (+0.22 ± 0.12, z 1.9),
     as full harmonisation's does (+0.32, z 3.0).
   - Unlike full harmonisation, it does not discount the 240+ militia masses.
7. **The value version matters little for AC and more for ToW.**
   - AC: team totals correlate at ρ 0.987 (`sb` against `full`), and the best team agrees in 67% of
     cells by total and 79% by weakest.
   - ToW: ρ 0.957, and the best team agrees in only 30% / 35% of cells. The ToW table should be read
     with its `full` / `noise` columns.
8. **Sides are close in AC and not in ToW.**
   - AC: at equal points the median Imperial team is within ±6% of its Coalition opponent in every
     campaign with a real choice of teams. The largest gaps are Hundred Days (+6.2%), Austria 1809
     (+6.0%) and Russia 1812 (+5.7%). Egypt's +16.5% rests on its only possible Imperial team.
   - ToW: the Imperial pool is 9–12% ahead at T 36–40. No Coalition ToW army is above N = 10, so
     Coalition value stops rising at about T 36.

## 1. How the game scores and composes a team

From `source/original lua files/ntw3.lua` and the app's `web/src/domain/teamRule.ts`:

- **Points.** A team's points are the sum of its armies' corps numbers N, the number that opens each
  name (`Faction_Points` / `Factions_Points_Sums`). The lobby only displays the sums. A fixed total T
  is a convention players agree on.
- **Army Corps teams** (`Factions_Errors`):
  - all corps share one theatre code, the faction key's third part (e.g. `a11`), which also fixes the
    side;
  - no corps twice;
  - no ToW or Custom army.
- **ToW + Custom teams:**
  - one shared pool, all on one side;
  - Custom armies take their nation's side (`CUSTOM_ARMY_SIDE`); all five real Custom armies have a
    known one (Danmark and France Imperial; UK, HRE and Piemonte-Sardegna Coalition);
  - the Lua does not forbid the same army twice, so §5.4 also reports teams with repeats.
- **Teams of three corps are legal too.** This round covers four. `team_search.py --team-size 3` runs
  three, but that isn't analysed or reported yet.

Search space:
- **AC:** 223 corps with a roster, over 28 theatres, each with at least four corps. That gives
  **4 869** teams. German Campaign 1813 (`a16` / `b16`) is left out: the theatre is still being
  built in the mod and holds only work-in-progress corps (`ac_builds.WIP_THEATRES`). It never formed
  a team anyway; its one corps had only distorted the per-corps statistics.
- **ToW + Custom:** 55 armies; 23 Imperial and 32 Coalition. That gives **44 815** distinct teams, or
  67 310 with repeats.

## 2. Value bases (`analysis/team_values.py`, `value_bases.md`)

There are three versions, all valued at corps 8, with no army × class factor:

| Version | What it is |
|---|---|
| `sb` | The new size-band model from the AC study (F6: a free multiplier per size band per class, 240+ merged into 180–240). CV MAE: AC 25.6 / 41.0 / 44.8, ToW 22.4 / 31.4 / 25.7 (infantry / cavalry / artillery). |
| `full` | The adopted model (V4) with full size harmonisation (bias and noise of each size stratum removed). |
| `noise` | V4 with noise-only harmonisation (each stratum keeps its average). |

How each version handles the generals:
- **Commander cards:** the commander model on each version's regular values.
- **Staff generals:** the T3 star rule (refitted on AC for AC), plus the command correction of
  `cost_effective_builds.py`: λ 0.0045 for `sb` and `full`, 0.0035 for `noise`, with the speed
  nudge.

**The user's suspicion, tested.** The suspicion was that the size bands absorb the real size effect,
as harmonisation does. The table is AC infantry, median value ratio to raw V4:

| Models | 40–60 | 60–80 | 100–140 | 180–240 | 240+ |
|---|---|---|---|---|---|
| `sb` | ×0.96 | ×0.96 | ×1.03 | ×0.91 | ×1.02 |
| `full` | ×0.94 | ×0.95 | ×1.00 | ×0.91 | ×0.75 |
| `noise` | ×1.00 | ×0.99 | ×1.00 | ×0.98 | ×0.99 |

- `sb` follows `full`, not `noise`, everywhere except the 240+ militia masses.
- In the ToW ladder replays, the part of raw value that `sb` removes predicts the winner
  (+0.217 ± 0.117, z 1.9), as full harmonisation's removed part does (+0.317, z 3.0).
- So yes: **fitting the size curve better takes out much of the same size effect that full
  harmonisation takes out**, because both treat the price premium on small and very large units as
  something the stats don't justify. It does so a little more weakly, and it does not touch the
  largest units.

## 3. AC builds with formation rebates (`analysis/ac_builds.py`)

**Method.** An integer programme per corps (scipy `milp` / HiGHS), as for ToW, plus a 0/1 variable
per rebate-earning brigade and division.
- **Completion:** Σ cards placed in the group ≥ n · c. Combat generals count, as in the Lua.
- **Division replaces brigades:** c_brigade + c_division ≤ 1.
- **Budget:** list prices − rebates ≤ 10 000.
- **The game's limits:** 31 cards, one staff general, combat generals ≤ 9 − the key's x-digit and at
  most one per unit, unit and cap-group caps, foot artillery 2, horse artillery 1 (2 if
  cavalry-only), heavy cavalry 10.

**Recruit order.** The app credits a rebate only for groups completed by cards that were each
affordable at list price when taken (`build.ts` `affordableSubset`). That rule is part of the
programme:
- completed groups are recruited in a fixed order: rebate minus what a division's own brigades have
  already earned, descending (an exchange argument shows this is the best order);
- one row per group then checks the running total at its completing card.

Each solution is put in that recruit order (staff general, completed groups, loose cards) and
replayed through the Python port of the rules. A build that fails the replay would be cut and the
programme re-solved, but none does: **0 cuts over 223 corps × 4 versions**.

An earlier version only checked the order after solving. It needed cuts on 45–125 corps per version,
and its cuts banned whole sets of groups, so some builds fell short of the optimum. With the rule in
the model, 11–12 corps per version get a better build, by up to 11% (5. Steinheil / F.K); none gets
worse. The app's optimiser uses the same rows (`web/src/state/acOptimiser.ts`). Every one of
223 corps × 4 versions gets a legal build.

**Verification** (`ac_builds.py --check`, all versions):
- **Cost:** the rules engine's price ≤ the programme's own on all 223. It is lower on 1–10 corps,
  only because the build happens to complete a group the programme didn't need to count.
- **Recruit-order replay and the game's limits:** all pass.
- **Brute force:** over all 64 group-completion patterns of three corps, it matches the programme's
  optimum in every version.
- **Exported files:** every AC build was re-priced in its exported order to its summary cost
  (`export_team_builds.py`).

| Builds (median over 223 corps) | `sb` | `full` | `noise` | `price` (model-free) | `sb`, no rebates |
|---|---|---|---|---|---|
| Face value (list prices) | 10 908 | 10 915 | 10 909 | **11 037** | 9 998 |
| Rebate | 914 | 928 | 914 | 1 038 | 58 |
| Groups completed | 2 | 2 | 2 | 2 | 0 |
| Cards | 22 | 21 | 21 | 23 | 19 |
| Combat generals | 3 | 3 | 3 | 3 | 3 |

(The no-rebate builds still earn 58 by accident; the engine prices them as the game would.)

**The model-free version `price`** (the user's suggestion: use the real prices and squeeze the most
out of the formation discounts):
- **Objective:** a card's value is its list price, so the programme maximises face value. A tie-break
  under 1 gold picks the `sb`-best of equally priced builds.
- **No model is involved,** so the result is exact for the game as it stands.
- **Reach:** 208 of 223 corps exceed 10 500 of face value, 121 exceed 11 000, and 10 exceed 12 000.

| Top face values for 10 000 | Face | Rebate | Cards |
|---|---|---|---|
| 5. Steinheil / F.K | 12 687 | 2 687 | 30 |
| 9. Reuß-Plauen / Italien.R | 12 643 | 2 649 | 31 |
| 11. Eugène / Italie | 12 614 | 2 614 | 31 |
| 10. Masséna / Portugal | 12 472 | 2 472 | 31 |
| 7. Freire / 2-3° | 12 360 | 2 360 | 31 |

Face value is in each corps' own price scale (price ∝ 1/N), so it ranks builds within a corps, not
corps against each other. Measured with `sb`, the max-face-value build is worth a median 1.8% less
than the `sb` build (10% of corps lose more than 7.0%, the worst 20%). So the most rebate is usually,
but not always, the most stats.

## 4. The team search (`analysis/team_search.py`)

**Values per army:**
- **AC:** its best build in each version, from §3.
- **ToW and Custom:** the best build from at most four source corps (one roll, the app's default),
  re-run per version through `cost_effective_builds.army_builds`.

**Per team:** T = Σ N, total value, weakest member's value, and cost.

**Per pool, T and version:**
- the **best team by total**, with ties broken by weakest member;
- the **best by weakest member**, which favours teams without a weak link, with ties broken by total.

The tables below are best over all pools at each T. `best_teams.csv` also has the best team for
every single theatre and side at every T (`scope = pool`), which is the table to use for a match in a
given theatre.

## 5. Results

### 5.1 Balanced or lopsided?

| | Value ∝ N^b, b (± se) | 6+6+12+12 vs 9×4 on that curve | Within-cell slope, % of team value per SD of N | Mean ρ(spread, value) | Best team at or below median spread |
|---|---|---|---|---|---|
| AC, `sb` | 0.951 ± 0.021 | −0.26% | +0.48 | +0.09 | 58% |
| AC, `full` | 0.983 ± 0.018 | −0.09% | +0.36 | +0.09 | 54% |
| ToW, `sb` | 1.001 ± 0.057 | +0.01% | −2.45 | −0.25 | 70% |
| ToW, `full` | 1.022 ± 0.050 | +0.13% | −1.71 | −0.21 | 67% |

- **AC:** prices fall almost as 8/N (γ 0.89–0.94 in the AC study), so a corps buys stats almost in
  proportion to N. The concavity that would reward balance is tiny, and corps-specific value swamps
  it.
- **ToW:** the curve is linear too, but the low- and high-N armies on each side happen to be weaker
  buys than the middle, so balanced teams win on average.

### 5.2 Value per point: the rule behind the best teams

Since value ∝ N, a team's value is close to T × its members' N-weighted value per point. The full
ranking is in `value_per_point.csv`. Per AC theatre (`sb`; value per point in gold):

<!-- TABLE:theatres -->
| Code | Theatre | Corps | N | T | Most value per point (top 3) | Least | Median team value / T |
|---|---|---|---|---|---|---|---|
| a03 | Rhine-Italy (1798-1800) | 10 | 5–12 | 24–40 | 5. Humbert / Irlande 1688, 6. Desaix / Italie.R 1580, 12. Bonaparte / Italie.C 1547 | 8. Gouvion Saint-Cyr / Rhin.C 1406 | 1509 |
| a04 | Egypt (1798-1801) | 4 | 3–10 | 27–27 | 3. Chabot / Corfou 2250, 8. Desaix / Nil 1855, 10. Bonaparte / Alexandrie 1733 | 6. Menou / Damiette 1645 | 1807 |
| a05 | Germany (1805) | 9 | 5–13 | 25–39 | 9. Murat / RC 1779, 5. Marmont / II.C 1777, 6. Davout / III.C 1678 | 9. Lannes / V.C 1443 | 1581 |
| a06 | Prussia (1806-1807) | 10 | 4–12 | 22–45 | 7. Garde impériale 1632, 6. Bernadotte / I.C 1598, 12. Davout / III.C 1556 | 8. Ney / VI.C 1337 | 1492 |
| a07 | Finland (1808-1809) | 4 | 4–10 | 28–28 | 4. Hessen-Kassel / DK 1628, 8. Koulnyov / AG 1499, 10. Buxhoeveden / I.SA 1466 | 6. Kamenski / II.SA 1435 | 1492 |
| a08 | Austria (1809) | 12 | 5–11 | 24–42 | 11. Eugène / Italie 1695, 7. Bernadotte / IX.C 1625, 10. Masséna / IV.C 1580 | 6. Vandamme / VIII.C 1369 | 1527 |
| a09 | Spain (1809) | 9 | 5–11 | 25–39 | 9. Gouvion Saint-Cyr / VII.C 1593, 7. Joseph / CR 1550, 6. Mortier / V.C 1527 | 7. Sébastiani / IV.C 1411 | 1485 |
| a10 | War of 1812 (1812) | 4 | 5–7 | 24–24 | 5. Harrison / 8th 1825, 6. Smith / 10th 1636, 7. Brown / 9th 1464 | 6. Jackson / 7th 1455 | 1580 |
| a11 | Russia (1812) | 14 | 5–13 | 24–44 | 10. Murat / RC 1795, 7. Garde impériale 1636, 6. Gouvion Saint-Cyr / VI.C 1572 | 7. Junot / VIII.C 1423 | 1532 |
| a12 | Hundred Days (1815) | 8 | 5–10 | 25–35 | 8. Kellermann / III.RC 2127, 7. Pajol / I.RC 1859, 10. Garde impériale 1526 | 5. Mouton / VI.C 1392 | 1605 |
| a13 | Spain (1811) | 7 | 5–10 | 25–35 | 10. Masséna / Portugal 1720, 9. Soult / Sud 1597, 9. Suchet / Aragon 1494 | 7. Joseph / Centre 1434 | 1543 |
| a14 | Naples (1815) | 4 | 3–9 | 26–26 | 3. Suchet / Alpes 1686, 7. Carrascosa / I-II 1536, 7. Lecchi / III-IV 1519 | 9. Murat / Guardia reale 1413 | 1506 |
| a15 | Liberation War (1804-1813) | 4 | 5–11 | 31–31 | 7. Kotlyarevski / Valakhiya 1542, 11. Koutouzov / Dunau 1488, 8. Goudovitch / Kavkaz 1476 | 5. Tsitsyanov / Kaspiy 1406 | 1484 |
| a17 | France (1814) | 9 | 5–10 | 26–38 | 9. Macdonald / XI.C,VII.C 1639, 10. Victor / II.C 1569, 8. Soult / Pyrénées 1559 | 9. Augereau / Rhône 1395 | 1508 |
| b03 | 2nd Coalition (1798-1800) | 9 | 5–10 | 25–38 | 8. York / Helder 1553, 9. Souvorov / Italiya 1522, 10. Sztáray / Schwaben.R 1511 | 6. Reuß-Plauen / Schwaben.L 1344 | 1468 |
| b04 | Egypt (1798-1801) | 9 | 5–11 | 27–37 | 5. Ibrahim / Ghugha 1842, 7. Abdoullah / Şam 1656, 11. Mourad / Hashdu 1587 | 8. Abū Marak / Yeniçeri 1346 | 1509 |
| b05 | 3rd Coalition (1805) | 8 | 4–12 | 25–40 | 9. Reuß-Plauen / Italien.R 1643, 12. Buxhoeveden / Slavkov.L 1554, 7. Bagration / Slavkov.P 1518 | 4. Cathcart / Hanover 1413 | 1495 |
| b06 | 4th Coalition (1806-1807) | 12 | 4–13 | 22–45 | 8. Zezschwitz / SH 1591, 8. Kalckreuth / RK 1445, 11. Hohenlohe / SK 1437 | 6. L'Estocq / GK 1367 | 1417 |
| b07 | Finland (1808-1809) | 4 | 4–9 | 28–28 | 4. Moore / Baltic 1551, 7. Klingspor / Motstånd 1526, 9. Adlercreutz / Spetsen 1434 | 8. Döbeln / Östersjön 1413 | 1468 |
| b08 | 5th Coalition (1809) | 13 | 4–12 | 21–42 | 6. Chasteler / VIII.K 1922, 8. D’Este / VII.K 1552, 7. Kollowrat / II.K 1484 | 11. Liechtenstein / RK 1353 | 1442 |
| b09 | Peninsular War (1809) | 8 | 4–13 | 24–40 | 7. Coupigny / la Derecha I 1642, 8. Del Parque / la Izquierda 1612, 7. Beresford / Sul 1526 | 6. Blake y Joyes / la Derecha II 1398 | 1503 |
| b10 | War of 1812 (1812) | 4 | 3–9 | 24–24 | 3. Kindelán / Florida 2357, 6. Brock / Confederacy 1898, 6. Drummond / EF.A 1444 | 9. Ross / EF.EC 1360 | 1640 |
| b11 | Patriotic War (1812) | 12 | 5–12 | 26–43 | 6. Davidov / Narod 2661, 8. Toutchkov / III.K 1586, 5. Steinheil / F.K 1535 | 11. Wittgenstein / I.K 1351 | 1458 |
| b12 | Hundred Days (1815) | 8 | 5–11 | 25–36 | 9. Uxbridge / CC 1778, 7. Hill / II.C 1522, 6. Zieten / I.K 1505 | 8. Wellington / RC 1359 | 1495 |
| b13 | Peninsular War (1811) | 8 | 5–11 | 24–37 | 5. Mendizábal / 7° 1859, 7. Freire / 2-3° 1655, 11. Wellington / Coa 1631 | 7. Santocildes / 6° 1398 | 1565 |
| b14 | Italy (1815) | 4 | 5–8 | 26–26 | 8. Frimont / Alpen.R 1699, 5. Neipperg / Italien.L 1469, 8. Bianchi / Italien.R 1466 | 5. Bubna / Alpen.L 1431 | 1531 |
| b15 | Subjugation (1804-1813) | 6 | 5–11 | 25–34 | 11. Kör Yusuf Ziyaüddin / Rum 1531, 9. Javad Qajar / Azrbadjan 1504, 7. Laz Aziz / Güney Kafkasya 1456 | 7. Koca Hüsrev / Batı Kafkasya 1392 | 1468 |
| b17 | France (1814) | 10 | 5–11 | 25–40 | 5. Wrede / V.K 1652, 9. Bianchi / Süd 1601, 7. Bülow / Nord 1576 | 7. Wintzingerode / Syever 1411 | 1516 |
<!-- /TABLE:theatres -->

### 5.3 Army Corps: best team at each points total, any theatre (`sb`)

"full / noise agree" marks whether those versions pick the same team.

<!-- TABLE:ac -->
**Best by total**

| T | Theatre | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|---|
| 21 | 5th Coalition (1809) (Coa) | 6+6+4+5 | 6. Chasteler / VIII.K + 6. Ludwig / V.K + 4. Kienmayer / Aufstand + 5. Pitt / Walcheren.R | 33,194 | 5,835 | ✓ ✓ |
| 22 | 5th Coalition (1809) (Coa) | 6+7+4+5 | 6. Chasteler / VIII.K + 7. Kollowrat / II.K + 4. Kienmayer / Aufstand + 5. Pitt / Walcheren.R | 34,770 | 5,835 | ✓ ✓ |
| 23 | 5th Coalition (1809) (Coa) | 6+8+4+5 | 6. Chasteler / VIII.K + 8. D’Este / VII.K + 4. Kienmayer / Aufstand + 5. Pitt / Walcheren.R | 36,802 | 5,835 | ✗ ✗ |
| 24 | War of 1812 (1812) (Coa) | 6+9+6+3 | 6. Drummond / EF.A + 9. Ross / EF.EC + 6. Brock / Confederacy + 3. Kindelán / Florida | 39,359 | 7,070 | ✗ ✗ |
| 25 | Germany (1805) (Imp) | 6+7+7+5 | 6. Davout / III.C + 7. Bernadotte / I.C + 7. Masséna / Italie + 5. Marmont / II.C | 41,146 | 8,885 | ✓ ✗ |
| 26 | Patriotic War (1812) (Coa) | 6+8+7+5 | 6. Davidov / Narod + 8. Toutchkov / III.K + 7. Osterman-Tolstoi / IV.K + 5. Steinheil / F.K | 45,998 | 7,674 | ✗ ✗ |
| 27 | Egypt (1798-1801) (Imp) | 10+8+6+3 | 10. Bonaparte / Alexandrie + 8. Desaix / Nil + 6. Menou / Damiette + 3. Chabot / Corfou | 48,788 | 6,750 | ✗ ✗ |
| 28 | Hundred Days (1815) (Imp) | 7+8+6+7 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 6. Vandamme / III.C + 7. Gérard / IV.C | 48,993 | 8,732 | ✓ ✓ |
| 29 | Patriotic War (1812) (Coa) | 6+8+5+10 | 6. Davidov / Narod + 8. Toutchkov / III.K + 5. Steinheil / F.K + 10. Tchitchagov / D.ZA | 51,026 | 7,674 | ✗ ✗ |
| 30 | Hundred Days (1815) (Imp) | 7+8+9+6 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 9. Reille / II.C + 6. Vandamme / III.C | 52,271 | 8,732 | ✓ ✓ |
| 31 | Patriotic War (1812) (Coa) | 6+12+8+5 | 6. Davidov / Narod + 12. Bagration / II.ZA + 8. Toutchkov / III.K + 5. Steinheil / F.K | 54,273 | 7,674 | ✗ ✗ |
| 32 | Hundred Days (1815) (Imp) | 7+8+7+10 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 7. Gérard / IV.C + 10. Garde impériale | 55,519 | 10,234 | ✓ ✓ |
| 33 | Hundred Days (1815) (Imp) | 7+8+8+10 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 8. d'Erlon / I.C + 10. Garde impériale | 56,740 | 11,455 | ✓ ✓ |
| 34 | Hundred Days (1815) (Imp) | 7+8+9+10 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 9. Reille / II.C + 10. Garde impériale | 58,797 | 13,015 | ✓ ✓ |
| 35 | Patriotic War (1812) (Coa) | 6+12+8+9 | 6. Davidov / Narod + 12. Bagration / II.ZA + 8. Toutchkov / III.K + 9. Dokhtourov / VI.K | 59,102 | 12,502 | ✗ ✗ |
| 36 | Patriotic War (1812) (Coa) | 6+12+8+10 | 6. Davidov / Narod + 12. Bagration / II.ZA + 8. Toutchkov / III.K + 10. Tchitchagov / D.ZA | 61,304 | 12,684 | ✗ ✗ |
| 37 | Patriotic War (1812) (Coa) | 6+12+8+11 | 6. Davidov / Narod + 12. Bagration / II.ZA + 8. Toutchkov / III.K + 11. Wittgenstein / I.K | 61,459 | 12,684 | ✗ ✗ |
| 38 | Patriotic War (1812) (Coa) | 10+6+12+10 | 10. Platov / Atamanstvo + 6. Davidov / Narod + 12. Bagration / II.ZA + 10. Tchitchagov / D.ZA | 62,592 | 13,972 | ✗ ✗ |
| 39 | Patriotic War (1812) (Coa) | 6+12+11+10 | 6. Davidov / Narod + 12. Bagration / II.ZA + 11. Wittgenstein / I.K + 10. Tchitchagov / D.ZA | 63,480 | 14,705 | ✗ ✗ |
| 40 | Russia (1812) (Imp) | 10+13+10+7 | 10. Murat / RC + 13. Davout / I.C + 10. Eugène / IV.C + 7. Garde impériale | 64,714 | 11,451 | ✓ ✓ |
| 41 | Russia (1812) (Imp) | 10+13+7+11 | 10. Murat / RC + 13. Davout / I.C + 7. Garde impériale + 11. Oudinot / II.C | 66,602 | 11,451 | ✓ ✓ |
| 42 | Russia (1812) (Imp) | 10+13+11+8 | 10. Murat / RC + 13. Davout / I.C + 11. Oudinot / II.C + 8. Victor / IX.C | 67,426 | 12,274 | ✓ ✓ |
| 43 | Russia (1812) (Imp) | 10+13+9+11 | 10. Murat / RC + 13. Davout / I.C + 9. Poniatowski / V.C + 11. Oudinot / II.C | 68,466 | 13,314 | ✓ ✓ |
| 44 | Russia (1812) (Imp) | 10+13+10+11 | 10. Murat / RC + 13. Davout / I.C + 10. Eugène / IV.C + 11. Oudinot / II.C | 70,049 | 14,897 | ✓ ✓ |
| 45 | Prussia (1806-1807) (Imp) | 12+12+10+11 | 12. Murat / RC + 12. Davout / III.C + 10. Soult / IV.C + 11. Lannes / V.C | 67,771 | 14,128 | ✓ ✓ |

**Best by weakest**

| T | Theatre | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|---|
| 21 | 5th Coalition (1809) (Coa) | 6+6+4+5 | 6. Chasteler / VIII.K + 6. Ludwig / V.K + 4. Kienmayer / Aufstand + 5. Pitt / Walcheren.R | 33,194 | 5,835 | ✓ ✓ |
| 22 | Prussia (1806-1807) (Imp) | 6+7+5+4 | 6. Bernadotte / I.C + 7. Garde impériale + 5. Mortier / VIII.C + 4. La Romana / D.N | 33,958 | 5,854 | ✓ ✓ |
| 23 | Prussia (1806-1807) (Imp) | 8+6+5+4 | 8. Ney / VI.C + 6. Bernadotte / I.C + 5. Mortier / VIII.C + 4. La Romana / D.N | 33,232 | 5,854 | ✓ ✓ |
| 24 | War of 1812 (1812) (Imp) | 6+7+5+6 | 6. Jackson / 7th + 7. Brown / 9th + 5. Harrison / 8th + 6. Smith / 10th | 37,919 | 8,730 | ✓ ✓ |
| 25 | Germany (1805) (Imp) | 6+7+7+5 | 6. Davout / III.C + 7. Bernadotte / I.C + 7. Masséna / Italie + 5. Marmont / II.C | 41,146 | 8,885 | ✓ ✓ |
| 26 | Russia (1812) (Imp) | 6+7+7+6 | 6. Gouvion Saint-Cyr / VI.C + 7. Reynier / VII.C + 7. Garde impériale + 6. Augereau / XI.C | 40,738 | 9,361 | ✗ ✗ |
| 27 | Rhine-Italy (1798-1800) (Imp) | 6+7+7+7 | 6. Desaix / Italie.R + 7. Masséna / Italie.D + 7. Brune / Hollande + 7. Sainte-Suzanne / Rhin.G | 40,746 | 9,483 | ✓ ✓ |
| 28 | Germany (1805) (Imp) | 6+8+7+7 | 6. Davout / III.C + 8. Garde impériale + 7. Bernadotte / I.C + 7. Masséna / Italie | 44,418 | 10,065 | ✓ ✓ |
| 29 | 5th Coalition (1809) (Coa) | 6+7+8+8 | 6. Chasteler / VIII.K + 7. Kollowrat / II.K + 8. Hohenzollern / III.K + 8. D’Este / VII.K | 45,670 | 10,387 | ✗ ✓ |
| 30 | Patriotic War (1812) (Coa) | 6+8+8+8 | 6. Davidov / Narod + 8. Baggovout / II.K + 8. Toutchkov / III.K + 8. Tormassov / III.OA | 51,440 | 10,995 | ✓ ✓ |
| 31 | Patriotic War (1812) (Coa) | 6+8+9+8 | 6. Davidov / Narod + 8. Toutchkov / III.K + 9. Dokhtourov / VI.K + 8. Tormassov / III.OA | 52,947 | 11,797 | ✓ ✓ |
| 32 | Patriotic War (1812) (Coa) | 6+8+9+9 | 6. Davidov / Narod + 8. Toutchkov / III.K + 9. Konstantin / LG + 9. Dokhtourov / VI.K | 53,546 | 12,396 | ✓ ✗ |
| 33 | Patriotic War (1812) (Coa) | 6+8+9+10 | 6. Davidov / Narod + 8. Toutchkov / III.K + 9. Dokhtourov / VI.K + 10. Tchitchagov / D.ZA | 55,855 | 12,502 | ✓ ✗ |
| 34 | Hundred Days (1815) (Imp) | 7+8+9+10 | 7. Pajol / I.RC + 8. Kellermann / III.RC + 9. Reille / II.C + 10. Garde impériale | 58,797 | 13,015 | ✓ ✓ |
| 35 | Patriotic War (1812) (Coa) | 6+8+11+10 | 6. Davidov / Narod + 8. Toutchkov / III.K + 11. Wittgenstein / I.K + 10. Tchitchagov / D.ZA | 58,212 | 12,684 | ✗ ✗ |
| 36 | Patriotic War (1812) (Coa) | 6+12+8+10 | 6. Davidov / Narod + 12. Bagration / II.ZA + 8. Toutchkov / III.K + 10. Tchitchagov / D.ZA | 61,304 | 12,684 | ✗ ✗ |
| 37 | Patriotic War (1812) (Coa) | 10+6+11+10 | 10. Platov / Atamanstvo + 6. Davidov / Narod + 11. Wittgenstein / I.K + 10. Tchitchagov / D.ZA | 59,501 | 13,972 | ✗ ✗ |
| 38 | Patriotic War (1812) (Coa) | 10+6+12+10 | 10. Platov / Atamanstvo + 6. Davidov / Narod + 12. Bagration / II.ZA + 10. Tchitchagov / D.ZA | 62,592 | 13,972 | ✗ ✗ |
| 39 | Patriotic War (1812) (Coa) | 6+12+11+10 | 6. Davidov / Narod + 12. Bagration / II.ZA + 11. Wittgenstein / I.K + 10. Tchitchagov / D.ZA | 63,480 | 14,705 | ✗ ✗ |
| 40 | France (1814) (Coa) | 10+11+10+9 | 10. Schwarzenberg / Böhmen + 11. Barclay de Tolly / VI.K + 10. Blücher / Schlesien + 9. Bianchi / Süd | 61,162 | 14,225 | ✓ ✓ |
| 41 | Russia (1812) (Imp) | 10+10+10+11 | 10. Murat / RC + 10. Ney / III.C + 10. Eugène / IV.C + 11. Oudinot / II.C | 64,330 | 14,696 | ✓ ✓ |
| 42 | Austria (1809) (Imp) | 10+11+10+11 | 10. Davout / III.C + 11. Lannes / II.C + 10. Masséna / IV.C + 11. Eugène / Italie | 66,791 | 15,449 | ✓ ✓ |
| 43 | Russia (1812) (Imp) | 10+13+10+10 | 10. Murat / RC + 13. Davout / I.C + 10. Ney / III.C + 10. Eugène / IV.C | 67,959 | 14,696 | ✓ ✓ |
| 44 | Russia (1812) (Imp) | 10+13+10+11 | 10. Murat / RC + 13. Davout / I.C + 10. Eugène / IV.C + 11. Oudinot / II.C | 70,049 | 14,897 | ✓ ✓ |
| 45 | Prussia (1806-1807) (Imp) | 12+12+10+11 | 12. Murat / RC + 12. Davout / III.C + 10. Soult / IV.C + 11. Lannes / V.C | 67,771 | 14,128 | ✓ ✓ |
<!-- /TABLE:ac -->

### 5.4 ToW + Custom: best team at each points total, per side (`sb`)

<!-- TABLE:tow -->
**Imperial, best by total**

| T | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|
| 23 | 5+6+6+6 | [1798] 5. France (Irlande) + [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1815] 6. Napoli | 36,429 | 7,594 | ✓ ✓ |
| 24 | 5+6+6+7 | [1798] 5. France (Irlande) + [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1812] 7. United States | 40,640 | 7,594 | ✓ ✓ |
| 25 | 5+6+7+7 | [1798] 5. France (Irlande) + [1805] 6. France (Tyrol) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 44,749 | 7,594 | ✓ ✓ |
| 26 | 6+6+7+7 | [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 46,762 | 9,607 | ✓ ✓ |
| 27 | 5+8+7+7 | [1798] 5. France (Irlande) + [1798] 8. France (Égypte) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 49,384 | 7,594 | ✗ ✓ |
| 28 | 8+6+7+7 | [1798] 8. France (Égypte) + [1805] 6. France (Tyrol) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 51,497 | 9,706 | ✗ ✓ |
| 29 | 7+8+7+7 | 7. Danmark + [1798] 8. France (Égypte) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 53,485 | 11,694 | ✗ ✓ |
| 30 | 8+8+7+7 | [1798] 8. France (Égypte) + [1814] 8. France + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 55,972 | 13,716 | ✓ ✓ |
| 31 | 8+9+7+7 | [1798] 8. France (Égypte) + [1815] 9. France (Flandres) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 56,858 | 13,716 | ✗ ✓ |
| 32 | 8+10+7+7 | [1798] 8. France (Égypte) + [1809] 10. France (Espagne) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 58,425 | 13,716 | ✗ ✗ |
| 33 | 7+12+7+7 | 7. Danmark + [1806] 12. France (Prusse) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 59,206 | 11,694 | ✗ ✓ |
| 34 | 8+12+7+7 | [1798] 8. France (Égypte) + [1806] 12. France (Prusse) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 61,853 | 13,716 | ✗ ✓ |
| 35 | 12+9+7+7 | [1806] 12. France (Prusse) + [1815] 9. France (Flandres) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 62,579 | 13,716 | ✓ ✓ |
| 36 | 12+10+7+7 | [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 64,146 | 13,716 | ✓ ✓ |
| 37 | 8+12+10+7 | [1798] 8. France (Égypte) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1812] 7. United States | 64,772 | 13,733 | ✗ ✗ |
| 38 | 12+10+9+7 | [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) + [1812] 7. United States | 65,498 | 13,733 | ✓ ✓ |
| 39 | 12+10+10+7 | [1806] 12. France (Prusse) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1812] 7. United States | 66,236 | 13,733 | ✗ ✗ |
| 40 | 11+12+10+7 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1812] 7. United States | 67,638 | 13,733 | ✓ ✓ |
| 41 | 8+11+12+10 | [1798] 8. France (Égypte) + [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) | 68,246 | 14,342 | ✗ ✗ |
| 42 | 11+12+10+9 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 68,972 | 15,068 | ✓ ✓ |
| 43 | 11+12+10+10 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) | 69,711 | 15,807 | ✗ ✗ |
| 44 | 11+12+10+11 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1812] 11. France (Russie-Centre) | 70,912 | 16,635 | ✓ ✓ |

**Imperial, best by weakest**

| T | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|
| 23 | 5+6+6+6 | [1798] 5. France (Irlande) + [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1815] 6. Napoli | 36,429 | 7,594 | ✓ ✓ |
| 24 | 5+6+6+7 | [1798] 5. France (Irlande) + [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1812] 7. United States | 40,640 | 7,594 | ✓ ✓ |
| 25 | 6+6+7+6 | [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1812] 7. United States + [1815] 6. Napoli | 42,568 | 9,522 | ✓ ✓ |
| 26 | 6+6+7+7 | [1805] 6. France (Tyrol) + [1812] 6. France (Russie-Nord) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 46,762 | 9,607 | ✓ ✓ |
| 27 | 7+6+7+7 | 7. Danmark + [1805] 6. France (Tyrol) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 48,850 | 9,706 | ✓ ✓ |
| 28 | 7+7+7+7 | 7. Danmark + [1799] 7. France (Hollande) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 50,047 | 10,904 | ✓ ✗ |
| 29 | 7+8+7+7 | 7. Danmark + [1798] 8. France (Égypte) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 53,485 | 11,694 | ✗ ✓ |
| 30 | 8+8+7+7 | [1798] 8. France (Égypte) + [1814] 8. France + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 55,972 | 13,716 | ✓ ✓ |
| 31 | 8+9+7+7 | [1798] 8. France (Égypte) + [1815] 9. France (Flandres) + [1809] 7. Polska, sojusznicy + [1812] 7. United States | 56,858 | 13,716 | ✗ ✗ |
| 32 | 8+9+8+7 | [1798] 8. France (Égypte) + [1815] 9. France (Flandres) + [1814] 8. France + [1812] 7. United States | 57,324 | 13,733 | ✗ ✓ |
| 33 | 8+10+8+7 | [1798] 8. France (Égypte) + [1809] 10. France (Espagne) + [1814] 8. France + [1812] 7. United States | 58,891 | 13,733 | ✗ ✗ |
| 34 | 9+8+9+8 | 9. France (1796) + [1798] 8. France (Égypte) + [1815] 9. France (Flandres) + [1814] 8. France | 58,407 | 14,182 | ✗ ✗ |
| 35 | 8+10+9+8 | [1798] 8. France (Égypte) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) + [1814] 8. France | 60,226 | 14,182 | ✗ ✗ |
| 36 | 9+8+10+9 | 9. France (1796) + [1798] 8. France (Égypte) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 60,860 | 14,342 | ✗ ✗ |
| 37 | 8+10+10+9 | [1798] 8. France (Égypte) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 61,851 | 14,342 | ✗ ✗ |
| 38 | 9+10+10+9 | 9. France (1796) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 62,325 | 14,816 | ✓ ✓ |
| 39 | 9+11+10+9 | 9. France (1796) + [1805] 11. France (Allemagne) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 63,726 | 14,816 | ✓ ✓ |
| 40 | 11+10+10+9 | [1805] 11. France (Allemagne) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 64,717 | 15,068 | ✓ ✓ |
| 41 | 12+10+10+9 | [1806] 12. France (Prusse) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1815] 9. France (Flandres) | 67,571 | 15,068 | ✓ ✓ |
| 42 | 11+10+10+11 | [1805] 11. France (Allemagne) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) + [1812] 11. France (Russie-Centre) | 66,657 | 15,807 | ✓ ✓ |
| 43 | 11+12+10+10 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Autriche) + [1809] 10. France (Espagne) | 69,711 | 15,807 | ✓ ✓ |
| 44 | 11+12+10+11 | [1805] 11. France (Allemagne) + [1806] 12. France (Prusse) + [1809] 10. France (Espagne) + [1812] 11. France (Russie-Centre) | 70,912 | 16,635 | ✓ ✓ |

**Coalition, best by total**

| T | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|
| 24 | 5+6+7+6 | [1798] 5. UK (Ireland) + [1809] 6. UK (Walcheren) + [1812] 7. UK (USA) + [1815] 6. Österreich (Italien) | 37,503 | 6,448 | ✗ ✓ |
| 25 | 5+6+8+6 | [1798] 5. UK (Ireland) + [1809] 6. UK (Walcheren) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 40,352 | 6,448 | ✗ ✗ |
| 26 | 5+7+8+6 | [1798] 5. UK (Ireland) + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 43,857 | 6,448 | ✗ ✗ |
| 27 | 6+7+8+6 | [1809] 6. UK (Walcheren) + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 45,896 | 8,487 | ✗ ✗ |
| 28 | 7+8+6+7 | [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) + [1804] 7. Irānshahr | 48,493 | 10,575 | ✗ ✗ |
| 29 | 8+7+8+6 | [1798] 8. Mamālīk + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 51,343 | 10,575 | ✗ ✗ |
| 30 | 8+8+6+8 | [1798] 8. Mamālīk + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) + [1814] 8. Österreich (Frankreich) | 52,432 | 10,575 | ✓ ✗ |
| 31 | 8+8+6+9 | [1798] 8. Mamālīk + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) + [1806] 9. Osmanlı | 54,346 | 10,575 | ✗ ✗ |
| 32 | 8+7+8+9 | [1798] 8. Mamālīk + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 55,763 | 11,992 | ✗ ✗ |
| 33 | 8+8+9+8 | [1798] 8. Mamālīk + [1812] 8. Russkiy narod + [1806] 9. Osmanlı + [1814] 8. Österreich (Frankreich) | 56,852 | 13,081 | ✗ ✗ |
| 34 | 8+9+8+9 | [1798] 8. Mamālīk + [1809] 9. España + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 58,188 | 13,934 | ✗ ✗ |
| 35 | 9+8+9+9 | [1809] 9. España + [1812] 8. Russkiy narod + [1815] 9. UK, Nederlanden + [1806] 9. Osmanlı | 58,541 | 14,288 | ✗ ✗ |
| 36 | 10+9+8+9 | [1806] 10. Preußen + [1809] 9. España + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 58,947 | 14,417 | ✗ ✗ |
| 37 | 10+10+8+9 | [1806] 10. Preußen + [1809] 10. Österreich + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 59,064 | 14,534 | ✗ ✗ |
| 38 | 10+10+9+9 | [1806] 10. Preußen + [1809] 10. Österreich + [1809] 9. España + [1806] 9. Osmanlı | 58,639 | 14,417 | ✗ ✗ |
| 39 | 10+10+10+9 | [1806] 10. Preußen + [1809] 10. Österreich + [1812] 10. Rossiya + [1806] 9. Osmanlı | 58,690 | 14,468 | ✗ ✗ |
| 40 | 10+10+10+10 | [1806] 10. Preußen + [1809] 10. Österreich + [1809] 10. UK, España, Portugal + [1812] 10. Rossiya | 58,063 | 14,369 | ✓ ✓ |

**Coalition, best by weakest**

| T | N | Team | Total | Weakest | full / noise agree |
|---|---|---|---|---|---|
| 24 | 5+6+7+6 | [1798] 5. UK (Ireland) + [1809] 6. UK (Walcheren) + [1812] 7. UK (USA) + [1815] 6. Österreich (Italien) | 37,503 | 6,448 | ✗ ✓ |
| 25 | 5+6+8+6 | [1798] 5. UK (Ireland) + [1809] 6. UK (Walcheren) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 40,352 | 6,448 | ✗ ✗ |
| 26 | 6+7+6+7 | [1809] 6. UK (Walcheren) + [1812] 7. UK (USA) + [1815] 6. Österreich (Italien) + [1804] 7. Irānshahr | 42,138 | 8,487 | ✗ ✓ |
| 27 | 7+7+6+7 | [1812] 7. UK (USA) + [1811] 7. España + [1815] 6. Österreich (Italien) + [1804] 7. Irānshahr | 44,094 | 10,443 | ✗ ✗ |
| 28 | 7+8+6+7 | [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) + [1804] 7. Irānshahr | 48,493 | 10,575 | ✗ ✗ |
| 29 | 8+7+8+6 | [1798] 8. Mamālīk + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1815] 6. Österreich (Italien) | 51,343 | 10,575 | ✗ ✗ |
| 30 | 8+7+8+7 | [1798] 8. Mamālīk + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1804] 7. Irānshahr | 51,852 | 11,084 | ✗ ✗ |
| 31 | 8+7+8+8 | [1798] 8. Mamālīk + [1812] 7. UK (USA) + [1812] 8. Russkiy narod + [1814] 8. Österreich (Frankreich) | 53,849 | 11,992 | ✗ ✓ |
| 32 | 8+8+8+8 | [1798] 8. Mamālīk + [1805] 8. Österreich + [1812] 8. Russkiy narod + [1814] 8. Österreich (Frankreich) | 54,067 | 12,210 | ✗ ✗ |
| 33 | 8+8+9+8 | [1798] 8. Mamālīk + [1812] 8. Russkiy narod + [1806] 9. Osmanlı + [1814] 8. Österreich (Frankreich) | 56,852 | 13,081 | ✗ ✗ |
| 34 | 8+9+8+9 | [1798] 8. Mamālīk + [1809] 9. España + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 58,188 | 13,934 | ✗ ✗ |
| 35 | 9+8+9+9 | [1809] 9. España + [1812] 8. Russkiy narod + [1815] 9. UK, Nederlanden + [1806] 9. Osmanlı | 58,541 | 14,288 | ✗ ✗ |
| 36 | 10+9+8+9 | [1806] 10. Preußen + [1809] 9. España + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 58,947 | 14,417 | ✗ ✗ |
| 37 | 10+10+8+9 | [1806] 10. Preußen + [1809] 10. Österreich + [1812] 8. Russkiy narod + [1806] 9. Osmanlı | 59,064 | 14,534 | ✗ ✗ |
| 38 | 10+10+10+8 | [1806] 10. Preußen + [1809] 10. Österreich + [1812] 10. Rossiya + [1812] 8. Russkiy narod | 58,536 | 14,468 | ✗ ✗ |
| 39 | 10+10+10+9 | [1806] 10. Preußen + [1809] 10. Österreich + [1812] 10. Rossiya + [1806] 9. Osmanlı | 58,690 | 14,468 | ✗ ✗ |
| 40 | 10+10+10+10 | [1806] 10. Preußen + [1809] 10. Österreich + [1809] 10. UK, España, Portugal + [1812] 10. Rossiya | 58,063 | 14,369 | ✓ ✓ |
<!-- /TABLE:tow -->

**Repeats.** If the same ToW army may appear twice, the best team uses a repeat in 38 of 39 cells.
It gains a median 3.1% by total (max 12.8%). Examples:
- Imperial T 30: France (Flandres) + three [1812] 7. United States;
- Coalition T 36: four [1806] 9. Osmanlı.

### 5.5 What the formation rebates change

| | `sb` | `full` | `noise` |
|---|---|---|---|
| Corps value gained from rebates, median / p90 / max | 6.1 / 11.1 / 20.7% | 6.4 / 11.6 / 21.5% | 6.2 / 11.4 / 21.3% |
| Corps gaining > 1% | 217 | 216 | 215 |
| Team totals, ρ with vs without rebates | 0.988 | 0.988 | 0.989 |
| Same best team per theatre × T, by total / by weakest | 57% / 74% | 53% / 72% | 57% / 76% |

### 5.6 What the value version changes

| Pair | AC: ρ team totals | AC: same best (total / weakest) | ToW: ρ | ToW: same best |
|---|---|---|---|---|
| `sb` vs `full` | 0.987 | 67% / 79% | 0.957 | 30% / 35% |
| `sb` vs `noise` | 0.985 | 71% / 83% | 0.969 | 46% / 46% |
| `full` vs `noise` | 0.996 | 87% / 92% | 0.990 | 62% / 68% |

### 5.7 Sides at equal points (AC campaigns)

Median team value at equal T, Imperial over Coalition (`sb`):

<!-- TABLE:campaigns -->
| Imperial theatre | Coalition theatre | Shared T | Imperial vs Coalition |
|---|---|---|---|
| Rhine-Italy (1798-1800) | 2nd Coalition (1798-1800) | 25–38 | +2.8% |
| Egypt (1798-1801) | Egypt (1798-1801) | 27–27 | +16.5% (one Imperial team) |
| Germany (1805) | 3rd Coalition (1805) | 25–39 | +4.9% |
| Prussia (1806-1807) | 4th Coalition (1806-1807) | 22–45 | +5.4% |
| Finland (1808-1809) | Finland (1808-1809) | 28–28 | +1.6% (one Imperial team) |
| Austria (1809) | 5th Coalition (1809) | 24–42 | +6.0% |
| Spain (1809) | Peninsular War (1809) | 25–39 | -1.7% |
| War of 1812 (1812) | War of 1812 (1812) | 24–24 | -3.7% (one Imperial team) |
| Russia (1812) | Patriotic War (1812) | 26–43 | +5.7% |
| Hundred Days (1815) | Hundred Days (1815) | 25–35 | +6.2% |
| Spain (1811) | Peninsular War (1811) | 25–35 | -1.2% |
| Naples (1815) | Italy (1815) | 26–26 | -1.6% (one Imperial team) |
| Liberation War (1804-1813) | Subjugation (1804-1813) | 31–31 | +0.4% (one Imperial team) |
| France (1814) | France (1814) | 26–38 | -0.6% |
<!-- /TABLE:campaigns -->

## 6. Limitations

- **Large militia.** The pricing model overprices very large militia units (PRICING_MODEL_REPORT).
  `sb` keeps them near raw value, while `full` discounts them ×0.75. The extreme case: Guerasim
  Kourin's 552-model card in 6. Davidov / Narod is valued 2 882 in `sb`, against 1 899 raw and
  1 105 in `full`.
  - Davidov's bargain status falls from +73% (`sb`) to +36% (`full`).
  - The Russia 1812 Coalition teams that rank first in `sb` at T 35–39 do not in `full` / `noise`.
  - The same applies to [1812] 8. Russkiy narod in ToW.
  - Read those rows with the `full` column.
- **Value is stats per gold, not battlefield strength.** It weighs stats as the game's prices do,
  with the command correction for staff generals. It knows nothing of terrain, micro or how units
  combine.
- **[1809] 7. Polska's** prices were flagged as suspect in the ToW study (lancers at ×0.57). If those
  prices are a mistake the game later fixes, its place in the Imperial teams goes with it.
- **ToW builds use one roll** (four source corps). Each player rolls separately, so a team's four
  builds don't constrain each other.
- **Solver precision.** The model-based programmes stop within a 1e-4 relative gap (about 1 value
  point per corps). Teams closer than a few points are ties.
- **Teams of three** are legal but not analysed here.

## 7. Files for the app (`analysis/export_team_builds.py`)

Import with **⤓ Offline → Import saves…**. The JSON files are regenerable and gitignored; each folder's
`README.md` indexes them.

| Folder | Contents |
|---|---|
| `analysis/output/app_builds_ac_sb/` | Every AC corps' best `sb` build (223) |
| `analysis/output/app_builds_ac_price/` | Every AC corps' most-face-value build (223) |
| `analysis/output/app_builds_teams/` | The best teams of §5.3 and §5.4, one backup file per team holding its four builds (94) |

AC builds are written in their verified recruit order (staff general first, then the instances).
**Don't reorder them in the app**: AC rebates depend on the order.

## 8. Next: the app (phase B of the plan)

- **AC in the Optimise panel.** Rebate variables and completion constraints in
  `web/src/state/optimiser.ts`, the AC combat-general cap, and output in a recruit order `priceBuild`
  accepts. Three value modes:
  - **size bands** (`sb`);
  - **quality / quantity** (`full` / `noise`);
  - **max face value**, the model-free one, which needs no shipped values at all.
- **Team suggestion in the Ordre de Bataille planner.** Given a points total and the plan's pool,
  suggest the best four (by total or by weakest member).
  - **Mixed teams are refused:** when the plan mixes AC with ToW/Custom, AC theatres, or sides
    (`teamRule.ts`), the suggest and optimise buttons are disabled with a message naming the
    conflict.
- **Teams of three** via the same search.

## Commands

```bash
py -3.13 analysis/team_values.py                  # value bases (~1 min with the AC study's caches)
py -3.13 analysis/ac_builds.py                    # AC builds, versions sb full noise price (~6 min)
py -3.13 analysis/ac_builds.py --no-rebates --versions sb full noise
py -3.13 analysis/ac_builds.py --check            # verification
py -3.13 analysis/team_search.py                  # teams (~2 min cold, 10 s with analysis/.cache/teams/)
py -3.13 analysis/export_team_builds.py           # app files
```
