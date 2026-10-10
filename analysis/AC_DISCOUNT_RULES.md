# Army Corps formation rebates

How an Army Corps (AC) army is priced, what the app adds to the game's rule, where the
two disagree, and how large the rebates are across all 238 AC corps. This is step 1 of
the AC pricing study ([`AC_STUDY_PLAN.md`](AC_STUDY_PLAN.md)). Every number below comes
from [`ac_discounts.py`](ac_discounts.py) and its outputs in `analysis/output/ac/`.

**In short:** an AC army costs the sum of its cards' list prices, minus a rebate for every
brigade or division whose whole roster is on the field. A complete group of total cap
*n* is **(n − 1)% off** that group's full roster cost, rounded down. The app follows the
Lua exactly, except in 5 fully tagged artillery divisions. Only 3 small groups among them
can actually be completed, and those need checking in game.

---

## 1. The game's rule (Lua)

Source: `source/original lua files/ntw3.lua`. The quotes are verbatim.

**Army price** (`NTW3.ArmyPrice`, lines 420–429):

```lua
function NTW3.ArmyPrice(faction, cards)
  local S = 0
  for i, v in ipairs(cards) do
    S = S + v.MPCost
  end
  if string.find(faction, "_ac_") ~= nil then
    S = S - NTW3.AC_DivisionBrigade_Bonus(faction, cards)
  end
  return S
end
```

**Placement tag** (`NTW3.AC_DivisionBrigade_Locate`, lines 441–450). The division and
brigade are read from the `ACDV<d>B<b>` text in the card's localised description:

```lua
function NTW3.AC_DivisionBrigade_Locate(dsc)
  local _, x = string.find(dsc, "ACDV")
  if x ~= nil then
    local divbgd = string.sub(dsc, x + 1)
    local vals = NTW3.Explode("B", divbgd)
    return tonumber(vals[1]), tonumber(vals[2])
  else
    return 0, 0
  end
end
```

**Rebate** (`NTW3.AC_DivisionBrigade_Bonus`, lines 452–474):

```lua
function NTW3.AC_DivisionBrigade_Bonus(faction, cards)
  local cut = 0
  local ratio = 1
  if NTW3.FactionIsGermanStates(faction) then
    ratio = ratio * 1.5
  end
  local RosterDivisions = NTW3.AC_DivisionBrigade_Roster(faction)
  local SelectedDivisions = NTW3.AC_DivisionBrigade_Selected(cards)
  for n_division, SelectedDivision in pairs(SelectedDivisions) do
    local RosterDivision = RosterDivisions[n_division]
    if SelectedDivision.NbUnits >= RosterDivision.NbUnits then
      cut = cut + NTW3.AC_DivisionBrigade_PriceCut(RosterDivision)
    else
      for n_brigade, SelectedBrigade in pairs(SelectedDivision.Brigades) do
        local RosterBrigade = RosterDivision.Brigades[n_brigade]
        if SelectedBrigade.NbUnits >= RosterBrigade.NbUnits then
          cut = cut + NTW3.AC_DivisionBrigade_PriceCut(RosterBrigade)
        end
      end
    end
  end
  return math.floor(cut * ratio)
end
```

**Price cut per group** (`NTW3.AC_DivisionBrigade_PriceCut`, lines 476–478):

```lua
function NTW3.AC_DivisionBrigade_PriceCut(Group)
  return math.floor(Group.Cost / 100 * (Group.NbUnits - 1))
end
```

**Roster totals** (`NTW3.AC_DivisionBrigade_Roster`, lines 480–505). The roster is the
corps' recruitable units (`NTW3.Faction_Units_List`, lines 405–418). The core of the loop:

```lua
    if v.Class ~= "General" then
      local n_division, n_brigade = NTW3.AC_DivisionBrigade_Locate(v.Description)
      if 0 < n_division and 0 < n_brigade then
        ...
        RosterDivisions[n_division].Cost = RosterDivisions[n_division].Cost + v.Cap * v.MPCost
        RosterDivisions[n_division].NbUnits = RosterDivisions[n_division].NbUnits + v.Cap
        RosterDivisions[n_division].Brigades[n_brigade].Cost = RosterDivisions[n_division].Brigades[n_brigade].Cost + v.Cap * v.MPCost
        RosterDivisions[n_division].Brigades[n_brigade].NbUnits = RosterDivisions[n_division].Brigades[n_brigade].NbUnits + v.Cap
```

**Selected counts** (`NTW3.AC_DivisionBrigade_Selected`, lines 507–526). This counts
every selected card with a tag, generals included:

