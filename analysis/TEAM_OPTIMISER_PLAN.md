# AC build optimiser and best 4-corps teams — plan and progress

> **Resume here.** Plan approved by the user (2026-10-10), with a progress checklist updated after
> every step. A fresh session reads this file and continues with the first unticked step.
> Python: `py -3.13`. Checkpoints: `analysis/.cache/teams/`. Commit only when the user asks.

## Progress

- [x] **A−1. AC pricing study committed** (`b45ec6af`).
- [x] **A0. Plan saved** here.
- [x] **A1. Value bases** — `analysis/team_values.py`: `sb` (pooled size-band model at corps 8), `full`, `noise`; size-effect test.
- [x] **A2. AC build optimiser with rebates** — `analysis/ac_builds.py`, recruit-order check, 224 corps × 4 versions (sb, full, noise + model-free `price`).
- [x] **A3. Team search** — `analysis/team_search.py` (k = 4; k = 3 legal, future).
- [x] **A4. Report and app files** — `analysis/TEAM_BUILDS_REPORT.md`, exported builds.

### Log

- A−1, A0 done.
- A1 done: `analysis/team_values.py` → `analysis/output/teams/values_ac.csv` (7 198 units + 5 627 commanders, versions raw/sb/full/noise), `values_tow_sb.csv`, `value_bases.md`, `sb_cv.json`. Deviation from plan: no pooled refit — AC and ToW/Custom teams never mix, so each pool uses its own fits (AC from the AC study's checkpoints, ToW from the ToW ones); `harmonise_by_size` gained an `oof=` argument for AC's own V4 errors. sb (F6, 240+ merged into 180+) CV: AC 25.55/41.03/44.84, ToW 22.38/31.38/25.74. Size test: sb moves values like full harmonisation (40–80 and 180–240 infantry ×0.91–0.96 both; noise ≈1.0), but keeps 240+ mass near raw (full ×0.75); what sb removes predicts winning +0.217 ± 0.117 (z 1.9) vs full +0.317 (z 3.0) — the user's suspicion holds.
- A2 done: `py -3.13 analysis/ac_builds.py` (all versions, ~6 min) → `analysis/output/teams/ac_build_summary_<v>.csv` (per corps: cards, list_cost, rebate, final_cost, value, efficiency, value_sb, groups, combat generals, staff) and `ac_builds_<v>.csv` (per card, in verified recruit order). `--check` verifies: rules-engine cost ≤ MILP cost on every corps (lower on 6–12 corps only because the build completes an extra group the MILP didn't need to count), recruit-order replay (`ac_discounts.affordable_prefix`) and `check_known_limits` pass on all 224, brute force over all 64 group-completion patterns matches the MILP on 3 corps, all 4 versions. All 224 corps get a legal build.
- **User addition (2026-10-10): model-free `price` version.** "for single ACs you could add a direct optimisation without the price model: just use the real price and try to get maximum value from formation discounts. with discounts you can often bring an army whose face value is above 10k". Implemented as version `price` in ac_builds.py: value = list price (staff too), no command correction, tie-break 1e-5 × sb value, mip_rel_gap 1e-8. Result: median face value 11 014 for 10 000 (median rebate 1 027); 207/224 corps > 10 500, 118 > 11 000, 9 > 12 000; best 9. Reuß-Plauen / Italien.R 12 623. Face value is per-corps scale (∝ 1/N), so it is reported per corps, not used to rank teams. Phase B: offer it in the app as an AC Optimise mode ("max face value").
- **Next (A3):** write `analysis/team_search.py`. Inputs: AC `ac_build_summary_{sb,full,noise}.csv` (value per corps = best build's value; corps_number = N; theatre = 3rd key part); ToW/Custom from `analysis/output/cost_effective_builds*.csv` (`full`/`noise`) and an `sb` run (ToW sb builds not yet made — add an `sb` size mode to cost_effective_builds.load_cards reading `values_tow_sb.csv`, or skip sb for ToW and say so). Enumerate 4-subsets per theatre / per side, T = Σ N, best by total and by weakest per T, balanced-vs-lopsided test.
- A2 addendum: `ac_builds.py --no-rebates` → `ac_build_summary_<v>_norebate.csv` (sb/full/noise), the counterfactual for "how much do rebates change the ranking". Summaries now carry `value_sb` (every version's build valued on the size-band scale).
- A3 in progress: `analysis/team_search.py` written (reads the AC summaries; re-runs ToW/Custom "four corps" builds per version via `ceb.load_cards` + `ceb.army_builds`, `sb` by swapping in `values_tow_sb.csv`; caches `analysis/.cache/teams/tow_builds_<v>.pkl`). Outputs teams_ac.csv, teams_tow.csv, best_teams.csv (scope pool/all × criterion total/weakest × version), team_search.json/.md. Real Custom armies all have a known side (DK, FR imperial; GB, HRE, PS coalition). If interrupted: re-run `py -3.13 analysis/team_search.py` (ToW builds resume from the cache).
- A3 done (`py -3.13 analysis/team_search.py`, ~2 min cold, 10 s cached): AC 4 869 teams over 29 theatres; ToW/Custom 44 815 distinct (67 310 with repeats). Outputs in analysis/output/teams/: teams_ac.csv, teams_tow.csv, best_teams.csv (scope pool|all), value_per_point.csv, team_search.json/.md. Findings: AC value ∝ N^0.95–0.99, so balance barely matters (6+6+12+12 vs 9×4: −0.25%; within-cell slope +0.5%/SD N, ρ 0.08); ToW balanced better (−2.4%/SD, ρ −0.25). Rebates: corps value +6% median (p90 11%, max 21%), team ranking ρ 0.989 but best team per (theatre,T) changes in ~45% of cells (by total). Versions: AC sb vs full ρ 0.987, same best 67%/81% (total/weakest); ToW sb vs full ρ 0.957, same best only 30%/35%. Bargains robust in all versions: Kellermann III.RC +35%, Chasteler VIII.K +30–46%, Uxbridge CC +20%; Davidov/Narod +75% in sb is largely the model's large-militia weak spot (Kourin's 552-model card sb 2 882 vs full 1 105), still +38% in full. ToW: US 1812 and Polska 1809 in nearly every best imperial team.
- A4 in progress: `analysis/export_team_builds.py` done → app_builds_ac_sb/ (224), app_builds_ac_price/ (224), app_builds_teams/ (94 backup files, sb, best per T over all pools, by total and weakest); every AC build re-priced exactly through recruit-order replay. Remaining: write `analysis/TEAM_BUILDS_REPORT.md`, update analysis/HANDOFF.md + README pointers.
- **User note (2026-10-10): German Campaign 1813 (a16/b16) is WIP in the mod — ignore it.** `ac_builds.py` now skips `WIP_THEATRES` (only 11. Schwarzenberg / Böhmen was affected; b16 never formed a team). Re-running: ac_builds (4 versions), --no-rebates, --check, then team_search, export_team_builds, then refresh every number in `analysis/TEAM_BUILDS_REPORT.md` (draft written; tables are `<!-- TABLE:... -->` markers filled from best_teams.csv / value_per_point.csv / teams_ac.csv by a scratch script — regenerate them the same way).
- A4 done. Re-run without a16/b16: 223 corps × 4 versions built and checked (engine ≤ MILP everywhere, lower on 5–11; brute force OK), team search re-run (4 869 AC teams over 28 theatres; every curve/balance/rebate/version/bargain number unchanged), 223 + 223 AC app builds re-priced exactly, 94 team files. `analysis/TEAM_BUILDS_REPORT.md` written; its tables refresh with `py -3.13 analysis/team_report_tables.py` (paired `<!-- TABLE:x -->` / `<!-- /TABLE:x -->` markers). HANDOFF §3 + §8 item 6 and README pointer added. **Phase A complete; nothing committed** (user commits on request). Next, when the user asks: phase B (app) or teams of three.

## Phase B — the optimiser in the app (approved 2026-10-10)

> **Resume here for phase B.** The full approved plan is copied below the checklist. Tick each step and
> add a log line when it's done. Commit only when the user asks.

- [x] **B0.** Exact recruit order in the Python model (`ac_builds.py`: g/q columns, affordability rows,
      shared group order ≺, brigade-by-brigade recruit order); re-run ac_builds (4 versions, --no-rebates,
      --check → 0 cuts), team_search (+ army_values.csv), export_team_builds, team_report_tables; refresh
      TEAM_BUILDS_REPORT numbers.
- [x] **B1.** Export + pipeline: values CSV with value_size_bands, pool params {tow, ac}, army values CSV,
      SCHEMA_VERSION 3, bestBuildValue on corps entries; regenerate data.
- [x] **B2.** Types and loaders (`types.ts`, `load.ts`).
- [x] **B3.** Solver options (`solveLp.ts`, worker, `test/highs.ts`, cancelSolves).
- [x] **B4.** ToW golden LP test, then the mode refactor (allowedModes, normaliseSettings, cardValue).
- [x] **B5.** `acOptimiser.ts` + verify/cut loop + `acOptimiser.test.ts`.
- [x] **B6.** Fixture (`--fixture`, 3 AC armies × 3 modes) + parity tests.
- [x] **B7.** Builder + OptimiseModal for AC.
- [x] **B8.** Team conflict rule, `teamSuggest.ts`, plan helpers, tests.
- [x] **B9.** `ensure` in usePlanRosters, `teamBuild.ts`, tests.
- [x] **B10.** SuggestTeamModal, PlannerScreen button, TeamConflictWarning.
- [x] **B11.** Docs (HANDOFF §4.6 + planner, OPTIMISER_PLAN note, CLAUDE.md commands).
- [x] **B12.** Full checks: typecheck, lint, test, pytest; manual check in the dev server.

### Phase B log

- B plan approved. User decisions: AC modes Quantity / Size bands / "Formation discount only" (AC only); ToW/Custom keep Quantity / Quality; default Quantity. Team ranking: precomputed values when unconstrained, live optimisation when constrained. Picking a team fills the plan and builds each army (Undo). Partial plans: "Optimise remainder" toggle vs full overwrite. Mixed teams refused with a named conflict. Teams of 3 future.
- B0 in progress: `ac_builds.py` now has the affordability rows (q columns, ≺ = rebate − credit descending — corrected from the plan's plain rebate order by the exchange argument with division credits; `group_order_key`, `division_credit`, `in_group`, brigade-by-brigade `recruit_order`), MIP gap 1e-6 (models) / 1e-8 (price). Spot test: 0 cuts on 6 corps that needed up to 10; Eugène / Italie sb 17 713 → 18 647 (old cuts were suboptimal); all < 1 s. Next: full re-run (4 versions, --no-rebates, --check), team_search + army_values.csv, export_team_builds, team_report_tables, refresh report numbers.
- B1–B4 code done (not yet run end to end): export_optimiser_values.py rewritten (pools, AC values, army values CSV, AC parity builds); build_web_data.py schema 3 (+ unittest cases; pytest isn't installed — run `py -3.13 -m unittest tools.tests.test_build_web_data tools.tests.test_army_builder_rules`, 45 OK); types/load.ts (OptimiserValue {quantity, quality?, sizeBands?}, ValueMode, OptimiserMode + formationDiscount, CorpsEntry.bestBuildValue); solveLp SolveOptions/cancelSolves/SolveCancelled/retry; optimiser.ts refactored (problem = parts + rows; renderOptimiseLp(problem, cuts); cardValue; allowedModes/normaliseMode; AC rebate rows; verify → cut → fallback loop) + new acOptimiser.ts. Golden ToW LP snapshots (optimiser.golden.test.ts, written before the refactor) still match; 24 optimiser tests pass.
- B0 done: full re-run, 0 cuts in all 4 versions × 223 corps (was 45–125 corps/version); 11–12 corps/version improved (max +11%, Steinheil F.K), none worse; team_search (+ army_values.csv), export_team_builds, team_report_tables re-run; TEAM_BUILDS_REPORT prose refreshed (best face value now 5. Steinheil / F.K 12 687; campaign gaps ±6%). B1 done: export → 25 038 card values (ToW unchanged: 0 of 12 226 rows differ), build_web_data schema 3, 0 validation errors, 223 AC factions with optimiser data, 278 army values on corps-index. B6 done: fixture with 3 AC armies × 3 modes; parity test tightened (final cost, list cost, rebate, completed groups equal Python; 0 cuts) — 22 pass. Next: B5 unit tests (acOptimiser.test.ts), then B7 Builder UI.
- B5 done: acOptimiser.test.ts (11 cases: modes, brigade rebate > 10 000 list, division replaces brigades, affordability trap refused with 0 cuts, ≺ order contiguous, remainder, support division / Davout exception, comparator, combat cap, formation discount, stub-solver cut → fallback). buildValue's groupsCompleted counts only groups with discount > 0. Full web suite 495 pass; typecheck + lint clean. Next: B7 (Builder.tsx gate + OptimiseModal modes/summary).
- B7 done: Builder shows Optimise for every army (disabled without data; WIP-1813 tooltip via acOptimiser.isWorkInProgressCorps), message and modal show list − discounts and formations, fallback warning; OptimiseModal takes factionKey, lists allowedModes, hints for Size bands and "Formation discount only". Typecheck + lint clean. Next: B8 (teamRule conflict, teamSuggest.ts, plan helpers).
- B8 done: teamRule.planTeamConflict/teamConflictText (pool | theatre | side; opposite-side campaign corps reported as side) + tests; planSummary.corpsPoints exported; new state/teamSuggest.ts (teamPools, poolsFor, teamModes, precomputedValue, needsLiveValues, candidatesOf, suggestTeams, reachableTotals, teamOptimiseSettings, TEAM_SIZE=4) + teamSuggest.test.ts; plan.ts emptyBuildFor / applySuggestedTeam (keep vs overwrite) / fillPlaceholder (TeamPlaceholder). 509 web tests pass. Next: B9 (usePlanRosters ensure, state/teamBuild.ts).
- B9 done: usePlanRosters.ensure(key) (shared promise cache; retry semantics unchanged); new state/teamBuild.ts (optimiseArmy, optimiseArmies, cachedArmy, liveArmyResults, clearLiveArmyCache; full roster, no filters; offline roster → per-army error) + teamBuild.test.ts. Next: B10 UI (SuggestTeamModal, PlannerScreen button + TeamConflictWarning, App passes ensure).
- B10 done (code + logic verified; NOT yet eyeballed in a browser): components/SuggestTeamModal.tsx (pool, points, best by total/weakest, value mode per pool, optimise-remainder toggle, build settings → live values with progress/cancel, repeats for ToW, top 5, Use this team → applySuggestedTeam + per-army optimise with progress/cancel, errors listed); PlannerScreen: Suggest team button (disabled + tooltip on conflict), Undo suggestion, TeamConflictWarning (PlanParts) in the strip; App passes planRosters.ensure. 512 tests pass, typecheck + lint clean. E2E on real generated data (temp test, deleted): Reuß-Plauen formation discount list 12 643 / final 9 994 / rebate 2 649 (= Python), Steinheil 12 687 (= Python), Russia 1812 T40 suggestion = best_teams.csv in both modes (~1 ms). Next: B11 docs, B12 checks + browser look.
- B11 done: docs/HANDOFF.md §4.6 (AC model, modes, tests, refresh) + new §4.7 (team suggestion); OPTIMISER_PLAN.md superseded note; CLAUDE.md commands; README features (AC optimise, Suggest a team). B12 done: typecheck 0 errors, lint clean, 512 vitest pass, `npm run build` OK, Python tool tests 63 OK (test_database_builder needs pandas, not installed for py -3.13 — unrelated). **Phase B complete except a by-eye check of the UI in a browser (the user, dev server on 127.0.0.1:5173). Nothing committed.** Future: teams of three (k=3 is supported in teamSuggest/team_search; UI offers 4).

### Phase B plan (copy)

#### Plan: the optimiser in the app — Army Corps builds and team suggestions (phase B)

#### Context

Phase A, the analysis, is done and logged in `analysis/TEAM_OPTIMISER_PLAN.md`. It produced:
- an Army Corps (AC) build optimiser with formation rebates (`analysis/ac_builds.py`);
- a model-free "real prices" mode;
- the best 4-corps teams per points total (`analysis/TEAM_BUILDS_REPORT.md`).

The user now wants this in the app. Today the Builder's **Optimise** covers only Theatre-of-War (ToW) and Custom armies:
- `web/src/state/optimiser.ts`, HiGHS WASM in a worker;
- the budget row has no discounts;
- `Builder.tsx` L164/L1040 hides the button for `_ac_` factions;
- no AC values ship.

The Ordre de Bataille planner has no team suggestion. It only filters pickers when a plan mixes pools, and gives no standing warning.

**User's decisions:**
- **Value modes.**
  - **AC:** Quantity / **Size bands** / **"Formation discount only"** (the real-prices mode; AC only).
  - **ToW and Custom:** keep Quantity / Quality.
  - **Default:** Quantity everywhere, unchanged.
- **Team ranking.**
  - When nothing constrains the suggestion (no units kept, default settings), use each army's precomputed best-build value: instant and offline.
  - When something does (a card cap, no staff, single roll off, kept armies with units), optimise every candidate army live.
- **Picking a team** fills the plan and builds each army with the optimiser, with Undo.
- **Partial plans** get a toggle, like the Builder's: "Optimise remainder" (keep the current armies and their units, fill the rest) or full overwrite.
- **Mixed teams are refused.** Suggest is disabled with a message naming the conflict (from the earlier plan).
- **Teams of three** are legal but future: the code takes `k`, and the UI offers 4.

**A finding that shapes the plan.** The offline AC optimiser needed no-good cuts on 45–50 of 223 corps (model versions) and 125 (face value), up to 10 per corps. Those cuts ban whole rebate patterns, so some "optima" aren't optimal, and in the app they would mean 10–20 s solves.

**Fix:** put the app's recruit-order affordability rule *into* the model, in both Python and TypeScript. Verify-and-cut then stays only as a safety net. The phase A numbers will be refreshed; builds can only improve.

#### Step 0 — Exact recruit order in the model (Python first)

`analysis/ac_builds.py` `solve_corps`.

**Order.** A static order ≺ over rebate groups: rebate descending, then division before brigade, then division id, then brigade id. Recruiting the larger rebate first is optimal by an exchange argument, because a group's list cost is ≥ its rebate.

**Per group k:**
- a binary `g_k` (completed);
- a continuous `q_k` (list cost of its new members);
- `q_k ≥ Σ_{j∈k} cost_j·x_j − M_k(1−g_k)`;
- an affordability row at its completing card:
  `staff + Σ_{h≺k}(q_h − r_h·g_h) + q_k − credit_k·g_k ≤ 10 000 − F`.
  - `credit_d` = Σ brigade rebates − the smallest brigade rebate, for a division recruited brigade by brigade (largest first).
  - `credit_k` = 0 for brigades.
- Loose cards come after all groups, and always fit when the final cost is ≤ 10 000.

**Recruit order output:** within a division, brigade by brigade.

**Keep verify-and-cut** (`affordable_prefix` + `calculate_army_cost` + `check_known_limits`) as the safety net, and fix the docstring.

**Also:**
- `team_search.py` writes `analysis/output/teams/army_values.csv`: faction, pool, N, and best-build value per version.
- Re-run:
  - `ac_builds.py` (4 versions, `--no-rebates`, `--check`; expect 0 cuts);
  - `team_search.py`, `export_team_builds.py`, `team_report_tables.py`.
- Update the prose numbers in `TEAM_BUILDS_REPORT.md`.

#### Step 1 — Data pipeline

**`analysis/export_optimiser_values.py`:**
- **Values CSV:** `data/generated/ntw3_optimiser_values.csv`, columns `faction_key, unit_key, value_quality, value_quantity, value_size_bands`. Blanks are allowed.
  - ToW/Custom fill quality (full) and quantity (noise), as today.
  - AC fill quantity (`values_ac.csv` `value_noise`) and size bands (`value_sb`).
  - Skip the WIP theatres via `ac_builds.WIP_THEATRES` (`a16`/`b16`).
- **Params:** `ntw3_optimiser_params.json` becomes `{pools: {tow: {...}, ac: {...}}, generated, source}`.
  - `lambda` gains `size_bands` (0.0045).
  - The `ac` block uses the AC T3 refit from `analysis/output/ac/ac_staff.json` (`t3_b` 82.99, `t3_q` 1.34).
- **New** `data/generated/ntw3_optimiser_army_values.csv`, from `army_values.csv`: AC quantity and size bands; ToW/Custom quantity and quality (the one-roll build).
- **`--fixture`:** add the AC armies below. `FIXTURE_FIELDS` gains `name, division, brigade, placementSource`; support-division detection needs them.

**`tools/build_web_data.py`:**
- `SCHEMA_VERSION` 2 → 3.
- `roster["optimiser"]` takes the pool block (`ac` when `_ac_` is in the key, otherwise `tow`), so each faction file keeps one flat params block.
- Attach `bestBuildValue` to the corps entries in `corps-index.json`. It is precached by Workbox and always loaded, so ranking works offline; it adds about 20 KB.
- Add build-report counts.

**`web/src/domain/types.ts`:**
- `OptimiserValue {quantity; quality?; sizeBands?}`;
- `OptimiserMode = "quantity" | "quality" | "sizeBands" | "formationDiscount"`;
- `OptimiserParams.lambda` gains `sizeBands`;
- `CorpsEntry.bestBuildValue?`.

**`web/src/data/load.ts`:** the normalisers for the new shapes. Schema-2 data simply leaves the optimiser off.

`SAVE_FORMAT_VERSION` stays the same: saved builds and plans don't change. Offline caches reset, as after any data change.

#### Step 2 — AC in the optimiser

**New `web/src/state/acOptimiser.ts`**, used by `optimiser.ts` when the faction is AC.

**Before refactoring:** add a golden test of today's ToW LP text. With no groups, the ToW LP must stay byte-identical.

**Model** — the same as step 0:
- **Groups:** `rebateGroups` from the existing `buildRosterTotals` + `groupDiscount` (`web/src/rules/rules.ts`; no rules edits, so no parity-pair churn).
  - Drop groups that can't be completed. Drop groups already complete in kept cards; their rebate is inside `F = priceBuild(kept).finalCost`.
  - A division whose kept brigades are complete gets `r'_d = r_d − Σ` of those brigades' rebates.
- **Rows:** completion `Σx + kept ≥ n·g` (combat generals count), `g_b + g_d ≤ 1`, the budget minus `Σ r'·g`, the `q` links and the affordability rows.
- **Shared comparator:** `compareRebateGroups`. TS and Python must sort identically.

**Modes:**
- `cardValue(card, mode)`. `formationDiscount` uses `cost + 1e-5·sizeBands`, with staff valued `cost + 1e-5·T3` and no command correction.
- `allowedModes(kind)`: ToW/Custom `[quantity, quality]`; AC `[quantity, sizeBands, formationDiscount]`.
- `normaliseSettings` falls back to `quantity` for a mode the kind doesn't allow.

**Decode (AC):**
1. Kept instances first, in the player's order.
2. Completed groups in ≺ order, brigade by brigade inside divisions, members by descending cost.
3. Loose cards.

The staff general goes in `staffSlotUnitKey`. `priceBuild` recruits it first, as Python does.

**`optimiseBuild` loop:** solve → decode → verify.
- **Verify:** `priceBuild.finalCost ≤ 10 000`, equal to `calculateArmyCost` (every rebate earned), and `summarize().limits.valid`.
- **On failure:** append the no-good row and solve again.
- **Limits:** `MAX_CUTS` = 5 and a 30 s budget.
- **Last resort:** solve without rebates, and tell the user.

**Supporting changes:**
- `OptimiseProblem` keeps `rows[]` so cuts can be appended.
- `OptimiseSummary` gains `listCost`, `rebate` and `groupsCompleted`.
- `solveLp.ts` / `optimiser.worker.ts` / `test/highs.ts`: `LpSolver(lp, opts?: {timeLimit, mipRelGap})`. MIP gap 1e-6 for the models, 1e-8 for `formationDiscount`, matching Python.
- `cancelSolves()`, for the planner's Cancel.

#### Step 3 — Builder UI

**`web/src/components/Builder.tsx`:**
- Show Optimise for every kind, disabled when there is no `roster.optimiser`.
- The tooltip for `a16`/`b16` says "German Campaign (1813) is still a work in progress in the mod".
- Pass `kind` to the modal.

**`web/src/components/OptimiseModal.tsx`:**
- The mode control lists the kind's allowed modes.
- "Formation discount only" has the hint: "Ignores unit stats. Uses the game's own prices to field the most list value: an Army Corps can field over 10 000 thanks to brigade and division discounts."
- Single roll stays ToW only.
- For AC, the result line reads e.g. "9 998 gold (list 11 041 − discounts 1 043, 4 formations) · value …", plus a notice if the no-rebate fallback was used.

#### Step 4 — "Suggest a team" in the Ordre de Bataille planner

**`web/src/domain/teamRule.ts`:**
- `planTeamConflict(slots, keys)` walks the filled slots with the existing `joinTeam` and returns `{kind: pool | theatre | side, first, second}`.
- `teamConflictText` turns it into a message like: "Army 3 (5. Davout / III.C, Army Corps · Germany (1805)) and Army 1 ([1806] 10. Preußen, Theatres of War + Custom) can't share a team: Army Corps never mix with Theatres of War or Custom armies. Change or remove one to get suggestions."
- The same message shows as a standing `TeamConflictWarning` in `PlanParts.tsx`; today there is none.

**New `web/src/state/teamSuggest.ts`**, pure:
- `teamPools(index, keys, mode, k)` covers AC theatres by side and ToW+Custom per side. It needs a value and a numeric rating, which leaves out WIP and unrated armies.
- `suggestTeams(members, {total, k, criterion: total | weakest, mode, fixed[], repeats, limit})` enumerates combinations (at most about 36k, under 10 ms). It ranks by one criterion, breaks ties on the other, and returns `{teams, nearestTotals}`.
- `planPoints` gets a reused `corpsPoints`.

**Value source per army** (`teamValues`):
- **Precomputed `bestBuildValue`** when the army has no kept units and the settings are default: 31 cards, a staff general, single roll on for ToW.
- **Otherwise live:**
  - each candidate army is optimised with the suggestion's settings;
  - kept armies with units get a remainder optimisation of their build;
  - sequential through the one worker, with progress, Cancel and a session cache keyed by faction, mode, settings and kept build;
  - armies whose roster can't be loaded offline are skipped and listed.

**New `web/src/components/SuggestTeamModal.tsx`:**
- **Inputs:**
  - points total (default: the plan's total if it has 4 armies, else the median feasible total; the valid range is shown);
  - criterion (Best total / Strongest weakest army);
  - value mode (AC: Quantity / Size bands; ToW: Quantity / Quality; "Formation discount only" is left out because it isn't comparable across corps);
  - the **Optimise remainder** toggle (keep current armies and their units) or full overwrite;
  - max cards, allow no staff, single roll (ToW);
  - a pool picker when nothing is kept (AC theatre grouped by side, or a ToW+Custom side);
  - a "same army twice" toggle (ToW only; the Lua allows it).
- **Results:** the top 5 teams with flags, N, total and weakest; kept armies are marked; a note shows when values were computed live.
- **"Use this team":**
  - `applySuggestedTeam` in `web/src/state/plan.ts`, with `emptyBuildFor` moved there from PlannerScreen;
  - then a new `web/src/state/teamBuild.ts` `buildTeamArmies` runs the optimiser per army: fresh for new armies, remainder for kept ones with units;
  - progress and Cancel;
  - a result only lands if the slot still holds the placeholder build;
  - full overwrite asks for confirmation;
  - one-step **Undo** restores the previous plan.

**`PlannerScreen.tsx`:** a "Suggest team" toolbar button, disabled with the conflict text as its tooltip, and the warning above the armies.

**`components/usePlanRosters.ts`:** `ensure(key)`, a shared promise cache, so building and live ranking don't fetch twice.

#### Step 5 — Tests and parity

- **`optimiser.test.ts`:** the ToW golden LP; mode fallback.
- **New `acOptimiser.test.ts`** (synthetic rosters via `web/src/test/factories.ts` `makeUnit`):
  - a brigade rebate buys an extra card (list > 10 000, final ≤ 10 000);
  - a division replaces its brigades;
  - an affordability trap is refused or ordered with 0 cuts;
  - groups are contiguous in ≺ order and `priceBuild` = `calculateArmyCost`;
  - remainder: kept instances stay first and a completed brigade's rebate is earned;
  - a support division earns nothing, but the Davout key's brigade does;
  - the combat cap (9 − digit);
  - formation-discount efficiency > 1;
  - a stub solver forces cuts and then the fallback.
- **`optimiser.parity.test.ts`:** 3 AC armies × 3 AC modes against `ac_builds.solve_corps`, expecting 0 cuts.
  - `ntw3_ac_a11_x5_117` (Davout, the support exception);
  - `ntw3_ac_a03_x5_080` (Bonaparte, the placement override);
  - `ntw3_ac_a08_x5_242` (Eugène, 9 cuts before the fix).
- **New `teamSuggest.test.ts`:**
  - conflict kinds and their texts; side-less Custom armies fit;
  - totals hit T exactly; both criteria and their tie-breaks;
  - kept members; distinct AC armies and ToW repeats; excluded WIP and unrated armies;
  - k = 3 works; `nearestTotals`; precomputed vs live selection.
- **Elsewhere:** `plan.test.ts` (`applySuggestedTeam`), `teamBuild.test.ts` (node solver, failing loader, abort), `data.test.ts` (normalisers), and `tools/tests` for `build_web_data` (pool params, three value columns, army values).

#### Step 6 — Docs and progress

- `docs/HANDOFF.md` §4.6 is extended to AC: the model, affordability rows, modes and safety net. Add a planner-suggestion subsection.
- Add a note to `docs/OPTIMISER_PLAN.md`.
- Add the commands to `CLAUDE.md`.
- `analysis/TEAM_OPTIMISER_PLAN.md` gets a **phase B checklist and log**, updated after every step so a cut-off session resumes.
- Commit only when the user asks. The web release is labelled by date, and `package.json` semver stays the same.

#### Order of work

1. Step 0, with a re-run of phase A outputs and refreshed report numbers.
2. Export and pipeline (schema 3), then regenerate the data.
3. Types and loaders.
4. Solver options.
5. The ToW golden test, then the mode refactor.
6. `acOptimiser` with the verify loop and its tests.
7. The fixture and parity tests.
8. The Builder and modal.
9. The conflict rule, `teamSuggest` and the plan helpers, with tests.
10. `ensure` and `teamBuild`.
11. The modal, PlannerScreen and the warning.
12. Docs.
13. The full checks.

#### Risks

- **Formation-discount mode** at gap 1e-8 has many near-ties. The time budget and HiGHS incumbents cover it.
- **The HiGHS WASM worker** can abort after many solves. Retry once on a fresh worker.
- **Live ranking of a 32-army ToW side** takes about 30 s, so it shows progress and can be cancelled.
- **Planner values assume all cards.** Builds that respect the Builder's "Offered now" filter can land lower; the modal says so.
- **TS and Python must share the group order exactly**, or parity breaks on ties.

#### Verification

- `cd web && npm run typecheck && npm run lint && npm test`.
- `python -m pytest tools/tests`.
- `py -3.13 analysis/ac_builds.py --check`: every corps legal, with **0 cuts**. Each corps' value is ≥ its phase A value.
- **Parity tests:** the app's AC objectives match Python within 1e-6.
- **Manual, in the dev server (`npm run dev`):**
  - **Builder:** 9. Reuß-Plauen / Italien.R → Optimise → "Formation discount only" → list ≈ 12 600, final ≤ 10 000. The Builder's own price shows the same, and Undo works. The Size bands and Quantity builds are legal and priced identically by the Builder.
  - **Planner, empty plan:** Suggest → Russia (1812) Imperial, T 40 → teams appear instantly and match `best_teams.csv`. "Use this team" builds 4 armies with progress, and Undo restores the plan.
  - **Planner, a card cap of 20:** the "computed live" note appears.
  - **Planner, a plan mixing an AC corps and a ToW army:** Suggest is disabled, and the warning names both armies.

---

# Phase A plan (done)

## Context

The AC pricing study is done (`analysis/AC_PRICING_REPORT.md`). Its main findings:
- AC list prices follow the ToW price rule, plus a ~10% hand-set corps × class premium;
- formation rebates are exact: (n − 1)% off a completed brigade or division;
- size-band multipliers per class (F6) are the best size curve.

The user now wants the optimiser adapted, and in particular this question answered: **given a fixed
points total for a team, which combination of 4 corps gives the most cost-effective builds?**

**How the game scores teams** (`source/original lua files/ntw3.lua`):
- **Points:** `Faction_Points` / `Factions_Points_Sums`. A team's points are the sum of its armies'
  corps numbers N, the number that opens the name. The lobby only displays the sums; a fixed total is
  a player convention.
- **Team composition** (`Factions_Errors`):
  - AC corps must share one theatre code (the 3rd faction-key part, e.g. `a11`; it also fixes the
    side);
  - no AC corps twice;
  - AC corps may not mix with the ToW/Custom pool.
- **The app's ToW/Custom rule:** ToW and Custom armies form one pool and must share a side
  (`web/src/domain/teamRule.ts`).

**Data:**
- **30 AC theatres** with 4–14 corps each, so **4 869** AC teams of 4 distinct corps. The German
  Campaign 1813 theatres (`a16`, `b16`) have no rosters and are left out.
- **The ToW/Custom pool:** 55 armies over two sides.
- **AC combat-general cap:** 9 − the faction key's x-digit (`rules.ts` `generalCaps`), against 1 in
  ToW.

**User's decisions:**
- **Both pools:** AC theatres and ToW/Custom.
- **Rank teams two ways:** by total value and by weakest member.
- **A value toggle:** the new size-band model against the current adopted model with harmonisation.
  The user suspects the size bands absorb the real size effect, as full harmonisation does: test it.
- **Analysis first.** The app comes in a later phase. That phase must refuse mixed teams: an error
  message, or a disabled button.

## Phase A: analysis (this round)

**A−1. Commit the AC pricing study first** (user request), on branch `build-optimisation`:
- **In the commit:**
  - `analysis/ac_pricing.py`, `ac_discounts.py`, `ac_natural_experiment.py`;
  - `analysis/AC_PRICING_REPORT.md`, `AC_DISCOUNT_RULES.md`, `AC_STUDY_PLAN.md`;
  - `analysis/output/ac/` (16 MB of result CSVs and JSON);
  - `analysis/ac_blind/`: brief, data, scripts, REPORT.md / RESULTS.md / NOTES.md, outputs;
  - the README and `analysis/HANDOFF.md` updates.
- **Left out:** the 51 intermediate `analysis/ac_blind/out/*.npy` arrays (3 MB, binary, regenerated by
  its scripts), added to `.gitignore`. The checkpoints in `analysis/.cache/ac/` are already ignored.
- **Message:** a short summary of the study, with the attribution trailer. No push unless asked.

**A0. Saved progress.** `analysis/TEAM_OPTIMISER_PLAN.md`, a copy of this plan with a checklist,
ticked after each step. Checkpoints go in `analysis/.cache/teams/`. No commits.

**A1. Value bases.** New `analysis/team_values.py`, writing per-card values in each version:

| Version | How it is built |
|---|---|
| `sb` | The new **size-band model**: the adopted form with F6 size bands per class, fitted on AC + ToW + Custom together. Reuses `ac_pricing.py`: `size_form_run`, `with_bands`, the loaders. The thin top band (240+) is merged into 180–240 so the edge doesn't overshoot. Value = prediction at corps 8, coalition, with no army × class factor: one value scale for AC and ToW |
| `full` | The current adopted form (V4 at corps 8) with **full** size harmonisation |
| `noise` | The same, with **noise-only** harmonisation |

- For AC cards in `full` and `noise`, the harmonisation strata are estimated from AC's own V4
  out-of-fold errors (`ac_oof_*.csv` `oof_v4`). `harmonise_by_size` is generalised to take those
  errors instead of reading `price_database.csv`.
- **Commander versions:** the commander model on each version's regular values, as
  `cost_effective_builds.commander_values` does.
- **Staff generals:** T3 (AC refit for AC) plus the hand-set command correction (`Command`, same λ/σ
  per version).
- **Test of the user's suspicion** ("size bands absorb the real size effect like harmonisation"):
  - per size stratum, the median ratios `sb`/raw, `full`/raw and `noise`/raw: does `sb` track `full`
    or `noise`?
  - the ladder-replay check (ToW only; AC has no replays), reusing `size_replay_check`: does the part
    `sb` removes from raw value predict winning, as the bias part did (+0.44 ± 0.16)?

**A2. AC build optimiser with formation rebates.** New `analysis/ac_builds.py`, an MILP via
`scipy.optimize.milp`, as `cost_effective_builds.solve`.
- **Variables:**
  - unit copies x;
  - combat-general versions (binary);
  - one staff option (exactly one);
  - per eligible brigade a binary c_b, per eligible division a binary c_d (support groups excluded,
    as `ac_discounts.py` / `tools/army_builder_rules.py` decide).
- **Constraints:**
  - **completion:** Σ x over the group ≥ n_g · c_g (combat generals count);
  - **division replaces brigades:** c_b + c_d ≤ 1;
  - **budget:** Σ cost·x + staff cost − Σ rebate_g · c_g ≤ 10 000;
  - **cards:** at most 31 including staff (optional user cap, as `--max-cards`);
  - **generals:** combat generals ≤ the AC cap and at most one per unit;
  - **caps:** unit and cap-group caps, foot artillery 2, horse artillery 1 (2 if cavalry-only), heavy
    cavalry 10.
- **Objective:** Σ value · x + staff value (the command-correction linearisation reused), with a cost
  tie-break.
- **Recruit order**, which the app enforces (`build.ts` `affordableSubset`):
  - Each solution is ordered staff general first (the app's `recruitOrder`), then completed groups by
    descending rebate, then loose cards.
  - The order is replayed with the Python port `ac_discounts.affordable_prefix` and
    `army_builder_rules.calculate_army_cost`.
  - If a card fails, cut that build and re-solve.
- **Runs:** every AC corps with units (224) × the 3 value versions. Output:
  `analysis/output/teams/ac_builds_<version>.csv` (cards, cost, rebates, value, efficiency).
- **ToW/Custom builds:** `cost_effective_builds.py` already gives `full` and `noise`. Add the `sb`
  values through `load_cards` (a third size mode reading `team_values` output).

**A3. Team search.** New `analysis/team_search.py`, by plain enumeration.
- **Team size is a parameter `k`, default 4.** Teams of **3 corps are also legal** in game. This round
  runs k = 4 only; k = 3 is a noted future extension (same code, `--team-size 3`), not run or reported
  now.
- **AC:** every 4-subset of distinct corps in a theatre (4 869).
- **ToW/Custom:** every 4-subset on one side. Custom armies of unknown side fit either; side comes
  from `teamRule.ts` `CUSTOM_ARMY_SIDE`. The Lua doesn't forbid repeats in this pool, so a
  repeats-allowed variant is also reported.
- **Per team:** points T = Σ N; total value; weakest member's value; mean efficiency (value ÷ cost).
- **Per pool × T × version:** the best team by total, and the best by weakest member.
- **Output:** `analysis/output/teams/best_teams_<version>.csv` and the full table.
- **Questions the report answers:**
  - Is a balanced split of N better than a lopsided one at a fixed T? Price ∝ N^−γ with γ < 1 implies
    value grows concavely in N, so balanced should win unless corps-specific bargains or rebates
    override that.
  - Which corps are bargains for their points?
  - How much do rebates change the ranking?
  - Does the value version change the answer?

**A4. Report and app files.**
- **Report:** `analysis/TEAM_BUILDS_REPORT.md`, covering the value-basis test, AC build results, the
  best teams per theatre and total, and the balanced-vs-lopsided finding.
- **App files:** the best teams' builds as importable saves, via `export_builds_for_app.py`. AC
  instances must be written in the verified recruit order, because AC pricing is order-sensitive.

## Phase B: app (planned, a later round)

- **AC in the Optimise panel** (`web/src/state/optimiser.ts`):
  - rebate binaries and completion constraints in the LP;
  - the AC combat-general cap;
  - instances emitted in a recruit order that `priceBuild` accepts;
  - AC values shipped through the same pipeline;
  - the value toggle (size bands / quality / quantity).
- **Team suggestion in the Ordre de Bataille planner:** given a points total and the plan's pool,
  suggest the best 4 (by total or by weakest member).
  - **Mixed teams are refused:** when the plan mixes pools or theatres (`teamRule.ts`), the suggest
    and optimise buttons are disabled with a message naming the conflict.

## Files

- **New:** `analysis/team_values.py`, `analysis/ac_builds.py`, `analysis/team_search.py`,
  `analysis/TEAM_OPTIMISER_PLAN.md`, `analysis/TEAM_BUILDS_REPORT.md`, `analysis/output/teams/`.
- **Edited, small:**
  - `analysis/cost_effective_builds.py`: `harmonise_by_size` takes an errors source; an `sb` size
    mode;
  - `analysis/export_builds_for_app.py`: AC builds in recruit order.
- **Reused:**
  - `analysis/ac_pricing.py` (size forms, loaders, AC caches);
  - `analysis/ac_discounts.py` (`affordable_prefix`, group totals);
  - `tools/army_builder_rules.py` (`calculate_army_cost`, `check_known_limits`, `support_divisions`);
  - `cost_effective_builds.py` (`Command`, `commander_values`, `solve` pattern).
- **Unchanged:** the app (phase B), `rules.ts`, the pricing model's committed outputs.

## Verification

1. **Values.** The `sb` model's CV MAE on the pooled data is reported and matches the per-kind F6
   results in `ac_pricing_results.md` within noise. The size-stratum table shows `full`/`noise`
   reproducing today's ToW values exactly (off-switch regression, as before).
2. **AC builds.** Every build passes `check_known_limits`. `calculate_army_cost` equals the MILP's
   claimed final cost and rebates. The recruit-order replay keeps every card affordable. On 3 small
   corps, the optimum is checked by brute force over group completions.
3. **Team search.** Team counts match (4 869 AC). Σ N is correct, and no team breaks the Lua team
   rule (same theatre code, distinct corps) or the side rule for ToW/Custom.
4. **App files.** Every exported build re-prices in the app's rules to the reported cost.
