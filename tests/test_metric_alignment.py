"""Regression tests for unified baseline metric accounting."""

from __future__ import annotations

import py_compile
import unittest
from pathlib import Path


class MetricAlignmentTest(unittest.TestCase):
    """Lock down the shared environment and metric-surface invariants."""

    def test_env_chengdu_compiles_cleanly(self) -> None:
        """`env/chengdu.py` should compile without merge-conflict markers."""

        source = Path(__file__).resolve().parents[1] / "env" / "chengdu.py"
        py_compile.compile(str(source), doraise=True)


if __name__ == "__main__":
    unittest.main()