```lua
  for i, v in ipairs(cards) do
    local n_division, n_brigade = NTW3.AC_DivisionBrigade_Locate(v.Description)
    if 0 < n_division and 0 < n_brigade then
      ...
      SelectedDivisions[n_division].NbUnits = SelectedDivisions[n_division].NbUnits + 1
      SelectedDivisions[n_division].Brigades[n_brigade].NbUnits = SelectedDivisions[n_division].Brigades[n_brigade].NbUnits + 1
```

**What this means:**

- **Group size and cost.** A group's cost is Σ cap × list price over its full roster,
  and its size *n* is Σ cap. Generals are left out of both.
- **Completion.** A group is complete when the selected tagged cards, combat generals
  included, reach *n*. A combat general can therefore stand in for one copy of its unit.
- **A complete division replaces its brigades.** It earns its own cut instead of theirs.
  If the division is not complete, each complete brigade earns its own cut.
- **No rebate:** cards without a tag, and division 0 or brigade 0.
- **German States** (`NTW3.FactionIsGermanStates`, lines 69–72) means a "g" in the 4th key
  component, which gives ×1.5. No shipped corps matches, which was checked in game (see
  `isGermanStates`).
- **No per-corps price multiplier exists.** The corps number N appears only in
  `NTW3.Faction_Points` (lines 346–354), the lobby's team points.
- **Display only.** The lobby layout (`NTW3AC.Divisions_Build`, `ntw3ac.lua` lines
  98–139) draws untagged cards in its last line, grouped by artillery type. This is why
  players see an untagged "support division". The price ignores those cards.

## 2. Consequence: (n − 1)% off

Rebate = ⌊C × (n − 1) / 100⌋, where C is the group's full roster cost. As a fraction of C,
the rebate falls in the range (n − 1 − 100/C, n − 1]%.

| Group size n (Σ cap) | 1 | 2 | 4 | 8 | 11 | 20 | 31 |
|---|---|---|---|---|---|---|---|
| Rebate, % of roster cost | 0 | 1 | 3 | 7 | 10 | 19 | 30 |

- **The roster is fixed.** C and n always cover the *whole* roster, so the rebate does not
  depend on which copies are fielded. A combat general can replace a copy (it counts toward
  *n*) without changing the rebate.
- **Float and integer floors agree.** Lua 5.1 computes `Cost / 100 * (n - 1)` in doubles,
  while the app uses the integer `C * (n − 1) // 100`. The two can differ for some (C, n)
  pairs, but they agree on all 3 517 Lua groups in the shipped data.
- **Effective price** (used in `ac_discounts.csv`): list × (1 − rebate / C). This spreads
  the group's rebate over its roster in proportion to list price. Commanders get the same
  fraction of their own price.

## 3. What the app adds

The rules live in `web/src/rules/rules.ts` (the reference) and `tools/army_builder_rules.py`
(the parity port).

| Rule | What it does | Where | Basis |
|---|---|---|---|
| **Same core rule** | Roster totals, `floor(C(n−1)/100)`, division-replaces-brigades, generals count toward completion but not the roster, ×1.5 German States | `groupDiscount` rules.ts 256; `buildRosterTotals` 271; `calculateArmyCost` 335; `isGermanStates` 266. Python: `group_discount` 358, `build_roster_totals` 330, `calculate_army_cost` 374, `is_german_states` 369 | The Lua (§1) |
| **Support divisions earn nothing** | A division earns no rebate, and neither do its brigades, when either (a) every card is a support arm (artillery, skirmisher, sapper or marine by name) and it holds artillery, or (b) the builder designated it the support division (`placement_source` ∈ `SUPPORT_PLACEMENT_SOURCES`) | `supportDivisions` rules.ts 130; `SUPPORT_PLACEMENT_SOURCES` 20. Python: `support_divisions` 300, 30 | Described in the code as in-game behaviour. See §5 for where it departs from the Lua |
| **Builder placements** | The app's placements fill gaps the tags leave: untagged support cards go to a new final division (`infer_final_division_placements`), untagged division-0 cards to a reserve division 0 (line 227), untagged commanders inherit their base unit's placement (`inherit_commander_placements`), and Bonaparte / Italie.C d5 comes from `DIVISION_PLACEMENT_OVERRIDES` | `tools/build_ntw3_army_builder_database.py` 189, 227, 302, 62 | Builder conventions, plus one placement confirmed in game |
| **Davout exception** | In `ntw3_ac_a11_x5_117` (13. Davout / I.C), the non-artillery brigades of the support division (d7 B5 sappers, B6 tirailleurs) keep their brigade rebate | `SUPPORT_DIVISION_BRIGADE_DISCOUNT_FACTIONS` rules.ts 35, orphan-brigade loop 407. Python: 47, 429 | Observed in game |
| **Recruit-order affordability** | Rebates count only over the prefix of the recruit order (commander first) that stayed affordable: each card's list price, added to the discounted total so far, must fit under 10 000. Over-budget cards are paid in full but complete nothing | `affordableSubset` `web/src/state/build.ts` 327; `priceBuild` 357; `MAX_BUILD_COST` rules.ts 40 | Observed in game. Not in the Lua, which prices whatever list it is given |

