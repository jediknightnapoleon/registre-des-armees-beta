"""Export the top cost-effective builds as an app backup file.

Reads analysis/output/cost_effective_builds.csv (analysis/cost_effective_builds.py)
and writes the best builds in the app's saved-build format (web/src/state/saves.ts,
SAVE_FORMAT_VERSION 2, an "rda-builds-backup" file). Import it in the app with
⤓ Offline → Import saves…, open a build from the saved builds, and use "Save
image" in the bottom tray to get the app's own unit-card strip.

"Top builds": the five most efficient max-value builds, plus the five best priced
for their own rating (efficiency × N/8), deduplicated. Each build puts the army's
cheapest staff general in the staff slot, as cost_effective_builds.py assumes.

Output: analysis/output/top_builds_backup.json

    python analysis/export_builds_for_app.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

OUT = up.ROOT / "analysis" / "output"
SAVE_FORMAT_VERSION = 2          # web/src/state/saves.ts
TOP = 5


def main() -> int:
    builds: dict[str, list[dict]] = defaultdict(list)
    with open(OUT / "cost_effective_builds.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["variant"] == "max value":
                builds[r["faction_key"]].append(r)
    ratings = up.load_ratings()
    staff: dict[str, tuple[int, str, str]] = {}
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["faction_key"] in builds and r["is_general"] == "true" and r["men_raw"] in ("32", "122"):
                entry = (int(r["base_mp_cost"]), r["unit_key"], r["unit_name"])
                if r["faction_key"] not in staff or entry < staff[r["faction_key"]]:
                    staff[r["faction_key"]] = entry

    def summary(faction: str) -> dict:
        rows = builds[faction]
        cost = sum(int(r["copies"]) * int(r["cost_each"]) for r in rows) + staff[faction][0]
        value = sum(int(r["copies"]) * float(r["value_each"]) for r in rows)
        n = ratings[faction]
        return {"faction": faction, "army": rows[0]["army_corps_name"], "N": n, "cost": cost,
                "efficiency": value / cost, "own": value / cost * up.REF_RATING / n}

    table = [summary(f) for f in builds]
    by_abs = sorted(table, key=lambda t: -t["efficiency"])[:TOP]
    by_own = sorted(table, key=lambda t: -t["own"])[:TOP]
    chosen, seen = [], set()
    for tag, group in (("most value for 10 000", by_abs), ("best priced for its rating", by_own)):
        for t in group:
            if t["faction"] not in seen:
                seen.add(t["faction"])
                chosen.append((tag, t))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    order = {"artillery": 0, "cavalry": 1, "infantry": 2}
    saved = []
    for i, (tag, t) in enumerate(chosen):
        rows = sorted(builds[t["faction"]], key=lambda r: (order.get(r["unit_class"].split("_")[0], 3), -float(r["value_each"])))
        instances = [r["unit_key"] for r in rows for _ in range(int(r["copies"]))]
        saved.append({
            "saveFormatVersion": SAVE_FORMAT_VERSION,
            "id": f"b_costeff_{i + 1:02d}",
            "name": f"Cost-effective: {t['army']} (eff {t['efficiency']:.2f}, {t['own']:.2f} for its rating) — {tag}",
            "createdAt": now, "updatedAt": now,
            "factionKey": t["faction"], "armyCorpsName": t["army"],
            "instances": instances, "staffSlotUnitKey": staff[t["faction"]][1],
            "config": {"density": "comfortable", "showCombatGenerals": True},
        })
        print(f"{t['army']:40} {len(instances):2} units + {staff[t['faction']][2]} ({staff[t['faction']][0]} gold); "
              f"cost {t['cost']:,}  eff {t['efficiency']:.3f} / {t['own']:.3f}  [{tag}]")
    backup = {"format": "rda-builds-backup", "version": SAVE_FORMAT_VERSION, "exportedAt": now, "builds": saved}
    (OUT / "top_builds_backup.json").write_text(json.dumps(backup, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(saved)} builds → analysis/output/top_builds_backup.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
