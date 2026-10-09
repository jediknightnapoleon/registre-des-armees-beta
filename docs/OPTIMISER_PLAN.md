# In-app build optimiser — plan and progress

> **Resume here.** This file is the plan for the in-app optimiser (approved by
> the user, October 2026) plus a progress checklist updated after every step.
> A fresh session should read this file, then continue with the first unticked
> step. Python: use `py -3.13` (a Node.js install put a bare Python 3.14 first
> on PATH). No commits unless the user asks.

## Progress

- [x] **0. Plan saved** to `docs/OPTIMISER_PLAN.md`.
- [x] **1. Data export** — `analysis/export_optimiser_values.py` → `data/generated/ntw3_optimiser_values.csv`, `ntw3_optimiser_params.json`, `web/src/state/__fixtures__/optimiser-parity.json`.
- [x] **2. Pipeline** — `tools/build_web_data.py` (+ test), `SCHEMA_VERSION` 1 → 2, `web/src/domain/types.ts`, `web/src/data/load.ts`; regenerate `web/public/data`.
- [x] **3. Pure model** — `web/src/state/optimiser.ts`, `solveLp.ts` (+ unit and parity tests).
- [x] **4. Worker + wasm wiring** — `optimiser.worker.ts`, `vite.config.ts` glob, Electron MIME.
- [x] **5. UI** — `OptimiseModal.tsx`, Builder wiring, `filteredCards`, CSS.
- [x] **6. Docs** — HANDOFF, CLAUDE.md, README; final checks.

### Log

**All steps done (2026-10-09).** Nothing committed.

- Step 0 done.
- Step 1 done: `analysis/export_optimiser_values.py` written and run → `data/generated/ntw3_optimiser_values.csv` (12 226 cards, 55 armies, both versions, all keys in the builder CSV), `ntw3_optimiser_params.json`, `analysis/output/optimiser_parity_python.json` (Python max-value + four-corps builds for Preußen 10, Napoli, HRE). Its `--fixture` stage runs after step 2.
- Step 2 done: `tools/build_web_data.py` merges the values (`load_optimiser_inputs`, `attach_optimiser_values`), `SCHEMA_VERSION` = 2; `tools/tests/test_build_web_data.py` +2 tests (56 pipeline tests pass via `py -3.13 -m unittest tools.tests.test_build_web_data tools.tests.test_army_builder_rules tools.tests.test_army_corps_catalog tools.tests.test_division_placement`; `test_database_builder` needs pandas, pre-existing). `web/public/data` regenerated: 55 armies, 12 226 valued cards, AC files untouched. `UnitCard.optimiserValue?`, `FactionRoster.optimiser?`, `OptimiserParams` in `domain/types.ts`; `load.ts` normalises them (`normalizeCard`, `normalizeOptimiserParams` exported). typecheck + 438 tests pass. Parity fixture written: `web/src/state/__fixtures__/optimiser-parity.json`.
- Step 3 in progress: `highs@1.15.3` installed (wasm 3.5 MB). `rules.ts` now exports `cappedClassOf` (no behaviour change). Written: `web/src/state/solveLp.ts`, `web/src/state/optimiser.ts`, `web/src/test/highs.ts` (Node HiGHS loader), `web/src/state/optimiser.parity.test.ts` — **12/12 parity cases pass** (same optimum + staff general as Python, no rule violations; 0.3–1.9 s per solve). Then `web/src/state/optimiser.test.ts` (9 tests: legal default build, card cap, no-staff toggle, remainder keeps build + caps, candidates only, one combat general, foot-artillery cap, single roll ≤ 4 corps, error messages). Step 3 done: 21 optimiser tests pass, typecheck + lint clean.
- Step 4 done: `web/src/state/optimiser.worker.ts` (HiGHS in a module worker, wasm via `highs/runtime?url`), `workerSolver` in `solveLp.ts`, `vite.config.ts` (`**/*.wasm` precache glob, `worker.format: "es"`), `electron/main.cjs` (`.wasm` → `application/wasm`). typecheck + `npm run build` pass. The `.wasm` is not emitted until the UI imports `workerSolver` (step 5) — re-check `dist/assets/*.wasm` and the precache manifest then.
- Step 5 in progress: `web/src/components/OptimiseModal.tsx` written; `Builder.tsx` wired (header "Optimise" button for ToW/Custom, state, `filteredCards` memo, `runOptimise` with `workerSolver`, Undo, modal in `modalOpen`, reset in the seed effect); `.opt-*` CSS in `styles.css`. typecheck + lint pass. Next: full `npm test`, `npm run build` (wasm emitted + precached), manual run in dev.
- Step 5 done: 459 tests pass; `npm run build` emits `assets/highs-*.wasm` (3.5 MB) and the SW precache lists it. Driven in Edge (playwright-core, scratchpad): Preußen 10 defaults → 24 cards, 10 000 gold, value 14 093 (= Python quantity/four corps), Kalckreuth, 4/4 corps, 1.9 s; Undo empties; Quality ≤ 20 cards → 17 cards, 14 177 (= Python); HRE → 27 cards, 13 217 (= Python), no Single-roll toggle; Army Corps → no button; no console errors. First click in a fresh dev session could hit Vite's lazy dep optimisation (page reload) → `optimizeDeps.include: ["highs"]` added.
- Step 6 done: docs/HANDOFF.md §3.6 (optional optimiser inputs, SCHEMA_VERSION 2) and new §4.6 (the optimiser), README feature paragraph, CLAUDE.md §3 command, analysis/HANDOFF.md command row. Final: typecheck, lint, 459 tests, build (wasm precached), 56 pipeline tests — all pass.