The card limits (31 cards from `NTW3.MaxUnits`, 2 foot and 1 horse artillery (2 for a
cavalry-only corps), 10 heavy cavalry, unit caps) are not rebate rules. They decide
whether a group can be completed at all (§6).

## 4. Worked example: the verified 5 645-gold build

The example is pinned by `tools/tests/test_army_builder_rules.py`
(`test_verified_5645_example`, line 111) and `web/src/rules/rules.test.ts`
("verified 5645 example", line 123).

**Roster of the brigade** (division 1, brigade 1 in the test):

| Card | List | Cap | Cap × list |
|---|---|---|---|
| roster_a | 1 003 | 2 | 2 006 |
| roster_b | 807 | 2 | 1 614 |
| roster_c | 384 | 4 | 1 536 |
| **Brigade** | | **n = 8** | **C = 5 156** |

A one-card brigade 2 (100 gold) makes the division n = 9, so a full brigade does not
complete the division.

**Selected cards** (8, all tagged d1 B1): 1 003, 1 003, 807, 807, 384, 384, 772, plus a
tagged general at 845.

- Base = 6 005.
- Selected in the brigade = 8 ≥ n = 8, so the brigade is complete. The division is not
  (8 < 9).
- Rebate = ⌊5 156 × 7 / 100⌋ = ⌊360.92⌋ = **360**, which is 6.98%, just under n − 1 = 7%.
- Price = 6 005 − 360 = **5 645**.

**The brigade in today's data.** The roster is exactly **7. Garde impériale**
(`ntw3_ac_a11_x5_130`), division 4, brigade 2: Fusiliers-grenadiers 1 003 × 2,
Fusiliers-chasseurs 807 × 2, Flanqueurs-chasseurs 384 × 4. The 845 general matches the
Pierre Bodelin variant of the Fusiliers-grenadiers (`…_0565_com_0301`, also ACDV4B2).

No card in that brigade costs 772 today. Here is a legal build with current prices that
the script checks:

- Fusiliers-grenadiers ×1 + Bodelin, Fusiliers-chasseurs ×2, Flanqueurs ×4.
- 4 998 − 360 = **4 638**.

## 5. Lua/app disagreements: for in-game verification (the app is not changed)

The script re-reads every card's ACDV tag from `source/tables/` (land units and
localisation). It parses each tag the way `AC_DivisionBrigade_Locate` does, rebuilds the
Lua's roster, and compares rebates group by group and card by card. All 11 891 tags
parse cleanly. The 11 889 on `localisation_tag` rows equal the builder's placements, and
the other 2 are ACDV0 tags, which the Lua ignores.

**The only disagreements are 5 fully tagged support divisions.** The app gives them
nothing, while the Lua credits them. This confirms the list in the study plan.

| Corps | Div | Lua division rebate (n, C) | Lua brigade rebates (B: gold) | Can the Lua-only groups be completed? |
|---|---|---|---|---|
| `ntw3_ac_a11_x5_117` 13. Davout / I.C | 7 | 1 785 (19, 9 917) | B1 113, B2 22, B3 28, B4 8; B5 5 and B6 55 (the app gives these too) | **No.** B1/B3 hold 4 and 3 foot batteries, B2/B4 hold 2 horse batteries each, so caps block the division and B1–B4 |
| `ntw3_ac_a11_x5_123` 7. Reynier / VII.C | 4 | 65 (4, 2 181) | B1 14, B2 7 | **Yes, all three** |
| `ntw3_ac_a11_x7_126` 5. Macdonald / X.C | 3 | 34 (3, 1 733) | B1 7, B2 0 | **Yes** (2 foot batteries + 1 horse) |
| `ntw3_ac_a11_x7_126` 5. Macdonald / X.C | 7 | 574 (9, 7 184) | B1 103, B2 26, B3 21 | **Only B3.** The division, B1 (4 foot) and B2 (2 horse) are blocked by caps |
| `ntw3_ac_b17_x7_281` 10. Blücher / Schlesien | 7 | 522 (11, 5 225) | B1 256, B2 12, B3 0 | **Only B3,** which is 0 gold (n = 1). The division, B1 (8 foot copies) and B2 (2 horse) are blocked |

