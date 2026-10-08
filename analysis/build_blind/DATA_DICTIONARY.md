# Data dictionary

## `data/cards.csv`: every card of every army (12 514 rows, 55 armies)

| Column | Meaning |
| --- | --- |
| `faction_key` | The army. |
| `card_key` | The card's key, as it appears in `armies.csv`. |
| `kind` | `unit` (regular unit), `commander` (a unit led by a named combat general) or `staff` (the army's commanding general). |
| `base_unit_key` | For a commander card, the regular unit it is a version of; otherwise the card itself. Cards sharing it share a cap. |
| `name` | Display name, ending in a speed tag such as `[L3]`, `[C4]` or `[F2]`. |
| `unit_class` | E.g. `infantry_line`, `infantry_light`, `infantry_skirmishers`, `cavalry_heavy`, `artillery_foot`; `general` for staff generals. |
| `arm` | `infantry`, `cavalry`, `artillery` or `staff`. |
| `cost` | Price in gold. |
| `unit_cap` | Maximum copies (shared with commander versions); 0 = no cap. |
| `source_corps` | The historical corps the card comes from (Theatre-of-War armies); empty for Custom armies. |
| `models`, `men` | Unit size (models = men ÷ 2); for artillery, crews. |
| `command_stars` | Staff generals only: the general's command stars. |
| `normative_value` | What the game's average pricing rule charges for this card's stats in a reference army, in gold. Value ÷ cost above 1 means more stats per gold than average. Probably overstated for units above 240 models. |

## `data/armies.csv`: one army in one game (8 053 rows)

| Column | Meaning |
| --- | --- |
| `match_id` | The game; both teams' armies share it. |
| `played_at` | Game time (UTC). Some dates lie in the future because of changed PC clocks. |
| `map` | Battle map. |
| `faction_key`, `army_corps_name` | The army. |
| `player` | Player name. |
| `team` | 0 or 1. |
| `result` | `win`, `loss`, `draw` or `unknown`. |
| `player_rating_change` | The player's ladder rating change for this game (e.g. +12 / −12); empty if unknown. |
| `staff_key` | The staff general's card key. |
| `unit_keys` | Every other card fielded, space-separated, one entry per copy. |

Only Theatre-of-War and Custom armies are included. The other armies in the
same games (Army Corps armies, AI players) are not, so a game may show armies
on one team only.

## `data/split.json`

The fixed train/test cut date (see `TASK.md`).
