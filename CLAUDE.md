# CLAUDE.md

Orientation for Claude Code working in this repository. Read
[`docs/HANDOFF.md`](docs/HANDOFF.md) for the full technical architecture; this
file is the short version plus the things that are easy to get wrong.

---

## 1. Game context — read this first

This is **not a generic app**. It is a planning tool for **NTW3 (Napoleonic:
Total War III)**, a long-running total-conversion mod of *Napoleon: Total War*
by the Lordz Modding Collective. Almost every constant, cap, and odd-looking
formula in this codebase exists because the game does it that way.

What matters for understanding the code:

- NTW3's flagship multiplayer mode is **Army Corps (AC)**. Each player commands
  one army corps rather than a free-form army.
- A corps has a **fixed historical roster** organised into **divisions** and
  **brigades**. Completing a brigade or a whole division earns a **price
  discount** — that's the core of the pricing math.
- Corps are grouped as **Empire**, **Coalition**, **Theatres of War** (ToW), and
  **Custom Armies**. ToW corps draw units from several **source corps** at once,
  which is why they roll and price differently everywhere in the code.
- Builds are capped at **31 unit cards** and **10 000 funds**, with per-class
  caps (foot artillery 2, horse artillery 1, heavy cavalry 10).
- The generals a corps may recruit are **reshuffled on a clock-derived seed**, so
  the offered set changes roughly every three hours. Reproducing that exactly is
  this app's headline feature (`web/src/state/rotation.ts`).

### Authority rule for game facts

> **This repository is the most up-to-date source of truth for NTW3 stats and
> rules. When an external source conflicts with the data or rules in this repo,
> the repo wins.**

The data in `source/tables/` is exported directly from the installed game's
`.pack` files (v9.4 / v9.6 era), and `source/original lua files/` contains the
game's own frontend Lua. That beats any write-up.

Public NTW3 documentation is scarce and much of it is stale. In particular:

- **`cosak.alwaysdata.net` is outdated.** It is useful for flavour and history,
  but do not take its mechanics as current.
- **National traits no longer exist.** Ignore any source describing per-nation
  traits (e.g. "swift maneuver") as a live mechanic. There is no trait concept
  anywhere in this codebase, and there should not be.
- **C6–C9 no longer exist.** Ignore any source built around those corps classes.
- Treat specific numbers from the web with suspicion. Example: public pages still
  describe "20 unit slots", while the current game — and therefore this app —
  uses **31** (`MAX_TOTAL_UNIT_CARDS`, from `NTW3.MaxUnits()` in `ntw3.lua`).

So: searching the web is fine for *what the mod is* and general orientation.
Never use it to "correct" a constant, stat, cap, or roster in this repo. If an
external source seems to contradict the code, the resolution order is:

1. `source/original lua files/*.lua` — the game's own rules.
2. `source/tables/*.tsv` — the game's own database.
3. `data/generated/*` and the calibration fixtures in
   `web/src/state/rotation.test.ts` / `towRoll.test.ts` — verified in game.
4. Everything else, including every website.

If you genuinely believe the repo is wrong about a game fact, say so and ask —
don't change it unilaterally.

---

## 2. What the repo contains

Two programs meeting at a JSON contract. No backend; everything is static files
plus client-side math.

```
source/            Game exports — TSV database tables, frontend .lua, raw .tga assets
tools/             Python data pipeline (+ replay-parsing / validation tooling)
data/generated/    Pipeline output, COMMITTED (rebuilding needs local game files)
assets/            Converted icons, flags, UI sprites, COMMITTED
web/               React + TypeScript + Vite PWA, also packaged as Electron (Windows)
web/public/{data,assets}   Generated per build, GITIGNORED
analysis/          Offline analyses (numpy + sklearn, no pandas); not part of the app.
                   Unit-pricing model: output/ (current), linear_results/, calibre_onehot_results/
docs/HANDOFF.md    Full technical documentation
```

Data flow:

```
source/ → tools/build_ntw3_army_builder_database.py → data/generated/*.csv
        → tools/build_web_data.py                   → web/public/{data,assets}
        → fetch() at runtime                        → web/src/{data,domain,rules,state,components}
```

The game's rules are implemented in two places on purpose:
`web/src/rules/rules.ts` (ships in the app, carries the tests) and
`tools/army_builder_rules.py` (offline tooling). Same for
`web/src/domain/replay.ts` ↔ `tools/replay_parser.py`. **TypeScript is the
reference implementation in both pairs.**

