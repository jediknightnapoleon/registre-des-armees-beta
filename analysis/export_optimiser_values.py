"""Export the cost-effective-builds valuation for the app's in-app optimiser.

The app's "Optimise" panel (web/src/state/optimiser.ts) solves the same integer
programme as analysis/cost_effective_builds.py solve(), in the browser with HiGHS.
It cannot run the pricing models, so this script ships what it needs as data:

- data/generated/ntw3_optimiser_values.csv — every unit and commander card of
  every ToW / Custom army with its normative value in both size versions:
  value_quality = full size harmonisation ("Quality" in the app: the size bias is
  removed), value_quantity = noise-only harmonisation ("Quantity": the size
  discount is kept). Staff generals are not listed: the app values them itself
  from their stars (T3) plus the command correction, which depends on the build.
- data/generated/ntw3_optimiser_params.json — the staff-general rule T3 (b, q),
  the command correction (m_ref, λ per version, σ, melee bonus) and the standard
  general's melee attack that marks a fighting bodyguard.

tools/build_web_data.py merges both into the faction JSON. Both files are
committed (data/generated is committed; rebuilding needs the local
analysis/.cache checkpoints).

Parity with the Python optimiser (two stages, because the app-side fixture needs
the cards exactly as the app sees them, which only exist after the pipeline):

1. this script also writes analysis/output/optimiser_parity_python.json — Python's
   max-value and four-corps builds for a few armies, in both versions;
2. after `python tools/build_web_data.py`, `--fixture` joins those builds with the
   generated faction files into web/src/state/__fixtures__/optimiser-parity.json,
   which web/src/state/optimiser.parity.test.ts checks the TypeScript optimiser
   against.

    py -3.13 analysis/export_optimiser_values.py              # values, params, Python builds
    py -3.13 tools/build_web_data.py                          # → web/public/data (with values)
    py -3.13 analysis/export_optimiser_values.py --fixture    # → the app's parity fixture
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cost_effective_builds as ceb  # noqa: E402
import unit_pricing as up  # noqa: E402

GENERATED = up.ROOT / "data" / "generated"
VALUES_CSV = GENERATED / "ntw3_optimiser_values.csv"
PARAMS_JSON = GENERATED / "ntw3_optimiser_params.json"
PYTHON_BUILDS = ceb.OUT / "optimiser_parity_python.json"
FACTIONS = up.ROOT / "web" / "public" / "data" / "factions"
FIXTURE = up.ROOT / "web" / "src" / "state" / "__fixtures__" / "optimiser-parity.json"
# App mode → size version of cost_effective_builds.py.
MODES = {"quality": "full", "quantity": "noise"}
# Parity armies: a ToW army with a cheap 2★ anchor general, a ToW army anchored on Murat (C4),
# and a Custom army (no source corps).
PARITY_ARMIES = ("ntw3_tow_b06_x8_009", "ntw3_tow_c14_x8_030", "ntw3_hre")
# Card fields the optimiser reads (web/src/state/optimiser.ts); the fixture keeps only these.
FIXTURE_FIELDS = ("unitKey", "factionKey", "unitClass", "underlyingUnitClass", "cost", "menRaw", "speedCode",
                  "commandStars", "isGeneral", "isCommanderVariant", "generalKind", "cap", "groupCap",
                  "capGroupKey", "baseUnitKey", "stats", "optimiserValue")


def export(started: float) -> None:
    melee = ceb.bodyguard_melee_bonus()
    values: dict[tuple[str, str], dict[str, float]] = {}
    python_builds: dict[str, dict] = {}
    for mode, version in MODES.items():
        by_faction, staff_of, top_star, army_of = ceb.load_cards(started, size_mode=version)
        for f, cards in by_faction.items():
            for c in cards:
                values.setdefault((f, c["key"]), {})[mode] = c["value"]
        command = ceb.Command(ceb.COMMAND_LAMBDA[version], ceb.SPEED_BONUS, melee)
        for f in PARITY_ARMIES:
            for variant, chosen, general in ceb.army_builds(by_faction[f], staff_of[f], top_star[f], command,
                                                            ("max value", "four corps")):
                python_builds.setdefault(f, {})[f"{mode}/{variant}"] = {
                    "objective": sum(c["value"] * k for c, k in chosen) + general["value"],
                    "cost": sum(c["cost"] * k for c, k in chosen) + general["cost"],
                    "staff": general["key"],
                    "units": sorted([c["key"], k] for c, k in chosen)}
        up.log(f"{mode} ({version}) values for {len(by_faction)} armies", started)
    missing = [k for k, v in values.items() if set(v) != set(MODES)]
    if missing:
        raise SystemExit(f"{len(missing)} cards lack a value in one version, e.g. {missing[:3]}")

    builder_keys = set()
    with (GENERATED / "ntw3_army_builder_units.csv").open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            builder_keys.add((r["faction_key"], r["unit_key"]))
    unknown = [k for k in values if k not in builder_keys]
    if unknown:
        raise SystemExit(f"{len(unknown)} valued cards are not in the builder CSV, e.g. {unknown[:3]}")

    with VALUES_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["faction_key", "unit_key", "value_quality", "value_quantity"])
        for (f, k), v in sorted(values.items()):
            w.writerow([f, k, f"{v['quality']:.6f}", f"{v['quantity']:.6f}"])
    b, q = ceb.staff_value_rule()
    PARAMS_JSON.write_text(json.dumps({
        "t3_b": b, "t3_q": q, "m_ref": ceb.M_REF,
        "lambda": {mode: ceb.COMMAND_LAMBDA[version] for mode, version in MODES.items()},
        "speed_bonus": ceb.SPEED_BONUS, "melee_bonus": melee,
        "standard_general_melee": ceb.STANDARD_GENERAL_MELEE,
        "generated": date.today().isoformat(),
        "source": "analysis/export_optimiser_values.py (cost_effective_builds.py valuation)"}, indent=2) + "\n",
        encoding="utf-8")
    PYTHON_BUILDS.write_text(json.dumps(python_builds, indent=2) + "\n", encoding="utf-8")
    armies = {f for f, _ in values}
    up.log(f"{len(values)} cards in {len(armies)} armies → {VALUES_CSV.relative_to(up.ROOT)}; "
           f"params → {PARAMS_JSON.relative_to(up.ROOT)}; Python builds → {PYTHON_BUILDS.relative_to(up.ROOT)}",
           started)


def fixture(started: float) -> None:
    """Join Python's builds with the generated faction files into the app's parity fixture."""
    if not PYTHON_BUILDS.exists():
        raise SystemExit(f"run without --fixture first ({PYTHON_BUILDS.relative_to(up.ROOT)} is missing)")
    python_builds = json.loads(PYTHON_BUILDS.read_text(encoding="utf-8"))
    armies = {}
    for f, builds in python_builds.items():
        path = FACTIONS / f"{f}.json"
        if not path.exists():
            raise SystemExit(f"{path} is missing: run tools/build_web_data.py first")
        roster = json.loads(path.read_text(encoding="utf-8"))
        if "optimiser" not in roster:
            raise SystemExit(f"{path} has no optimiser params: rebuild it after exporting the values")
        armies[f] = {"optimiser": roster["optimiser"],
                     "cards": [{k: c[k] for k in FIXTURE_FIELDS if k in c} for c in roster["cards"]],
                     "python": builds}
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps({"generated": date.today().isoformat(),
                                   "source": "analysis/export_optimiser_values.py --fixture",
                                   "armies": armies}, separators=(",", ":"), ensure_ascii=False) + "\n",
                       encoding="utf-8")
    up.log(f"parity fixture for {len(armies)} armies → {FIXTURE.relative_to(up.ROOT)}", started)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fixture", action="store_true",
                        help="only build the app's parity fixture (after tools/build_web_data.py)")
    args = parser.parse_args()
    started = time.time()
    fixture(started) if args.fixture else export(started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
