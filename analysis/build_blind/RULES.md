# Build rules (Theatre-of-War and Custom armies)

A legal build for an army (`faction_key`) is a multiset of that army's cards from
`data/cards.csv`.

1. **Exactly one staff general**: one card with `kind = staff`.
2. **At most 31 cards in total**, staff general included.
3. **Total cost ≤ 10 000** (sum of `cost` over all copies). There are no discounts.
4. **At most one combat general.** A card with `kind = commander` is a unit led
   by a named general. At most one commander card per build.
5. **Unit caps.** A unit and its commander versions share one cap. All cards
   with the same `base_unit_key` together may appear at most `unit_cap` times,
   and at most one of them may be a commander card. `unit_cap = 0` means no
   cap.
6. **Class caps:**
   - **foot artillery:** at most 2 cards with `unit_class = artillery_foot`;
   - **horse artillery:** at most 1 card with `unit_class = artillery_horse`,
     or 2 if the army has no infantry cards at all;
   - **heavy cavalry:** at most 10 cards with `unit_class = cavalry_heavy`.

   A commander card counts as its `unit_class`.
7. **The `4corps` variant** additionally allows at most 4 distinct
   `source_corps` values among all cards of the build, staff general included.
   That is all one game "roll" offers. Cards with an empty `source_corps`
   (Custom armies) are not limited.

Copies: a regular unit card may be taken several times, up to its cap. A
commander card or a staff general at most once.
