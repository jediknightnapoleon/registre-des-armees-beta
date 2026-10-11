"""The committed outputs still follow from the checkpoints: values recomputed by today's code equal the
CSVs the app's data was exported from, and the AC optimiser reproduces its summary rows."""

from __future__ import annotations

import csv
import unittest

from support import ANALYSIS, HAS_CACHE

TEAMS = ANALYSIS / "output" / "teams"


def rows(name: str) -> list[dict]:
    with open(TEAMS / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@unittest.skipUnless(HAS_CACHE, "needs the local checkpoints in analysis/.cache/")
class OutputTests(unittest.TestCase):
    def test_ac_unit_values(self) -> None:
        import team_values as tv
        import unit_pricing as up
        stored = {(r["faction_key"], r["unit_key"]): r for r in rows("values_ac.csv") if r["kind"] == "unit"}
        for arm in up.ARMS:
            sl = tv.slice_of("ac", arm)
            raw, _ = tv.v4_raw_and_oof("ac", arm, sl.units)
            sb, _ = tv.sb_values("ac", arm, sl.units, sl.plan.folds)
            with self.subTest(arm=arm):
                for k, v in raw.items():
                    self.assertEqual(f"{v:.3f}", stored[k]["value_raw"], k)
                for k, v in sb.items():
                    self.assertEqual(f"{v:.3f}", stored[k]["value_sb"], k)

    def test_tow_size_band_values(self) -> None:
        import team_values as tv
        import unit_pricing as up
        stored = {(r["faction_key"], r["unit_key"]): r["value_sb"] for r in rows("values_tow_sb.csv") if r["kind"] == "unit"}
        for arm in up.ARMS:
            sl = tv.slice_of("tow", arm)
            sb, _ = tv.sb_values("tow", arm, sl.units, sl.plan.folds)
            with self.subTest(arm=arm):
                for k, v in sb.items():
                    self.assertEqual(f"{v:.3f}", stored[k], k)

    def test_ac_builds(self) -> None:
        import ac_builds as ab
        import cost_effective_builds as ceb
        catalog, values, extra, _, _, t3 = ab.load_inputs()
        command = ceb.Command(ab.LAMBDA["sb"], ceb.SPEED_BONUS, ceb.bodyguard_melee_bonus())
        summary = {r["faction_key"]: r for r in rows("ac_build_summary_sb.csv")}
        for faction in ("ntw3_ac_a11_x5_117", "ntw3_ac_a03_x5_080", "ntw3_ac_a08_x5_242"):
            res = ab.solve_corps(faction, catalog, values["sb"], extra, t3, command, 31)
            with self.subTest(corps=faction):
                self.assertEqual(f"{res['value']:.1f}", summary[faction]["value"])
                self.assertEqual(str(res["price"].final_cost), summary[faction]["final_cost"])
                self.assertEqual(str(res["price"].base_cost), summary[faction]["list_cost"])
                self.assertEqual(res["cuts"], 0)


if __name__ == "__main__":
    unittest.main()
