# Experiments

Each script here asks one question and answers it in a report under `analysis/output/`. Their findings
are recorded in the reports linked below; nothing in the app or the pipeline that feeds it
(`team_values` → `export_optimiser_values` → `tools/build_web_data.py`) depends on them. They
stay runnable, so a finding can be re-checked.

Run them from the repository root, e.g. `python analysis/experiments/fclass_table.py`. Each script
puts `analysis/` on the import path itself and shares the pricing model and checkpoints with the
pipeline (`analysis/unit_pricing.py`, `analysis/.cache/`).

| Script | Question | Output (in `analysis/output/`) |
|---|---|---|
| `ac_natural_experiment.py` | What sets Army Corps prices versus Theatre-of-War prices (AC/ToW pairs)? | `ac/natural_experiment_report.md` |
| `calibre_function.py` | Can a smooth function of range and damage replace the cannon-type one-hot? | `calibre_function_report.md` |
| `commander_stage.py` | A commander priced from its unit's price (the rejected stars-only form) | `commander_stage_report.md` |
| `commander_within_unit.py` | Commander price vs stars, inside units with several generals | `commander_within_unit_report.md` |
| `extreme_pinning.py` | Does pinning extreme units to the training set help? | `extreme_pinning_report.md` |
| `fclass_table.py` | The adopted model's army × unit-class multipliers as tables | `faction_class_multipliers*.md/.csv` |
| `general_command_effect.py` | Is a staff general's command worth more in large, low-morale armies? (replays) | `general_command_report.md` |
| `replay_unit_usage.py` | Which units do players bring, and how do those armies fare? | `unit_usage_report.md` |
| `two_compartment.py` | Two-compartment build model: normative value + replay evidence | `two_compartment_*.md` |
| `size_weighting.py` | Size-frequency weighting in the fits (`diagnostics`, `run`) | `size_weighting_diagnostics.md` |
| `size_weighting_report.py` | The size-weighting report, built from its checkpoints | `size_weighting_report.md` |
| `size_weighting_builds.py` | Do size-weighted values change which unit sizes the optimiser picks? | `size_weighting_builds.md` |

The size-weighting study is written up in `analysis/SIZE_WEIGHTING_REPORT.md` (not adopted); the
pricing-model experiments are summarised in `analysis/PRICING_MODEL_REPORT.md`.