These divisions hold 46 cards (37 units, 9 commanders), all flagged `lua_differs` with
`lua_note = tagged_support_division`.

**Davout and Blücher agree with the Lua in practice.** Every Lua-only rebate there needs
more artillery than the caps allow. The Davout exception (B5 and B6 keep their rebate) is
exactly what the Lua gives for the groups that can be completed.

**Three cheap groups would show the difference in game:**

| Build (nothing else from that division) | List | Lua price | App price |
|---|---|---|---|
| Reynier / VII.C d4 B1: both foot batteries, 1. Fußbatterie 924 + 2. Fußbatterie 527 | 1 451 | 1 437 (−14) | 1 451 |
| Reynier / VII.C d4 whole: + Infanterie-Schützen × 2 (365 × 2) | 2 181 | 2 116 (−65) | 2 181 |
| Macdonald / X.C d3 whole: two foot batteries 96 + 678, horse battery 959 | 1 733 | 1 699 (−34) | 1 733 |
| Macdonald / X.C d7 B3: Pioniere 591 + Schützen 248 × 2 | 1 087 | 1 066 (−21) | 1 087 |

**What agrees with the Lua:**

- **The other 165 support divisions are untagged in game:** 163 inferred final divisions
  (731 cards), Bonaparte / Italie.C d5 (the override) and one division-0 reserve. The Lua
  gives untagged cards nothing, so "support earns nothing" and "untagged earns nothing"
  coincide.
- **202 commanders have no tag of their own:** 201 whose placement the builder inherits,
  and 1 in the Bonaparte override. All sit in those untagged support divisions. They would
  not count toward completion in the Lua, but no rebate is at stake either way.
- **The other 5 426 commanders carry their own tag.** No tagged card points at a group the
  Lua roster lacks; in the Lua that would be a nil-index error.
- **Float and integer floors agree** on every group (§2).

## 6. Rebates across the 238 corps

**Coverage:**

- **224 corps have rebate-eligible groups:** 2 519 brigades and 979 divisions.
- **14 AC corps have no regular units at all,** only a staff general. These are 4.
  Dąbrowski and the 1813 German Campaign entries: Napoléon / Centre, Ney / Nord, Murat /
  Sud, Garde impériale / Centre, Bertrand / Réserve, Hessen-Kassel / Slesvig, Bernadotte /
  Norr, Blücher / Schlesien (12.), Kleist / Böhmen, Barclay de Tolly / ZA.I, Konstantin /
  ZA.R, Bennigsen / Polsha and Gyulay / Lindenau.
- **Regular cards:** 6 426 are rebate-eligible, 778 sit in support divisions, and 1 has no
  placement (`ntw3_inf_line_290_999_7045` in `ntw3_ac_a17_x6_290`).

**"Completable"** means the group's full roster, taken alone, passes the app's card limits
and fits under 10 000 in the best brigade order under the recruit-order rule. This is
confirmed by replaying `affordableSubset` on all 962 eligible divisions that pass the card
limits. Commander costs are not included.

**Rebate % of roster cost:**

| Population | n | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| Brigades (eligible) | 2 519 | 0.00 | 0.98 | **2.96** | 4.95 | 18.00 | 3.07 |
| Brigades, completable | 2 513 | 0.00 | 0.98 | 2.96 | 4.95 | 18.00 | 3.06 |
| Divisions (eligible) | 979 | 0.00 | 4.99 | **8.97** | 12.99 | 64.00 | 9.51 |
| Divisions, completable | 888 | 0.00 | 4.98 | 7.99 | 11.98 | 29.00 | 8.57 |
| Full corps, % of eligible roster | 224 | 2.58 | 7.44 | **9.97** | 12.66 | 35.86 | 10.73 |
| Full corps, % of all regulars | 224 | 2.11 | 6.47 | 8.53 | 11.54 | 34.44 | 9.68 |
| Best division per corps | 224 | 3.00 | 10.24 | 13.00 | 17.00 | 64.00 | 14.81 |
| Best completable division per corps | 223 | 1.99 | 9.00 | 11.99 | 15.99 | 29.00 | 12.75 |
| Mean brigade per corps | 224 | 0.56 | 2.35 | 2.97 | 3.94 | 10.32 | 3.18 |

