# Registre des Armées

> ## This branch: `analysis/unit-pricing`
>
> This branch adds an **offline analysis of how NTW3 prices its units**. Nothing
> in the app changes: everything new lives under [`analysis/`](analysis/) and in
> the extended analysis dataset `data/generated/ntw3_units_analysis.csv`. The
> app description further down is the same as on `main`.
>
> **The question.** Can the multiplayer price of every Theatre-of-War and Custom
> army unit be predicted from the unit's stats, type, size and army, with a
> formula a person can read?
>
> **The answer: yes, to within about 5–8%.** Cross-validated on units the model
> never saw:
>
> | | Units | Mean error | Mean % error |
> | --- | --- | --- | --- |
> | Infantry | 4 370 | 27 gold | 7.7% |
> | Cavalry | 1 724 | 35 gold | 4.6% |
> | Artillery | 894 | 32 gold | 6.8% |
> | Staff generals | 288 | 9 gold | 2.2% |
>
> **The model in one line:**
>
> ```
> price = (8 / N) × army×class multiplier × size^p × (b0 + Σ β·stat^a + traits + class + speed)
> ```
>
> - **N** is the corps number ("7. Danmark" → 7); price scales with 1/N.
> - **Size** is models for infantry and cavalry, guns for artillery.
> - The **army × class multiplier** captures each army's own pricing of each
>   unit class. Polska lancers, for example, are priced at ×0.57.
> - **Staff generals** cost 76.6 × stars^1.39 × 8/N, or 1 gold without stars.
>
> **Two versions of the model:**
> - **The main model** shares coefficients across unit classes, so classes can
>   be compared like for like.
> - **A per-class alternative ("V4")** gives each class its own formula. It is
>   more accurate (25 / 33 / 27 gold), but classes can then only be compared
>   through their predicted prices.
>
> **Known weak spots:**
> - Very large militia units are overpriced; one 487-model unit is predicted at
>   ~2 200 against 608 actual.
> - Tiny skirmisher units are slightly underpriced.
> - Army Corps prices are not modelled yet.
>
> **Commander variants** (a named general leading a unit) are priced from their
> regular unit's price P. A card starts at about 0.88·P − 110 gold, then adds the
> general's stat bonuses, charged mostly as a share of P, and a small fee per
> star. That is within 8.6 gold (1.1%) when P is known. A model built on stars
> alone cannot do this: the same stars buy different bonuses on different
> units, and a bonus costs more on a more expensive unit. See §7 of the report.
>
> **Price database:** [`analysis/output/price_database.csv`](analysis/output/price_database.csv)
> lists every unit (regular units, commanders, staff generals) with its true
> price and each model's out-of-fold prediction. Over all 12 492 predicted units
> the best pipeline is off by 27 gold (3.7% median).
>
> **Where to read:**
>
> | File | What |
> | --- | --- |
> | [`analysis/PRICING_MODEL_REPORT.md`](analysis/PRICING_MODEL_REPORT.md) | The model written out: equations, parameters, a worked example, limitations, the per-class alternative |
> | [`analysis/output/faction_class_multipliers.md`](analysis/output/faction_class_multipliers.md) | Every army's price multiplier per unit class (also as CSV) |
> | [`analysis/output/unit_pricing_report.md`](analysis/output/unit_pricing_report.md) | Full technical report of the current run |
> | [`analysis/HANDOFF.md`](analysis/HANDOFF.md) | For whoever (or whichever AI) continues the work: rules, commands, code map, checks, next steps |
>
> **Running it** needs Python with numpy and scikit-learn. Run from the
> repository root:
>
> ```bash
> python tools/build_analysis_dataset.py   # the analysis dataset (already committed)
> python analysis/unit_pricing.py          # full model + report → analysis/output/ (~50 min, 6 worker processes)
> python analysis/fclass_table.py          # army × class multiplier tables (seconds)
> python analysis/class_structure.py       # per-class alternative V4 (~40 min, resumable)
> python analysis/build_commander_pairs.py # regular/commander pairs (seconds)
> python analysis/commander_within_unit.py # generals of the same unit compared (seconds)
> python analysis/commander_model.py        # commander + combined models, price database (~1 min)
> ```
>
> The other `analysis/*.py` scripts are the individual experiments behind the
> model choices: calibre curve, blind-study ideas, extreme units. Each writes
> its own report to `analysis/output/`.
>
> An independent "blind" attempt at the same question, made without knowledge
> of this model, is on branch [`blind-pricing-study`](../../tree/blind-pricing-study).

---

