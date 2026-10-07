"""Download every match replay from the Redcoatz NTW3 ladder (https://redcoatz.com).

The site's public API (the one its own pages use):
  GET /v1/matches?limit=100&offset=N&sort=recent  -> {"total", "matches": [...]}, at most 100 per page
  GET /v1/replays/<match id>                       -> the .replay file (application/octet-stream)

Each match record already carries the site's parsed armies, units, map, outcome and
rating changes; they are saved alongside the replays as matches.jsonl, one JSON
object per line.

Polite by design: one request at a time with a pause between requests, a clear
User-Agent, and resumable — files already on disk are skipped, and partial
downloads are written to *.part and only renamed when complete. Re-running it
later fetches only the new matches.

Output (gitignored, ~0.5 MB per replay, about 1–1.5 GB in total):
  replays/redcoatz/matches.jsonl                       every match record
  replays/redcoatz/<played_at>_<match id>.replay       one file per replay
  replays/redcoatz/missing.txt                         matches whose replay could not be fetched

    python tools/download_redcoatz_replays.py [--delay 1.0] [--limit N] [--metadata-only]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://redcoatz.com"
OUT = Path(__file__).resolve().parent.parent / "replays" / "redcoatz"
PAGE = 100                    # the API's maximum page size
USER_AGENT = "registre-des-armees replay archiver (personal NTW3 analysis; one request at a time)"


def get(url: str, timeout: float = 60.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""


def fetch_matches(delay: float) -> list[dict]:
    matches, offset, total = [], 0, None
    while total is None or offset < total:
        status, body = get(f"{BASE}/v1/matches?limit={PAGE}&offset={offset}&sort=recent")
        if status != 200:
            raise SystemExit(f"match list failed at offset {offset}: HTTP {status}")
        page = json.loads(body)
        total = page["total"]
        matches += page["matches"]
        print(f"  match list: {len(matches)} / {total}", flush=True)
        if not page["matches"]:
            break
        offset += PAGE
        time.sleep(delay)
    return matches


def filename(match: dict) -> str:
    stamp = re.sub(r"[^0-9T]", "", (match.get("played_at") or "")[:19]) or "unknown"
    return f"{stamp}_{match['id']}.replay"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds to wait between requests (default 1)")
    parser.add_argument("--limit", type=int, default=None, help="download at most N replays this run")
    parser.add_argument("--metadata-only", action="store_true", help="only refresh matches.jsonl")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    print("fetching the match list …", flush=True)
    matches = fetch_matches(args.delay)
    with (OUT / "matches.jsonl").open("w", encoding="utf-8") as fh:
        for m in matches:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"{len(matches)} matches → {OUT / 'matches.jsonl'}", flush=True)
    if args.metadata_only:
        return 0

    todo = [m for m in matches if not (OUT / filename(m)).exists()]
    on_disk = len(matches) - len(todo)
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{on_disk} replays already on disk; downloading {len(todo)} …", flush=True)
    missing, done, size = [], 0, 0
    for i, m in enumerate(todo, 1):
        status, body = get(f"{BASE}/v1/replays/{m['id']}")
        if status == 200 and body:
            part = OUT / (filename(m) + ".part")
            part.write_bytes(body)
            part.replace(OUT / filename(m))
            done += 1
            size += len(body)
        else:
            missing.append(f"{m['id']}\tHTTP {status}")
        if i % 25 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}: {done} saved ({size / 1e6:.0f} MB), {len(missing)} missing", flush=True)
        time.sleep(args.delay)
    if missing:
        with (OUT / "missing.txt").open("a", encoding="utf-8") as fh:
            fh.write("\n".join(missing) + "\n")
    print(f"done: {done} new replays ({size / 1e6:.0f} MB), {len(missing)} missing → {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