---


## Context

The analysis (`analysis/cost_effective_builds.py`) finds the most valuable legal build per army offline. The user wants the same in the app's corps build view: a panel that produces an optimised build for the current ToW or Custom army.

**Settings:**

| Setting | Default |
|---|---|
| Max unit cards | 31 |
| Quality / Quantity (fully harmonised values / noise-only values) | Quantity |
| Optimise remainder (keep the current build and fill the rest of the funds) | Off: rebuild the whole deck |
| Only filtered units | On |
| Allow no staff general | Off |
| Single roll (≤ 4 source corps), ToW only | On |

**User decisions:** Custom armies are included. Results apply immediately, with a toast.

**What exploration established:**
- The app has no solver.
- For ToW and Custom, the price is Σ card cost; there are no discounts.
- The app's rules (`web/src/rules/rules.ts`):
  - 31 cards including the staff slot;
  - staff generals: 0 or 1;
  - combat generals: cap 1;
  - shared cap groups;
  - at most 1 combat general per group;
  - foot artillery 2, horse artillery 1 (2 if the roster is cavalry-only), heavy cavalry 10, counted by the unit a combat general leads.
- App unit keys equal the analysis keys, so values can be joined on (faction_key, unit_key).

## Design

### 1. Values shipped as data (offline → pipeline → faction JSON)

**New `analysis/export_optimiser_values.py`.** It reuses `load_cards(size_mode=…)`, `bodyguard_melee_bonus()`, `COMMAND_LAMBDA`, `SPEED_BONUS`, `M_REF` and `staff_value_rule()` from `cost_effective_builds.py`, and writes:
- `data/generated/ntw3_optimiser_values.csv` (committed): `faction_key, unit_key, value_quality, value_quantity`. Quality = full harmonisation, quantity = noise-only. It covers unit and commander cards; staff generals are valued in the app.
- `data/generated/ntw3_optimiser_params.json` (committed):
  - `t3_b`, `t3_q`;
  - `m_ref`;
  - `lambda: {quality, quantity}`;
  - `speed_bonus`;
  - `melee_bonus`;
  - `standard_general_melee`;
  - `generated` date.
