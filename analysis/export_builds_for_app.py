"""Export the cost-effective builds as files the app can import.

Reads analysis/output/cost_effective_builds.csv (analysis/cost_effective_builds.py)
and writes builds in the app's saved-build format (web/src/state/saves.ts,
SAVE_FORMAT_VERSION 2). Import in the app with ⤓ Offline → Import saves… (it takes
a backup file or a single build), open the build from the saved builds, and use
"Save image" in the bottom tray for the app's unit-card strip. Each build's staff
general is the one cost_effective_builds.py chose for it (read from its CSV).

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

The same again for each size-harmonisation version of cost_effective_builds.py:
the files above come from the fully harmonised builds; the noise-only builds
(cost_effective_builds_noise_only.csv) go to top_builds_backup_noise_only.json
and app_builds_noise_only/. A run with a micro card cap (cost_effective_builds.py
--max-cards N) adds the suffix _max<N> to all of these. Every builds CSV found is
exported. Ids and names carry the version, so the sets can be imported side by
side.

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
SAVE_FORMAT_VERSION = 2          # web/src/state/saves.ts
TOP = 5
ORDER = {"artillery": 0, "cavalry": 1, "infantry": 2}
STEM = "cost_effective_builds"
MAX_CARDS = 31                   # the game's limit, staff general included


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def version(suffix: str) -> tuple[bool, int]:
    """(noise-only?, card cap) of a cost_effective_builds{suffix}.csv, e.g. "_noise_only_max20" → (True, 20)."""
    m = re.fullmatch(r"(_noise_only)?(?:_max(\d+))?", suffix)
    if m is None:
        raise ValueError(f"unrecognised builds file suffix {suffix!r}")
    return bool(m.group(1)), int(m.group(2) or MAX_CARDS)


def main() -> int:
    """Export every version cost_effective_builds.py has written: size version × card cap."""
    for path in sorted(OUT.glob(f"{STEM}*.csv")):
        export(path.stem[len(STEM):])
    return 0


def export(suffix: str) -> None:
    """One version: cost_effective_builds{suffix}.csv → top_builds_backup{suffix}.json, app_builds{suffix}/.

    Build names carry the version ("harmonised" / "noise-only", and the card cap if any) and ids a
    matching prefix (ce, cen, cem20, cenm20 …), so every version can be imported side by side."""
    noise, max_cards = version(suffix)
    capped = max_cards < MAX_CARDS
    tag = ("noise-only" if noise else "harmonised") + (f", ≤ {max_cards} cards" if capped else "")
    prefix = "ce" + ("n" if noise else "") + (f"m{max_cards}" if capped else "")
    folder = OUT / f"app_builds{suffix}"
    builds: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with open(OUT / f"cost_effective_builds{suffix}.csv", encoding="utf-8") as fh:
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
    for why, group in (("most value for 10 000", by_abs), ("best priced for its rating", by_own)):
        for f in group:
            if f not in [g for g, _ in top]:
                top.append((f, why))
    backup = {"format": "rda-builds-backup", "version": SAVE_FORMAT_VERSION, "exportedAt": now,
              "builds": [saved(f, "max value", f"b_{prefix}eff_{i + 1:02d}",
                               f"Cost-effective ({tag}): {table[f]['army']} (eff {table[f]['efficiency']:.2f}, "
                               f"{table[f]['own']:.2f} for its rating) — {why}")
                         for i, (f, why) in enumerate(top)]}
    (OUT / f"top_builds_backup{suffix}.json").write_text(json.dumps(backup, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")

    # 2. The four builds of every army, one file each.
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
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
            name = (f"{s['army']} — build {number} ({tag}): {label}, eff {s['efficiency']:.2f} "
                    f"({s['own']:.2f} for its rating)")
            file = f"{rank:02d}_{slug(s['army'])}_build{number}.json"
            (folder / file).write_text(json.dumps(saved(f, variant, f"b_{prefix}_{rank:02d}_{number}", name), indent=2,
                                                  ensure_ascii=False), encoding="utf-8")
            index.append([f"`{file}`", s["army"], s["N"], number, label, f"{s['efficiency']:.3f}", f"{s['own']:.3f}",
                          f"{s['cost']:,}", s["units"],
                          f"{s['arms']['infantry']}/{s['arms']['cavalry']}/{s['arms']['artillery']}",
                          f"{general(f, variant)[2]} ({general(f, variant)[0]} gold)",
                          corps_of[(f, variant)] or "—"])
    other = (("fully harmonised", suffix.replace("_noise_only", "")) if noise
             else ("noise-only", "_noise_only" + suffix))
    lines = [f"# Cost-effective builds ({tag}), ready to import into the app", "",
             "Generated by `analysis/export_builds_for_app.py` from `analysis/cost_effective_builds.py` (method and "
             f"caveats: `analysis/output/{STEM}{suffix}.md`). Four builds per army, one file each, in "
             "the app's saved-build format.", "",
             f"Unit values here are {'size-harmonised for noise only' if noise else 'fully size-harmonised'} "
             f"(report §5); the {other[0]} version is in `app_builds{other[1]}/`. Build ids and names carry the "
             "version, so the sets can be imported side by side.", ""]
    if capped:
        lines += [f"**Micro cap: at most {max_cards} cards** including the staff general ({max_cards - 1} units), "
                  f"set with `python analysis/cost_effective_builds.py --max-cards {max_cards}`. The game allows 31; "
                  "fewer units are easier to control, which no price captures.", ""]
    lines += ["**To use one:** in the app, ⤓ Offline → *Import saves…* → pick the file, then open the build from your "
             "saved builds. *Save image* in the bottom tray renders its unit cards. For Theatre-of-War armies, "
             "*Generate times* finds a window in which the roll offers every unit.", "",
             "- **Build 1** is the max-value build.",
             "- **Build 2** is the balanced build (≥ 4 cavalry, ≥ 2 artillery) when it differs, otherwise the "
             "runner-up (the best build differing from build 1 in at least one unit).",
             "- **Build 3** takes the army's highest-star staff general (cheapest on a tie) and the max-value build "
             "with the budget left. Its general is valued by the price rule alone, so its efficiency drops by "
             "whatever the better general costs beyond that value.",
             "- **Build 4** draws its units *and* staff general from at most 4 source corps, which is all one "
             "Theatre-of-War roll offers without changing the clock (`NTW3AC.ToWFarmycorps`, max 4). The staff "
             "general is chosen jointly, since his corps uses one of the 4. Custom armies have no source corps, so "
             "their build 4 equals build 1. A combat general must still be among the 4 the roll draws from those "
             "corps.",
             "- **Efficiency** = the build's normative value ÷ its cost; *for its rating* removes the corps-number "
             "effect.",
             "- **Rules:** one staff general (valued by the global general price rule and chosen by the optimiser; build 3 "
             f"takes the highest-star one) + up to {max_cards - 1} units = {max_cards} cards"
             + (" (the user's micro cap; the game allows 31)" if capped else "") + ", at most one combat "
             "general, 10 000 funds, unit caps, artillery and heavy-cavalry caps. Files are numbered by build 1's "
             "efficiency.", ""]
    lines += up.table(["file", "army", "N", "build", "kind", "efficiency", "for its rating", "cost", "units",
                       "inf/cav/art", "staff general", "source corps"], index)
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(backup['builds'])} top builds → top_builds_backup{suffix}.json; "
          f"{len(index)} files → {folder.relative_to(up.ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
