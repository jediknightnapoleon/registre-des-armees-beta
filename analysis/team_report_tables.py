"""Refresh the generated tables in analysis/TEAM_BUILDS_REPORT.md from the team-search outputs.

Each table sits between `<!-- TABLE:<name> -->` and `<!-- /TABLE:<name> -->` in the report and is
rewritten in place, so re-running analysis/team_search.py and then this script keeps the report's
tables current without hand edits. (The prose numbers come from team_search.json and the build
summaries; update them by hand.)

Tables: `theatres` (value per point per AC theatre), `ac` (best AC team per T, any theatre),
`tow` (best ToW + Custom team per T, per side), `campaigns` (Imperial vs Coalition at equal T).

    py -3.13 analysis/team_report_tables.py
"""

from __future__ import annotations

import csv
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unit_pricing as up  # noqa: E402

TEAMS = up.ROOT / "analysis" / "output" / "teams"
REPORT = up.ROOT / "analysis" / "TEAM_BUILDS_REPORT.md"


def theatre_names() -> dict[str, str]:
    names = {}
    with open(up.ROOT / "data" / "generated" / "army_corps_catalog.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if "_ac_" in r["faction_key"]:
                names[r["faction_key"].split("_")[2]] = r["theatre_name"]
    return names


def read(name: str) -> list[dict]:
    with open(TEAMS / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def theatres_table(names: dict[str, str]) -> list[str]:
    vpp: dict[str, list[dict]] = defaultdict(list)
    for r in read("value_per_point.csv"):
        if r["kind"] == "ac":
            vpp[r["pool"]].append(r)
    teams: dict[str, list[dict]] = defaultdict(list)
    for r in read("teams_ac.csv"):
        teams[r["pool"]].append(r)
    L = ["| Code | Theatre | Corps | N | T | Most value per point (top 3) | Least | Median team value / T |",
         "|---|---|---|---|---|---|---|---|"]
    for code in sorted(vpp):
        rows = sorted(vpp[code], key=lambda r: int(r["rank_in_pool_sb"]))
        ns = [int(r["N"]) for r in rows]
        ts = [int(t["T"]) for t in teams[code]]
        top = ", ".join(f'{r["army"]} {float(r["value_per_point_sb"]):.0f}' for r in rows[:3])
        least = f'{rows[-1]["army"]} {float(rows[-1]["value_per_point_sb"]):.0f}'
        per_t = f'{st.median(float(t["total_sb"]) / int(t["T"]) for t in teams[code]):.0f}' if ts else "—"
        t_range = f"{min(ts)}–{max(ts)}" if ts else "— (< 4 corps)"
        L.append(f"| {code} | {names.get(code, '?')} | {len(rows)} | {min(ns)}–{max(ns)} | {t_range} | {top} | "
                 f"{least} | {per_t} |")
    return L


def best_index() -> dict[tuple, dict]:
    return {(r["kind"], r["scope"], r["pool"] if r["scope"] == "pool" else "*", r["criterion"], r["version"], r["T"]): r
            for r in read("best_teams.csv")}


def agree(idx: dict, kind: str, scope: str, pool: str, crit: str, t: str, members: str) -> str:
    marks = []
    for v in ("full", "noise"):
        o = idx.get((kind, scope, pool, crit, v, t))
        marks.append("✓" if o and o["members"] == members else "✗")
    return " ".join(marks)


def ac_table(idx: dict, names: dict[str, str]) -> list[str]:
    L = []
    for crit in ("total", "weakest"):
        L += [f"**Best by {crit}**", "", "| T | Theatre | N | Team | Total | Weakest | full / noise agree |",
              "|---|---|---|---|---|---|---|"]
        rows = sorted((r for k, r in idx.items() if k[:5] == ("ac", "all", "*", crit, "sb")), key=lambda r: int(r["T"]))
        for r in rows:
            side = "Imp" if r["pool"].startswith("a") else "Coa"
            L.append(f"| {r['T']} | {names[r['pool']]} ({side}) | {r['Ns']} | {r['members']} | "
                     f"{float(r['total']):,.0f} | {float(r['weakest']):,.0f} | "
                     f"{agree(idx, 'ac', 'all', '*', crit, r['T'], r['members'])} |")
        L.append("")
    return L[:-1]


def tow_table(idx: dict) -> list[str]:
    L = []
    for side in ("imperial", "coalition"):
        for crit in ("total", "weakest"):
            L += [f"**{side.capitalize()}, best by {crit}**", "", "| T | N | Team | Total | Weakest | full / noise agree |",
                  "|---|---|---|---|---|---|"]
            rows = sorted((r for k, r in idx.items() if k[:5] == ("tow", "pool", side, crit, "sb")),
                          key=lambda r: int(r["T"]))
            for r in rows:
                L.append(f"| {r['T']} | {r['Ns']} | {r['members']} | {float(r['total']):,.0f} | "
                         f"{float(r['weakest']):,.0f} | {agree(idx, 'tow', 'pool', side, crit, r['T'], r['members'])} |")
            L.append("")
    return L[:-1]


def campaigns_table(names: dict[str, str]) -> list[str]:
    by_t: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in read("teams_ac.csv"):
        by_t[r["pool"]][int(r["T"])].append(float(r["total_sb"]))
    L = ["| Imperial theatre | Coalition theatre | Shared T | Imperial vs Coalition |", "|---|---|---|---|"]
    for a in sorted(by_t):
        b = "b" + a[1:]
        if not a.startswith("a") or b not in by_t:
            continue
        shared = sorted(set(by_t[a]) & set(by_t[b]))
        if not shared:
            continue
        gap = st.median(st.median(by_t[a][t]) / st.median(by_t[b][t]) - 1 for t in shared)
        single = " (one Imperial team)" if sum(len(v) for v in by_t[a].values()) == 1 else ""
        L.append(f"| {names[a]} | {names[b]} | {shared[0]}–{shared[-1]} | {100 * gap:+.1f}%{single} |")
    return L


def main() -> int:
    names, idx = theatre_names(), best_index()
    tables = {"theatres": theatres_table(names), "ac": ac_table(idx, names), "tow": tow_table(idx),
              "campaigns": campaigns_table(names)}
    text = REPORT.read_text(encoding="utf-8")
    for name, lines in tables.items():
        block = f"<!-- TABLE:{name} -->\n" + "\n".join(lines) + f"\n<!-- /TABLE:{name} -->"
        pattern = re.compile(rf"<!-- TABLE:{name} -->(?:.*?<!-- /TABLE:{name} -->)?", re.S)
        assert pattern.search(text), name
        text = pattern.sub(lambda _: block, text, count=1)
    REPORT.write_text(text, encoding="utf-8")
    print(f"refreshed {', '.join(tables)} in {REPORT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