- `web/src/state/__fixtures__/optimiser-parity.json`: for 3 armies (Preußen 10, Napoli, one Custom army), the cards' optimiser fields plus Python's max-value build and objective at 31 cards, both modes. It feeds the TS parity test.

**`tools/build_web_data.py`.** If those two files exist:
- add per card `optimiserValue: {quality, quantity}`;
- add per faction JSON a top-level `optimiser: {params}`, only for armies with values;
- bump `SCHEMA_VERSION` 1 → 2 (CLAUDE.md invariant 9).

The values ride inside the faction files, so they are cached by the service worker, saved by "⤓ Save offline", and included in `contentHash` with no new route or file. Extend `tools/tests/test_build_web_data.py`: fields present when the inputs exist; build unchanged when they don't.

**`web/src/domain/types.ts` and `web/src/data/load.ts`:**
- add optional `UnitCard.optimiserValue: {quality: number; quantity: number} | null`;
- add optional `FactionRoster.optimiser: OptimiserParams | null`;
- normalise both defensively, as `normalizeCard` does: malformed → null.
- Old cached data simply has no values; the button is then disabled with a tooltip.

### 2. The optimisation model: `web/src/state/optimiser.ts` (pure, framework-free)

The model mirrors `cost_effective_builds.solve()` and reuses the rules helpers exported from `rules.ts`: `cappedClassOf`, `horseArtilleryMax`, `generalCaps`, and cap-group keys.
- **Exported:**
  - `OptimiseSettings`, `DEFAULT_OPTIMISE_SETTINGS`;
  - `buildOptimiseProblem(index, build, candidates, settings, params) → {lp: string, vars, fixed} | {error}`;
  - `decodeSolution(problem, primal) → {build: BuildState, summary}`.
- **Fixed part:**
  - Remainder off: empty; the staff slot is replaced too.
  - Remainder on: the current instances and the staff slot. They are subtracted from every limit: budget, cards, cap groups, class caps, combat-general count. Their corps are forced on, and their morale deficit is added to D.
- **Variables:**
  - `x_j` integer, 0 … min(groupCap or units, units), for each unit card; binary for combat-general cards;
  - `z_i` binary, one per staff-general option (no variables when the slot is already filled in remainder mode);
  - `y_k` binary, one per source corps, only when Single roll is on and the army is ToW;
  - `w_i` continuous, 0 … D_max, one per staff option.
- **Objective (maximise):** Σ v_j x_j + Σ_i (const_i z_i + slope_i w_i) − 10⁻⁶·Σ cost, where:
  - v_j = `optimiserValue[mode]`;
  - const_i = T3(stars)·(1 + σ·fast) + melee·[meleeAttack > 3];
  - slope_i = λ_mode·stars·(1 + σ·fast);
  - T3 = b·stars^q, or 1 gold without stars (stars null → 0); fast = `speedCode` starts with "C".
  - The −10⁻⁶·cost term breaks ties toward the cheaper build, as in Python.
- **Constraints:**
  - **Budget:** Σ cost ≤ 10 000 − fixed cost.
  - **Cards:** Σ x + Σ z ≤ maxCards − fixed cards (the staff general counts).
  - **Staff general:**
    - Σ z = 1 when a staff general is needed;
    - Σ z ≤ 1 when "Allow no staff general" is on;
    - no z variables when the slot is already filled, or a staff general already sits in the line.
  - **Combat generals:** Σ combat ≤ cap − fixed against-cap count.
  - **Cap groups:** per group, Σ ≤ groupCap − fixed copies, and ≤ 1 combat general.
  - **Class caps:** foot artillery, horse artillery and heavy cavalry, by `cappedClassOf`.
  - **Single roll:**
    - Σ y ≤ 4;
    - x_j ≤ ub_j·y_corps;
    - z_i ≤ y_corps;
    - corps of fixed cards: y = 1 (more than 4 already → a clear error).
  - **Command correction:**
    - D = Σ d_j x_j + D_fixed, with d_j = (menRaw/2)·max(0, m_ref − morale);
    - w_i ≤ D;
    - w_i ≤ D_max·z_i;
    - a staff general fixed in remainder mode adds slope·D directly.
