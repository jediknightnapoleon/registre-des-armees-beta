"""The ladder and clan replays for the analyses: match records, parsed armies (cached), and each
army's team, player and result.

Source: tools/download_redcoatz_replays.py → replays/redcoatz/ (gitignored): `matches.jsonl` (the
site's match records: teams, players, outcome, rating changes) and one `<played_at>_<match id>.replay`
per match. Each replay is read with the repo's own parser (tools/replay_parser.py, the port of
web/src/domain/replay.ts): every army's corps key (= faction_key), the key in its commander slot and
its unit keys in the order the replay lists them.

Clan Games replays (Clan League, seasons 8–10; data/clan_games_replays/ on the maintainer's main branch,
extracted to replays/clan_games/<season>/, gitignored) have no match record: no teams, results, rating
changes or dates — only what the replay itself holds. Many are also on Redcoatz; battle_signature() finds
those (the same armies, players and units), so a battle is never counted twice.

Parsed replays are cached in analysis/.cache/veteran/parsed.pkl (parsed_clan.pkl) and only new files are parsed on
the next run (about 0.04 s per replay). Nothing replay-derived is committed: callers write row-level
results under analysis/local/ (gitignored).

Joining an army to the match record: by the player name the replay carries. The parser sometimes
reads the corps name, or nothing, as the player; then the site's own army list is used — the army's
name, when it appears on exactly one team (as analysis/experiments/replay_unit_usage.py does).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checkpoints as ckpt  # noqa: E402
import common  # noqa: E402

sys.path.insert(0, str(common.ROOT))
from tools.replay_parser import parse  # noqa: E402

REPLAYS = common.ROOT / "replays" / "redcoatz"
CLAN = common.ROOT / "replays" / "clan_games"
AI_NAMES = ("AI Bot",)
SAVE_EVERY = 200          # parsed replays between checkpoint writes


@dataclass(frozen=True)
class ParsedArmy:
    faction_key: str
    player: str
    commander_key: str | None          # the commander slot: a staff general, or a combat general in command
    unit_keys: tuple[str, ...]         # the rest of the army, in the replay's order


@dataclass(frozen=True)
class ParsedReplay:
    match_id: str
    game_build: str
    armies: tuple[ParsedArmy, ...]


def load_matches(path: Path = REPLAYS / "matches.jsonl") -> dict[str, dict]:
    """The site's match records by match id."""
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            out[m["id"]] = m
    return out


def replay_files(folder: Path = REPLAYS) -> dict[str, Path]:
    """match id → .replay file (named <played_at>_<match id>.replay)."""
    return {p.stem.split("_", 1)[1]: p for p in sorted(folder.glob("*.replay"))}


def clan_files(folder: Path = CLAN) -> dict[str, Path]:
    """"clan:<season>/<file name>" → .replay file (a few names end in a stray quote: .replay")."""
    return {f"clan:{p.parent.name}/{p.name}": p for p in sorted(folder.rglob("*.replay*"))}


def battle_signature(armies: tuple[ParsedArmy, ...]) -> tuple:
    """The same battle saved twice (or uploaded to two places) has the same armies, players and units."""
    return tuple(sorted((a.faction_key, a.player, a.unit_keys) for a in armies))


def parsed_replays(files: dict[str, Path] | None = None, fresh: bool = False,
                   log=None, cache_name: str = "parsed") -> dict[str, ParsedReplay | None]:
    """Every replay parsed (None when it fails to parse), from the cache plus the new files."""
    files = replay_files() if files is None else files
    path = ckpt.veteran(cache_name)
    cache: dict[str, ParsedReplay | None] = {} if fresh or not path.exists() else common.load_pickle(path)
    todo = [m for m in files if m not in cache]
    for i, match_id in enumerate(todo, 1):
        try:
            b = parse(files[match_id].read_bytes())
            cache[match_id] = ParsedReplay(match_id, b.game_build, tuple(
                ParsedArmy(a.army_key, a.player, a.staff_key, tuple(u.key for u in a.units)) for a in b.armies))
        except Exception:                                    # noqa: BLE001 — a bad file must not stop the run
            cache[match_id] = None
        if i % SAVE_EVERY == 0 or i == len(todo):
            common.save_pickle(path, cache)
            if log:
                log(f"parsed {i} / {len(todo)} new replays")
    return {m: cache[m] for m in files}


@dataclass
class MatchContext:
    """One match record, ready to place armies on teams and read their results."""
    match: dict
    team_of: dict[str, int] = field(default_factory=dict)
    ai: set[str] = field(default_factory=set)
    label_team: dict[str, set[int]] = field(default_factory=dict)
    label_player: dict[str, str] = field(default_factory=dict)

    @classmethod
    def of(cls, match: dict) -> "MatchContext":
        ctx = cls(match)
        for t in match.get("teams", []):
            for p in t.get("players", []):
                ctx.team_of[p] = t["team"]
            for a in t.get("armies") or []:
                if a.get("is_ai") or a.get("player") in AI_NAMES:
                    ctx.ai.add(a.get("player"))
                if a.get("label"):
                    ctx.label_team.setdefault(a["label"], set()).add(t["team"])
                    ctx.label_player[a["label"]] = a.get("player", "")
        return ctx

    def is_ai(self, player: str) -> bool:
        return player in self.ai or player.startswith("CPU ") or player in AI_NAMES

    def place(self, player: str, army_name: str) -> tuple[int, str, str] | None:
        """(team, player, how) for an army, or None when it can't be placed on one team."""
        if player in self.team_of:
            return self.team_of[player], player, "player"
        teams = self.label_team.get(army_name, set())
        if len(teams) == 1:
            return next(iter(teams)), self.label_player.get(army_name) or player, "army name"
        return None

    def result(self, team: int) -> str:
        outcome = self.match.get("outcome", "")
        if outcome == "draw":
            return "draw"
        if outcome.startswith("team ") and outcome.endswith(" wins"):
            return "win" if int(outcome.split()[1]) == team else "loss"
        return "unknown"

    def rating_delta(self, player: str) -> float | None:
        v = (self.match.get("rating_delta") or {}).get(player)
        return None if v is None else float(v)