**A desktop army builder for Napoleonic Total War 3 (NTW3).**

Registre des Armées lets you plan a multiplayer army corps outside the game:
pick a corps, browse every unit it can recruit, assemble a build, and watch the
cost, discounts, and limits update live — exactly the way the in-game lobby
does. It also tells you **when** the game will offer each general you want.

> Made for NTW3 multiplayer players who want to plan and price a corps before
> they sit down in the lobby.

---

## What it does

### Pick your corps
Browse every army corps in the game, grouped the way the lobby presents them —
**Empire**, **Coalition**, **Theatres of War**, and **Custom Armies** — each with
its historical theatre, year, rating, and flag.

### See every unit
For the corps you choose, you get the full roster of recruitable cards: line and
light infantry, grenadiers, cavalry, artillery, skirmishers, plus its staff and
combat generals. Each card shows its cost, men, speed, command stars, special
abilities (square, stamina, guerrilla deployment, stakes, and more), and full
stats — accuracy, morale, melee, charge, range.

### Build and price an army, live
Add units to your build and everything updates instantly:

- **Running cost** against the 10,000 budget, with the gold you have left.
- **Formation discounts** — completing a brigade or a full division earns the
  same brigade/division discount the game gives you, shown as you fill them in.
- **Limits** enforced like the game: 31 cards, artillery and heavy-cavalry caps,
  one combat general per unit, and the corps' combat-general cap.
- **Totals** for men and squares, so you can read the army at a glance.

### Auto combat generals
One click finds the **cheapest** way to add combat generals to the units you've
already picked — taking the discounts that lower your total and skipping the ones
that would make it dearer. A second click resets them.

### Know when a general is available — the "Generate times" feature
In NTW3, the generals a corps offers **rotate roughly every three hours**, so the
combat and staff generals you want aren't always on the menu. Registre des Armées
reproduces that rotation exactly and tells you, for each general in your build,
**the nearest local time you can recruit them** — whether that's right now, later
today, or a window that just passed.

For Theatres-of-War corps, "Generate times" instead times the **whole build you
made**: it finds the nearest window whose roll offers every corps your selected
units come from *and* the combat generals you used — so you can land the exact
army you designed.

It's calibrated against real in-game timings, so the times it shows match what
the game will actually offer. (The rotation runs on your PC's clock, just like
the game, and repeats every year.)

### Save, load, filter, search
Save builds and reload them later, search by name, and filter the roster by class,
cost, men, stars, speed, abilities, and division/brigade to find what you need.

---

## Getting it

Registre des Armées runs two ways — pick whichever suits you.

### On your phone or in a browser (no install needed)

Open the web app at
**https://ministere-de-la-guerre.github.io/registre-des-armees/**. It works in
any modern browser and can be installed as an app that runs **offline**:

- **iPhone / iPad (Safari):** tap **Share → Add to Home Screen**.
- **Android (Chrome):** tap the **Install app** prompt (or the ⋮ menu → *Install app*).

Once installed it launches full-screen like a native app. To use it without a
connection, open a corps and tap **⤓ Save offline** — that downloads everything
that faction needs. Your saved builds live on the device; use **⤓ Offline →
Export saves** to back them up or move them to another device.

### On Windows (desktop app)

Download the latest installer from the [Releases page](../../releases), run it,
and you're set — it updates itself when a new version ships.

Because the app isn't code-signed yet, Windows SmartScreen may show a
"Windows protected your PC" prompt on first run. Click **More info → Run anyway**
to continue.

---

## A note on the data

All the unit stats, costs, generals, flags, and abilities come straight from the
game's own data tables, so what you see in the builder matches the game. Unlike
the in-game lobby, the builder deliberately shows you **every** general a corps
can field at once (the rotation feature then tells you when each is offered) — so
you can plan around who you actually want.

---

## For developers

This repository also contains the data-build pipeline (Python tools that turn the
exported game tables into the app's data) and the React/TypeScript/Electron app
source under `web/`. If you want to build, modify, or extend it, start with
[`docs/HANDOFF.md`](docs/HANDOFF.md) — it documents the architecture, data
pipeline, rules math, the general-rotation engine, and the release workflow.
The unit-pricing analysis on this branch has its own guide,
[`analysis/HANDOFF.md`](analysis/HANDOFF.md).

---

## Credits

The application icon features **"Napoleonic Eagle" by Sodacan**
([Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Napoleonic_Eagle.svg)),
licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
The eagle is unmodified, composited onto a coloured background; the resulting icon
is distributed under CC BY-SA 3.0. See `web/build/ICON_CREDIT.txt`.
