"""Army Corps builds from the Redcoatz ladder replays and the Clan Games replays, and the elite-player candidates.

Step 1–2 of the "Veteran's choice" study (plan: elite players' AC builds reveal value the price models
miss; analysis/VETERAN_CHOICE_REPORT.md once written). Replay-derived rows (builds, player names,
rankings) are written under analysis/local/veteran/ (gitignored) and never committed.

  extract     every AC army in every replay (analysis/replays.py), placed on its team, with its result
              and rating change, checked against today's data. Clan Games replays already on Redcoatz
              (same file, or the same battle) are skipped; the rest join with no team, result or rating
              (source = clan), dated by the median Redcoatz date of their season's duplicates:
              - the corps and every card exist today and the corps isn't work in progress (1813);
              - legal today: after formation rebates it costs ≤ 10 000, every card is affordable in the
                replay's order (ac_discounts.affordable_prefix, the app's recruit-order rule), and the
                rules engine's limits hold (check_known_limits, commander slot last, as ac_builds.py);
              → analysis/local/veteran/ac_builds.csv and extract_summary.md (counts per year × reason).
  candidates  per AC player: appearances, legal builds, results, ladder rating (rankings.json when
              fetched, else the sum of their rating changes), last game, name variants
              → analysis/local/veteran/candidates.csv, for the user to pick the elite list
              (analysis/local/veteran/players.txt: one player per line, aliases on the same line
              separated by " | ").

    py -3.13 analysis/veteran_builds.py extract
    py -3.13 analysis/veteran_builds.py candidates
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac_discounts as acd  # noqa: E402
import common  # noqa: E402
import replays  # noqa: E402

sys.path.insert(0, str(common.ROOT))
from tools import army_builder_rules as abr  # noqa: E402

LOCAL = common.LOCAL / "veteran"
BUILDS_CSV = LOCAL / "ac_builds.csv"
COLUMNS = ["source", "match_id", "played_at", "year", "map", "game_build", "faction_key", "army_corps_name", "player",
           "placed_by", "team", "result", "rating_delta", "commander_key", "unit_keys", "cards", "list_cost",
           "rebate", "final_cost", "legal", "reason"]


def army_names() -> dict[str, str]:
    with common.DATA_CSV.open(encoding="utf-8-sig", newline="") as fh:
        return {r["faction_key"]: r["army_corps_name"] for r in csv.DictReader(fh)}


def legality(faction: str, commander: str | None, units: tuple[str, ...], catalog: abr.UnitCatalog,
             rosters: dict[str, tuple]) -> tuple[str, dict]:
    """("" when legal today, else the first reason) and the build's prices."""
    if common.is_wip(faction):
        return "work-in-progress corps", {}
    roster = rosters.get(faction)
    if not roster:
        return "corps not in today's data", {}
    keys = units + ((commander,) if commander else ())
    try:
        cards = catalog.resolve_selection(faction, list(keys))
    except Exception:                                        # noqa: BLE001 — an unknown key
        return "card not in today's roster", {}
    sel_units, sel_commander = cards[:len(units)], cards[len(units):]
    selected = sel_units + sel_commander                     # commander slot last (expandBuild), as ac_builds.py
    price = abr.calculate_army_cost(selected, roster, faction)
    info = {"cards": len(selected), "list_cost": price.base_cost, "rebate": price.applied_discount,
            "final_cost": price.final_cost}
    if not commander:
        return "no commander slot", info
    if price.final_cost > acd.MAX_BUILD_COST:
        return "over 10 000 after rebates", info
    try:
        limits = abr.check_known_limits(selected, faction, staff_slot_index=len(selected) - 1,
                                        recruitable_cards=roster)
    except abr.RuleDataError as error:                 # e.g. a regular unit in the commander slot
        return f"rules: {error}", info
    if not limits.valid:
        return f"limits: {limits.violations[0].rule}", info
    order = sel_commander + sel_units                        # the commander slot is recruited first
    if len(acd.affordable_prefix(order, roster, faction)) < len(order):
        return "not affordable in the replay's order", info
    return "", info


