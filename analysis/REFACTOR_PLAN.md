# Analysis tidy-up — plan and progress

> **Resume here.** Approved 2026-10-11. Tick each step and add a log line when it is verified. Commit after
> each verified step (approved with the plan). Baseline snapshots: the session scratchpad `refactor_baseline/`
> (if lost, regenerate them from the commit tagged in the log before continuing).

## Checklist

- [x] R0. Baseline snapshots (golden metrics, load hashes, fit SSEs, size weights, gitignored outputs, s3 smoke runs).
- [x] R1. Test suite analysis/tests/ (passes on the old code).
- [x] R2. common.py + checkpoints.py; callers switched.
- [ ] R3. Monkeypatching removed (FCLASS_GRID, in_scope/side_of, SIZE_BANDS, PAIRS).
- [ ] R4. pricing/config.py Settings + up.configure; setters switched.
- [ ] R5. unit_pricing split into analysis/pricing/ (3 moves) behind the facade.
- [ ] R6. Pipeline scripts tidied.
- [ ] R7. Experiments moved to analysis/experiments/; docs updated.
- [ ] R8. requirements.txt + CLAUDE.md / HANDOFF code map.
- [ ] R9. (Optional) full unit_pricing acceptance run.

## Log

- Plan approved.

- Baseline commit 32c6fd63 (size-weighting work). R0: golden snapshots via analysis/tests/make_golden.py (checkpoint fingerprints are CANONICAL — sets sorted, because pickled set order follows PYTHONHASHSEED and varies per process), gitignored outputs + unit_pricing smoke run copied to the scratchpad refactor_baseline/. ac_pricing is verified by re-running its phases on the 500-seed checkpoints (an s3 run would overwrite tracked outputs).
- R1: analysis/tests/ (support.py, test_golden.py, test_outputs.py): 6 tests, ~8 s, pass on the baseline. Run: `py -3.13 -m unittest discover -s analysis/tests -t analysis/tests`. The import-side-effect test comes with its fix in R3.

- R2: analysis/common.py (paths, constants, WIP_THEATRES/theatre_of/is_wip, the 5 named size-band sets, log/table/write_csv/read_csv, atomic cached/save/load) + analysis/checkpoints.py (all checkpoint names + kappa_of); callers switched (unit_pricing log/table/paths/ARMS; cached in ac_pricing/class_structure/team_values; hard-coded v2_/tow_builds/sb names in cost_effective_builds/commander_model/commander_stage/team_search/export_team_builds/size_weighting; team_search cache now atomic and its side check a ValueError; theatre parsing ×7). Dropped dead WELLESLEY (kept LinearRegression: it IS used at the staff fit). Fixed a baseline bug: team_values main had `versions` in 3 lines from the size-weighting sed edit. Verified: tests 10/10; team_values/team_search/team_report_tables/export_optimiser_values(+build_web_data, --fixture)/export_team_builds/ac_builds (4 versions + no-rebates) → tracked outputs unchanged (only the date stamp, restored); 543 gitignored build files identical with timestamps masked; teams_tow.csv identical.

## Plan (copy)

# Plan: tidy the analysis code — readable, modular, robust (results identical)

### Context

The analysis code has grown to about 12 700 lines.
- **Size:** `unit_pricing.py` is 3 354 lines, and some functions run to 933 lines.
- **Duplication:** helpers are copied across scripts, including 4 checkpoint helpers, about 15 path
  definitions, 5 size-band definitions and `sys.path` boilerplate in 22 files.
- **Hidden side effects:**
  - Importing `ac_pricing` changes `up.FCLASS_GRID` for every script that imports it.
  - Scripts swap other modules' settings temporarily (`up.in_scope`/`side_of`, `ap.SIZE_BANDS`,
    `cm.PAIRS`).
- **Hard-coded names:** checkpoint file names are written into several files.
- **No safety net:** there are no tests.

The user asked to tidy it for readability, modularity and robustness.

**User's decisions:**
- **Scope:** shared foundations plus the core. That means splitting `unit_pricing.py` behind a
  compatibility front and tidying the pipeline scripts that feed the app.
