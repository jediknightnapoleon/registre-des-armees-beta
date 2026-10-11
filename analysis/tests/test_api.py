"""The analysis scripts' contract with each other: importing a script changes no other module's
settings (ac_pricing used to widen unit_pricing's κ grid for every importer), and the names other
scripts use from unit_pricing keep resolving."""

from __future__ import annotations

import subprocess
import sys
import unittest

from support import ANALYSIS

SNAPSHOT = """
import sys
sys.path.insert(0, {analysis!r})
import common, unit_pricing as up, commander_model as cm
def snap():
    return repr((sorted(up.FCLASS_GRID.items()), up.WORKERS, up.SIZE_WEIGHTING, up.P_GRID, up.POWER_GRID,
                 up.MAX_PASSES, up.FINE_PASSES, up.MAX_ITER, up.TOLERANCE, up.ARTILLERY_CAL, str(up.DATA_CSV),
                 up.in_scope.__qualname__, up.side_of.__qualname__, sorted(common.AC_STUDY_BANDS.items()),
                 sorted(common.SB_BANDS.items()), str(cm.PAIRS)))
before = snap()
import ac_pricing, class_structure, cost_effective_builds, team_values, ac_builds, team_search  # noqa
import export_optimiser_values, export_team_builds, size_weighting, size_weighting_builds  # noqa
print("SAME" if snap() == before else "CHANGED:\\n" + before + "\\n" + snap())
"""

# Names other scripts read from unit_pricing (grep `up\\.<name>` over analysis/); they must keep resolving.
PUBLIC = """ROOT log table Unit Spec REF_RATING design_for CVRun num data_for load_ratings fit_on size_of DATA_CSV
slice_units Design predict_total load ARMS joint_fclass_spec make_slice in_scope side_of SliceData Slice fclass_cv
cv_spec WORKERS FCLASS_MAKERS FCLASS_FORM with_powers staff_power_fit parallel_map PowerResult N_SPLITS FCLASS_GRID
staff_power_price size_weights size_band_labels metrics make_staff_slice kish_ess Staff OUT_DIR spline_knots pm
nested_powers natural_spline_basis fclass_multiplier f2 f1 StaffRun SPEED_TAG_RE SIZE_WEIGHT_BANDS SIZE_WEIGHTING
MULT_CATEGORICAL FclassResult FCLASS_LABEL DEV_CORPS PriceModel SplitPlan StaffSlice""".split()
PICKLED = ("Unit", "Staff", "Spec", "SplitPlan", "PriceModel", "CVRun", "Slice", "FclassResult", "StaffRun", "StaffSlice")


class ApiTests(unittest.TestCase):
    def test_importing_scripts_changes_no_shared_setting(self) -> None:
        out = subprocess.run([sys.executable, "-c", SNAPSHOT.format(analysis=str(ANALYSIS))],
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        self.assertEqual(out.strip(), "SAME", out)

    def test_public_names_resolve(self) -> None:
        import unit_pricing as up
        missing = [name for name in PUBLIC if not hasattr(up, name)]
        self.assertEqual(missing, [])

    def test_pickled_classes_keep_their_module_path(self) -> None:
        # Checkpoints in analysis/.cache/ pickle these as unit_pricing.<Name>; moving one breaks them.
        import unit_pricing as up
        for name in PICKLED:
            cls = getattr(up, name)
            self.assertEqual((cls.__module__, cls.__qualname__), ("unit_pricing", name))


if __name__ == "__main__":
    unittest.main()