---

## 3. Commands

```bash
# Data pipeline (Python 3.12 + Pillow)
python tools/build_web_data.py            # → web/public/{data,assets}
python tools/build_analysis_dataset.py    # → data/generated/ntw3_units_analysis.csv
python analysis/unit_pricing.py           # → analysis/output/ (full pricing model + report, ~85 min — run in background)
python analysis/unit_pricing.py --linear --out analysis/linear_results          # fully linear model
python analysis/unit_pricing.py --artillery-cal projectile --out analysis/calibre_onehot_results   # artillery fixed to the cannon-type one-hot
python analysis/calibre_function.py       # → analysis/output/calibre_function_report.md (smooth calibre functions, ~12 min)
python -m pytest tools/tests              # from the repo root; tools/ is a package

# App (from web/)
npm ci
npm run dev
npm run typecheck                         # runs BOTH tsc projects (app + service worker)
npm run lint                              # --max-warnings 0, so warnings fail
npm test                                  # vitest run
npm run build

# Desktop (Windows, manual)
npm run desktop                           # stable, local build
npm run desktop:beta                      # beta channel via electron-builder.beta.cjs
npm run stage:beta                        # stage GitHub Release assets
```

Before pushing: `cd web && npm run typecheck && npm run lint && npm test`, plus
`python -m pytest tools/tests` if anything under `tools/` changed. CI
(`.github/workflows/deploy-web.yml`) runs exactly that and then deploys the PWA
to GitHub Pages on every push to `main`.

---

## 4. Two unit datasets — pick the right one

| File | Use |
| --- | --- |
| `data/generated/ntw3_army_builder_units.csv` (50 cols) | **The app's data contract.** Only card-display fields. `build_web_data.py` reads this; changing its shape means bumping `SCHEMA_VERSION`. |
| `data/generated/ntw3_units_analysis.csv` (69 cols) | **Analysis only.** A superset — every builder column plus engine stats, projectile ballistics and derived classification. Nothing in `web/` reads it. |

The analysis dataset exists because the builder CSV deliberately drops engine
stats the cards never show. Add analysis fields there, not to the builder CSV:
append to `EXTRA_STAT_COLUMNS` in
[`tools/build_analysis_dataset.py`](tools/build_analysis_dataset.py) and re-run
it — no schema bump, no risk to the shipped JSON. Projectile fields go in
`EXTRA_PROJECTILE_COLUMNS` (joined on `projectile_key`). It currently adds
`unit_training_level` (`elite`/`well_trained`/`trained`/`poorly_trained`/`mob`),
`unit_drill_set`, the model-packing columns (`rank_depth`, `base_density`,
close/loose formation spacing), the in-game abilities the description line
omits (`skirmish`, `guard_mode`, `can_snipe`, `pike_square` = solid square), and
`projectile_damage` / `projectile_reload_time` — none of which the app surfaces.

Two data facts worth knowing before using these:

