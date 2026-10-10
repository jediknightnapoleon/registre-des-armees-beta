# How Army Corps prices are used in the game

You model the **list price** (`base_mp_cost`) of each unit. The game stores one list price
per unit per army; nothing below changes it. This page only explains the context.

- **An army** is a selection of at most 31 cards from its army's roster, within 10 000 gold.
- **Army price** = the sum of the list prices of the selected cards, minus **formation
  rebates**:
  - every unit sits in a *brigade* inside a *division* (`division_id`, `brigade_id`);
  - when the selection contains **every copy of every unit of a brigade** (each unit's
    `unit_cap` copies), the army gets a rebate of `floor(C / 100 × (n − 1))` gold, where
    `C` = Σ `unit_cap` × list price over the brigade's units and `n` = Σ `unit_cap` — i.e.
    (n − 1)% of the brigade's full price;
  - a **complete division** earns the same rule over the whole division instead of its
    brigades' rebates;
  - generals don't count in `C` or `n`; division 0 and units without a placement earn none.
- **Caps:** each unit at most `unit_cap` copies (shared with its combat-general versions);
  foot artillery ≤ 2, horse artillery ≤ 1, heavy cavalry ≤ 10 cards per army.
- **Generals:** an army takes one staff general; combat-general versions replace a copy of
  their unit.
