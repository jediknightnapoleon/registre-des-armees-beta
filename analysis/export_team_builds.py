"""Export the AC builds and the best teams as files the app can import (step A4).

Writes the app's saved-build format (web/src/state/saves.ts, SAVE_FORMAT_VERSION 2), like
analysis/export_builds_for_app.py. Import with ⤓ Offline → Import saves….

AC pricing is order-sensitive: the app replays the staff general first, then `instances` in their
saved order, and credits a formation rebate only for groups completed by cards that were each
affordable at list price when taken (web/src/state/build.ts recruitOrder / affordableSubset). So an
AC build is written in the recruit order analysis/ac_builds.py verified, and re-priced here through
the Python port of the rules (tools/army_builder_rules.calculate_army_cost +
ac_discounts.affordable_prefix); a build whose replayed price differs from its summary is refused.

Outputs (gitignored JSON; the README.md indexes stay tracked):
- analysis/output/app_builds_ac_sb/: every AC corps' best build on the size-band values;
- analysis/output/app_builds_ac_price/: every AC corps' most face value for 10 000 (model-free);
- analysis/output/app_builds_teams/: one backup file per best team (sb; AC over all theatres,
  ToW + Custom over both sides; by total and by weakest member), holding its four builds.

    py -3.13 analysis/export_team_builds.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ac_discounts as acd  # noqa: E402
import export_builds_for_app as eba  # noqa: E402
import checkpoints as ckpt  # noqa: E402
import common  # noqa: E402
import unit_pricing as up  # noqa: E402
from tools import army_builder_rules as abr  # noqa: E402

TEAMS = common.TEAMS_OUT
OUT = common.OUTPUT
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def saved(faction: str, army: str, ident: str, name: str, instances: list[str], staff: str) -> dict:
    return {"saveFormatVersion": eba.SAVE_FORMAT_VERSION, "id": ident, "name": name, "createdAt": NOW,
            "updatedAt": NOW, "factionKey": faction, "armyCorpsName": army, "instances": instances,
            "staffSlotUnitKey": staff, "config": {"density": "comfortable", "showCombatGenerals": True}}


def ac_builds(version: str, catalog: abr.UnitCatalog) -> dict[str, dict]:
    """faction → {army, N, order (staff first), final cost, value, face} for one version, every
    build re-priced in recruit order and checked against its summary row."""
    order: dict[str, list[tuple[int, str]]] = defaultdict(list)
    with open(TEAMS / f"ac_builds_{version}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            order[r["faction_key"]].append((int(r["recruit_position"]), r["unit_key"]))
    out = {}
    with open(TEAMS / f"ac_build_summary_{version}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["cards"]:
                continue
            f = r["faction_key"]
            keys = [k for _, k in sorted(order[f])]
            roster = list(catalog.cards_for_faction(f))
            by_key = {c.unit_key: c for c in roster}
            cards = [by_key[k] for k in keys]
            price = abr.calculate_army_cost(cards[1:] + cards[:1], roster, f)
            assert len(acd.affordable_prefix(cards, roster, f)) == len(cards), f
            assert price.final_cost == int(r["final_cost"]) <= 10_000, (f, price.final_cost, r["final_cost"])
            out[f] = {"army": r["army_corps_name"], "N": int(r["corps_number"]), "keys": keys,
                      "final": price.final_cost, "face": price.base_cost, "rebate": price.applied_discount,
                      "value": float(r["value"]), "value_sb": float(r["value_sb"])}
    return out


def tow_builds(version: str) -> dict[str, dict]:
    builds = common.load_pickle(ckpt.tow_builds_path(version))
    return {f: {"army": b["name"], "N": b["n"], "staff": b["staff"],
                "instances": [k for k, n in b["cards"] for _ in range(n)], "final": b["cost"], "value": b["value"]}
            for f, b in builds.items()}


def write_folder(folder: Path, files: list[tuple[str, dict]], index: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
        old.unlink()
    for name, body in files:
        (folder / name).write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def main() -> int:
    catalog = abr.UnitCatalog.from_csv(up.ROOT / "data" / "generated" / "ntw3_army_builder_units.csv")
    ac = {v: ac_builds(v, catalog) for v in ("sb", "price")}
    for v, title in (("sb", "best build on the size-band values"),
                     ("price", "most face value for 10 000 (real list prices, no model)")):
        files, index = [], [f"# AC builds — {title}", "",
                            "Generated by analysis/export_team_builds.py from analysis/output/teams/"
                            f"ac_builds_{v}.csv. Recruit order matters for AC rebates: import as is, don't reorder.",
                            "", "| File | Army | N | Face value | Rebate | Cost | Value (sb) |", "|---|---|---|---|---|---|---|"]
        for f, b in sorted(ac[v].items(), key=lambda t: (t[1]["N"], t[1]["army"])):
            file = f"{eba.slug(b['army'])}_{f}.json"
            name = (f"AC {'size-band' if v == 'sb' else 'max face value'}: {b['army']} — face {b['face']} − rebate "
                    f"{b['rebate']} = {b['final']}")
            files.append((file, saved(f, b["army"], f"b_ac{v}_{f}", name, b["keys"][1:], b["keys"][0])))
            index.append(f"| {file} | {b['army']} | {b['N']} | {b['face']} | {b['rebate']} | {b['final']} | "
                         f"{b['value_sb']:.0f} |")
        write_folder(OUT / f"app_builds_ac_{v}", files, index)
        print(f"app_builds_ac_{v}: {len(files)} builds")

    tow = tow_builds("sb")
    files, index = [], ["# Best teams of four — one backup file per team", "",
                        "Generated by analysis/export_team_builds.py from analysis/output/teams/best_teams.csv "
                        "(size-band values; best over all theatres / both sides at each points total T). Each file "
                        "holds the team's four builds; import it with ⤓ Offline → Import saves….", "",
                        "| File | Pool | T | Best by | Team (N) | Total value | Weakest |", "|---|---|---|---|---|---|---|"]
    with open(TEAMS / "best_teams.csv", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["scope"] == "all" and r["version"] == "sb"
                and r["kind"] in ("ac", "tow")]
    for r in sorted(rows, key=lambda r: (r["kind"], int(r["T"]), r["criterion"])):
        builds = []
        for i, f in enumerate(r["factions"].split("|")):
            if r["kind"] == "ac":
                b = ac["sb"][f]
                instances, staff = b["keys"][1:], b["keys"][0]
            else:
                b = tow[f]
                instances, staff = b["instances"], b["staff"]
            builds.append(saved(f, b["army"], f"b_team_{r['kind']}_T{r['T']}_{r['criterion']}_{i + 1}",
                                f"Team T{r['T']} best by {r['criterion']} ({i + 1}/4): {b['army']}", instances, staff))
        file = f"{r['kind']}_T{int(r['T']):02d}_{r['criterion']}.json"
        files.append((file, {"format": "rda-builds-backup", "version": eba.SAVE_FORMAT_VERSION, "exportedAt": NOW,
                             "builds": builds}))
        index.append(f"| {file} | {r['pool']} | {r['T']} | {r['criterion']} | {r['members']} ({r['Ns']}) | "
                     f"{float(r['total']):.0f} | {float(r['weakest']):.0f} |")
    write_folder(OUT / "app_builds_teams", files, index)
    print(f"app_builds_teams: {len(files)} teams")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