- **Encoding:** the model is written as CPLEX LP text (Maximize / Subject To / Bounds / Generals / Binary / End).
- **Candidates:** cards with `optimiserValue` that are in the candidate list passed in.
- **Output:** the new instances (fresh `makeInstanceId`) are ordered artillery → cavalry → infantry, by value, as in the export script, and appended after the fixed ones.

### 3. Solver: HiGHS WebAssembly in a worker

- Add the dependency `highs` (1.15.3, MIT, no deps). It is HiGHS, the solver `scipy.optimize.milp` uses, so app and analysis agree.
- `web/src/state/solveLp.ts`: the interface `solveLp(lp, {timeLimit}) → Promise<{status, columns}>`.
- `web/src/state/optimiser.worker.ts`:
  - loads `highs` with `locateFile` → `import wasmUrl from "highs/build/highs.wasm?url"`;
  - receives LP text and posts back the solution;
  - started with `new Worker(new URL(…, import.meta.url), {type: "module"})`;
  - type `self` with a narrow cast (tsconfig.app has DOM lib only).
- Tests call `highs` directly in Node (it finds its own `.wasm`).
- Time limit 10 s. Non-"Optimal" statuses map to user messages: infeasible → "No legal build fits these settings"; time limit → use the best found, if any.
- **PWA:** add `"**/*.wasm"` to `globPatterns` in `web/vite.config.ts`, so the solver works offline. The file is a few MB, under the 6 MB cap.
- **Electron:** add `".wasm": "application/wasm"` to the `protocol.handle("app")` MIME map in `web/electron/main.cjs`. Touch nothing else there (invariant 6).

### 4. UI: `web/src/components/OptimiseModal.tsx` + `Builder.tsx` wiring

**Button.** An "Optimise" button in the Builder header next to "Generate times". It shows only for ToW and Custom (`isTow || isCustom`), and is disabled with a tooltip when the roster has no optimiser data. It opens the modal (existing pattern: `.modal-backdrop > .modal`, Escape closes, added to `modalOpen`).

**Controls:**
- **Max unit cards:** a single `<input type="range">` 2–31 with its value shown (new small CSS, reusing the `.dual` look).
- **Quality / Quantity:** a segmented control (`.tri .seg` pattern). The hint says: Quality = size-bias removed; Quantity = keeps the size discount.
- **Checkboxes**, the existing label-checkbox pattern:
  - Optimise remainder;
  - Only filtered units (with a count of eligible cards);
  - Allow no staff general;
  - Single roll (≤ 4 source corps), ToW only.
- The settings live in Builder `useState`, so they persist while the corps view is open.

**Optimise button:**
1. Runs the worker; shows "Optimising…" and disables itself.
2. Calls `setBuild(result)` immediately and remembers the previous build.
3. Shows a toast: "Optimised: N cards, cost …, value … (eff …)".
4. The modal gets an "Undo optimise" button that restores the previous build until the next build change.

**Filtered candidate list.**
- Refactor Builder's `matchCount` predicate into a memoised `filteredCards` list: `matchesCard` && not hidden by rotation / corps roll. `matchCount` becomes its length.
- The optimiser gets `filteredCards` when "Only filtered units" is on, else every roster card.
- **Not applied:** the "Combat generals" *display* switch (`isHiddenByGeneralSwitch`). It is off by default for ToW and only hides medallions, so applying it would silently forbid combat generals.

The business logic stays in `state/`; the component only gathers settings and calls `optimiseBuild(...)`.

### 5. Docs

- `docs/HANDOFF.md`: an "Optimiser" section covering the data flow, the model, how to refresh the values (re-run the export script, then `build_web_data.py`), and the schema bump.
- CLAUDE.md §3: add the export command.
- README: one feature paragraph.
- `analysis/HANDOFF.md`: one line on the export.

