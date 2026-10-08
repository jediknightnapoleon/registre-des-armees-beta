"""Independent legality checker for out/builds.csv against RULES.md.

Reads cards.csv directly (not through the model code) and checks, per
(faction_key, variant):
  1 exactly one staff card (copies 1)          2 <= 31 cards
  3 total cost <= 10 000                       4 <= 1 commander card
  5 per base_unit_key: copies <= unit_cap (if > 0) and <= 1 commander version
  6 foot artillery <= 2, horse artillery <= 1 (2 if the army has no infantry),
    heavy cavalry <= 10
  7 4corps: <= 4 distinct non-empty source_corps (staff included)
  + every card belongs to the army, copies are positive integers, commander
    and staff cards at most one copy, both variants present for all 55 armies.
Usage: python check_builds.py [path-to-builds.csv]   (exit code 1 on any failure)
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "builds.csv")
    cards = defaultdict(dict)
    with open(os.path.join(ROOT, "data", "cards.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cards[r["faction_key"]][r["card_key"]] = r
    builds = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            builds[(r["faction_key"], r["variant"])].append((r["card_key"], r["copies"]))
    errors = []
    for fac in cards:
        for v in ("free", "4corps"):
            if (fac, v) not in builds:
                errors.append(f"{fac} {v}: missing build")
    for (fac, v), items in sorted(builds.items()):
        tag = f"{fac} {v}"
        if v not in ("free", "4corps"):
            errors.append(f"{tag}: unknown variant")
        fc = cards.get(fac)
        if fc is None:
            errors.append(f"{tag}: unknown faction")
            continue
        seen = set()
        sel = []
        for k, n in items:
            if k in seen:
                errors.append(f"{tag}: card listed twice {k}")
            seen.add(k)
            if k not in fc:
                errors.append(f"{tag}: card not in army {k}")
                continue
            try:
                n = int(n)
            except ValueError:
                errors.append(f"{tag}: non-integer copies {k}")
                continue
            if n <= 0:
                errors.append(f"{tag}: non-positive copies {k}")
            sel.append((fc[k], n))
        staff = sum(n for c, n in sel if c["kind"] == "staff")
        if staff != 1:
            errors.append(f"{tag}: rule 1 staff generals = {staff}")
        total = sum(n for c, n in sel)
        if total > 31:
            errors.append(f"{tag}: rule 2 cards = {total}")
        cost = sum(float(c["cost"]) * n for c, n in sel)
        if cost > 10000:
            errors.append(f"{tag}: rule 3 cost = {cost}")
        cmd = sum(n for c, n in sel if c["kind"] == "commander")
        if cmd > 1:
            errors.append(f"{tag}: rule 4 commanders = {cmd}")
        for c, n in sel:
            if c["kind"] in ("commander", "staff") and n > 1:
                errors.append(f"{tag}: {c['kind']} card with {n} copies")
        by_base = defaultdict(lambda: [0, 0])
        for c, n in sel:
            if c["kind"] == "staff":
                continue
            by_base[c["base_unit_key"]][0] += n
            by_base[c["base_unit_key"]][1] += n if c["kind"] == "commander" else 0
        for b, (n, ncmd) in by_base.items():
            cap = int(fc[b]["unit_cap"] or 0) if b in fc else 0
            if cap > 0 and n > cap:
                errors.append(f"{tag}: rule 5 base {b} copies {n} > cap {cap}")
            if ncmd > 1:
                errors.append(f"{tag}: rule 5 base {b} has {ncmd} commander versions")
        for c, n in sel:  # a card's own cap as well (identical to the base cap in the data)
            cap = int(c["unit_cap"] or 0)
            if c["kind"] == "unit" and cap > 0 and n > cap:
                errors.append(f"{tag}: rule 5 card {c['card_key']} copies {n} > cap {cap}")
        has_inf = any(c["arm"] == "infantry" for c in fc.values())
        foot = sum(n for c, n in sel if c["unit_class"] == "artillery_foot")
        horse = sum(n for c, n in sel if c["unit_class"] == "artillery_horse")
        heavy = sum(n for c, n in sel if c["unit_class"] == "cavalry_heavy")
        if foot > 2:
            errors.append(f"{tag}: rule 6 foot artillery {foot}")
        if horse > (1 if has_inf else 2):
            errors.append(f"{tag}: rule 6 horse artillery {horse}")
        if heavy > 10:
            errors.append(f"{tag}: rule 6 heavy cavalry {heavy}")
        if v == "4corps":
            corps = {c["source_corps"] for c, n in sel if c["source_corps"]}
            if len(corps) > 4:
                errors.append(f"{tag}: rule 7 source corps {len(corps)}")
    n_builds = len(builds)
    if errors:
        print(f"FAIL: {len(errors)} problems in {n_builds} builds")
        for e in errors[:50]:
            print("  ", e)
        sys.exit(1)
    print(f"PASS: {n_builds} builds ({len(cards)} armies x 2 variants) satisfy every rule in RULES.md")


if __name__ == "__main__":
    main()
