"""Regression tests for the CAPA utility-module slimming refactor."""

from __future__ import annotations

from pathlib import Path
import unittest

import capa.utility as utility


REPO_ROOT = Path(__file__).resolve().parents[1]


class CAPAUtilitySlimmingTests(unittest.TestCase):
    """Verify utility helpers are consolidated into `capa.utility`."""

    def test_utility_exports_merged_tool_helpers(self) -> None:
        """`capa.utility` should expose the merged helper surface."""

        self.assertIsNotNone(utility.InsertionCache)
        self.assertIsNotNone(utility.GeoIndex)
        self.assertIsNotNone(utility.TimingAccumulator)
        self.assertIsNotNone(utility.TimedTravelModel)
        self.assertIsNotNone(utility.BatchDistanceMatrix)
        self.assertIsNotNone(utility.PersistentDirectedDistanceCache)
        self.assertIsNotNone(utility.DistanceMatrixTravelModel)

    def test_old_tool_only_modules_are_removed(self) -> None:
        """Tool-only modules should disappear after the slimming refactor."""

        self.assertFalse((REPO_ROOT / "capa" / "cache.py").exists())
        self.assertFalse((REPO_ROOT / "capa" / "geo.py").exists())
        self.assertFalse((REPO_ROOT / "capa" / "timing.py").exists())
        self.assertFalse((REPO_ROOT / "capa" / "batch_distance.py").exists())
        self.assertFalse((REPO_ROOT / "capa" / "travel.py").exists())
        self.assertFalse((REPO_ROOT / "capa" / "revenue.py").exists())

    def test_constraints_module_is_kept_as_a_separate_boundary(self) -> None:
        """The agreed boundary keeps constraints as an explicit standalone module."""

        self.assertTrue((REPO_ROOT / "capa" / "constraints.py").exists())


if __name__ == "__main__":
    unittest.main()