No commits.

## Work order, saved as we go (the user asked: usage may run out midway)

**Step 0 (first action).**
- Copy this plan into the repo as `docs/OPTIMISER_PLAN.md`, with a **progress checklist** for the steps below.
- After each step, tick it and add one line on its state: files touched, what's verified, what's next.
- A fresh session can resume from that file alone. Intermediate outputs are files on disk too.
- No commits (standing preference); the user can ask for one at any checkpoint.

Each step leaves the repo consistent: tests pass and the app still runs.

1. **Data export:** `analysis/export_optimiser_values.py`.
   - Run it, and keep its outputs: the values CSV, params JSON and parity fixture.
   - Check: row counts, every key in the builder CSV.
2. **Pipeline:** `build_web_data.py` (+ test), the schema bump, and `types.ts` / `load.ts`.
   - Regenerate `web/public/data`.
   - Check: pytest, typecheck, tests.
3. **Pure model:** `optimiser.ts` + `solveLp.ts` (Node path) + unit and parity tests.
   - Check: `npm test`.
4. **Worker + wasm wiring:** `optimiser.worker.ts`, `vite.config.ts` glob, Electron MIME.
   - Check: `npm run build`, with the `.wasm` in the precache manifest.
5. **UI:** `OptimiseModal.tsx`, Builder wiring, `filteredCards` refactor, CSS.
   - Check: typecheck, lint, tests, manual run in dev.
6. **Docs:** HANDOFF, CLAUDE.md, README.
   - Final full check, and mark the checklist done.

## Files

- **New:**
  - `analysis/export_optimiser_values.py`;
  - `data/generated/ntw3_optimiser_values.csv`, `ntw3_optimiser_params.json`;
  - `web/src/state/optimiser.ts` (+ `.test.ts`, `optimiser.parity.test.ts`, `__fixtures__/optimiser-parity.json`);
  - `web/src/state/solveLp.ts`, `optimiser.worker.ts`;
  - `web/src/components/OptimiseModal.tsx`.
- **Edited:**
  - `tools/build_web_data.py` (+ test);
  - `web/src/domain/types.ts`, `web/src/data/load.ts`, `web/src/components/Builder.tsx`, `web/src/styles.css`;
  - `web/vite.config.ts`, `web/electron/main.cjs`, `web/package.json` / lock (`highs`);
  - the docs above.

## Verification

1. **Pipeline:**
   - `py -3.13 analysis/export_optimiser_values.py`, then `py -3.13 tools/build_web_data.py`;
   - the faction JSON for a ToW and a Custom army has `optimiserValue` on its cards and `optimiser` params;
   - an Army Corps file has neither;
   - `py -3.13 -m pytest tools/tests` passes.
2. **Unit tests** (`npm test`), on synthetic rosters from `test/factories.ts`:
   - the result passes `checkKnownLimits` with cost ≤ 10 000;
   - max cards is honoured;
   - exactly one staff general by default; zero allowed only with the toggle;
   - remainder mode keeps every fixed instance and respects the caps it already uses;
   - only candidate cards are used;
   - single roll gives ≤ 4 corps;
   - infeasible settings give the error.
3. **Parity test:** at 31 cards, no roll limit, the TS objective equals Python's for the 3 fixture armies in both modes, to 10⁻⁶ relative. The builds may differ only on exact ties.
4. **Checks:**
   - `npm run typecheck && npm run lint && npm test`;
   - `npm run build`: the `.wasm` is emitted and listed in the service worker's precache manifest.
5. **Manual in `npm run dev`:**
   - open a ToW army (e.g. [1806] 10. Preußen) and a Custom army;
   - Optimise with defaults: the build fills, the header shows ≤ 31 cards, cost ≤ 10 000 and no limit warnings;
   - try each toggle, remainder with a few units placed, a filter (e.g. class = line infantry), and Undo;
   - Generate times on a single-roll ToW build finds a window.
