import json
import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.monitor_split import collect_split_progress
from experiments.progress import read_point_progress


class ProgressIOTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="progress_io_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_read_point_progress_returns_none_for_empty_file(self) -> None:
        progress_path = self.temp_root / "progress.json"
        progress_path.write_text("", encoding="utf-8")

        self.assertIsNone(read_point_progress(progress_path))

    def test_collect_split_progress_tolerates_empty_point_progress_file(self) -> None:
        tmp_root = self.temp_root / "split_tmp"
        point_output_dir = tmp_root / "point_1000"
        point_output_dir.mkdir(parents=True)
        (point_output_dir / "progress.json").write_text("", encoding="utf-8")
        (tmp_root / "split_status.json").write_text(
            json.dumps(
                {
                    "state": "running",
                    "experiment_label": "Exp-1",
                    "axis_name": "num_parcels",
                    "updated_at": 0.0,
                    "points": {
                        "1000": {
                            "pid": 123,
                            "returncode": None,
                            "output_dir": str(point_output_dir),
                            "total_algorithms": 6,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        snapshot = collect_split_progress(tmp_root)

        self.assertEqual(snapshot["state"], "running")
        self.assertIn("1000", snapshot["points"])
        self.assertEqual(snapshot["points"]["1000"]["state"], "running")
        self.assertEqual(snapshot["points"]["1000"]["completed_algorithms"], [])


if __name__ == "__main__":
    unittest.main()