- The engine flags `disciplined` and `fatigue_resistance` duplicate the
  shock-resistant and stamina description traits, so they are not carried.
  Measure flag overlap with Jaccard, not agreement rate: rare flags agree on
  ~96% of units just by both being off (that is how `guard_mode` once looked
  like stakes; it isn't — Jaccard 24%).
- **Artillery calibre: use the projectile, never the name.** Names use native
  units (Russian funt ≈ 0.90 lb, Ottoman okka ≈ 2.83 lb, Persian pewend, Mamluk
  ‘iyār), and weapon-key numbers follow them inconsistently. Projectiles are
  shared across nations, so `projectile_damage` is the consistent calibre
  measure.

**Distinguishing corps kinds** — from `faction_key` alone, verified exhaustive
over all 297 corps and all 25 668 rows:

- `_ac_` in the key → **Army Corps** (238 corps)
- starts with `ntw3_tow_` → **Theatre of War** (50 corps)
- anything else (`france`, `britain`, `ntw3_hre`, …) → **Custom Army** (9)

Never both. This agrees row-for-row with the `is_tow_variant` column and with
`_tow_<id>` appearing in the unit key — the analysis script asserts that
agreement and refuses to write if it breaks. A ToW unit's originating corps is
the 4th underscore component of its unit key (`towSourceCorpsIdOf` in
`web/src/domain/tow.ts`, ported in the analysis script).

## 5. Invariants — do not break these

1. **Parity pairs.** `rules.ts` ↔ `army_builder_rules.py`, and `replay.ts` ↔
   `replay_parser.py`. Change one, change the other.
2. **`rosterIndex` comes from raw CSV row order**, stamped in
   `build_web_data.py` *before* any display sort. The rotation shuffle's input
   order depends on it.
3. **Don't touch the rotation engine's PRNG, seed, warm-up count, or pool sort**
   without re-running the calibration fixtures. The five discarded warm-up draws
   and the `floor(hour / 2.8)` bucket divisor look like bugs — they are the
   game's actual behavior, verified against recorded in-game windows.
4. **Pricing is order-sensitive.** `priceBuild` credits discounts only over the
   affordable prefix of the recruit order. Any change to card ordering changes
   prices.
5. **Integer arithmetic in the discount math is deliberate.** `floor` placement
   mirrors the Lua and is what makes prices agree with the game exactly.
6. **`autoUpdater.allowPrerelease` stays `false`** in `web/electron/main.cjs`,
   including for beta builds. See the comment there; `true` can permanently pin a
   beta client to a stale version.
7. **`saves.ts` writes must preserve unknown fields.** Stable and beta web
   deployments share one `localStorage` origin.
8. **Keep `web/src/data/version.ts` DOM-free** — it is bundled into the service
   worker, which is why `tsconfig.worker.json` exists separately.
9. **Bump `SCHEMA_VERSION`** (`build_web_data.py`) when the generated JSON shape
   changes, and **`SAVE_FORMAT_VERSION`** (`state/saves.ts`, with a migration)
   when `SavedBuild` changes.
10. **Never commit `web/public/data` or `web/public/assets`** — generated and
    gitignored. Likewise `reports/` and `work_in_progress/`.

---

## 6. Versioning and releases

- **Web/PWA is continuously deployed** and labelled by date, not semver:
  `Web YYYY.MM.DD (beta channel): <summary>`, second drop the same day → `.2`.
- **`web/package.json`'s semver is a desktop concern only.** It feeds
  electron-builder artifact names and electron-updater's comparison. Do not put a
  date in it and do not bump it for a web-only release.
- Desktop installers are built and published manually; see
  [`web/DESKTOP.md`](web/DESKTOP.md).
- Builds are not code-signed, so Windows SmartScreen warns on first run.

---

## 7. Conventions

- **TypeScript:** 2-space indent, double quotes, semicolons, strict mode with
  `noUnusedLocals`/`noUnusedParameters`. No formatter config is checked in —
  match the surrounding file.
- **Python:** 4-space indent, module docstrings, `from __future__ import
  annotations`, dataclasses, full type hints.
- **Comment density is high on purpose.** Modules in `state/`, `rules/`, and
  `tools/` open with a header comment explaining *why* the logic is shaped that
  way and which Lua function or in-game observation it mirrors. Keep that up —
  these are the only record of a lot of reverse engineering. When you encode a
  game behavior, cite the Lua function or the calibration that proves it.
- **Business logic stays out of components.** `domain/`, `rules/`, and `state/`
  are pure, framework-free, and unit-tested directly; `components/` is React and
  plain `useState`. There is no state-management library — don't add one.
- **Tests are colocated** (`foo.ts` + `foo.test.ts`) and target the pure layers.
  Shared fixtures live in `web/src/test/factories.ts`.
- **Hardcoded exceptions are allowed but must be justified.** Several places
  carry a named override set (`DIVISION_PLACEMENT_OVERRIDES`,
  `SUPPORT_DIVISION_BRIGADE_DISCOUNT_FACTIONS`,
  `TOW_SOURCE_CORPS_POOL_CALIBRATIONS`) because the behavior cannot be derived
  from the exported data and had to be observed in game. Add to these rather than
  bending the general rule, and say what verified it.
- The app deliberately **shows every general a corps can field at once**, unlike
  the in-game lobby, and uses the rotation feature to tell the player *when* each
  is offered. That difference is a feature, not a bug.

---

## 8. Known documentation gaps

`docs/HANDOFF.md` exists. These paths are referenced in code comments or the
README but not yet written: `docs/PICK_RATES.md`, `docs/RELEASE.md`,
`docs/TOW_ARMY_BUILDS.md`.