def extract(started: float) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    matches = replays.load_matches()
    parsed = replays.parsed_replays(log=lambda s: common.log(s, started))
    names = army_names()
    catalog = abr.UnitCatalog.from_csv(common.BUILDER_CSV)
    rosters = {f: catalog.cards_for_faction(f) for f in {c.faction_key for c in catalog.cards}}
    stats, by_year = Counter(), defaultdict(Counter)
    rows = []
    for match_id, rep in parsed.items():
        m = matches.get(match_id)
        if m is None:
            stats["replay without match record"] += 1
            continue
        if rep is None:
            stats["replay failed to parse"] += 1
            continue
        ctx = replays.MatchContext.of(m)
        year = (m.get("played_at") or "")[:4]
        for army in rep.armies:
            if "_ac_" not in army.faction_key:
                continue
            stats["AC armies"] += 1
            if ctx.is_ai(army.player):
                stats["AI armies"] += 1
                continue
            placed = ctx.place(army.player, names.get(army.faction_key, ""))
            if placed is None:
                stats["not placed on a team"] += 1
                continue
            team, player, how = placed
            reason, info = legality(army.faction_key, army.commander_key, army.unit_keys, catalog, rosters)
            by_year[year][reason or "legal today"] += 1
            delta = ctx.rating_delta(player)
            rows.append({"source": "redcoatz", "match_id": match_id, "played_at": m.get("played_at", ""), "year": year,
                         "map": m.get("map_name", ""), "game_build": rep.game_build, "faction_key": army.faction_key,
                         "army_corps_name": names.get(army.faction_key, ""), "player": player, "placed_by": how,
                         "team": team, "result": ctx.result(team), "rating_delta": "" if delta is None else f"{delta:g}",
                         "commander_key": army.commander_key or "", "unit_keys": " ".join(army.unit_keys),
                         "cards": info.get("cards", ""), "list_cost": info.get("list_cost", ""),
                         "rebate": info.get("rebate", ""), "final_cost": info.get("final_cost", ""),
                         "legal": int(not reason), "reason": reason})
    rows += clan_rows(parsed, matches, names, catalog, rosters, stats, by_year, started)
    with BUILDS_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    years = sorted(by_year)
    reasons = sorted({r for c in by_year.values() for r in c}, key=lambda r: (r != "legal today", r))
    L = ["# AC builds from the replays — extraction summary (analysis/veteran_builds.py extract)", "",
         f"Redcoatz replays {len(parsed)} ({len(matches)} match records); Clan Games replays in replays/clan_games/. " +
         ", ".join(f"{k}: {v}" for k, v in sorted(stats.items())) + ".", "",
         "Placed AC armies by year (Redcoatz) or season (clan, new battles only) and legality today:", ""]
    L += common.table(["reason", *years, "total"],
                      [[r, *(by_year[y][r] for y in years), sum(by_year[y][r] for y in years)] for r in reasons])
    (LOCAL / "extract_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    common.log(f"{len(rows)} placed AC armies, {sum(r['legal'] for r in rows)} legal today → {BUILDS_CSV}", started)


def clan_rows(parsed: dict, matches: dict, names: dict[str, str], catalog, rosters, stats: Counter,
              by_year: dict, started: float) -> list[dict]:
    """AC armies of the Clan Games replays that are not already on Redcoatz."""
    files = replays.clan_files()
    clan = replays.parsed_replays(files, log=lambda s: common.log(s, started), cache_name="parsed_clan")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    red_hash = {digest(path): m for m, path in replays.replay_files().items()}
    red_sig = {replays.battle_signature(r.armies): m for m, r in parsed.items() if r and r.armies}
    duplicate, season_dates = {}, defaultdict(list)
    for cid, rep in clan.items():
        m = red_hash.get(digest(files[cid])) or (red_sig.get(replays.battle_signature(rep.armies))
                                                  if rep and rep.armies else None)
        if m:
            duplicate[cid] = m
            season_dates[season_of(cid)].append(matches.get(m, {}).get("played_at", ""))
    season_mid = {s: sorted(v)[len(v) // 2] for s, v in season_dates.items() if v}
    corps_names = set(names.values())
    rows = []
    for cid, rep in clan.items():
        if cid in duplicate:
            stats["clan replays already on Redcoatz (same file or battle)"] += 1
            continue
        if rep is None or not rep.armies:
            stats["clan replays unreadable"] += 1
            continue
        stats["clan replays new"] += 1
        label = "clan S" + season_of(cid).split("_")[-1]
        for army in rep.armies:
            if "_ac_" not in army.faction_key:
                continue
            stats["clan AC armies (new battles)"] += 1
            player = army.player.strip()
            if not player or player in corps_names or player.startswith("CPU ") or player in replays.AI_NAMES:
                stats["clan AC armies without a readable player"] += 1
                continue
            reason, info = legality(army.faction_key, army.commander_key, army.unit_keys, catalog, rosters)
            by_year[label][reason or "legal today"] += 1
            rows.append({"source": "clan", "match_id": cid, "played_at": season_mid.get(season_of(cid), ""),
                         "year": label, "map": "", "game_build": rep.game_build, "faction_key": army.faction_key,
                         "army_corps_name": names.get(army.faction_key, ""), "player": player,
                         "placed_by": "replay (clan games)", "team": "", "result": "", "rating_delta": "",
                         "commander_key": army.commander_key or "", "unit_keys": " ".join(army.unit_keys),
                         "cards": info.get("cards", ""), "list_cost": info.get("list_cost", ""),
                         "rebate": info.get("rebate", ""), "final_cost": info.get("final_cost", ""),
                         "legal": int(not reason), "reason": reason})
    return rows


def season_of(clan_id: str) -> str:
    return clan_id.split(":", 1)[1].split("/", 1)[0]


# --- elite candidates ------------------------------------------------------------------------------

CLAN_TAG = re.compile(r"^\s*[\[\(\{<|][^\]\)\}>|]{1,8}[\]\)\}>|]\s*|\s*[\[\(\{<|][^\]\)\}>|]{1,8}[\]\)\}>|]\s*$")


def name_key(name: str) -> str:
    """A player name without clan tags, case or spacing: groups probable variants of one name."""
    return re.sub(r"[\s_.\-]+", "", CLAN_TAG.sub("", name)).casefold()


def ladder_ratings(path: Path = LOCAL / "rankings.json") -> dict[str, tuple[float, int | None]]:
    """name → (rating, rank) from the site's /v1/rankings ({"players": [{name, rating, rank, …}],
    "scope", "updated_at"}: the overall ladder, every game mode), or {} when not fetched."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = (data.get("players") or data.get("rankings") or []) if isinstance(data, dict) else data
    out = {}
    for r in rows if isinstance(rows, list) else []:
        name = r.get("name") or r.get("player")
        if name and r.get("rating") is not None:
            out[name] = (float(r["rating"]), r.get("rank"))
    return out


def candidates(started: float) -> None:
    with BUILDS_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    matches = replays.load_matches()
    delta_sum, games_all = Counter(), Counter()              # every rated game, AC or not
    for m in matches.values():
        for p, d in (m.get("rating_delta") or {}).items():
            if d is not None:
                delta_sum[p] += float(d)
                games_all[p] += 1
    ladder = ladder_ratings()
    per = defaultdict(lambda: {"ac": 0, "clan": 0, "legal": 0, "win": 0, "loss": 0, "draw": 0, "last": "",
                               "corps": set()})
    for r in rows:
        p = per[r["player"]]
        p["ac"] += 1
        p["clan"] += r.get("source") == "clan"
        p["legal"] += int(r["legal"])
        if r["result"] in ("win", "loss", "draw"):
            p[r["result"]] += 1
        p["last"] = max(p["last"], r["played_at"])
        p["corps"].add(r["faction_key"])
    variants = defaultdict(set)
    for name in per:
        variants[name_key(name)].add(name)
    out = []
    for name, p in per.items():
        rating, rank = ladder.get(name, (None, None))
        decided = p["win"] + p["loss"]
        out.append({"player": name, "ladder_rating": "" if rating is None else f"{rating:.0f}",
                    "ladder_rank": rank if rank is not None else "",
                    "rating_change_sum": f"{delta_sum[name]:+.0f}", "rated_games": games_all[name],
                    "ac_appearances": p["ac"], "ac_redcoatz": p["ac"] - p["clan"], "ac_clan": p["clan"],
                    "ac_legal_today": p["legal"], "ac_wins": p["win"],
                    "ac_losses": p["loss"], "ac_win_rate": f"{p['win'] / decided:.2f}" if decided else "",
                    "distinct_corps": len(p["corps"]), "last_game": p["last"][:10],
                    "name_variants": " | ".join(sorted(variants[name_key(name)] - {name}))})
    out.sort(key=lambda r: (-(float(r["ladder_rating"]) if r["ladder_rating"] else -1e9),
                            -float(r["rating_change_sum"]), -r["ac_legal_today"]))
    path = LOCAL / "candidates.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    common.log(f"{len(out)} AC players → {path} (ladder ratings: {'yes' if ladder else 'no, rating-change sums'})",
               started)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("extract", "candidates"))
    args = parser.parse_args()
    started = time.time()
    extract(started) if args.step == "extract" else candidates(started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
