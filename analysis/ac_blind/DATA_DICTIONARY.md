# Data dictionary — `data/ac_units.csv`

Unit data exported from the *Napoleonic Total War III* mod, for the multiplayer army
builder: every **Army Corps** army's roster.

- **One row per (unit, army):** 13 116 rows, 238 armies (`faction_key`), 72 columns.
- **Format:** UTF-8, comma-separated. **Missing values:** empty cells. **Booleans:** `true` / `false`.

**Target:** `base_mp_cost`, the unit's list price in gold.

## Added columns

| Column | Meaning |
| --- | --- |
| `corps_number` | The number that opens the army's name (`army_corps_name` "8. Ney / VI.C" → 8). 3–13 |
| `fold` | Cross-validation fold 1–5 to use for every experiment. Empty = out of scope (fixed artillery) or a row that must always stay in training (it alone carries some attribute value) — never score those |
| `corps_holdout` | 1 for the 17 armies of the unseen-army test (`TASK.md`) |

## Identity and faction

| Column | Meaning |
| --- | --- |
| `unit_key` | Unit identifier |
| `faction_key` | Faction (army) identifier |
| `army_corps_name` | Display name of the faction/army, e.g. `[1812] 10. Rossiya` |
| `unit_name` | Display name of the unit. Usually ends with a bracketed speed tag such as `[L4]` |
| `faction_kind` | Always `army_corps` here |
| `corps_side` | `empire` or `coalition` |
| `is_tow_variant` | Always `false` here |
| `source_corps_id`, `source_corps_faction_key`, `source_corps_name` | Empty here |

## Type, size and movement

| Column | Meaning |
| --- | --- |
| `unit_class` | One of 15 classes: `infantry_line`, `infantry_light`, `infantry_grenadiers`, `infantry_skirmishers`, `infantry_militia`, `infantry_irregulars`, `cavalry_light`, `cavalry_standard`, `cavalry_lancers`, `cavalry_heavy`, `cavalry_missile`, `artillery_foot`, `artillery_horse`, `artillery_fixed`, `general` |
| `men_raw` | Number of soldiers in the unit file |
| `men_display` | Soldiers shown in game, = floor(`men_raw` / 2) |
| `guns` | Number of guns (artillery only) |
| `speed_code` | Speed class derived by the data pipeline from the movement entity (e.g. `L3`, `C4`, `F2`) |
| `speed_entity_key` | The movement entity `speed_code` was derived from |
| `rank_depth` | Number of ranks the unit forms in |
| `base_density`, `close_formation_spacing_horizontal`, `close_formation_spacing_vertical`, `loose_formation_spacing_horizontal`, `loose_formation_spacing_vertical` | Formation geometry |
| `unit_drill_set` | Drill set, i.e. which formations the unit can use |
| `unit_training_level` | `elite`, `well_trained`, `trained`, `poorly_trained` or `mob` |

## Combat stats

| Column | Meaning |
| --- | --- |
| `accuracy`, `reload_skill`, `ammo` | Ranged stats |
| `morale` | Morale |
| `melee_attack`, `melee_defense`, `charge_bonus` | Melee stats |
| `range` | Weapon range |
| `weapon_key`, `firearm` | Weapon identifier and firearm display name |
| `projectile_key` | The projectile the unit fires |
| `range_selection_method` | How the pipeline resolved the projectile |
| `projectile_damage`, `projectile_reload_time` | Stats of that projectile |

## Abilities (booleans)

| Column | Meaning |
| --- | --- |
| `can_form_square`, `has_stamina`, `is_shock_resistant`, `can_inspire`, `has_guerrilla_deployment`, `can_place_stakes`, `can_place_mines`, `scares_enemies`, `can_build_barricades` | Abilities listed in the unit description |
| `skirmish`, `guard_mode`, `can_snipe`, `pike_square` | Engine ability flags |

## Generals

| Column | Meaning |
| --- | --- |
| `is_general` | The row is a general (`unit_class` = `general`) |
| `is_commander_variant` | A general attached to a regular unit |
| `command_stars` | General's command rating, 1–9 (blank if none) |

## Army-builder placement and assets

| Column | Meaning |
| --- | --- |
| `division_brigade_code`, `division_id`, `brigade_id`, `placement_source` | Where the unit sits on the army roster |
| `unit_cap` | Maximum copies allowed in one army |
| `icon_*`, `command_star_*`, `guerrilla_badge_*` | Icon and UI asset paths and layout |