- **One-off experiments** move to `analysis/experiments/`.
- **A small test suite** gets added.
- **Blind-study folders** (`ac_blind`, `build_blind`, `commander_blind`) stay untouched.

**Hard constraint: results stay identical.**
- The 184 checkpoints in `analysis/.cache/` (hours of fits) pickle ten classes as `unit_pricing.<Name>`:
  `Unit`, `Staff`, `Spec`, `SplitPlan`, `PriceModel`, `CVRun`, `Slice`, `FclassResult`, `StaffRun`,
  `StaffSlice`.
- Those classes keep their fields and keep `__module__ == "unit_pricing"`.
- Cache versions and file names don't change.

### Steps

Each step is verified before the next one starts: the test suite, plus re-running the affected scripts
and checking the output files are byte-identical (`git status` clean on `analysis/output`,
`data/generated`, the web fixtures and the gitignored build files, compared against a scratchpad
baseline). Progress goes into `analysis/REFACTOR_PLAN.md` after every step.

**Commits.** The size-weighting work from the last task is still uncommitted. I'll commit it first as the
clean baseline, then commit after each verified step, so every step can be rolled back. Approving this
plan counts as asking for those commits.

0. **Baseline.** In the scratchpad, write golden snapshots from today's code:
   - every checkpoint's type and stored metrics (MAE, κ);
   - a hash of the ToW and AC unit loads;
   - a few `fit_on` SSEs and the `size_weights` output;
   - copies of the gitignored outputs.

   Also run a quick reduced run (the HANDOFF smoke run, plus `ac_pricing --phase model --arm artillery
   --seeds 3`, which writes separate s3 checkpoints) into the scratchpad as a baseline.
1. **Tests first** (`analysis/tests/`, unittest, about 1 min, run with
   `py -3.13 -m unittest discover -s analysis/tests -t analysis`). Cache-dependent tests skip when
   `analysis/.cache/` is absent. They must pass on the old code before anything moves.
   - **api:** the 59 names scripts use still resolve; pickled classes still report `unit_pricing`; and
     importing `ac_pricing`, `team_values` or `size_weighting` changes no setting of another module.
   - **checkpoints:** every `.pkl` loads and matches the golden metrics.
   - **load:** the unit-load hashes match.
   - **values:** recomputed V4 values and AC sb/full values equal `values_ac.csv` / `values_tow_sb.csv`.
   - **numerics:** the golden `fit_on` SSEs and the size weights match.
   - **ac_builds:** `solve_corps` on 3 corps equals the summary CSV rows.
   - **common:** the shared helpers work.
2. **Shared foundations.**
   - **`analysis/common.py`:**
     - paths: ROOT, OUTPUT, GENERATED, CACHE_ROOT, DATA_CSV, CATALOG_CSV;
     - `log`, `table`, `write_csv` (same encoding and newlines as today);
     - `atomic_write_bytes`, and `cached(path, compute, fresh)`;
     - `theatre_of(key)`, which replaces 7 copies of `split("_")[2]`, and `WIP_THEATRES`;
     - `BUDGET`, `MAX_CARDS`, `DEFAULT_SEEDS`, `ARMS`, `ARM_SHORT`;
     - one named block holding all five size-band definitions with their original values and a comment
       on what each is for. They are not merged, because merging would change results.
   - **`analysis/checkpoints.py`:** the only place checkpoint names are built (`slice_of`, `kappa_of`,
     `v4_of`, `tow_builds`, …). It replaces the hard-coded `v2_…`, `tow_builds_v2_…` and `sb_…` names.
   - `team_search`'s non-atomic pickle write switches to `cached`.
3. **Remove the monkeypatching**, one change at a time.
   - **`up.FCLASS_GRID`:** `fclass_cv(..., grid=)`. `ac_pricing` passes its AC grid explicitly; the
     import-time patch is deleted.
   - **`in_scope`/`side_of`:** `load(..., scope=, side=)` and `build_pairs(..., scope=, side=)`.
   - **`ap.SIZE_BANDS`:** a `bands=` argument on `band_of`, `with_bands` and `size_form_run`.
   - **`cm.PAIRS`:** `Pairs(path=)`.
