"""Which units do players actually bring, per faction, and how do those armies fare?

Source: the Redcoatz ladder replays (tools/download_redcoatz_replays.py →
replays/redcoatz/). Each .replay is read with the repo's own parser
(tools/replay_parser.py, a port of web/src/domain/replay.ts), which yields every
army's corps key (= faction_key) and the exact unit keys it fielded, commander
versions and the staff general included. Results come from the site's match
records (replays/redcoatz/matches.jsonl): "team N wins" / "draw", joined to an
army through its player name.

Scope: Theatre-of-War and Custom armies only (faction_kind in the analysis
dataset, without the developer corps aaa_lordz / austria / hannover / saxony, as in
the pricing models); Army Corps armies, AI players and armies whose player cannot
be placed on a team are left out (counted in the report). A replay in which any
army — on either side — has a corps or unit key that is not in the current
database is disregarded entirely: it comes from another mod or an older version.

Outputs (analysis/output/):
  replay_army_builds.csv   one row per army appearance: match, date, faction,
                           player, team, result, staff general, unit keys
  faction_usage.csv        per faction: appearances, wins / losses / draws, win rate
  unit_usage.csv           per faction × unit (every recruitable card, brought or
                           not): times brought, share of the faction's appearances,
                           copies, win rate when brought vs when not brought
  unit_usage_report.md     coverage and highlights

Win rate = wins ÷ (wins + losses); draws and undetermined games are counted but
left out of it.

    python analysis/replay_unit_usage.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "analysis"))
from tools.replay_parser import parse  # noqa: E402
import unit_pricing as up  # noqa: E402

REPLAYS = ROOT / "replays" / "redcoatz"
OUT = ROOT / "analysis" / "output"
AI_NAMES = ("AI Bot",)


def table(header: list[str], rows: list[list[object]]) -> list[str]:
    return (["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
            + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def winrate(w: int, l: int) -> float:
    return w / (w + l) if w + l else float("nan")


def main() -> int:
    started = time.time()
    with up.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    kind = {r["faction_key"]: r["faction_kind"] for r in rows}
    army_name = {r["faction_key"]: r["army_corps_name"] for r in rows}
    card = {(r["faction_key"], r["unit_key"]): r for r in rows}
    roster: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        roster[r["faction_key"]].append(r["unit_key"])
    in_scope = {f for f, k in kind.items() if k in ("theatre_of_war", "custom") and f not in up.DEV_CORPS}

    matches = {}
    with (REPLAYS / "matches.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            matches[m["id"]] = m

    stats = Counter()
    army_rows: list[dict] = []
    for path in sorted(REPLAYS.glob("*.replay")):
        match_id = path.stem.split("_", 1)[1]
        m = matches.get(match_id)
        if m is None:
            stats["replay without match record"] += 1
            continue
        try:
            battle = parse(path.read_bytes())
        except Exception:                                    # noqa: BLE001 — a bad file must not stop the run
            stats["replay failed to parse"] += 1
            continue
        foreign = [a for a in battle.armies
                   if a.army_key not in kind or any((a.army_key, u.key) not in card for u in a.units)
                   or (a.staff_key and (a.army_key, a.staff_key) not in card)]
        if foreign or not battle.armies:
            stats["replays disregarded: corps or unit not in the database" if foreign
                  else "replays disregarded: no armies parsed"] += 1
            continue
        stats["replays parsed"] += 1
        team_of, ai, label_team, label_player = {}, set(), defaultdict(set), {}
        for t in m["teams"]:
            for p in t.get("players", []):
                team_of[p] = t["team"]
            for a in t.get("armies", []):
                if a.get("is_ai") or a.get("player") in AI_NAMES:
                    ai.add(a.get("player"))
                if a.get("label"):
                    label_team[a["label"]].add(t["team"])
                    label_player[a["label"]] = a.get("player", "")
        outcome = m["outcome"]
        winner = int(outcome.split()[1]) if outcome.startswith("team ") and outcome.endswith(" wins") else None
        for army in battle.armies:
            stats["armies"] += 1
            if army.army_key not in in_scope:
                stats["armies outside ToW/Custom"] += 1
                continue
            if army.player in ai or army.player.startswith("CPU ") or army.player in AI_NAMES:
                stats["AI armies"] += 1
                continue
            team = team_of.get(army.player)
            if team is None:
                # The parser sometimes reads the corps name, or nothing, as the player. Fall back
                # to the site's own army list: the army's name, when it is unique in this match.
                teams = label_team.get(army_name[army.army_key], set())
                if len(teams) == 1:
                    team = next(iter(teams))
                    army.player = label_player.get(army_name[army.army_key]) or army.player
                    stats["ToW/Custom armies placed by army name"] += 1
            if team is None:
                stats["ToW/Custom armies not placed on a team"] += 1
                continue
            result = ("draw" if outcome == "draw" else "unknown" if winner is None
                      else "win" if team == winner else "loss")
            keys = [u.key for u in army.units]
            army_rows.append({"match_id": match_id, "played_at": m.get("played_at", ""), "map": m.get("map_name", ""),
                              "faction_key": army.army_key, "army_corps_name": army_name[army.army_key],
                              "player": army.player, "team": team, "result": result,
                              "staff_key": army.staff_key or "", "unit_keys": keys})
            stats["ToW/Custom armies kept"] += 1

    # Per faction and per faction × unit.
    fac = defaultdict(Counter)
    brought = defaultdict(lambda: defaultdict(Counter))
    for a in army_rows:
        f, res = a["faction_key"], a["result"]
        fac[f]["appearances"] += 1
        fac[f][res] += 1
        copies = Counter(a["unit_keys"])
        if a["staff_key"]:
            copies[a["staff_key"]] += 1
        for k, n in copies.items():
            brought[f][k]["armies"] += 1
            brought[f][k]["copies"] += n
            brought[f][k][res] += 1

    with open(OUT / "replay_army_builds.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["match_id", "played_at", "map", "faction_key", "army_corps_name", "player", "team", "result",
                    "staff_key", "units", "unit_keys"])
        for a in army_rows:
            w.writerow([a["match_id"], a["played_at"], a["map"], a["faction_key"], a["army_corps_name"], a["player"],
                        a["team"], a["result"], a["staff_key"], len(a["unit_keys"]), " ".join(a["unit_keys"])])
    with open(OUT / "faction_usage.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "army_corps_name", "kind", "appearances", "wins", "losses", "draws", "unknown",
                    "winrate"])
        for f in sorted(in_scope, key=lambda f: -fac[f]["appearances"]):
            c = fac[f]
            w.writerow([f, army_name[f], kind[f], c["appearances"], c["win"], c["loss"], c["draw"], c["unknown"],
                        f"{winrate(c['win'], c['loss']):.3f}" if c["win"] + c["loss"] else ""])
    unit_rows = []
    for f in sorted(in_scope):
        c = fac[f]
        for k in roster[f]:
            r, b = card[(f, k)], brought[f][k]
            not_w, not_l = c["win"] - b["win"], c["loss"] - b["loss"]
            unit_rows.append([f, army_name[f], k, r["unit_name"], r["unit_class"], r["is_general"], r["base_mp_cost"],
                              r["unit_cap"], c["appearances"], b["armies"],
                              f"{b['armies'] / c['appearances']:.3f}" if c["appearances"] else "",
                              b["copies"], f"{b['copies'] / b['armies']:.2f}" if b["armies"] else "",
                              b["win"], b["loss"], b["draw"],
                              f"{winrate(b['win'], b['loss']):.3f}" if b["win"] + b["loss"] else "",
                              f"{winrate(not_w, not_l):.3f}" if not_w + not_l else ""])
    with open(OUT / "unit_usage.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "army_corps_name", "unit_key", "unit_name", "unit_class", "is_general", "cost",
                    "unit_cap", "faction_appearances", "armies_bringing", "pick_rate", "total_copies",
                    "copies_when_brought", "wins_when_brought", "losses_when_brought", "draws_when_brought",
                    "winrate_when_brought", "winrate_when_not_brought"])
        w.writerows(unit_rows)

    # Report.
    total = sum(fac[f]["appearances"] for f in in_scope)
    L = ["# Unit usage and win rates in Redcoatz ladder games (ToW and Custom armies)", "",
         "Generated by `analysis/replay_unit_usage.py` from the replays in `replays/redcoatz/` (parsed with "
         "`tools/replay_parser.py`) and the site's match results. Win rate = wins ÷ (wins + losses). Small samples "
         "are noisy: a unit brought in 5 games says little.", "",
         "## Coverage", ""]
    L += [f"- {k}: {v}" for k, v in stats.most_common()] + [
        f"- ToW/Custom factions seen: {sum(1 for f in in_scope if fac[f]['appearances'])} of {len(in_scope)}", ""]
    L += ["## Factions", ""]
    L += table(["army", "appearances", "W / L / D", "win rate"],
               [[army_name[f], fac[f]["appearances"], f"{fac[f]['win']} / {fac[f]['loss']} / {fac[f]['draw']}",
                 f"{winrate(fac[f]['win'], fac[f]['loss']):.3f}" if fac[f]["win"] + fac[f]["loss"] else "—"]
                for f in sorted(in_scope, key=lambda f: -fac[f]["appearances"]) if fac[f]["appearances"]])
    L += ["", "## Most-picked units per faction (top 3, factions with ≥ 20 appearances)", ""]
    rows_md = []
    for f in sorted(in_scope, key=lambda f: -fac[f]["appearances"]):
        if fac[f]["appearances"] < 20:
            continue
        top = sorted(((b["armies"], k) for k, b in brought[f].items() if card.get((f, k), {}).get("is_general") != "true"),
                     reverse=True)[:3]
        rows_md.append([army_name[f], fac[f]["appearances"],
                        "; ".join(f"{card[(f, k)]['unit_name']} {n / fac[f]['appearances']:.0%}" for n, k in top)])
    L += table(["army", "appearances", "most-picked units (pick rate)"], rows_md)
    L += ["", f"Total ToW/Custom army appearances: {total}.", "", f"*Runtime {time.time() - started:.0f} s.*", ""]
    (OUT / "unit_usage_report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"{stats['replays parsed']} replays, {stats['ToW/Custom armies kept']} ToW/Custom armies → "
          "analysis/output/unit_usage.csv, faction_usage.csv, replay_army_builds.csv, unit_usage_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
