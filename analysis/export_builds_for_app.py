"""Export the cost-effective builds as files the app can import.

Reads analysis/output/cost_effective_builds.csv (analysis/cost_effective_builds.py)
and writes builds in the app's saved-build format (web/src/state/saves.ts,
SAVE_FORMAT_VERSION 2). Import in the app with ⤓ Offline → Import saves… (it takes
a backup file or a single build), open the build from the saved builds, and use
"Save image" in the bottom tray for the app's unit-card strip. Every build puts the
army's cheapest staff general in the staff slot, as cost_effective_builds.py
assumes.

Outputs:
- analysis/output/top_builds_backup.json: one backup file with the top builds
  overall — the five most efficient, plus the five best priced for their own
  rating (efficiency × N/8), deduplicated.
- analysis/output/app_builds/: the top two builds of every army, one JSON file
  each, plus README.md as an index. Build 1 is the max-value build. Build 2 is
  the balanced build (≥ 4 cavalry, ≥ 2 artillery) if it differs, otherwise the
  runner-up (the best build that differs from build 1 in at least one unit).
  Build 3 takes the army's highest-star staff general (cheapest on a tie) and
  the max-value build with the budget left. Build 4 is the max-value build from
  at most 4 source corps — what one Theatre-of-War roll can offer without
  changing the clock (Custom armies: no source corps, same as build 1).

    python analysis/export_builds_for_app.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

OUT = up.ROOT / "analysis" / "output"
FOLDER = OUT / "app_builds"
SAVE_FORMAT_VERSION = 2          # web/src/state/saves.ts
TOP = 5
ORDER = {"artillery": 0, "cavalry": 1, "infantry": 2}


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> int:
    builds: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with open(OUT / "cost_effective_builds.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            builds[(r["faction_key"], r["variant"])].append(r)
    factions = sorted({f for f, _ in builds})
    ratings = up.load_ratings()
    staff: dict[str, tuple[int, str, str]] = {}          # cheapest staff general
    staff_top: dict[str, tuple[int, str, str, int]] = {}  # highest-star staff general, cheapest on a tie
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["faction_key"] in factions and r["is_general"] == "true" and r["men_raw"] in ("32", "122"):
                entry = (int(r["base_mp_cost"]), r["unit_key"], r["unit_name"])
                if r["faction_key"] not in staff or entry < staff[r["faction_key"]]:
                    staff[r["faction_key"]] = entry
                stars = int(up.num(r["command_stars"]))
                old = staff_top.get(r["faction_key"])
                if old is None or (-stars, entry[0]) < (-old[3], old[0]):
                    staff_top[r["faction_key"]] = (*entry, stars)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def general(faction: str, variant: str) -> tuple:
        """(cost, key, name, stars) of the staff general the optimiser used for this build."""
        r = builds[(faction, variant)][0]
        return int(r["staff_cost"]), r["staff_key"], r["staff_name"], int(r["staff_stars"])

    def stats(faction: str, variant: str) -> dict:
        rows = builds[(faction, variant)]
        cost = sum(int(r["copies"]) * int(r["cost_each"]) for r in rows) + general(faction, variant)[0]
        value = sum(int(r["copies"]) * float(r["value_each"]) for r in rows)
        n = ratings[faction]
        arms = defaultdict(int)
        for r in rows:
            arms[r["unit_class"].split("_")[0]] += int(r["copies"])
        return {"army": rows[0]["army_corps_name"], "N": n, "cost": cost, "efficiency": value / cost,
                "own": value / cost * up.REF_RATING / n, "units": sum(arms.values()), "arms": arms}

    def saved(faction: str, variant: str, ident: str, name: str) -> dict:
        rows = sorted(builds[(faction, variant)],
                      key=lambda r: (ORDER.get(r["unit_class"].split("_")[0], 3), -float(r["value_each"])))
        return {"saveFormatVersion": SAVE_FORMAT_VERSION, "id": ident, "name": name, "createdAt": now, "updatedAt": now,
                "factionKey": faction, "armyCorpsName": rows[0]["army_corps_name"],
                "instances": [r["unit_key"] for r in rows for _ in range(int(r["copies"]))],
                "staffSlotUnitKey": general(faction, variant)[1],
                "config": {"density": "comfortable", "showCombatGenerals": True}}

    def same(faction: str, a: str, b: str) -> bool:
        key = lambda v: sorted((r["unit_key"], r["copies"]) for r in builds[(faction, v)])  # noqa: E731
        return key(a) == key(b)

    # 1. The top builds overall, as one backup file.
    table = {f: stats(f, "max value") for f in factions}
    by_abs = sorted(factions, key=lambda f: -table[f]["efficiency"])[:TOP]
    by_own = sorted(factions, key=lambda f: -table[f]["own"])[:TOP]
    top = []
    for tag, group in (("most value for 10 000", by_abs), ("best priced for its rating", by_own)):
        for f in group:
            if f not in [g for g, _ in top]:
                top.append((f, tag))
    backup = {"format": "rda-builds-backup", "version": SAVE_FORMAT_VERSION, "exportedAt": now,
              "builds": [saved(f, "max value", f"b_costeff_{i + 1:02d}",
                               f"Cost-effective: {table[f]['army']} (eff {table[f]['efficiency']:.2f}, "
                               f"{table[f]['own']:.2f} for its rating) — {tag}")
                         for i, (f, tag) in enumerate(top)]}
    (OUT / "top_builds_backup.json").write_text(json.dumps(backup, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. The top two builds of every army, one file each.
    FOLDER.mkdir(parents=True, exist_ok=True)
    for old in FOLDER.glob("*.json"):
        old.unlink()
    index = []
    corps_of = {}
    for (f, v), rows in builds.items():
        corps_of[(f, v)] = rows[0].get("source_corps", "")
    ranked = sorted(factions, key=lambda f: -table[f]["efficiency"])
    for rank, f in enumerate(ranked, 1):
        second = "balanced" if (f, "balanced") in builds and not same(f, "max value", "balanced") else "runner-up"
        for number, variant in ((1, "max value"), (2, second), (3, "top staff"), (4, "four corps")):
            if (f, variant) not in builds:
                continue
            s = stats(f, variant)
            label = {"max value": "max value", "balanced": "balanced (≥ 4 cavalry, ≥ 2 artillery)",
                     "runner-up": "runner-up (next-best max-value build)",
                     "top staff": f"highest-star staff general ({general(f, variant)[3]}★), max value",
                     "four corps": "max value from ≤ 4 source corps (one roll)"
                                   + ("" if f.startswith("ntw3_tow_") else " — Custom army: no corps limit")}[variant]
            name = f"{s['army']} — build {number}: {label}, eff {s['efficiency']:.2f} ({s['own']:.2f} for its rating)"
            file = f"{rank:02d}_{slug(s['army'])}_build{number}.json"
            (FOLDER / file).write_text(json.dumps(saved(f, variant, f"b_ce_{rank:02d}_{number}", name), indent=2,
                                                  ensure_ascii=False), encoding="utf-8")
            index.append([f"`{file}`", s["army"], s["N"], number, label, f"{s['efficiency']:.3f}", f"{s['own']:.3f}",
                          f"{s['cost']:,}", s["units"],
                          f"{s['arms']['infantry']}/{s['arms']['cavalry']}/{s['arms']['artillery']}",
                          f"{general(f, variant)[2]} ({general(f, variant)[0]} gold)",
                          corps_of[(f, variant)] or "—"])
    lines = ["# Cost-effective builds, ready to import into the app", "",
             "Generated by `analysis/export_builds_for_app.py` from `analysis/cost_effective_builds.py` (method and "
             "caveats: `analysis/output/cost_effective_builds.md`). Two builds per army, one file each, in the app's "
             "saved-build format.", "",
             "**To use one:** in the app, ⤓ Offline → *Import saves…* → pick the file, then open the build from your "
             "saved builds. *Save image* in the bottom tray renders its unit cards. For Theatre-of-War armies, "
             "*Generate times* finds a window in which the roll offers every unit.", "",
             "- **Build 1** is the max-value build.",
             "- **Build 2** is the balanced build (≥ 4 cavalry, ≥ 2 artillery) when it differs, otherwise the "
             "runner-up (the best build differing from build 1 in at least one unit).",
             "- **Build 3** takes the army's highest-star staff general (cheapest on a tie) and the max-value build "
             "with the budget left. Staff generals are not counted in *value*, so its efficiency drops by what the "
             "better general costs.",
             "- **Build 4** draws its units *and* staff general from at most 4 source corps, which is all one "
             "Theatre-of-War roll offers without changing the clock (`NTW3AC.ToWFarmycorps`, max 4). The staff "
             "general is chosen jointly, since his corps uses one of the 4. Custom armies have no source corps, so "
             "their build 4 equals build 1. A combat general must still be among the 4 the roll draws from those "
             "corps.",
             "- **Efficiency** = the build's normative value ÷ its cost; *for its rating* removes the corps-number "
             "effect.",
             "- **Rules:** one staff general (the army's cheapest, except in build 3) + up to 30 units = 31 cards, at most one combat "
             "general, 10 000 funds, unit caps, artillery and heavy-cavalry caps. Files are numbered by build 1's "
             "efficiency.", ""]
    lines += up.table(["file", "army", "N", "build", "kind", "efficiency", "for its rating", "cost", "units",
                       "inf/cav/art", "staff general", "source corps"], index)
    (FOLDER / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(backup['builds'])} top builds → top_builds_backup.json; {len(index)} files → {FOLDER.relative_to(up.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
