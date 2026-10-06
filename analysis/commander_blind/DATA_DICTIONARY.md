# `data/pairs.csv`: column meanings

One row per commander card (5 238 rows), paired with its regular counterpart in the
same army. Prices are in gold, the game's multiplayer currency. "Regular" is the
plain unit; "commander" is the same unit led by a named combat general.

| Column | Meaning |
| --- | --- |
| `pair_id` | Row id. |
| `faction_key` | The army (one army = one faction key; 55 armies). |
| `army_corps_name` | The army's display name; its leading number is `corps_number`. |
| `corps_number` | The army's corps number, 5–12. |
| `side` | `imperial` or `coalition`. |
| `arm` | `infantry`, `cavalry` or `artillery`. |
| `unit_class` | The regular unit's class (e.g. `infantry_line`, `cavalry_heavy`, `artillery_foot`). |
| `regular_unit_key`, `commander_unit_key` | Game keys. The same regular unit can have several commander versions (different generals). |
| `commander_name` | Card name: the general, then the unit in brackets, then a speed tag. |
| `command_stars` | The general's command stars, 0–7 (0 = none listed). |
| `regular_price`, `commander_price` | The two prices. |
| `regular_men`, `commander_men` | Men in the unit (models = men ÷ 2). They usually match; a few commanders lead a larger unit. |
| `regular_guns`, `commander_guns` | Number of guns, for artillery; blank otherwise. |
| `speed_tag` | Movement class and tier from the name, e.g. `L3`, `C4`, `F2` (same for both). |
| `training_level` | `elite`, `well_trained`, `trained`, `poorly_trained` or `mob`. |
| `regular_rank_depth`, `commander_rank_depth` | Formation depth. |
| `regular_<stat>`, `commander_<stat>` | The game stats morale, melee_attack, melee_defense, charge_bonus, accuracy, reload_skill, ammo and range, for the regular unit and for the commander version. The general changes some of them. |
| `regular_<flag>`, `commander_<flag>` | Ability flags, 0/1: can_form_square, has_stamina, is_shock_resistant, can_inspire, has_guerrilla_deployment, can_place_stakes, can_place_mines, scares_enemies, can_build_barricades, guard_mode, skirmish, can_snipe, pike_square (solid square). |
