"""Regression test for importing the Chengdu graph utilities."""

import subprocess
import unittest
from pathlib import Path


class GraphUtilsImportTests(unittest.TestCase):
    """Ensure the Chengdu graph parser completes without index errors."""

    def test_graphutils_import_succeeds(self) -> None:
        """Importing `GraphUtils_ChengDu` should finish successfully in a fresh interpreter."""
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["python3", "-c", "import GraphUtils_ChengDu as g; print(len(g.s.nMap), getattr(g.s, 'edgeNumber', None))"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        final_line = result.stdout.strip().splitlines()[-1]
        node_count = int(final_line.split()[0])
        self.assertGreater(node_count, 10000, msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