4. **Settings.** Add `analysis/pricing/config.py`: one `Settings` dataclass (workers, out dir, search
   grids, iteration limits, artillery calibre, size weighting) and `up.configure(**kw)`.
   - Reading `up.WORKERS` still works.
   - Assigning `up.WORKERS = …` raises a clear error pointing to `configure`. It is never silently
     ignored.
   - The worker pool passes the whole `Settings` object to its workers.
   - The 5 callers that set values change over: `ac_pricing`, `team_values`, `size_weighting`, the CLI and
     the HANDOFF smoke-run snippet.
5. **Split `unit_pricing.py`** into `analysis/pricing/`, in three verified moves:

   | Module | Contents |
   |---|---|
   | `constants` | fixed constants |
   | `data` | units, ratings, loading |
   | `spec` | model specification |
   | `design` | design matrix, splines |
   | `model` | `PriceModel`, metrics |
   | `splits` | fold search |
   | `cv` | `CVRun`, `SliceData`, size weighting, `fit_on`, `cv_spec`, `Slice` |
   | `pool` | worker pool |
   | `search` | p profile, power searches, shape variants |
   | `fclass` | κ and faction × class CV |
   | `final` | `FINAL`, moved from `blind_ideas`, which re-exports it |
   | `staff` | staff generals |
   | `diagnostics` | data diagnostics |
   | `report`, `outputs` | markdown report, output files |
   | `cli` | `main` and its phases |

   - **Pickled classes:** they move unchanged and carry a `@pickled_as_unit_pricing` decorator that pins
     `__module__`, so old checkpoints load and new pickles are byte-identical.
   - **`unit_pricing.py`** becomes a ~80-line front: explicit re-exports of the public API, `configure`,
     read access to settings, and `__main__` → `cli.main()`.
   - **Dead code:** drop the unused `WELLESLEY` constant and the unused sklearn import.
6. **Tidy the pipeline scripts:**
   - **Scripts:** team_values, ac_builds, export_optimiser_values, export_team_builds,
     export_builds_for_app, team_search, team_report_tables, cost_effective_builds, class_structure,
     ac_pricing, commander_model, build_commander_pairs and ac_discounts.
   - **Changes:** use `common`/`checkpoints`; remove the local `table`/`log` copies, repeated constants
     and arm maps; split overlong functions where it helps readability.
   - **`ac_discounts`:** its ~45 data-validation `assert`s become `check()` calls that raise
     `ValueError`, so `python -O` can't strip them.
7. **Move the one-off experiments to `analysis/experiments/`** with `git mv`, so history is kept:
   ac_natural_experiment, calibre_function, extreme_pinning, two_compartment, commander_stage,
   commander_within_unit, general_command_effect, fclass_table, size_weighting (with its builds and report
   modules) and replay_unit_usage.
   - Their output paths stay the same.
   - Imports switch to the parent folder.
   - Doc references are updated: CLAUDE.md, the HANDOFFs, the reports and the README.
   - The circular import between `size_weighting` and its report goes.
   - Add the missing `__main__` guards.
8. **Requirements and docs.**
   - Add `analysis/requirements.txt` (numpy, scipy, scikit-learn); scipy isn't listed anywhere today.
   - Update CLAUDE.md, which says "numpy + sklearn" and the wrong Python version, and give the analysis
     HANDOFF a code map of the new layout.
9. **Optional final acceptance (~50 min):** a full `unit_pricing` run into the scratchpad, diffed
   against `analysis/output`.

### Don'ts

- No cache version bumps.
- No renamed pickled classes, and no new fields or `default_factory` on them.
- No `from config import X` copies of settings.
- No merging of the size-band definitions.
- No `--fresh` runs during the refactor.
- Nothing under the blind-study folders, `web/` or `tools/` changes.

### Verification

- The test suite passes after every step.
- Byte-identical outputs after every step:
  - `team_values` (~1 min);
  - `team_search` (10 s);
  - `export_optimiser_values` then `build_web_data` (the web fixture unchanged);
  - `export_team_builds`;
  - `ac_builds` (~6 min, for the AC steps);
  - the s3 smoke runs against their baselines.
- Web tests still pass, as nothing there changes: `npm test`, plus
  `py -3.13 -m unittest tools.tests.test_build_web_data tools.tests.test_army_builder_rules`.