**Per regular card** (each card weighted once), the median brigade rebate is 3.95% and the
median division rebate is 11.00%.

**Group sizes:**

- Brigade n has a median of 4 (range 1–19).
- Division n has a median of 10 (range 1–65).
- **297 brigades are a single card** (n = 1). They are eligible but worth 0 gold.

**Divisions that cannot be completed:** 91 of the 979 eligible divisions.

- **74 cost too much:** more than 10 000 even in the best order.
- **7 exceed 31 cards.** The largest is 6. Dorsenne / Nord d1 at n = 65: 64% on paper,
  23 854 gold.
- **The other 10 break an artillery or heavy-cavalry cap.**
- Only 6 brigades cannot be completed.
- The largest completable division rebate is 29% (n = 30): 10. Schwarzenberg / Böhmen d1
  and 9. Osten-Sacken / Sileziya d4.
- **5. Neipperg / Italien.L has no completable division.** Both of its divisions cost
  more than 10 000.

**The full-corps rebate is a density measure, not an achievable saving.** It assumes every
eligible division is complete, which far exceeds 31 cards and 10 000 gold. It is inflated
by divisions that cannot be completed. The largest saving in one legal build is an
optimiser question.

**Smallest and largest full-corps rebate** (% of the eligible roster):

| Smallest | % | Largest | % |
|---|---|---|---|
| 7. Pajol / I.RC | 2.58 | 6. Dorsenne / Nord | 35.86 |
| 8. Kellermann / III.RC | 2.99 | 7. Bülow / Nord | 30.73 |
| 9. Murat / RC | 3.90 | 10. Masséna / Portugal | 26.90 |
| 8. Garde impériale (`a05_x4_096`) | 4.47 | 6. Johann / Tirol | 24.57 |
| 9. Dokhtourov / RK | 4.49 | 11. Schwarzenberg / Böhmen (`b16_x7_273`) | 23.99 |

- **The smallest are mostly cavalry reserve corps.** Their divisions are small, with n of
  2–8 (Pajol: 3, 3, 4, 4). The largest are driven by one oversized division.
- **The rebate shows no trend with corps number.** Median full-corps rebate by N:

  | N | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | Median % | 5.59 | 11.17 | 9.89 | 9.49 | 9.33 | 9.84 | 9.44 | 11.68 | 11.51 | 10.58 | 10.99 |
  | Corps | 3 | 7 | 23 | 28 | 43 | 38 | 32 | 23 | 16 | 7 | 4 |

- **By side:** Empire 9.27% (108 corps), Coalition 10.53% (116).
- **By ToW copy:** the 17 AC-only corps (no ToW copy, 612 regular units) have a median of
  11.30%, against 9.89% for the 207 corps that are copied whole.

**Odd caps.** Nine cheap militia, irregular and line units have caps of 8–14, for example
Humbert / Irlande militia (cap 14) and Johann / Tirol militia (cap 11). They make n, and so the
rebate, large without making the group expensive.

## 7. Files

- **`analysis/ac_discounts.py`** builds everything here and runs the self-checks. Run it
  from the repo root (~1 min, single process): `py -3.13 analysis/ac_discounts.py`.
  - **Self-checks:** row counts; Lua tags against builder placements; independent group
    totals; all 3 498 eligible groups selected in full give exactly the stated rebate, and
    one copy short never completes; 250 commander stand-ins; 238 full-corps selections;
    the 5 645 build and its real-data analogue; float floors; the affordability replay;
    the ToW-copy counts.
- **`analysis/output/ac/ac_discounts.csv`** has one row per AC card (13 116: 7 205 units,
  5 628 commanders, 283 staff). Its columns:
  - list price, cap and app placement;
  - `support_division`;
  - brigade and division n, roster cost, rebate (gold and %), and effective price (empty
    when not eligible);
  - `lua_differs` and `has_tow_copy`;
  - extras: `base_unit_key`, `underlying_unit_class`, `placement_source`, the eligibility
    and completability flags, and the Lua's own tag, rebates and `lua_note`.
- **`analysis/output/ac/ac_corps_discounts.csv`** has one row per corps (238): N, side,
  ToW copy, group counts (including ineligible ones), roster costs, full-corps rebate
  (gold, % of the eligible roster, % of all regulars), best division % (all and
  completable), mean brigade %, completable division count, and Lua-differing cards.
